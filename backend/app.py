"""
DecentralFund DAO - Main Backend Application
FastAPI-based REST API for decentralized mutual fund management
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import asyncio
from datetime import datetime, timedelta
import logging
from typing import List, Optional, Dict, Any
import uuid
import json
from sqlalchemy import select
from pydantic import BaseModel

# Import services
from backend.connection import get_db_session, init_database
from backend.models_comprehensive import *
from backend.blockchain_service import BlockchainService
from backend.sip_service import SIPService
from backend.governance_service import GovernanceService, ProposalCreationRequest
from backend.fund_management_service import FundManagementService, FundManagerCandidate
from backend.portfolio_service import PortfolioService
from backend.security_service import SecurityService
from backend.ai_service import AIService
from backend.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Dependency functions
def get_current_user():
    """Get current user dependency"""
    def _get_current_user():
        return get_current_user
    return Depends(_get_current_user)

# Pydantic models for API
class UserRegistration(BaseModel):
    wallet_address: str
    username: str
    full_name: Optional[str] = None
    country: Optional[str] = None
    email: Optional[str] = None

class SIPCreationRequest(BaseModel):
    amount_per_installment: float
    frequency: str  # daily, weekly, monthly
    duration_months: Optional[int] = None
    auto_compound: bool = True

class VoteRequest(BaseModel):
    proposal_id: str
    selected_option: str
    voting_power_to_use: Optional[float] = None

class FundManagerRegistration(BaseModel):
    experience_years: int
    education: str
    certifications: List[str]
    investment_philosophy: str
    risk_tolerance: str
    specialization: List[str]
    previous_performance: Dict[str, float]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    logger.info("🚀 Starting DecentralFund DAO Backend...")
    
    # Initialize database
    try:
        await init_database()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database init warning: {e}")
    
    # Initialize services
    app.state.blockchain = BlockchainService(settings.WEB3_PROVIDER_URL)
    app.state.sip_service = SIPService(app.state.blockchain)
    app.state.governance_service = GovernanceService(app.state.blockchain)
    app.state.fund_management_service = FundManagementService(app.state.blockchain)
    app.state.portfolio_service = PortfolioService(app.state.blockchain)
    app.state.security_service = SecurityService()
    app.state.ai_service = AIService()
    
    logger.info("✅ All services initialized successfully")
    
    yield
    
    logger.info("🛑 Shutting down DecentralFund DAO Backend...")

# Create FastAPI app
app = FastAPI(
    title="DecentralFund DAO API",
    description="World's First Decentralized Autonomous Mutual Fund",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# AUTHENTICATION & USER MANAGEMENT
# ============================================================================

@app.post("/api/auth/register")
async def register_user(request: UserRegistration):
    """Register a new user"""
    try:
        async with get_db_session() as session:
            # Check if user already exists
            existing_user = await session.execute(
                select(User).where(User.wallet_address == request.wallet_address)
            )
            if existing_user.scalar_one_or_none():
                return {"success": False, "error": "User already exists"}
            
            # Create new user
            user = User(
                wallet_address=request.wallet_address,
                username=request.username,
                full_name=request.full_name,
                country=request.country,
                email=request.email,
                governance_tokens=0.0,
                voting_power=0.0
            )
            
            session.add(user)
            await session.commit()
            
            # Create access token
            security_service = app.state.security_service
            access_token = security_service.create_access_token({"sub": user.id})
            refresh_token = security_service.create_refresh_token({"sub": user.id})
            
            return {
                "success": True,
                "user_id": user.id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "message": "User registered successfully"
            }
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return {"success": False, "error": f"Registration failed: {str(e)}"}

@app.post("/api/auth/login")
async def login_user(wallet_address: str, signature: str, message: str):
    """Authenticate user with wallet signature"""
    try:
        security_service = app.state.security_service
        user = await security_service.authenticate_user(wallet_address, signature, message)
        
        if not user:
            return {"success": False, "error": "Authentication failed"}
        
        # Create tokens
        access_token = security_service.create_access_token({"sub": user.id})
        refresh_token = security_service.create_refresh_token({"sub": user.id})
        
        return {
            "success": True,
            "user_id": user.id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_info": {
                "username": user.username,
                "governance_tokens": user.governance_tokens,
                "voting_power": user.voting_power
            }
        }
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return {"success": False, "error": f"Login failed: {str(e)}"}

@app.get("/api/user/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return {
        "success": True,
        "user": {
            "id": current_user.id,
            "wallet_address": current_user.wallet_address,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "country": current_user.country,
            "governance_tokens": current_user.governance_tokens,
            "voting_power": current_user.voting_power,
            "role": current_user.role.value,
            "is_verified": current_user.is_verified,
            "kyc_completed": current_user.kyc_completed,
            "created_at": current_user.created_at.isoformat()
        }
    }

# ============================================================================
# SIP (SYSTEMATIC INVESTMENT PLAN) ENDPOINTS
# ============================================================================

@app.post("/api/sip/create")
async def create_sip(request: SIPCreationRequest, current_user: User = Depends(get_current_user)):
    """Create a new SIP plan"""
    try:
        from backend.sip_service import SIPCreationRequest as SIPRequest
        
        sip_request = SIPRequest(
            user_id=current_user.id,
            amount_per_installment=request.amount_per_installment,
            frequency_days=7 if request.frequency == "weekly" else (1 if request.frequency == "daily" else 30),
            duration_months=request.duration_months,
            auto_compound=request.auto_compound
        )
        
        result = await app.state.sip_service.create_sip_plan(sip_request)
        return result
    except Exception as e:
        logger.error(f"SIP creation error: {str(e)}")
        return {"success": False, "error": f"SIP creation failed: {str(e)}"}

@app.get("/api/sip/user/{user_id}")
async def get_user_sips(user_id: str, current_user: User = Depends(get_current_user)):
    """Get user's SIP plans"""
    try:
        if current_user.id != user_id:
            return {"success": False, "error": "Unauthorized access"}
        
        sips = await app.state.sip_service.get_user_sip_plans(user_id)
        return {"success": True, "sips": sips}
    except Exception as e:
        logger.error(f"Error getting user SIPs: {str(e)}")
        return {"success": False, "error": f"Failed to get SIPs: {str(e)}"}

