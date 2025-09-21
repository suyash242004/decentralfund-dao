"""
DecentralFund DAO - Main Backend Application
FastAPI-based REST API for decentralized mutual fund management
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
import asyncio
from datetime import datetime, timedelta
import logging
from typing import List, Optional, Dict, Any

# Internal imports
from backend.database.connection import get_db_session, init_database
from backend.database.models import *
from backend.services.blockchain_service import BlockchainService
from backend.services.sip_service import SIPService
from backend.services.voting_service import VotingService
from backend.services.portfolio_service import PortfolioService
from backend.services.ai_service import AIService
from backend.api.auth import auth_router
from backend.api.sip import sip_router
from backend.api.voting import voting_router
from backend.api.portfolio import portfolio_router
from backend.api.governance import governance_router
from backend.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    logger.info("🚀 Starting DecentralFund DAO Backend...")
    
    # Initialize database
    await init_database()
    
    # Initialize blockchain service
    app.state.blockchain = BlockchainService(settings.WEB3_PROVIDER_URL)
    app.state.sip_service = SIPService(app.state.blockchain)
    app.state.voting_service = VotingService(app.state.blockchain)
    app.state.portfolio_service = PortfolioService(app.state.blockchain)
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

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(sip_router, prefix="/api/sip", tags=["SIP Management"])
app.include_router(voting_router, prefix="/api/voting", tags=["Voting System"])
app.include_router(portfolio_router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(governance_router, prefix="/api/governance", tags=["DAO Governance"])

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
    try:
        # Check database connection
        async with get_db_session() as db:
            await db.execute("SELECT 1")
        
        # Check blockchain connection
        blockchain_status = app.state.blockchain.is_connected()
        
        return {
            "status": "healthy",
            "database": "connected",
            "blockchain": "connected" if blockchain_status else "disconnected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/api/stats")
async def get_platform_stats():
    """Get platform-wide statistics"""
    try:
        async with get_db_session() as db:
            # Total users
            users_count = await db.scalar(
                "SELECT COUNT(*) FROM users WHERE is_active = true"
            )
            
            # Total AUM (Assets Under Management)
            total_aum = await db.scalar(
                "SELECT COALESCE(SUM(total_invested), 0) FROM user_portfolios"
            )
            
            # Active SIPs
            active_sips = await db.scalar(
                "SELECT COUNT(*) FROM sip_plans WHERE is_active = true"
            )
            
            # Active proposals
            active_proposals = await db.scalar(
                "SELECT COUNT(*) FROM proposals WHERE status = 'active'"
            )
            
            # Top performing assets
            top_assets = await db.execute("""
                SELECT asset_symbol, AVG(return_percentage) as avg_return
                FROM portfolio_assets 
                WHERE updated_at >= NOW() - INTERVAL '30 days'
                GROUP BY asset_symbol
                ORDER BY avg_return DESC
                LIMIT 5
            """)
            
            return {
                "total_users": users_count or 0,
                "total_aum_usd": float(total_aum or 0),
                "active_sips": active_sips or 0,
                "active_proposals": active_proposals or 0,
                "top_performing_assets": [
                    {"symbol": row[0], "return_30d": float(row[1])}
                    for row in top_assets.fetchall()
                ],
                "last_updated": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"Error fetching platform stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch platform statistics")

@app.get("/api/market-data")
async def get_market_data():
    """Get current market data for supported assets"""
    try:
        market_data = await app.state.portfolio_service.get_market_data()
        return {
            "assets": market_data,
            "last_updated": datetime.utcnow().isoformat(),
            "source": "Multiple APIs aggregated"
        }
    except Exception as e:
        logger.error(f"Error fetching market data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch market data")

@app.post("/api/ai/analyze-sentiment")
async def analyze_community_sentiment(
    text: str,
    context: Optional[str] = None
):
    """Analyze sentiment of community discussions"""
    try:
        sentiment = await app.state.ai_service.analyze_sentiment(text, context)
        return {
            "sentiment": sentiment,
            "analyzed_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to analyze sentiment")

@app.post("/api/ai/portfolio-recommendation")
async def get_portfolio_recommendation(
    current_allocation: Dict[str, float],
    risk_tolerance: str = "moderate",
    time_horizon: int = 12  # months
):
    """Get AI-powered portfolio optimization recommendations"""
    try:
        recommendation = await app.state.ai_service.optimize_portfolio(
            current_allocation, risk_tolerance, time_horizon
        )
        return {
            "recommendation": recommendation,
            "generated_at": datetime.utcnow().isoformat(),
            "risk_level": risk_tolerance,
            "time_horizon_months": time_horizon
        }
    except Exception as e:
        logger.error(f"Error generating portfolio recommendation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendation")

@app.post("/api/simulate-vote")
async def simulate_vote_outcome(
    proposal_id: str,
    hypothetical_votes: Dict[str, int]  # {"option_1": 1000, "option_2": 500}
):
    """Simulate voting outcomes for testing"""
    try:
        simulation = await app.state.voting_service.simulate_vote_outcome(
            proposal_id, hypothetical_votes
        )
        return {
            "simulation": simulation,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error simulating vote: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to simulate vote")

@app.websocket("/ws/live-voting/{proposal_id}")
async def websocket_live_voting(websocket, proposal_id: str):
    """WebSocket endpoint for real-time voting updates"""
    await websocket.accept()
    try:
        while True:
            # Get current voting stats
            voting_stats = await app.state.voting_service.get_live_voting_stats(proposal_id)
            await websocket.send_json(voting_stats)
            await asyncio.sleep(2)  # Update every 2 seconds
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()

# Background task for automated portfolio rebalancing
@app.post("/api/admin/trigger-rebalancing")
async def trigger_portfolio_rebalancing(background_tasks: BackgroundTasks):
    """Trigger automated portfolio rebalancing (admin only)"""
    try:
        background_tasks.add_task(app.state.portfolio_service.auto_rebalance)
        return {
            "message": "Portfolio rebalancing triggered",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering rebalancing: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to trigger rebalancing")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Endpoint not found",
        "message": "The requested resource does not exist",
        "path": str(request.url.path),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {str(exc)}")
    return {
        "error": "Internal server error",
        "message": "Something went wrong on our end",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )