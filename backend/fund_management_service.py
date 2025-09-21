"""
DecentralFund DAO - Fund Management Service
Handles fund manager elections, portfolio management, and investment decisions
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from decimal import Decimal
import json

from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload

from backend.connection import get_db_session
from backend.models_comprehensive import (
    User, FundManager, Proposal, Vote, PortfolioAsset, UserPortfolio,
    Transaction, TransactionType, AssetType, ProposalType, ProposalStatus
)
from backend.ai_service import AIService
from backend.blockchain_service import BlockchainService

logger = logging.getLogger(__name__)

@dataclass
class FundManagerCandidate:
    """Fund manager candidate information"""
    user_id: str
    name: str
    experience_years: int
    education: str
    certifications: List[str]
    investment_philosophy: str
    risk_tolerance: str
    specialization: List[str]
    previous_performance: Dict[str, float]

@dataclass
class PortfolioRebalancing:
    """Portfolio rebalancing recommendation"""
    current_allocation: Dict[str, float]
    target_allocation: Dict[str, float]
    rebalancing_trades: List[Dict[str, Any]]
    expected_return: float
    risk_reduction: float
    confidence: float

@dataclass
class InvestmentDecision:
    """Investment decision made by fund managers"""
    asset_symbol: str
    action: str  # buy, sell, hold
    quantity: float
    price: float
    reasoning: str
    risk_assessment: str
    expected_impact: str

class FundManagementService:
    """Service for managing fund operations and elections"""
    
    def __init__(self, blockchain_service: Optional[BlockchainService] = None):
        self.blockchain = blockchain_service
        self.ai_service = AIService()
        
        # Fund management configuration
        self.max_fund_managers = 7
        self.min_fund_managers = 3
        self.term_duration_days = 90
        self.min_experience_years = 3
        self.min_governance_tokens = 1000  # Minimum tokens to run for manager
        
        # Portfolio management limits
        self.max_single_asset_allocation = 0.15  # 15% max per asset
        self.min_diversification_assets = 5
        self.rebalancing_threshold = 0.05  # 5% deviation triggers rebalancing
        
        logger.info("🏛️ Fund Management Service initialized")
    
    async def register_fund_manager_candidate(
        self, 
        user_id: str, 
        candidate_data: FundManagerCandidate
    ) -> Dict[str, Any]:
        """Register a user as a fund manager candidate"""
        try:
            async with get_db_session() as session:
                # Check if user exists and has sufficient tokens
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return {"success": False, "error": "User not found"}
                
                if user.governance_tokens < self.min_governance_tokens:
                    return {
                        "success": False, 
                        "error": f"Minimum {self.min_governance_tokens} governance tokens required"
                    }
                
                if candidate_data.experience_years < self.min_experience_years:
                    return {
                        "success": False,
                        "error": f"Minimum {self.min_experience_years} years experience required"
                    }
                
                # Check if already registered
                existing_manager = await session.execute(
                    select(FundManager).where(FundManager.user_id == user_id)
                )
                if existing_manager.scalar_one_or_none():
                    return {"success": False, "error": "Already registered as fund manager"}
                
                # Create fund manager record
                fund_manager = FundManager(
                    user_id=user_id,
                    experience_years=candidate_data.experience_years,
                    education=candidate_data.education,
                    certifications=candidate_data.certifications,
                    previous_performance=candidate_data.previous_performance,
                    investment_philosophy=candidate_data.investment_philosophy,
                    risk_tolerance=candidate_data.risk_tolerance,
                    specialization=candidate_data.specialization
                )
                
                session.add(fund_manager)
                await session.commit()
                
                logger.info(f"✅ Fund manager candidate registered: {user_id}")
                
                return {
                    "success": True,
                    "message": "Successfully registered as fund manager candidate",
                    "manager_id": fund_manager.id
                }
                
        except Exception as e:
            logger.error(f"Error registering fund manager: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def get_fund_manager_candidates(self) -> List[Dict[str, Any]]:
        """Get all fund manager candidates"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(FundManager, User)
                    .join(User, FundManager.user_id == User.id)
                    .where(FundManager.is_elected == False)
                )
                
                candidates = []
                for fund_manager, user in result:
                    candidates.append({
                        "manager_id": fund_manager.id,
                        "user_id": user.id,
                        "name": user.full_name or user.username,
                        "experience_years": fund_manager.experience_years,
                        "education": fund_manager.education,
                        "certifications": fund_manager.certifications,
                        "investment_philosophy": fund_manager.investment_philosophy,
                        "risk_tolerance": fund_manager.risk_tolerance,
                        "specialization": fund_manager.specialization,
                        "previous_performance": fund_manager.previous_performance,
                        "governance_tokens": user.governance_tokens,
                        "voting_power": user.voting_power,
                        "created_at": fund_manager.created_at.isoformat()
                    })
                
                return candidates
                
        except Exception as e:
            logger.error(f"Error getting fund manager candidates: {str(e)}")
            return []
    
    async def create_fund_manager_election_proposal(
        self, 
        creator_id: str,
        candidate_ids: List[str]
    ) -> Dict[str, Any]:
        """Create a proposal for fund manager elections"""
        try:
            async with get_db_session() as session:
                # Get candidate information
                candidates_result = await session.execute(
                    select(FundManager, User)
                    .join(User, FundManager.user_id == User.id)
                    .where(FundManager.id.in_(candidate_ids))
                )
                
                candidates = []
                for fund_manager, user in candidates_result:
                    candidates.append({
                        "manager_id": fund_manager.id,
                        "name": user.full_name or user.username,
                        "experience": fund_manager.experience_years,
                        "philosophy": fund_manager.investment_philosophy[:100] + "..."
                    })
                
                if len(candidates) < self.min_fund_managers:
                    return {
                        "success": False,
                        "error": f"Minimum {self.min_fund_managers} candidates required"
                    }
                
                # Create election proposal
                voting_options = [f"Elect {c['name']}" for c in candidates] + ["None of the above"]
                
                proposal = Proposal(
                    creator_id=creator_id,
                    title="Fund Manager Election - Q1 2024",
                    description=f"Elect {len(candidates)} fund managers from {len(candidates)} candidates. Each voter can select up to {self.max_fund_managers} candidates.",
                    proposal_type=ProposalType.FUND_MANAGER_ELECTION,
                    voting_start_date=datetime.utcnow(),
                    voting_end_date=datetime.utcnow() + timedelta(days=7),
                    minimum_quorum=1000,
                    voting_options=voting_options,
                    status=ProposalStatus.ACTIVE,
                    category="governance",
                    tags=["election", "fund_managers", "leadership"]
                )
                
                session.add(proposal)
                await session.commit()
                
                logger.info(f"✅ Fund manager election proposal created: {proposal.id}")
                
                return {
                    "success": True,
                    "proposal_id": proposal.id,
                    "candidates": candidates,
                    "voting_ends": proposal.voting_end_date.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error creating election proposal: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def execute_fund_manager_election(self, proposal_id: str) -> Dict[str, Any]:
        """Execute fund manager election results"""
        try:
            async with get_db_session() as session:
                # Get proposal and votes
                proposal_result = await session.execute(
                    select(Proposal).where(Proposal.id == proposal_id)
                )
                proposal = proposal_result.scalar_one_or_none()
                
                if not proposal:
                    return {"success": False, "error": "Proposal not found"}
                
                if proposal.status != ProposalStatus.PASSED:
                    return {"success": False, "error": "Proposal not passed"}
                
                # Get vote results
                votes_result = await session.execute(
                    select(Vote).where(Vote.proposal_id == proposal_id)
                )
                votes = votes_result.scalars().all()
                
                # Count votes for each candidate
                candidate_votes = {}
                for vote in votes:
                    option = vote.selected_option
                    if option.startswith("Elect "):
                        candidate_name = option[6:]  # Remove "Elect " prefix
                        if candidate_name not in candidate_votes:
                            candidate_votes[candidate_name] = 0
                        candidate_votes[candidate_name] += vote.voting_power_used
                
                # Sort by votes and select top candidates
                sorted_candidates = sorted(
                    candidate_votes.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:self.max_fund_managers]
                
                # Update fund managers
                elected_managers = []
                for candidate_name, votes_received in sorted_candidates:
                    # Find the fund manager by name (simplified)
                    manager_result = await session.execute(
                        select(FundManager, User)
                        .join(User, FundManager.user_id == User.id)
                        .where(
                            or_(
                                User.full_name == candidate_name,
                                User.username == candidate_name
                            )
                        )
                    )
                    
                    fund_manager, user = manager_result.first()
                    if fund_manager:
                        fund_manager.is_elected = True
                        fund_manager.election_date = datetime.utcnow()
                        fund_manager.term_end_date = datetime.utcnow() + timedelta(days=self.term_duration_days)
                        fund_manager.total_votes_received = int(votes_received)
                        
                        elected_managers.append({
                            "manager_id": fund_manager.id,
                            "name": candidate_name,
                            "votes_received": votes_received
                        })
                
                # Update proposal status
                proposal.status = ProposalStatus.EXECUTED
                proposal.execution_date = datetime.utcnow()
                proposal.winning_option = f"Elected {len(elected_managers)} fund managers"
                
                await session.commit()
                
                logger.info(f"✅ Fund manager election executed: {len(elected_managers)} managers elected")
                
                return {
                    "success": True,
                    "elected_managers": elected_managers,
                    "total_candidates": len(candidate_votes),
                    "execution_date": proposal.execution_date.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error executing fund manager election: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def get_active_fund_managers(self) -> List[Dict[str, Any]]:
        """Get currently active fund managers"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(FundManager, User)
                    .join(User, FundManager.user_id == User.id)
                    .where(
                        and_(
                            FundManager.is_elected == True,
                            FundManager.term_end_date > datetime.utcnow()
                        )
                    )
                )
                
                managers = []
                for fund_manager, user in result:
                    managers.append({
                        "manager_id": fund_manager.id,
                        "user_id": user.id,
                        "name": user.full_name or user.username,
                        "experience_years": fund_manager.experience_years,
                        "investment_philosophy": fund_manager.investment_philosophy,
                        "risk_tolerance": fund_manager.risk_tolerance,
                        "specialization": fund_manager.specialization,
                        "portfolio_return": fund_manager.portfolio_return,
                        "risk_adjusted_return": fund_manager.risk_adjusted_return,
                        "assets_under_management": fund_manager.assets_under_management,
                        "election_date": fund_manager.election_date.isoformat(),
                        "term_end_date": fund_manager.term_end_date.isoformat(),
                        "votes_received": fund_manager.total_votes_received
                    })
                
                return managers
                
        except Exception as e:
            logger.error(f"Error getting active fund managers: {str(e)}")
            return []
    
    async def propose_portfolio_rebalancing(
        self,
        manager_id: str,
        current_allocation: Dict[str, float],
        reasoning: str
    ) -> Dict[str, Any]:
        """Propose portfolio rebalancing by fund manager"""
        try:
            async with get_db_session() as session:
                # Verify manager is active
                manager_result = await session.execute(
                    select(FundManager).where(
                        and_(
                            FundManager.id == manager_id,
                            FundManager.is_elected == True,
                            FundManager.term_end_date > datetime.utcnow()
                        )
                    )
                )
                manager = manager_result.scalar_one_or_none()
                
                if not manager:
                    return {"success": False, "error": "Manager not found or not active"}
                
                # Use AI to optimize portfolio
                ai_recommendation = await self.ai_service.optimize_portfolio(
                    current_allocation=current_allocation,
                    risk_tolerance=manager.risk_tolerance,
                    time_horizon=12
                )
                
                # Create rebalancing proposal
                voting_options = [
                    "Accept rebalancing proposal",
                    "Reject rebalancing proposal",
                    "Modify and re-vote"
                ]
                
                proposal = Proposal(
                    creator_id=manager.user_id,
                    title=f"Portfolio Rebalancing Proposal - {datetime.utcnow().strftime('%Y-%m-%d')}",
                    description=f"""
                    Fund Manager: {manager.user_id}
                    Reasoning: {reasoning}
                    
                    Current Allocation: {json.dumps(current_allocation, indent=2)}
                    Proposed Allocation: {json.dumps(ai_recommendation.recommended_allocation, indent=2)}
                    
                    Expected Return: {ai_recommendation.expected_return:.2%}
                    Expected Volatility: {ai_recommendation.volatility:.2%}
                    Sharpe Ratio: {ai_recommendation.sharpe_ratio:.2f}
                    
                    Rebalancing Trades: {len(ai_recommendation.rebalancing_trades)} trades required
                    """,
                    proposal_type=ProposalType.PORTFOLIO_CHANGE,
                    voting_start_date=datetime.utcnow(),
                    voting_end_date=datetime.utcnow() + timedelta(days=3),
                    minimum_quorum=500,
                    voting_options=voting_options,
                    status=ProposalStatus.ACTIVE,
                    category="portfolio",
                    tags=["rebalancing", "optimization", "risk_management"]
                )
                
                session.add(proposal)
                await session.commit()
                
                logger.info(f"✅ Portfolio rebalancing proposal created: {proposal.id}")
                
                return {
                    "success": True,
                    "proposal_id": proposal.id,
                    "ai_recommendation": {
                        "recommended_allocation": ai_recommendation.recommended_allocation,
                        "expected_return": ai_recommendation.expected_return,
                        "volatility": ai_recommendation.volatility,
                        "sharpe_ratio": ai_recommendation.sharpe_ratio,
                        "rebalancing_trades": ai_recommendation.rebalancing_trades,
                        "confidence": ai_recommendation.confidence
                    },
                    "voting_ends": proposal.voting_end_date.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error creating rebalancing proposal: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def execute_portfolio_rebalancing(
        self,
        proposal_id: str,
        user_portfolios: List[str]
    ) -> Dict[str, Any]:
        """Execute approved portfolio rebalancing"""
        try:
            async with get_db_session() as session:
                # Get proposal
                proposal_result = await session.execute(
                    select(Proposal).where(Proposal.id == proposal_id)
                )
                proposal = proposal_result.scalar_one_or_none()
                
                if not proposal or proposal.status != ProposalStatus.PASSED:
                    return {"success": False, "error": "Proposal not approved"}
                
                # Parse rebalancing details from proposal description
                # This is simplified - in production, store structured data
                rebalancing_trades = []  # Would be parsed from proposal
                
                executed_trades = []
                total_value_rebalanced = 0.0
                
                for portfolio_id in user_portfolios:
                    # Get portfolio
                    portfolio_result = await session.execute(
                        select(UserPortfolio).where(UserPortfolio.id == portfolio_id)
                    )
                    portfolio = portfolio_result.scalar_one_or_none()
                    
                    if not portfolio:
                        continue
                    
                    # Execute rebalancing trades (simplified)
                    for trade in rebalancing_trades:
                        # Create transaction record
                        transaction = Transaction(
                            user_id=portfolio.user_id,
                            transaction_type=TransactionType.REBALANCING,
                            amount=trade.get('amount', 0),
                            currency="USD",
                            asset_symbol=trade.get('asset', ''),
                            asset_quantity=trade.get('quantity', 0),
                            asset_price=trade.get('price', 0),
                            description=f"Portfolio rebalancing: {trade.get('action', '')} {trade.get('asset', '')}",
                            metadata=trade
                        )
                        
                        session.add(transaction)
                        executed_trades.append(trade)
                        total_value_rebalanced += trade.get('amount', 0)
                
                # Update proposal status
                proposal.status = ProposalStatus.EXECUTED
                proposal.execution_date = datetime.utcnow()
                proposal.execution_transaction_hash = f"0x{hash(proposal_id)}"
                
                await session.commit()
                
                logger.info(f"✅ Portfolio rebalancing executed: {len(executed_trades)} trades")
                
                return {
                    "success": True,
                    "executed_trades": executed_trades,
                    "total_value_rebalanced": total_value_rebalanced,
                    "portfolios_updated": len(user_portfolios),
                    "execution_date": proposal.execution_date.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error executing portfolio rebalancing: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def get_fund_performance_metrics(self) -> Dict[str, Any]:
        """Get overall fund performance metrics"""
        try:
            async with get_db_session() as session:
                # Get total AUM
                total_aum_result = await session.execute(
                    select(func.sum(UserPortfolio.current_value))
                )
                total_aum = total_aum_result.scalar() or 0.0
                
                # Get total invested
                total_invested_result = await session.execute(
                    select(func.sum(UserPortfolio.total_invested))
                )
                total_invested = total_invested_result.scalar() or 0.0
                
                # Calculate overall return
                overall_return = 0.0
                if total_invested > 0:
                    overall_return = ((total_aum - total_invested) / total_invested) * 100
                
                # Get active fund managers count
                active_managers_result = await session.execute(
                    select(func.count(FundManager.id)).where(
                        and_(
                            FundManager.is_elected == True,
                            FundManager.term_end_date > datetime.utcnow()
                        )
                    )
                )
                active_managers = active_managers_result.scalar() or 0
                
                # Get recent performance (last 30 days)
                thirty_days_ago = datetime.utcnow() - timedelta(days=30)
                recent_transactions_result = await session.execute(
                    select(Transaction)
                    .where(
                        and_(
                            Transaction.transaction_type == TransactionType.REBALANCING,
                            Transaction.initiated_at >= thirty_days_ago
                        )
                    )
                )
                recent_rebalancing_count = len(recent_transactions_result.scalars().all())
                
                return {
                    "total_aum_usd": total_aum,
                    "total_invested_usd": total_invested,
                    "overall_return_percentage": overall_return,
                    "unrealized_gains_usd": total_aum - total_invested,
                    "active_fund_managers": active_managers,
                    "recent_rebalancing_count": recent_rebalancing_count,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting fund performance metrics: {str(e)}")
            return {}
    
    async def get_manager_performance_ranking(self) -> List[Dict[str, Any]]:
        """Get fund manager performance ranking"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(FundManager, User)
                    .join(User, FundManager.user_id == User.id)
                    .where(FundManager.is_elected == True)
                    .order_by(FundManager.portfolio_return.desc())
                )
                
                ranking = []
                for i, (manager, user) in enumerate(result, 1):
                    ranking.append({
                        "rank": i,
                        "manager_id": manager.id,
                        "name": user.full_name or user.username,
                        "portfolio_return": manager.portfolio_return,
                        "risk_adjusted_return": manager.risk_adjusted_return,
                        "assets_under_management": manager.assets_under_management,
                        "experience_years": manager.experience_years,
                        "specialization": manager.specialization
                    })
                
                return ranking
                
        except Exception as e:
            logger.error(f"Error getting manager performance ranking: {str(e)}")
            return []