@app.post("/api/sip/pause/{sip_id}")
async def pause_sip(sip_id: str, current_user: User = Depends(get_current_user)):
    """Pause a SIP plan"""
    try:
        result = await app.state.sip_service.pause_sip_plan(sip_id, current_user.id)
        return result
    except Exception as e:
        logger.error(f"SIP pause error: {str(e)}")
        return {"success": False, "error": f"SIP pause failed: {str(e)}"}

@app.post("/api/sip/resume/{sip_id}")
async def resume_sip(sip_id: str, current_user: User = Depends(get_current_user)):
    """Resume a paused SIP plan"""
    try:
        result = await app.state.sip_service.resume_sip_plan(sip_id, current_user.id)
        return result
    except Exception as e:
        logger.error(f"SIP resume error: {str(e)}")
        return {"success": False, "error": f"SIP resume failed: {str(e)}"}

# ============================================================================
# GOVERNANCE ENDPOINTS
# ============================================================================

@app.post("/api/governance/create-proposal")
async def create_proposal(
    title: str,
    description: str,
    proposal_type: str,
    voting_options: List[str],
    voting_duration_days: int = 7,
    current_user: User = Depends(get_current_user)
):
    """Create a new governance proposal"""
    try:
        from backend.models_comprehensive import ProposalType
        
        proposal_type_enum = ProposalType(proposal_type)
        
        request = ProposalCreationRequest(
            creator_id=current_user.id,
            title=title,
            description=description,
            proposal_type=proposal_type_enum,
            voting_options=voting_options,
            voting_duration_days=voting_duration_days
        )
        
        result = await app.state.governance_service.create_proposal(request)
        return result
    except Exception as e:
        logger.error(f"Proposal creation error: {str(e)}")
        return {"success": False, "error": f"Proposal creation failed: {str(e)}"}

@app.post("/api/governance/vote")
async def cast_vote(request: VoteRequest, current_user: User = Depends(get_current_user)):
    """Cast a vote on a proposal"""
    try:
        result = await app.state.governance_service.cast_vote(
            proposal_id=request.proposal_id,
            voter_id=current_user.id,
            selected_option=request.selected_option,
            voting_power_to_use=request.voting_power_to_use
        )
        return result
    except Exception as e:
        logger.error(f"Vote casting error: {str(e)}")
        return {"success": False, "error": f"Vote casting failed: {str(e)}"}

@app.get("/api/governance/proposals")
async def get_proposals(limit: int = 20):
    """Get active governance proposals"""
    try:
        proposals = await app.state.governance_service.get_active_proposals(limit)
        return {"success": True, "proposals": proposals}
    except Exception as e:
        logger.error(f"Error getting proposals: {str(e)}")
        return {"success": False, "error": f"Failed to get proposals: {str(e)}"}

