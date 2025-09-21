"""
DecentralFund DAO - Portfolio Management Service
Handles portfolio creation, rebalancing, and performance tracking
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from decimal import Decimal
import json
import numpy as np

from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from backend.connection import get_db_session
from backend.models_comprehensive import (
    User, UserPortfolio, PortfolioAsset, Transaction, TransactionType,
    AssetType, MarketData, PortfolioPerformance, SupportedAsset
)
from backend.ai_service import AIService
from backend.blockchain_service import BlockchainService

logger = logging.getLogger(__name__)

@dataclass
class AssetAllocation:
    """Asset allocation in portfolio"""
    symbol: str
    name: str
    asset_type: AssetType
    quantity: float
    current_price: float
    total_value: float
    allocation_percentage: float
    target_allocation: float
    unrealized_gains: float
    return_percentage: float

@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    total_value: float
    total_invested: float
    unrealized_gains: float
    realized_gains: float
    total_return_percentage: float
    daily_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    beta: float
    alpha: float

@dataclass
class RebalancingRecommendation:
    """Portfolio rebalancing recommendation"""
    current_allocation: Dict[str, float]
    target_allocation: Dict[str, float]
    rebalancing_trades: List[Dict[str, Any]]
    expected_return: float
    risk_reduction: float
    confidence: float
    urgency: str  # low, medium, high

class PortfolioService:
    """Service for managing user portfolios"""
    
    def __init__(self, blockchain_service: Optional[BlockchainService] = None):
        self.blockchain = blockchain_service
        self.ai_service = AIService()
        
        # Portfolio configuration
        self.max_single_asset_allocation = 0.15  # 15% max per asset
        self.min_diversification_assets = 5
        self.rebalancing_threshold = 0.05  # 5% deviation triggers rebalancing
        self.risk_free_rate = 0.02  # 2% risk-free rate
        
        # Supported assets
        self.default_assets = {
            'BTC': {'name': 'Bitcoin', 'type': AssetType.CRYPTO, 'target_allocation': 0.10},
            'ETH': {'name': 'Ethereum', 'type': AssetType.CRYPTO, 'target_allocation': 0.10},
            'SPY': {'name': 'S&P 500 ETF', 'type': AssetType.INDEX, 'target_allocation': 0.30},
            'QQQ': {'name': 'NASDAQ ETF', 'type': AssetType.INDEX, 'target_allocation': 0.20},
            'GLD': {'name': 'Gold ETF', 'type': AssetType.COMMODITY, 'target_allocation': 0.10},
            'TLT': {'name': 'Long-term Treasury ETF', 'type': AssetType.BOND, 'target_allocation': 0.15},
            'VNQ': {'name': 'Real Estate ETF', 'type': AssetType.REIT, 'target_allocation': 0.05}
        }
        
        logger.info("💼 Portfolio Service initialized")
    
    async def create_user_portfolio(self, user_id: str, initial_investment: float) -> Dict[str, Any]:
        """Create a new portfolio for a user"""
        try:
            async with get_db_session() as session:
                # Check if user exists
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return {"success": False, "error": "User not found"}
                
                # Check if portfolio already exists
                existing_portfolio = await session.execute(
                    select(UserPortfolio).where(UserPortfolio.user_id == user_id)
                )
                if existing_portfolio.scalar_one_or_none():
                    return {"success": False, "error": "Portfolio already exists"}
                
                # Create portfolio
                portfolio = UserPortfolio(
                    user_id=user_id,
                    total_invested=initial_investment,
                    current_value=initial_invested,
                    unrealized_gains=0.0,
                    realized_gains=0.0,
                    total_return_percentage=0.0
                )
                
                session.add(portfolio)
                await session.flush()  # Get portfolio ID
                
                # Create initial asset allocations
                assets_created = []
                for symbol, asset_info in self.default_assets.items():
                    allocation_amount = initial_investment * asset_info['target_allocation']
                    
                    # Get current price (mock for demo)
                    current_price = await self._get_asset_price(symbol)
                    quantity = allocation_amount / current_price if current_price > 0 else 0
                    
                    portfolio_asset = PortfolioAsset(
                        portfolio_id=portfolio.id,
                        asset_symbol=symbol,
                        asset_name=asset_info['name'],
                        asset_type=asset_info['type'],
                        quantity=quantity,
                        average_price=current_price,
                        current_price=current_price,
                        total_invested=allocation_amount,
                        current_value=allocation_amount,
                        target_allocation_percentage=asset_info['target_allocation'] * 100,
                        current_allocation_percentage=asset_info['target_allocation'] * 100
                    )
                    
                    session.add(portfolio_asset)
                    assets_created.append({
                        'symbol': symbol,
                        'name': asset_info['name'],
                        'quantity': quantity,
                        'price': current_price,
                        'value': allocation_amount,
                        'allocation': asset_info['target_allocation'] * 100
                    })
                
                # Create initial transaction
                transaction = Transaction(
                    user_id=user_id,
                    transaction_type=TransactionType.SIP_INVESTMENT,
                    amount=initial_investment,
                    currency="USD",
                    description="Initial portfolio creation",
                    metadata={
                        "portfolio_id": portfolio.id,
                        "assets_allocated": len(assets_created)
                    }
                )
                
                session.add(transaction)
                await session.commit()
                
                logger.info(f"✅ Portfolio created for user {user_id}: ${initial_investment}")
                
                return {
                    "success": True,
                    "portfolio_id": portfolio.id,
                    "total_invested": initial_investment,
                    "assets_created": assets_created,
                    "transaction_id": transaction.id
                }
                
        except Exception as e:
            logger.error(f"Error creating portfolio: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def get_user_portfolio(self, user_id: str) -> Dict[str, Any]:
        """Get user's portfolio with current values"""
        try:
            async with get_db_session() as session:
                # Get portfolio
                portfolio_result = await session.execute(
                    select(UserPortfolio).where(UserPortfolio.user_id == user_id)
                )
                portfolio = portfolio_result.scalar_one_or_none()
                
                if not portfolio:
                    return {"success": False, "error": "Portfolio not found"}
                
                # Get portfolio assets
                assets_result = await session.execute(
                    select(PortfolioAsset).where(PortfolioAsset.portfolio_id == portfolio.id)
                )
                assets = assets_result.scalars().all()
                
                # Update current prices and calculate values
                updated_assets = []
                total_current_value = 0.0
                
                for asset in assets:
                    current_price = await self._get_asset_price(asset.asset_symbol)
                    current_value = asset.quantity * current_price
                    unrealized_gains = current_value - asset.total_invested
                    return_percentage = (unrealized_gains / asset.total_invested * 100) if asset.total_invested > 0 else 0
                    
                    # Update asset in database
                    asset.current_price = current_price
                    asset.current_value = current_value
                    asset.unrealized_gains = unrealized_gains
                    asset.return_percentage = return_percentage
                    asset.current_allocation_percentage = (current_value / portfolio.current_value * 100) if portfolio.current_value > 0 else 0
                    
                    updated_assets.append({
                        'symbol': asset.asset_symbol,
                        'name': asset.asset_name,
                        'asset_type': asset.asset_type.value,
                        'quantity': asset.quantity,
                        'average_price': asset.average_price,
                        'current_price': current_price,
                        'total_invested': asset.total_invested,
                        'current_value': current_value,
                        'unrealized_gains': unrealized_gains,
                        'return_percentage': return_percentage,
                        'allocation_percentage': asset.current_allocation_percentage,
                        'target_allocation': asset.target_allocation_percentage
                    })
                    
                    total_current_value += current_value
                
                # Update portfolio totals
                portfolio.current_value = total_current_value
                portfolio.unrealized_gains = total_current_value - portfolio.total_invested
                portfolio.total_return_percentage = (portfolio.unrealized_gains / portfolio.total_invested * 100) if portfolio.total_invested > 0 else 0
                
                await session.commit()
                
                # Calculate portfolio metrics
                metrics = await self._calculate_portfolio_metrics(portfolio, updated_assets)
                
                return {
                    "success": True,
                    "portfolio": {
                        "portfolio_id": portfolio.id,
                        "total_invested": portfolio.total_invested,
                        "current_value": portfolio.current_value,
                        "unrealized_gains": portfolio.unrealized_gains,
                        "realized_gains": portfolio.realized_gains,
                        "total_return_percentage": portfolio.total_return_percentage,
                        "last_rebalanced": portfolio.last_rebalanced.isoformat() if portfolio.last_rebalanced else None,
                        "created_at": portfolio.created_at.isoformat()
                    },
                    "assets": updated_assets,
                    "metrics": metrics
                }
                
        except Exception as e:
            logger.error(f"Error getting portfolio: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def add_investment_to_portfolio(
        self, 
        user_id: str, 
        amount: float, 
        asset_symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add investment to portfolio (SIP or one-time)"""
        try:
            async with get_db_session() as session:
                # Get portfolio
                portfolio_result = await session.execute(
                    select(UserPortfolio).where(UserPortfolio.user_id == user_id)
                )
                portfolio = portfolio_result.scalar_one_or_none()
                
                if not portfolio:
                    return {"success": False, "error": "Portfolio not found"}
                
                if asset_symbol:
                    # Add to specific asset
                    asset_result = await session.execute(
                        select(PortfolioAsset).where(
                            and_(
                                PortfolioAsset.portfolio_id == portfolio.id,
                                PortfolioAsset.asset_symbol == asset_symbol
                            )
                        )
                    )
                    asset = asset_result.scalar_one_or_none()
                    
                    if not asset:
                        return {"success": False, "error": "Asset not found in portfolio"}
                    
                    current_price = await self._get_asset_price(asset_symbol)
                    additional_quantity = amount / current_price
                    
                    # Update asset
                    asset.quantity += additional_quantity
                    asset.total_invested += amount
                    asset.average_price = asset.total_invested / asset.quantity
                    
                    # Create transaction
                    transaction = Transaction(
                        user_id=user_id,
                        transaction_type=TransactionType.SIP_INVESTMENT,
                        amount=amount,
                        currency="USD",
                        asset_symbol=asset_symbol,
                        asset_quantity=additional_quantity,
                        asset_price=current_price,
                        description=f"Investment in {asset_symbol}",
                        metadata={"portfolio_id": portfolio.id}
                    )
                    
                else:
                    # Distribute across portfolio according to target allocation
                    assets_result = await session.execute(
                        select(PortfolioAsset).where(PortfolioAsset.portfolio_id == portfolio.id)
                    )
                    assets = assets_result.scalars().all()
                    
                    transactions = []
                    for asset in assets:
                        allocation_amount = amount * (asset.target_allocation_percentage / 100)
                        current_price = await self._get_asset_price(asset.asset_symbol)
                        additional_quantity = allocation_amount / current_price
                        
                        # Update asset
                        asset.quantity += additional_quantity
                        asset.total_invested += allocation_amount
                        asset.average_price = asset.total_invested / asset.quantity
                        
                        # Create transaction
                        transaction = Transaction(
                            user_id=user_id,
                            transaction_type=TransactionType.SIP_INVESTMENT,
                            amount=allocation_amount,
                            currency="USD",
                            asset_symbol=asset.asset_symbol,
                            asset_quantity=additional_quantity,
                            asset_price=current_price,
                            description=f"Portfolio investment - {asset.asset_symbol}",
                            metadata={"portfolio_id": portfolio.id}
                        )
                        session.add(transaction)
                        transactions.append(transaction)
                
                # Update portfolio
                portfolio.total_invested += amount
                portfolio.current_value += amount  # Will be updated with real prices later
                
                session.add(transaction)
                await session.commit()
                
                logger.info(f"✅ Investment added to portfolio: ${amount} for user {user_id}")
                
                return {
                    "success": True,
                    "amount_invested": amount,
                    "transaction_id": transaction.id if asset_symbol else "multiple",
                    "updated_portfolio_value": portfolio.current_value
                }
                
        except Exception as e:
            logger.error(f"Error adding investment: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def rebalance_portfolio(
        self, 
        user_id: str, 
        target_allocation: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Rebalance portfolio to target allocation"""
        try:
            async with get_db_session() as session:
                # Get portfolio
                portfolio_result = await session.execute(
                    select(UserPortfolio).where(UserPortfolio.user_id == user_id)
                )
                portfolio = portfolio_result.scalar_one_or_none()
                
                if not portfolio:
                    return {"success": False, "error": "Portfolio not found"}
                
                # Get current assets
                assets_result = await session.execute(
                    select(PortfolioAsset).where(PortfolioAsset.portfolio_id == portfolio.id)
                )
                assets = assets_result.scalars().all()
                
                # Calculate current allocation
                current_allocation = {}
                for asset in assets:
                    current_price = await self._get_asset_price(asset.asset_symbol)
                    current_value = asset.quantity * current_price
                    allocation = current_value / portfolio.current_value if portfolio.current_value > 0 else 0
                    current_allocation[asset.asset_symbol] = allocation
                
                # Use AI to optimize if no target provided
                if not target_allocation:
                    ai_recommendation = await self.ai_service.optimize_portfolio(
                        current_allocation=current_allocation,
                        risk_tolerance='moderate',
                        time_horizon=12
                    )
                    target_allocation = ai_recommendation.recommended_allocation
                
                # Calculate rebalancing trades
                rebalancing_trades = []
                total_trade_value = 0.0
                
                for asset in assets:
                    current_allocation_pct = current_allocation.get(asset.asset_symbol, 0)
                    target_allocation_pct = target_allocation.get(asset.asset_symbol, 0)
                    
                    if abs(current_allocation_pct - target_allocation_pct) > self.rebalancing_threshold:
                        current_price = await self._get_asset_price(asset.asset_symbol)
                        current_value = asset.quantity * current_price
                        target_value = portfolio.current_value * target_allocation_pct
                        value_difference = target_value - current_value
                        
                        if abs(value_difference) > 10:  # Minimum $10 trade
                            action = "buy" if value_difference > 0 else "sell"
                            quantity = abs(value_difference) / current_price
                            
                            rebalancing_trades.append({
                                "asset_symbol": asset.asset_symbol,
                                "action": action,
                                "quantity": quantity,
                                "price": current_price,
                                "value": abs(value_difference),
                                "current_allocation": current_allocation_pct,
                                "target_allocation": target_allocation_pct
                            })
                            
                            total_trade_value += abs(value_difference)
                
                if not rebalancing_trades:
                    return {
                        "success": True,
                        "message": "Portfolio is already balanced",
                        "rebalancing_trades": []
                    }
                
                # Execute trades
                executed_trades = []
                for trade in rebalancing_trades:
                    asset = next(a for a in assets if a.asset_symbol == trade["asset_symbol"])
                    
                    if trade["action"] == "buy":
                        asset.quantity += trade["quantity"]
                        asset.total_invested += trade["value"]
                    else:
                        asset.quantity -= trade["quantity"]
                        asset.total_invested -= trade["value"]
                        portfolio.realized_gains += trade["value"] - (trade["quantity"] * asset.average_price)
                    
                    # Update average price
                    if asset.quantity > 0:
                        asset.average_price = asset.total_invested / asset.quantity
                    
                    # Create transaction
                    transaction = Transaction(
                        user_id=user_id,
                        transaction_type=TransactionType.REBALANCING,
                        amount=trade["value"],
                        currency="USD",
                        asset_symbol=trade["asset_symbol"],
                        asset_quantity=trade["quantity"],
                        asset_price=trade["price"],
                        description=f"Portfolio rebalancing: {trade['action']} {trade['asset_symbol']}",
                        metadata={
                            "portfolio_id": portfolio.id,
                            "rebalancing_trade": True,
                            "current_allocation": trade["current_allocation"],
                            "target_allocation": trade["target_allocation"]
                        }
                    )
                    
                    session.add(transaction)
                    executed_trades.append(trade)
                
                # Update portfolio
                portfolio.last_rebalanced = datetime.utcnow()
                
                await session.commit()
                
                logger.info(f"✅ Portfolio rebalanced for user {user_id}: {len(executed_trades)} trades")
                
                return {
                    "success": True,
                    "rebalancing_trades": executed_trades,
                    "total_trade_value": total_trade_value,
                    "rebalancing_date": portfolio.last_rebalanced.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error rebalancing portfolio: {str(e)}")
            return {"success": False, "error": f"Internal error: {str(e)}"}
    
    async def get_rebalancing_recommendation(self, user_id: str) -> RebalancingRecommendation:
        """Get AI-powered rebalancing recommendation"""
        try:
            async with get_db_session() as session:
                # Get portfolio
                portfolio_result = await session.execute(
                    select(UserPortfolio).where(UserPortfolio.user_id == user_id)
                )
                portfolio = portfolio_result.scalar_one_or_none()
                
                if not portfolio:
                    return None
                
                # Get current allocation
                assets_result = await session.execute(
                    select(PortfolioAsset).where(PortfolioAsset.portfolio_id == portfolio.id)
                )
                assets = assets_result.scalars().all()
                
                current_allocation = {}
                for asset in assets:
                    current_price = await self._get_asset_price(asset.asset_symbol)
                    current_value = asset.quantity * current_price
                    allocation = current_value / portfolio.current_value if portfolio.current_value > 0 else 0
                    current_allocation[asset.asset_symbol] = allocation
                
                # Get AI recommendation
                ai_recommendation = await self.ai_service.optimize_portfolio(
                    current_allocation=current_allocation,
                    risk_tolerance='moderate',
                    time_horizon=12
                )
                
                # Calculate rebalancing trades
                rebalancing_trades = []
                max_deviation = 0.0
                
                for asset in assets:
                    current_allocation_pct = current_allocation.get(asset.asset_symbol, 0)
                    target_allocation_pct = ai_recommendation.recommended_allocation.get(asset.asset_symbol, 0)
                    deviation = abs(current_allocation_pct - target_allocation_pct)
                    max_deviation = max(max_deviation, deviation)
                    
                    if deviation > self.rebalancing_threshold:
                        current_price = await self._get_asset_price(asset.asset_symbol)
                        current_value = asset.quantity * current_price
                        target_value = portfolio.current_value * target_allocation_pct
                        value_difference = target_value - current_value
                        
                        rebalancing_trades.append({
                            "asset_symbol": asset.asset_symbol,
                            "action": "buy" if value_difference > 0 else "sell",
                            "quantity": abs(value_difference) / current_price,
                            "price": current_price,
                            "value": abs(value_difference),
                            "current_allocation": current_allocation_pct,
                            "target_allocation": target_allocation_pct,
                            "deviation": deviation
                        })
                
                # Determine urgency
                if max_deviation > 0.10:  # 10% deviation
                    urgency = "high"
                elif max_deviation > 0.05:  # 5% deviation
                    urgency = "medium"
                else:
                    urgency = "low"
                
                return RebalancingRecommendation(
                    current_allocation=current_allocation,
                    target_allocation=ai_recommendation.recommended_allocation,
                    rebalancing_trades=rebalancing_trades,
                    expected_return=ai_recommendation.expected_return,
                    risk_reduction=ai_recommendation.volatility,
                    confidence=ai_recommendation.confidence,
                    urgency=urgency
                )
                
        except Exception as e:
            logger.error(f"Error getting rebalancing recommendation: {str(e)}")
            return None
    
    async def _calculate_portfolio_metrics(
        self, 
        portfolio: UserPortfolio, 
        assets: List[Dict[str, Any]]
    ) -> PortfolioMetrics:
        """Calculate portfolio performance metrics"""
        try:
            # Basic metrics
            total_value = portfolio.current_value
            total_invested = portfolio.total_invested
            unrealized_gains = portfolio.unrealized_gains
            realized_gains = portfolio.realized_gains
            total_return_percentage = portfolio.total_return_percentage
            
            # Calculate daily return (simplified)
            daily_return = 0.0  # Would be calculated from historical data
            
            # Calculate volatility (simplified)
            returns = [asset['return_percentage'] for asset in assets]
            volatility = np.std(returns) if returns else 0.0
            
            # Calculate Sharpe ratio
            sharpe_ratio = 0.0
            if volatility > 0:
                excess_return = (total_return_percentage / 100) - self.risk_free_rate
                sharpe_ratio = excess_return / (volatility / 100)
            
            # Calculate max drawdown (simplified)
            max_drawdown = 0.0  # Would be calculated from historical data
            
            # Calculate beta (simplified)
            beta = 1.0  # Would be calculated against market index
            
            # Calculate alpha (simplified)
            alpha = 0.0  # Would be calculated using CAPM
            
            return PortfolioMetrics(
                total_value=total_value,
                total_invested=total_invested,
                unrealized_gains=unrealized_gains,
                realized_gains=realized_gains,
                total_return_percentage=total_return_percentage,
                daily_return=daily_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                beta=beta,
                alpha=alpha
            )
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {str(e)}")
            return PortfolioMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0)
    
    async def _get_asset_price(self, symbol: str) -> float:
        """Get current asset price (mock implementation)"""
        # Mock prices for demo
        mock_prices = {
            'BTC': 43250.50,
            'ETH': 2650.75,
            'SPY': 445.20,
            'QQQ': 380.15,
            'GLD': 185.30,
            'TLT': 95.80,
            'VNQ': 85.40
        }
        
        # Add some random variation for demo
        import random
        base_price = mock_prices.get(symbol, 100.0)
        variation = random.uniform(-0.02, 0.02)  # ±2% variation
        return base_price * (1 + variation)
    
    async def get_portfolio_performance_history(
        self, 
        user_id: str, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get portfolio performance history"""
        try:
            async with get_db_session() as session:
                # Get portfolio
                portfolio_result = await session.execute(
                    select(UserPortfolio).where(UserPortfolio.user_id == user_id)
                )
                portfolio = portfolio_result.scalar_one_or_none()
                
                if not portfolio:
                    return []
                
                # Get performance records
                start_date = datetime.utcnow() - timedelta(days=days)
                performance_result = await session.execute(
                    select(PortfolioPerformance)
                    .where(
                        and_(
                            PortfolioPerformance.portfolio_id == portfolio.id,
                            PortfolioPerformance.date >= start_date
                        )
                    )
                    .order_by(PortfolioPerformance.date)
                )
                
                performance_data = []
                for record in performance_result.scalars().all():
                    performance_data.append({
                        "date": record.date.isoformat(),
                        "total_value": record.total_value,
                        "daily_return": record.daily_return,
                        "cumulative_return": record.cumulative_return,
                        "volatility": record.daily_volatility,
                        "sharpe_ratio": record.sharpe_ratio,
                        "asset_allocation": record.asset_allocation
                    })
                
                return performance_data
                
        except Exception as e:
            logger.error(f"Error getting performance history: {str(e)}")
            return []
    
    async def get_portfolio_statistics(self) -> Dict[str, Any]:
        """Get platform-wide portfolio statistics"""
        try:
            async with get_db_session() as session:
                # Total portfolios
                total_portfolios_result = await session.execute(
                    select(func.count(UserPortfolio.id))
                )
                total_portfolios = total_portfolios_result.scalar() or 0
                
                # Total AUM
                total_aum_result = await session.execute(
                    select(func.sum(UserPortfolio.current_value))
                )
                total_aum = total_aum_result.scalar() or 0.0
                
                # Total invested
                total_invested_result = await session.execute(
                    select(func.sum(UserPortfolio.total_invested))
                )
                total_invested = total_invested_result.scalar() or 0.0
                
                # Average return
                avg_return_result = await session.execute(
                    select(func.avg(UserPortfolio.total_return_percentage))
                )
                avg_return = avg_return_result.scalar() or 0.0
                
                # Top performing assets
                top_assets_result = await session.execute(
                    select(
                        PortfolioAsset.asset_symbol,
                        func.avg(PortfolioAsset.return_percentage).label('avg_return')
                    )
                    .group_by(PortfolioAsset.asset_symbol)
                    .order_by(desc('avg_return'))
                    .limit(5)
                )
                
                top_assets = []
                for symbol, avg_return in top_assets_result:
                    top_assets.append({
                        "symbol": symbol,
                        "average_return": avg_return
                    })
                
                return {
                    "total_portfolios": total_portfolios,
                    "total_aum_usd": total_aum,
                    "total_invested_usd": total_invested,
                    "average_return_percentage": avg_return,
                    "top_performing_assets": top_assets,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting portfolio statistics: {str(e)}")
            return {}
