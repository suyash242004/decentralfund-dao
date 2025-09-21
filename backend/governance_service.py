"""
DecentralFund DAO - Governance Service
Handles DAO governance, voting mechanisms, and proposal management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from decimal import Decimal
import json
import hashlib

from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from backend.connection import get_db_session
from backend.models_comprehensive import (
    User, Proposal, Vote, Transaction, TransactionType, 
    ProposalType, ProposalStatus, SystemConfig
)
from backend.blockchain_service import BlockchainService
from backend.ai_service import AIService

logger = logging.getLogger(__name__)

@dataclass
class ProposalCreationRequest:
    """Request to create a new governance proposal"""
    creator_id: str
    title: str
    description: str
    proposal_type: ProposalType
    voting_options: List[str]
    voting_duration_days: int = 7
    minimum_quorum: int = 1000
    category: str = "general"
    tags: List[str] = None
    ipfs_hash: Optional[str] = None

@dataclass
class VotingResult:
    """Result of a voting process"""
    proposal_id: str
    total_votes: int
    total_voting_power: float
    winning_option: str
    option_results: Dict[str, Dict[str, Any]]
    quorum_met: bool
    participation_rate: float

@dataclass
class DelegationRequest:
    """Request to delegate voting power"""
    delegator_id: str
    delegate_id: str
    amount: float
    duration_days: int = 90

class GovernanceService:
    """Service for managing DAO governance and voting"""
    
    def __init__(self, blockchain_service: Optional[BlockchainService] = None):
        self.blockchain = blockchain_service
        self.ai_service = AIService()
        
        # Governance configuration
        self.min_proposal_tokens = 100  # Minimum tokens to create proposal
        self.max_voting_duration_days = 30
        self.min_voting_duration_days = 1
        self.default_quorum_percentage = 0.1  # 10% of total tokens
        self.delegation_fee_percentage = 0.01  # 1% fee for delegation
        
        # Voting power calculation (quadratic voting)
        self.voting_power_exponent = 0.5  # sqrt(token_balance)
        
        logger.info("🗳️ Governance Service initialized")
    
    async def create_proposal(self, request: ProposalCreationRequest) -> Dict[str, Any]:
        """Create a new governance proposal"""
        try:
            async with get_db_session() as session:
                # Verify creator has sufficient tokens
                creator_result = await session.execute(
                    select(User).where(User.id == request.creator_id)
                )
                creator = creator_result.scalar_one_or_none()
                
                if not creator:
                    return {"success": False, "error": "Creator not found"}
                
                if creator.governance_tokens < self.min_proposal_tokens:
                    return {
                        "success": False,
                        "error": f"Minimum {self.min_proposal_tokens} governance tokens required"
                    }
                
                # Validate voting duration
                if not (self.min_voting_duration_days <= request.voting_duration_days <= self.max_voting_duration_days):
                    return {
                        "success": False,
                        "error": f"Voting duration must be between {self.min_voting_duration_days} and {self.max_voting_duration_days} days"
                    }
                
                # Validate voting options
                if len(request.voting_options) < 2:
                    return {"success": False, "error": "At least 2 voting options required"}
                
                # Calculate voting dates
                voting_start = datetime.utcnow()
                voting_end = voting_start + timedelta(days=request.voting_duration_days)
                
                # Create proposal
                proposal = Proposal(
                    creator_id=request.creator_id,
                    title=request.title,
                    description=request.description,
                    proposal_type=request.proposal_type,
                    voting_start_date=voting_start,
                    voting_end_date=voting_end,
                    minimum_quorum=request.minimum_quorum,
                    voting_options=request.voting_options,
                    status=ProposalStatus.ACTIVE,
                    category=request.category,
                    tags=request.tags or [],
                    ipfs_hash=request.ipfs_hash
                )
                
                session.add(proposal)
                await session.commit()
                
                # Create blockchain proposal if blockchain service available
                if self.blockchain:
                    try:
                        blockchain_result = await self.blockchain.create_proposal(
                            creator_address=creator.wallet_address,
                            title=request.title,
                            description=request.description,
                            options=request.voting_options,
                            voting_duration_days=request.voting_duration_days
                        )
                        
                        if blockchain_result.success:
                            proposal.onchain_proposal_id = blockchain_result.transaction_hash
                            await session.commit()
                    except Exception as e:
                        logger.warning(f"Blockchain proposal creation failed: {e}")
                
                logger.info(f"✅ Proposal created: {proposal.id} by {request.creator_id}")
                
                return {
                    "success": True,
                    "proposal_id": proposal.id,
                    "voting_start": voting_start.isoformat(),
                    "voting_end": voting_end.isoformat(),
                    "blockchain_tx": proposal.onchain_proposal_id
                }
                
        except Exception as e:
            logger.error(f"Error creating proposal: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def cast_vote(
        self,
        proposal_id: str,
        voter_id: str,
        selected_option: str,
        voting_power_to_use: Optional[float] = None
    ) -> Dict[str, Any]:
        """Cast a vote on a proposal"""
        try:
            async with get_db_session() as session:
                # Get proposal
                proposal_result = await session.execute(
                    select(Proposal).where(Proposal.id == proposal_id)
                )
                proposal = proposal_result.scalar_one_or_none()
                
                if not proposal:
                    return {"success": False, "error": "Proposal not found"}
                
                if proposal.status != ProposalStatus.ACTIVE:
                    return {"success": False, "error": "Proposal not active"}
                
                if datetime.utcnow() > proposal.voting_end_date:
                    return {"success": False, "error": "Voting period ended"}
                
                if selected_option not in proposal.voting_options:
                    return {"success": False, "error": "Invalid voting option"}
                
                # Get voter
                voter_result = await session.execute(
                    select(User).where(User.id == voter_id)
                )
                voter = voter_result.scalar_one_or_none()
                
                if not voter:
                    return {"success": False, "error": "Voter not found"}
                
                # Check if already voted
                existing_vote_result = await session.execute(
                    select(Vote).where(
                        and_(
                            Vote.proposal_id == proposal_id,
                            Vote.user_id == voter_id
                        )
                    )
                )
                if existing_vote_result.scalar_one_or_none():
                    return {"success": False, "error": "Already voted on this proposal"}
                
                # Calculate voting power
                if voting_power_to_use is None:
                    voting_power_to_use = voter.voting_power
                
                if voting_power_to_use > voter.voting_power:
                    return {"success": False, "error": "Insufficient voting power"}
                
                if voting_power_to_use <= 0:
                    return {"success": False, "error": "Must use some voting power"}
                
                # Create vote record
                vote = Vote(
                    proposal_id=proposal_id,
                    user_id=voter_id,
                    selected_option=selected_option,
                    voting_power_used=voting_power_to_use,
                    governance_tokens_staked=voter.governance_tokens,
                    transaction_hash=f"0x{hash(proposal_id + voter_id + selected_option)}"
                )
                
                session.add(vote)
                
                # Update proposal vote counts
                proposal.total_votes += 1
                proposal.total_voting_power += voting_power_to_use
                
                await session.commit()
                
                # Create blockchain vote if blockchain service available
                if self.blockchain:
                    try:
                        blockchain_result = await self.blockchain.cast_vote(
                            voter_address=voter.wallet_address,
                            proposal_id=int(proposal_id.split('-')[-1]) if '-' in proposal_id else 0,
                            option=proposal.voting_options.index(selected_option),
                            voting_power=voting_power_to_use
                        )
                        
                        if blockchain_result.success:
                            vote.transaction_hash = blockchain_result.transaction_hash
                            vote.block_number = blockchain_result.block_number
                            await session.commit()
                    except Exception as e:
                        logger.warning(f"Blockchain vote casting failed: {e}")
                
                logger.info(f"✅ Vote cast: {voter_id} voted '{selected_option}' on {proposal_id}")
                
                return {
                    "success": True,
                    "vote_id": vote.id,
                    "voting_power_used": voting_power_to_use,
                    "transaction_hash": vote.transaction_hash
                }
                
        except Exception as e:
            logger.error(f"Error casting vote: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def get_proposal_results(self, proposal_id: str) -> VotingResult:
        """Get voting results for a proposal"""
        try:
            async with get_db_session() as session:
                # Get proposal
                proposal_result = await session.execute(
                    select(Proposal).where(Proposal.id == proposal_id)
                )
                proposal = proposal_result.scalar_one_or_none()
                
                if not proposal:
                    return None
                
                # Get all votes
                votes_result = await session.execute(
                    select(Vote).where(Vote.proposal_id == proposal_id)
                )
                votes = votes_result.scalars().all()
                
                # Calculate results for each option
                option_results = {}
                for option in proposal.voting_options:
                    option_votes = [v for v in votes if v.selected_option == option]
                    total_votes = len(option_votes)
                    total_power = sum(v.voting_power_used for v in option_votes)
                    
                    option_results[option] = {
                        "votes": total_votes,
                        "voting_power": total_power,
                        "percentage": (total_power / proposal.total_voting_power * 100) if proposal.total_voting_power > 0 else 0
                    }
                
                # Find winning option
                winning_option = max(option_results.keys(), key=lambda x: option_results[x]["voting_power"])
                
                # Check quorum
                total_tokens = await self._get_total_governance_tokens()
                quorum_met = proposal.total_voting_power >= proposal.minimum_quorum
                
                # Calculate participation rate
                participation_rate = (proposal.total_voting_power / total_tokens * 100) if total_tokens > 0 else 0
                
                return VotingResult(
                    proposal_id=proposal_id,
                    total_votes=proposal.total_votes,
                    total_voting_power=proposal.total_voting_power,
                    winning_option=winning_option,
                    option_results=option_results,
                    quorum_met=quorum_met,
                    participation_rate=participation_rate
                )
                
        except Exception as e:
            logger.error(f"Error getting proposal results: {str(e)}")
            return None
    
    async def finalize_proposal(self, proposal_id: str) -> Dict[str, Any]:
        """Finalize a proposal after voting period"""
        try:
            async with get_db_session() as session:
                # Get proposal
                proposal_result = await session.execute(
                    select(Proposal).where(Proposal.id == proposal_id)
                )
                proposal = proposal_result.scalar_one_or_none()
                
                if not proposal:
                    return {"success": False, "error": "Proposal not found"}
                
                if proposal.status != ProposalStatus.ACTIVE:
                    return {"success": False, "error": "Proposal not active"}
                
                if datetime.utcnow() < proposal.voting_end_date:
                    return {"success": False, "error": "Voting period not ended"}
                
                # Get voting results
                results = await self.get_proposal_results(proposal_id)
                
                if not results:
                    return {"success": False, "error": "Could not get voting results"}
                
                # Determine proposal status
                if results.quorum_met:
                    proposal.status = ProposalStatus.PASSED
                    proposal.winning_option = results.winning_option
                else:
                    proposal.status = ProposalStatus.REJECTED
                    proposal.winning_option = "Quorum not met"
                
                proposal.execution_date = datetime.utcnow()
                await session.commit()
                
                logger.info(f"✅ Proposal finalized: {proposal_id} - {proposal.status.value}")
                
                return {
                    "success": True,
                    "proposal_status": proposal.status.value,
                    "winning_option": proposal.winning_option,
                    "quorum_met": results.quorum_met,
                    "participation_rate": results.participation_rate,
                    "finalization_date": proposal.execution_date.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error finalizing proposal: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def get_active_proposals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get active governance proposals"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Proposal, User)
                    .join(User, Proposal.creator_id == User.id)
                    .where(Proposal.status == ProposalStatus.ACTIVE)
                    .order_by(desc(Proposal.created_at))
                    .limit(limit)
                )
                
                proposals = []
                for proposal, creator in result:
                    # Get voting results
                    results = await self.get_proposal_results(proposal.id)
                    
                    proposals.append({
                        "proposal_id": proposal.id,
                        "title": proposal.title,
                        "description": proposal.description[:200] + "..." if len(proposal.description) > 200 else proposal.description,
                        "creator": creator.username or creator.wallet_address[:10] + "...",
                        "proposal_type": proposal.proposal_type.value,
                        "category": proposal.category,
                        "tags": proposal.tags,
                        "voting_start": proposal.voting_start_date.isoformat(),
                        "voting_end": proposal.voting_end_date.isoformat(),
                        "total_votes": proposal.total_votes,
                        "total_voting_power": proposal.total_voting_power,
                        "minimum_quorum": proposal.minimum_quorum,
                        "voting_options": proposal.voting_options,
                        "quorum_met": results.quorum_met if results else False,
                        "participation_rate": results.participation_rate if results else 0.0,
                        "time_remaining": max(0, (proposal.voting_end_date - datetime.utcnow()).total_seconds()),
                        "created_at": proposal.created_at.isoformat()
                    })
                
                return proposals
                
        except Exception as e:
            logger.error(f"Error getting active proposals: {str(e)}")
            return []
    
    async def get_proposal_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get proposal history"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Proposal, User)
                    .join(User, Proposal.creator_id == User.id)
                    .where(Proposal.status != ProposalStatus.ACTIVE)
                    .order_by(desc(Proposal.created_at))
                    .limit(limit)
                )
                
                proposals = []
                for proposal, creator in result:
                    # Get voting results
                    results = await self.get_proposal_results(proposal.id)
                    
                    proposals.append({
                        "proposal_id": proposal.id,
                        "title": proposal.title,
                        "creator": creator.username or creator.wallet_address[:10] + "...",
                        "proposal_type": proposal.proposal_type.value,
                        "status": proposal.status.value,
                        "winning_option": proposal.winning_option,
                        "total_votes": proposal.total_votes,
                        "total_voting_power": proposal.total_voting_power,
                        "quorum_met": results.quorum_met if results else False,
                        "participation_rate": results.participation_rate if results else 0.0,
                        "execution_date": proposal.execution_date.isoformat() if proposal.execution_date else None,
                        "created_at": proposal.created_at.isoformat()
                    })
                
                return proposals
                
        except Exception as e:
            logger.error(f"Error getting proposal history: {str(e)}")
            return []
    
    async def delegate_voting_power(self, request: DelegationRequest) -> Dict[str, Any]:
        """Delegate voting power to another user"""
        try:
            async with get_db_session() as session:
                # Get delegator and delegate
                delegator_result = await session.execute(
                    select(User).where(User.id == request.delegator_id)
                )
                delegator = delegator_result.scalar_one_or_none()
                
                delegate_result = await session.execute(
                    select(User).where(User.id == request.delegate_id)
                )
                delegate = delegate_result.scalar_one_or_none()
                
                if not delegator or not delegate:
                    return {"success": False, "error": "User not found"}
                
                if delegator.id == delegate.id:
                    return {"success": False, "error": "Cannot delegate to yourself"}
                
                if request.amount > delegator.voting_power:
                    return {"success": False, "error": "Insufficient voting power"}
                
                # Calculate delegation fee
                delegation_fee = request.amount * self.delegation_fee_percentage
                net_delegation = request.amount - delegation_fee
                
                # Update voting powers
                delegator.voting_power -= request.amount
                delegate.voting_power += net_delegation
                
                # Create transaction record
                transaction = Transaction(
                    user_id=request.delegator_id,
                    transaction_type=TransactionType.REWARD_DISTRIBUTION,
                    amount=delegation_fee,
                    currency="FUND",
                    description=f"Delegation fee for {net_delegation:.2f} voting power to {delegate.username}",
                    metadata={
                        "delegation_type": "voting_power",
                        "delegate_id": request.delegate_id,
                        "delegated_amount": net_delegation,
                        "fee_amount": delegation_fee,
                        "duration_days": request.duration_days
                    }
                )
                
                session.add(transaction)
                await session.commit()
                
                logger.info(f"✅ Voting power delegated: {request.delegator_id} -> {request.delegate_id}")
                
                return {
                    "success": True,
                    "delegated_amount": net_delegation,
                    "delegation_fee": delegation_fee,
                    "transaction_id": transaction.id
                }
                
        except Exception as e:
            logger.error(f"Error delegating voting power: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def get_governance_statistics(self) -> Dict[str, Any]:
        """Get governance platform statistics"""
        try:
            async with get_db_session() as session:
                # Total proposals
                total_proposals_result = await session.execute(
                    select(func.count(Proposal.id))
                )
                total_proposals = total_proposals_result.scalar() or 0
                
                # Active proposals
                active_proposals_result = await session.execute(
                    select(func.count(Proposal.id)).where(Proposal.status == ProposalStatus.ACTIVE)
                )
                active_proposals = active_proposals_result.scalar() or 0
                
                # Total votes cast
                total_votes_result = await session.execute(
                    select(func.count(Vote.id))
                )
                total_votes = total_votes_result.scalar() or 0
                
                # Total voting power
                total_voting_power_result = await session.execute(
                    select(func.sum(Vote.voting_power_used))
                )
                total_voting_power = total_voting_power_result.scalar() or 0.0
                
                # Total governance tokens
                total_tokens = await self._get_total_governance_tokens()
                
                # Average participation rate
                participation_rate = (total_voting_power / total_tokens * 100) if total_tokens > 0 else 0
                
                # Recent activity (last 7 days)
                seven_days_ago = datetime.utcnow() - timedelta(days=7)
                recent_proposals_result = await session.execute(
                    select(func.count(Proposal.id)).where(Proposal.created_at >= seven_days_ago)
                )
                recent_proposals = recent_proposals_result.scalar() or 0
                
                recent_votes_result = await session.execute(
                    select(func.count(Vote.id)).where(Vote.voted_at >= seven_days_ago)
                )
                recent_votes = recent_votes_result.scalar() or 0
                
                return {
                    "total_proposals": total_proposals,
                    "active_proposals": active_proposals,
                    "total_votes_cast": total_votes,
                    "total_voting_power": total_voting_power,
                    "total_governance_tokens": total_tokens,
                    "average_participation_rate": participation_rate,
                    "recent_proposals_7d": recent_proposals,
                    "recent_votes_7d": recent_votes,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting governance statistics: {str(e)}")
            return {}
    
    async def _get_total_governance_tokens(self) -> float:
        """Get total governance tokens in circulation"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(func.sum(User.governance_tokens))
                )
                return result.scalar() or 0.0
        except Exception as e:
            logger.error(f"Error getting total governance tokens: {str(e)}")
            return 0.0
    
    async def predict_proposal_outcome(self, proposal_id: str) -> Dict[str, Any]:
        """Predict proposal outcome using AI"""
        try:
            async with get_db_session() as session:
                # Get proposal
                proposal_result = await session.execute(
                    select(Proposal).where(Proposal.id == proposal_id)
                )
                proposal = proposal_result.scalar_one_or_none()
                
                if not proposal:
                    return {"success": False, "error": "Proposal not found"}
                
                # Get voting history for similar proposals
                similar_proposals_result = await session.execute(
                    select(Proposal).where(
                        and_(
                            Proposal.proposal_type == proposal.proposal_type,
                            Proposal.status != ProposalStatus.ACTIVE,
                            Proposal.created_at >= datetime.utcnow() - timedelta(days=90)
                        )
                    )
                )
                
                voting_history = []
                for similar_proposal in similar_proposals_result.scalars().all():
                    results = await self.get_proposal_results(similar_proposal.id)
                    if results:
                        voting_history.append({
                            "passed": similar_proposal.status == ProposalStatus.PASSED,
                            "participation_rate": results.participation_rate,
                            "quorum_met": results.quorum_met
                        })
                
                # Use AI to predict outcome
                prediction = await self.ai_service.predict_proposal_outcome(
                    proposal_text=proposal.description,
                    voting_history=voting_history
                )
                
                return {
                    "success": True,
                    "prediction": prediction
                }
                
        except Exception as e:
            logger.error(f"Error predicting proposal outcome: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