@app.get("/api/governance/proposals/{proposal_id}/results")
async def get_proposal_results(proposal_id: str):
    """Get voting results for a proposal"""
    try:
        results = await app.state.governance_service.get_proposal_results(proposal_id)
        if results:
            return {"success": True, "results": results.__dict__}
        else:
            return {"success": False, "error": "Proposal not found"}
    except Exception as e:
        logger.error(f"Error getting proposal results: {str(e)}")
        return {"success": False, "error": f"Failed to get results: {str(e)}"}

@app.post("/api/governance/proposals/{proposal_id}/finalize")
async def finalize_proposal(proposal_id: str, current_user: User = Depends(get_current_user)):
    """Finalize a proposal after voting period"""
    try:
        result = await app.state.governance_service.finalize_proposal(proposal_id)
        return result
    except Exception as e:
        logger.error(f"Proposal finalization error: {str(e)}")
        return {"success": False, "error": f"Proposal finalization failed: {str(e)}"}

# ============================================================================
# FUND MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/fund-managers/register")
async def register_fund_manager(
    request: FundManagerRegistration,
    current_user: User = Depends(get_current_user)
):
    """Register as a fund manager candidate"""
    try:
        candidate = FundManagerCandidate(
            user_id=current_user.id,
            name=current_user.full_name or current_user.username,
            experience_years=request.experience_years,
            education=request.education,
            certifications=request.certifications,
            investment_philosophy=request.investment_philosophy,
            risk_tolerance=request.risk_tolerance,
            specialization=request.specialization,
            previous_performance=request.previous_performance
        )
        
        result = await app.state.fund_management_service.register_fund_manager_candidate(
            current_user.id, candidate
        )
        return result
    except Exception as e:
        logger.error(f"Fund manager registration error: {str(e)}")
        return {"success": False, "error": f"Registration failed: {str(e)}"}

@app.get("/api/fund-managers/candidates")
async def get_fund_manager_candidates():
    """Get all fund manager candidates"""
    try:
        candidates = await app.state.fund_management_service.get_fund_manager_candidates()
        return {"success": True, "candidates": candidates}
    except Exception as e:
        logger.error(f"Error getting candidates: {str(e)}")
        return {"success": False, "error": f"Failed to get candidates: {str(e)}"}

@app.get("/api/fund-managers/active")
async def get_active_fund_managers():
    """Get currently active fund managers"""
    try:
        managers = await app.state.fund_management_service.get_active_fund_managers()
        return {"success": True, "managers": managers}
    except Exception as e:
        logger.error(f"Error getting active managers: {str(e)}")
        return {"success": False, "error": f"Failed to get managers: {str(e)}"}

@app.post("/api/fund-managers/election")
async def create_fund_manager_election(
    candidate_ids: List[str],
    current_user: User = Depends(get_current_user)
):
    """Create a fund manager election proposal"""
    try:
        result = await app.state.fund_management_service.create_fund_manager_election_proposal(
            current_user.id, candidate_ids
        )
        return result
    except Exception as e:
        logger.error(f"Election creation error: {str(e)}")
        return {"success": False, "error": f"Election creation failed: {str(e)}"}

# ============================================================================
# PORTFOLIO MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/portfolio/create")
async def create_portfolio(
    initial_investment: float,
    current_user: User = Depends(get_current_user)
):
    """Create a new portfolio for user"""
    try:
        result = await app.state.portfolio_service.create_user_portfolio(
            current_user.id, initial_investment
        )
        return result
    except Exception as e:
        logger.error(f"Portfolio creation error: {str(e)}")
        return {"success": False, "error": f"Portfolio creation failed: {str(e)}"}

@app.get("/api/portfolio/user/{user_id}")
async def get_user_portfolio(user_id: str, current_user: User = Depends(get_current_user)):
    """Get user's portfolio"""
    try:
        if current_user.id != user_id:
            return {"success": False, "error": "Unauthorized access"}
        
        result = await app.state.portfolio_service.get_user_portfolio(user_id)
        return result
    except Exception as e:
        logger.error(f"Error getting portfolio: {str(e)}")
        return {"success": False, "error": f"Failed to get portfolio: {str(e)}"}

@app.post("/api/portfolio/invest")
async def add_investment(
    amount: float,
    asset_symbol: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Add investment to portfolio"""
    try:
        result = await app.state.portfolio_service.add_investment_to_portfolio(
            current_user.id, amount, asset_symbol
        )
        return result
    except Exception as e:
        logger.error(f"Investment error: {str(e)}")
        return {"success": False, "error": f"Investment failed: {str(e)}"}

@app.post("/api/portfolio/rebalance")
async def rebalance_portfolio(
    target_allocation: Optional[Dict[str, float]] = None,
    current_user: User = Depends(get_current_user)
):
    """Rebalance portfolio"""
    try:
        result = await app.state.portfolio_service.rebalance_portfolio(
            current_user.id, target_allocation
        )
        return result
    except Exception as e:
        logger.error(f"Rebalancing error: {str(e)}")
        return {"success": False, "error": f"Rebalancing failed: {str(e)}"}

@app.get("/api/portfolio/recommendation")
async def get_rebalancing_recommendation(current_user: User = Depends(get_current_user)):
    """Get AI-powered rebalancing recommendation"""
    try:
        recommendation = await app.state.portfolio_service.get_rebalancing_recommendation(current_user.id)
        if recommendation:
            return {"success": True, "recommendation": recommendation.__dict__}
        else:
            return {"success": False, "error": "No recommendation available"}
    except Exception as e:
        logger.error(f"Recommendation error: {str(e)}")
        return {"success": False, "error": f"Failed to get recommendation: {str(e)}"}

# ============================================================================
# AI SERVICES ENDPOINTS
# ============================================================================

@app.post("/api/ai/analyze-sentiment")
async def analyze_sentiment(text: str, context: Optional[str] = None):
    """Analyze sentiment of text"""
    try:
        result = await app.state.ai_service.analyze_sentiment(text, context)
        return {"success": True, "result": result.__dict__}
    except Exception as e:
        logger.error(f"Sentiment analysis error: {str(e)}")
        return {"success": False, "error": f"Analysis failed: {str(e)}"}

@app.post("/api/ai/optimize-portfolio")
async def optimize_portfolio(
    current_allocation: Dict[str, float],
    risk_tolerance: str = "moderate",
    time_horizon: int = 12,
    current_user: User = Depends(get_current_user)
):
    """Get AI portfolio optimization recommendation"""
    try:
        result = await app.state.ai_service.optimize_portfolio(
            current_allocation, risk_tolerance, time_horizon
        )
        return {"success": True, "recommendation": result.__dict__}
    except Exception as e:
        logger.error(f"Portfolio optimization error: {str(e)}")
        return {"success": False, "error": f"Optimization failed: {str(e)}"}

@app.get("/api/ai/market-insights")
async def get_market_insights(assets: Optional[List[str]] = None):
    """Get AI-powered market insights"""
    try:
        insights = await app.state.ai_service.generate_market_insights(assets)
        return {"success": True, "insights": [insight.__dict__ for insight in insights]}
    except Exception as e:
        logger.error(f"Market insights error: {str(e)}")
        return {"success": False, "error": f"Failed to get insights: {str(e)}"}

# ============================================================================
# STATISTICS & ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/api/stats/platform")
async def get_platform_stats():
    """Get platform-wide statistics"""
    try:
        # Get statistics from various services
        sip_stats = await app.state.sip_service.get_sip_statistics()
        fund_stats = await app.state.fund_management_service.get_fund_performance_metrics()
        portfolio_stats = await app.state.portfolio_service.get_portfolio_statistics()
        governance_stats = await app.state.governance_service.get_governance_statistics()
        
        return {
            "success": True,
            "sip_statistics": sip_stats,
            "fund_statistics": fund_stats,
            "portfolio_statistics": portfolio_stats,
            "governance_statistics": governance_stats,
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return {"success": False, "error": f"Failed to get statistics: {str(e)}"}

@app.get("/api/market-data")
async def get_market_data():
    """Get current market data for supported assets"""
    try:
        # Mock market data for demo
        market_data = {
            "BTC": {"price": 43250.50, "change_24h": 2.3, "volume": 25000000000},
            "ETH": {"price": 2650.75, "change_24h": 1.8, "volume": 15000000000},
            "SPY": {"price": 445.20, "change_24h": 0.5, "volume": 5000000000},
            "QQQ": {"price": 380.15, "change_24h": 0.8, "volume": 3000000000},
            "GLD": {"price": 185.30, "change_24h": -0.2, "volume": 1000000000},
            "TLT": {"price": 95.80, "change_24h": 0.3, "volume": 800000000},
            "VNQ": {"price": 85.40, "change_24h": 0.1, "volume": 500000000}
        }
        
        return {
            "success": True,
            "market_data": market_data,
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Market data error: {str(e)}")
        return {"success": False, "error": f"Failed to get market data: {str(e)}"}

# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "🏛️ DecentralFund DAO API",
        "description": "World's First Decentralized Autonomous Mutual Fund",
        "version": "1.0.0",
        "features": [
            "Democratic fund management",
            "Global SIP investments", 
            "AI-powered insights",
            "Multi-asset portfolio",
            "DAO governance"
        ],
        "docs": "/docs",
        "status": "active",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "blockchain": "mock",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/stats")
async def get_platform_stats():
    """Get platform-wide statistics"""
    return {
        "total_users": 1250,
        "total_aum_usd": 5420000.0,
        "active_sips": 890,
        "active_proposals": 3,
        "top_performing_assets": [
            {"symbol": "BTC", "return_30d": 12.5},
            {"symbol": "ETH", "return_30d": 8.3},
            {"symbol": "SPY", "return_30d": 6.1},
            {"symbol": "GLD", "return_30d": 3.2},
            {"symbol": "TSLA", "return_30d": 15.7}
        ],
        "last_updated": datetime.utcnow().isoformat()
    }

@app.get("/api/market-data")
async def get_market_data():
    """Get current market data for supported assets"""
    return {
        "assets": {
            "BTC": {"price": 43250.50, "change_24h": 2.3},
            "ETH": {"price": 2650.75, "change_24h": 1.8},
            "SPY": {"price": 445.20, "change_24h": 0.5},
            "GLD": {"price": 185.30, "change_24h": -0.2},
            "TSLA": {"price": 235.60, "change_24h": 3.2}
        },
        "last_updated": datetime.utcnow().isoformat(),
        "source": "Demo data for hackathon"
    }

    




@app.post("/api/sip/create")
async def create_sip_plan(user_id: str, amount: float, frequency: str = "monthly"):
    try:
        async with get_db_session() as session:
            # Create or get user
            user_result = await session.execute(select(User).where(User.wallet_address == user_id))
            user = user_result.scalar_one_or_none()
            
            if not user:
                user = User(wallet_address=user_id)
                session.add(user)
                await session.flush()
            
            # Create real SIP plan
            sip = SIPPlan(
                user_id=user.id,
                amount_per_installment=amount,
                frequency=frequency,
                total_invested=amount,
                total_tokens_received=amount
            )
            session.add(sip)
            
            # Update user tokens
            user.governance_tokens += amount
            user.voting_power = (user.governance_tokens ** 0.5)  # Quadratic voting
            
            await session.commit()
            
            return {
                "success": True,
                "sip_id": sip.id,
                "tokens_received": amount,
                "message": "Real SIP created and stored in database!",
                "total_tokens": user.governance_tokens
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    
@app.get("/api/sip/user/{user_id}")
async def get_user_sips(user_id: str):
    try:
        async with get_db_session() as session:
            user_result = await session.execute(select(User).where(User.wallet_address == user_id))
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {"success": True, "sips": []}
            
            sips_result = await session.execute(select(SIPPlan).where(SIPPlan.user_id == user.id))
            sips = sips_result.scalars().all()
            
            sip_list = []
            for sip in sips:
                sip_list.append({
                    "id": sip.id,
                    "amount_per_installment": sip.amount_per_installment,
                    "frequency": sip.frequency,
                    "total_invested": sip.total_invested,
                    "total_tokens_received": sip.total_tokens_received,
                    "status": sip.status,
                    "created_at": sip.created_at.isoformat()
                })
            
            return {"success": True, "sips": sip_list, "total_tokens": user.governance_tokens}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/governance/create-proposal")
async def create_proposal(title: str, description: str, creator_address: str, options: str):
    try:
        async with get_db_session() as session:
            proposal = Proposal(
                title=title,
                description=description,
                creator_id=creator_address,
                options=options  # JSON string like '["Yes", "No"]'
            )
            session.add(proposal)
            await session.commit()
            
            return {"success": True, "proposal_id": proposal.id}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/governance/vote")
async def cast_vote(proposal_id: str, user_address: str, option: str, voting_power: float):
    try:
        async with get_db_session() as session:
            # Check if already voted
            existing_vote = await session.execute(
                select(Vote).where(Vote.proposal_id == proposal_id, Vote.user_id == user_address)
            )
            if existing_vote.scalar_one_or_none():
                return {"success": False, "error": "Already voted on this proposal"}
            
            # Get user's actual voting power
            user_result = await session.execute(select(User).where(User.wallet_address == user_address))
            user = user_result.scalar_one_or_none()
            
            if not user or user.voting_power < voting_power:
                return {"success": False, "error": "Insufficient voting power"}
            
            # Cast vote
            vote = Vote(
                proposal_id=proposal_id,
                user_id=user_address,
                option=option,
                voting_power=voting_power
            )
            session.add(vote)
            
            # Update proposal vote count
            proposal_result = await session.execute(select(Proposal).where(Proposal.id == proposal_id))
            proposal = proposal_result.scalar_one()
            proposal.total_votes += 1
            
            await session.commit()
            
            return {
                "success": True, 
                "message": "Vote recorded in database!",
                "transaction_hash": f"0x{hash(proposal_id + user_address + option)}"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}    

    
@app.get("/api/sip/user/{user_id}")
async def get_user_sips(user_id: str):
    """Get user's SIP plans"""
    try:
        sip_service = app.state.sip_service
        sips = await sip_service.get_user_sip_plans(user_id)
        return {"success": True, "sips": sips}
    except Exception as e:
        logger.error(f"Error getting user SIPs: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/api/governance/proposals")
async def get_proposals():
    """Get governance proposals"""
    return {
        "proposals": [
            {
                "id": "PROP-047",
                "title": "Increase Bitcoin Allocation from 10% to 15%",
                "description": "Given the recent market conditions and Bitcoin's strong performance...",
                "type": "Portfolio Change",
                "creator": "0x742d...8D",
                "created": "2 days ago",
                "voting_ends": "5 days",
                "total_votes": 2847,
                "options": {
                    "Yes (15% BTC)": 1823,
                    "No (Keep 10%)": 724,
                    "Alternative (12%)": 300
                },
                "status": "Active",
                "quorum": "✅ Met (2847/1000)"
            },
            {
                "id": "PROP-048", 
                "title": "Add Solana (SOL) to Portfolio - Max 5% Allocation",
                "description": "Solana has shown strong fundamentals and growing ecosystem...",
                "type": "New Asset",
                "creator": "0x8a3f...2C",
                "created": "1 day ago", 
                "voting_ends": "6 days",
                "total_votes": 1456,
                "options": {
                    "Yes (Add SOL)": 987,
                    "No (Don't Add)": 469
                },
                "status": "Active",
                "quorum": "✅ Met (1456/1000)"
            }
        ]
    }

@app.post("/api/governance/vote")
async def cast_vote(
    proposal_id: str,
    option: str,
    voting_power: float,
    user_address: str
):
    """Cast a vote on a proposal"""
    return {
        "success": True,
        "message": f"Vote cast successfully for {option}",
        "transaction_hash": f"0xdemo{hash(proposal_id + user_address)}",
        "voting_power_used": voting_power
    }

@app.get("/api/portfolio/user/{user_address}")
async def get_user_portfolio(user_address: str):
    """Get user portfolio"""
    return {
        "success": True,
        "portfolio": {
            "total_value": 5720.0,
            "total_invested": 5400.0,
            "unrealized_gains": 320.0,
            "return_percentage": 5.9,
            "assets": [
                {"symbol": "BTC", "allocation": 15, "value": 858, "return": 12.5},
                {"symbol": "ETH", "allocation": 12, "value": 686, "return": 8.3},
                {"symbol": "SPY", "allocation": 35, "value": 2002, "return": 6.1},
                {"symbol": "GLD", "allocation": 10, "value": 572, "return": 3.2},
                {"symbol": "TLT", "allocation": 18, "value": 1030, "return": 2.1},
                {"symbol": "CASH", "allocation": 10, "value": 572, "return": 0.0}
            ]
        }
    }

@app.post("/api/ai/analyze-sentiment")
async def analyze_sentiment(text: str, context: Optional[str] = None):
    """Analyze sentiment of community discussions"""
    # Mock AI sentiment analysis
    import random
    
    sentiments = ["positive", "neutral", "negative"]
    sentiment = random.choice(sentiments)
    confidence = random.uniform(0.7, 0.95)
    
    return {
        "sentiment": sentiment,
        "confidence": confidence,
        "analyzed_at": datetime.utcnow().isoformat(),
        "details": {
            "compound_score": random.uniform(-1, 1),
            "positive": random.uniform(0, 1),
            "neutral": random.uniform(0, 1),
            "negative": random.uniform(0, 1)
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )