"""
DecentralFund DAO - AI Service
Machine learning and artificial intelligence services for portfolio optimization,
sentiment analysis, and investment recommendations
"""

import asyncio
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import re

# ML libraries
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
import yfinance as yf

# Text processing
from textblob import TextBlob
import nltk
try:
    nltk.download('punkt', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
except:
    pass

from nltk.sentiment import SentimentIntensityAnalyzer

# Portfolio optimization
try:
    from pypfopt import EfficientFrontier, risk_models, expected_returns
    from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
except ImportError:
    # Fallback for missing dependencies
    EfficientFrontier = None

from backend.config import settings

logger = logging.getLogger(__name__)

@dataclass
class SentimentResult:
    """Sentiment analysis result"""
    sentiment: str  # positive, negative, neutral
    confidence: float
    compound_score: float
    details: Dict[str, float]

@dataclass
class PortfolioRecommendation:
    """Portfolio optimization recommendation"""
    recommended_allocation: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    rebalancing_trades: List[Dict[str, Any]]
    confidence: float

@dataclass
class MarketInsight:
    """AI-generated market insight"""
    title: str
    description: str
    confidence: float
    impact: str  # positive, negative, neutral
    affected_assets: List[str]
    timeframe: str

class AIService:
    """AI and machine learning service for DecentralFund DAO"""
    
    def __init__(self):
        # Initialize sentiment analyzer
        try:
            self.sentiment_analyzer = SentimentIntensityAnalyzer()
        except:
            self.sentiment_analyzer = None
            logger.warning("NLTK sentiment analyzer not available")
        
        # Portfolio optimization settings
        self.risk_free_rate = 0.02  # 2% risk-free rate
        self.lookback_period = 252  # 1 year of trading days
        
        # Asset universe for analysis
        self.supported_assets = {
            'BTC-USD': 'Bitcoin',
            'ETH-USD': 'Ethereum',
            'SPY': 'S&P 500 ETF',
            'QQQ': 'NASDAQ ETF',
            'GLD': 'Gold ETF',
            'TLT': 'Long-term Treasury ETF',
            'VTI': 'Total Stock Market ETF',
            'VXUS': 'International Stocks ETF',
            'BND': 'Bond ETF',
            'VNQ': 'Real Estate ETF'
        }
        
        # ML models cache
        self._models_cache = {}
        self._price_data_cache = {}
        
        logger.info("🤖 AI Service initialized")
    
    async def analyze_sentiment(self, text: str, context: Optional[str] = None) -> SentimentResult:
        """Analyze sentiment of text using multiple methods"""
        try:
            sentiments = {}
            
            # TextBlob analysis
            blob = TextBlob(text)
            textblob_sentiment = blob.sentiment
            sentiments['textblob'] = {
                'polarity': textblob_sentiment.polarity,
                'subjectivity': textblob_sentiment.subjectivity
            }
            
            # NLTK VADER analysis
            if self.sentiment_analyzer:
                vader_scores = self.sentiment_analyzer.polarity_scores(text)
                sentiments['vader'] = vader_scores
            
            # Custom financial sentiment analysis
            financial_sentiment = await self._analyze_financial_sentiment(text)
            sentiments['financial'] = financial_sentiment
            
            # Combine results
            combined_result = await self._combine_sentiment_results(sentiments, context)
            
            logger.info(f"📊 Sentiment analyzed: {combined_result.sentiment} ({combined_result.confidence:.2f})")
            
            return combined_result
            
        except Exception as e:
            logger.error(f"Sentiment analysis error: {str(e)}")
            return SentimentResult(
                sentiment='neutral',
                confidence=0.5,
                compound_score=0.0,
                details={'error': str(e)}
            )
    
    async def _analyze_financial_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment with financial context"""
        # Financial keywords and their sentiment weights
        bullish_keywords = [
            'bullish', 'buy', 'growth', 'profit', 'gain', 'increase', 'positive',
            'strong', 'outperform', 'rally', 'boom', 'surge', 'moon', 'hodl'
        ]
        
        bearish_keywords = [
            'bearish', 'sell', 'loss', 'decline', 'decrease', 'negative',
            'weak', 'crash', 'dump', 'fear', 'panic', 'bubble', 'correction'
        ]
        
        uncertainty_keywords = [
            'uncertain', 'volatile', 'risk', 'concern', 'worry', 'doubt',
            'unclear', 'mixed', 'cautious', 'watchful'
        ]
        
        text_lower = text.lower()
        
        bullish_score = sum(1 for word in bullish_keywords if word in text_lower)
        bearish_score = sum(1 for word in bearish_keywords if word in text_lower)
        uncertainty_score = sum(1 for word in uncertainty_keywords if word in text_lower)
        
        total_score = bullish_score + bearish_score + uncertainty_score
        
        if total_score == 0:
            return {'bullish': 0.33, 'bearish': 0.33, 'uncertain': 0.34}
        
        return {
            'bullish': bullish_score / total_score,
            'bearish': bearish_score / total_score,
            'uncertain': uncertainty_score / total_score
        }
    
    async def _combine_sentiment_results(
        self,
        sentiments: Dict[str, Dict],
        context: Optional[str]
    ) -> SentimentResult:
        """Combine multiple sentiment analysis results"""
        scores = []
        
        # TextBlob contribution
        if 'textblob' in sentiments:
            polarity = sentiments['textblob']['polarity']
            scores.append(polarity)
        
        # VADER contribution
        if 'vader' in sentiments:
            compound = sentiments['vader']['compound']
            scores.append(compound)
        
        # Financial sentiment contribution
        if 'financial' in sentiments:
            financial = sentiments['financial']
            financial_score = financial['bullish'] - financial['bearish']
            scores.append(financial_score)
        
        # Calculate combined score
        if scores:
            compound_score = np.mean(scores)
        else:
            compound_score = 0.0
        
        # Determine sentiment label
        if compound_score >= 0.1:
            sentiment = 'positive'
        elif compound_score <= -0.1:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        # Calculate confidence based on score consistency
        if len(scores) > 1:
            confidence = 1.0 - np.std(scores)
            confidence = max(0.0, min(1.0, confidence))
        else:
            confidence = abs(compound_score)
        
        return SentimentResult(
            sentiment=sentiment,
            confidence=confidence,
            compound_score=compound_score,
            details=sentiments
        )
    
    async def optimize_portfolio(
        self,
        current_allocation: Dict[str, float],
        risk_tolerance: str = 'moderate',
        time_horizon: int = 12,
        expected_returns_override: Optional[Dict[str, float]] = None
    ) -> PortfolioRecommendation:
        """Optimize portfolio allocation using modern portfolio theory"""
        try:
            logger.info(f"🎯 Optimizing portfolio: {risk_tolerance} risk, {time_horizon} months")
            
            # Get price data for assets
            price_data = await self._get_price_data(list(current_allocation.keys()))
            
            if price_data.empty:
                return await self._fallback_portfolio_recommendation(current_allocation)
            
            # Calculate expected returns and covariance matrix
            if expected_returns_override:
                mu = pd.Series(expected_returns_override)
            else:
                mu = expected_returns.mean_historical_return(price_data, frequency=252)
            
            S = risk_models.sample_cov(price_data, frequency=252)
            
            # Optimize portfolio based on risk tolerance
            if EfficientFrontier:
                ef = EfficientFrontier(mu, S)
                
                if risk_tolerance == 'conservative':
                    weights = ef.min_volatility()
                elif risk_tolerance == 'aggressive':
                    weights = ef.max_sharpe(risk_free_rate=self.risk_free_rate)
                else:  # moderate
                    # Target return between min volatility and max sharpe
                    min_vol_weights = ef.min_volatility()
                    ef = EfficientFrontier(mu, S)  # Reset
                    max_sharpe_weights = ef.max_sharpe(risk_free_rate=self.risk_free_rate)
                    
                    # Blend the two strategies
                    weights = {}
                    for asset in min_vol_weights:
                        weights[asset] = 0.6 * min_vol_weights[asset] + 0.4 * max_sharpe_weights[asset]
                
                ef = EfficientFrontier(mu, S)  # Reset for performance calculation
                ef.set_weights(weights)
                performance = ef.portfolio_performance(risk_free_rate=self.risk_free_rate)
                
                expected_return = performance[0]
                volatility = performance[1]
                sharpe_ratio = performance[2]
                
            else:
                # Fallback optimization without pypfopt
                weights = await self._simple_optimization(current_allocation, risk_tolerance)
                expected_return = 0.08  # Mock 8% expected return
                volatility = 0.15  # Mock 15% volatility
                sharpe_ratio = (expected_return - self.risk_free_rate) / volatility
            
            # Generate rebalancing trades
            rebalancing_trades = self._calculate_rebalancing_trades(current_allocation, weights)
            
            # Calculate confidence based on historical performance consistency
            confidence = await self._calculate_recommendation_confidence(weights, price_data)
            
            recommendation = PortfolioRecommendation(
                recommended_allocation=dict(weights),
                expected_return=expected_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                rebalancing_trades=rebalancing_trades,
                confidence=confidence
            )
            
            logger.info(f"✅ Portfolio optimized: Expected return {expected_return:.2%}, Sharpe {sharpe_ratio:.2f}")
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Portfolio optimization error: {str(e)}")
            return await self._fallback_portfolio_recommendation(current_allocation)
    
    async def _get_price_data(self, assets: List[str], period: str = "1y") -> pd.DataFrame:
        """Get historical price data for assets"""
        try:
            # Check cache first
            cache_key = f"{'-'.join(sorted(assets))}_{period}"
            if cache_key in self._price_data_cache:
                cached_data, timestamp = self._price_data_cache[cache_key]
                if datetime.now() - timestamp < timedelta(hours=1):  # 1 hour cache
                    return cached_data
            
            # Map asset symbols to Yahoo Finance symbols
            yf_symbols = []
            for asset in assets:
                if asset in self.supported_assets:
                    yf_symbols.append(asset)
                elif asset.upper() == 'BTC':
                    yf_symbols.append('BTC-USD')
                elif asset.upper() == 'ETH':
                    yf_symbols.append('ETH-USD')
                else:
                    yf_symbols.append(asset)
            
            # Download data
            data = yf.download(yf_symbols, period=period, interval="1d")
            
            if len(yf_symbols) == 1:
                price_data = pd.DataFrame({yf_symbols[0]: data['Adj Close']})
            else:
                price_data = data['Adj Close']
            
            # Cache the data
            self._price_data_cache[cache_key] = (price_data, datetime.now())
            
            return price_data.dropna()
            
        except Exception as e:
            logger.error(f"Error getting price data: {str(e)}")
            return pd.DataFrame()
    
    async def _simple_optimization(self, current_allocation: Dict[str, float], risk_tolerance: str) -> Dict[str, float]:
        """Simple portfolio optimization fallback"""
        assets = list(current_allocation.keys())
        
        if risk_tolerance == 'conservative':
            # Conservative: More bonds, less crypto
            base_weights = {
                'BTC': 0.05, 'ETH': 0.05, 'SPY': 0.30, 'QQQ': 0.15,
                'GLD': 0.15, 'TLT': 0.25, 'VNQ': 0.05
            }
        elif risk_tolerance == 'aggressive':
            # Aggressive: More crypto and growth stocks
            base_weights = {
                'BTC': 0.20, 'ETH': 0.15, 'SPY': 0.25, 'QQQ': 0.25,
                'GLD': 0.05, 'TLT': 0.05, 'VNQ': 0.05
            }
        else:  # moderate
            # Moderate: Balanced allocation
            base_weights = {
                'BTC': 0.10, 'ETH': 0.10, 'SPY': 0.30, 'QQQ': 0.20,
                'GLD': 0.10, 'TLT': 0.15, 'VNQ': 0.05
            }
        
        # Normalize weights for available assets
        available_weights = {asset: base_weights.get(asset, 0) for asset in assets}
        total_weight = sum(available_weights.values())
        
        if total_weight > 0:
            return {asset: weight / total_weight for asset, weight in available_weights.items()}
        else:
            # Equal weight fallback
            equal_weight = 1.0 / len(assets)
            return {asset: equal_weight for asset in assets}
    
    def _calculate_rebalancing_trades(
        self,
        current_allocation: Dict[str, float],
        target_allocation: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Calculate trades needed to rebalance portfolio"""
        trades = []
        
        for asset, target_weight in target_allocation.items():
            current_weight = current_allocation.get(asset, 0)
            weight_diff = target_weight - current_weight
            
            if abs(weight_diff) > 0.01:  # Only trade if difference > 1%
                action = "buy" if weight_diff > 0 else "sell"
                trades.append({
                    "asset": asset,
                    "action": action,
                    "weight_change": abs(weight_diff),
                    "current_weight": current_weight,
                    "target_weight": target_weight
                })
        
        return sorted(trades, key=lambda x: x["weight_change"], reverse=True)
    
    async def _calculate_recommendation_confidence(
        self,
        weights: Dict[str, float],
        price_data: pd.DataFrame
    ) -> float:
        """Calculate confidence in portfolio recommendation"""
        try:
            if price_data.empty:
                return 0.5
            
            # Calculate rolling Sharpe ratios to assess consistency
            returns = price_data.pct_change().dropna()
            
            rolling_sharpe = []
            window = 60  # 60 days rolling window
            
            for i in range(window, len(returns)):
                window_returns = returns.iloc[i-window:i]
                portfolio_returns = (window_returns * pd.Series(weights)).sum(axis=1)
                
                if portfolio_returns.std() > 0:
                    sharpe = (portfolio_returns.mean() - self.risk_free_rate/252) / portfolio_returns.std()
                    rolling_sharpe.append(sharpe)
            
            if rolling_sharpe:
                # Confidence based on Sharpe ratio consistency
                sharpe_std = np.std(rolling_sharpe)
                sharpe_mean = np.mean(rolling_sharpe)
                
                # Higher confidence for consistent positive Sharpe ratios
                consistency_score = 1 / (1 + sharpe_std) if sharpe_std > 0 else 1.0
                performance_score = max(0, min(1, (sharpe_mean + 1) / 2))
                
                confidence = (consistency_score + performance_score) / 2
                return min(0.95, max(0.05, confidence))
            
            return 0.5
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5
    
    async def _fallback_portfolio_recommendation(
        self,
        current_allocation: Dict[str, float]
    ) -> PortfolioRecommendation:
        """Fallback recommendation when optimization fails"""
        # Simple diversified allocation
        assets = list(current_allocation.keys())
        equal_weight = 1.0 / len(assets) if assets else 0
        
        recommended_allocation = {asset: equal_weight for asset in assets}
        rebalancing_trades = self._calculate_rebalancing_trades(current_allocation, recommended_allocation)
        
        return PortfolioRecommendation(
            recommended_allocation=recommended_allocation,
            expected_return=0.08,  # 8% expected return
            volatility=0.15,  # 15% volatility
            sharpe_ratio=0.4,  # (8% - 2%) / 15%
            rebalancing_trades=rebalancing_trades,
            confidence=0.5
        )
    
    async def generate_market_insights(self, assets: List[str] = None) -> List[MarketInsight]:
        """Generate AI-powered market insights"""
        try:
            if assets is None:
                assets = list(self.supported_assets.keys())[:5]  # Top 5 assets
            
            insights = []
            
            # Get recent price data
            price_data = await self._get_price_data(assets, period="3mo")
            
            if not price_data.empty:
                for asset in assets:
                    if asset in price_data.columns:
                        asset_insights = await self._analyze_asset_trends(asset, price_data[asset])
                        insights.extend(asset_insights)
            
            # Add general market insights
            general_insights = await self._generate_general_insights()
            insights.extend(general_insights)
            
            # Sort by confidence and return top insights
            insights.sort(key=lambda x: x.confidence, reverse=True)
            return insights[:10]  # Return top 10 insights
            
        except Exception as e:
            logger.error(f"Error generating market insights: {str(e)}")
            return []
    
    async def _analyze_asset_trends(self, asset: str, prices: pd.Series) -> List[MarketInsight]:
        """Analyze trends for a specific asset"""
        insights = []
        
        try:
            # Calculate technical indicators
            returns = prices.pct_change().dropna()
            
            # Moving averages
            ma_short = prices.rolling(window=20).mean().iloc[-1]
            ma_long = prices.rolling(window=50).mean().iloc[-1]
            current_price = prices.iloc[-1]
            
            # RSI calculation (simplified)
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1] if not rs.iloc[-1] == 0 else 50
            
            # Volatility
            volatility = returns.std() * np.sqrt(252)  # Annualized
            
            # Generate insights based on technical analysis
            if current_price > ma_short > ma_long:
                insights.append(MarketInsight(
                    title=f"{asset} in Strong Uptrend",
                    description=f"Price above both short and long-term moving averages. Current momentum is bullish.",
                    confidence=0.75,
                    impact="positive",
                    affected_assets=[asset],
                    timeframe="short-term"
                ))
            
            if rsi > 70:
                insights.append(MarketInsight(
                    title=f"{asset} Potentially Overbought",
                    description=f"RSI at {rsi:.1f} suggests asset may be overbought. Consider taking profits.",
                    confidence=0.65,
                    impact="negative",
                    affected_assets=[asset],
                    timeframe="short-term"
                ))
            elif rsi < 30:
                insights.append(MarketInsight(
                    title=f"{asset} Potentially Oversold",
                    description=f"RSI at {rsi:.1f} suggests asset may be oversold. Could be buying opportunity.",
                    confidence=0.65,
                    impact="positive",
                    affected_assets=[asset],
                    timeframe="short-term"
                ))
            
            if volatility > 0.3:  # High volatility
                insights.append(MarketInsight(
                    title=f"{asset} High Volatility Alert",
                    description=f"Asset showing {volatility:.1%} annual volatility. Exercise caution.",
                    confidence=0.80,
                    impact="neutral",
                    affected_assets=[asset],
                    timeframe="short-term"
                ))
            
        except Exception as e:
            logger.error(f"Error analyzing {asset}: {str(e)}")
        
        return insights
    
    async def _generate_general_insights(self) -> List[MarketInsight]:
        """Generate general market insights"""
        insights = [
            MarketInsight(
                title="Diversification Benefits",
                description="Current market conditions favor diversified portfolios across asset classes.",
                confidence=0.70,
                impact="positive",
                affected_assets=["SPY", "BTC", "GLD"],
                timeframe="medium-term"
            ),
            MarketInsight(
                title="DeFi Growth Opportunity",
                description="Decentralized finance protocols showing strong fundamentals and growing adoption.",
                confidence=0.60,
                impact="positive",
                affected_assets=["ETH", "BTC"],
                timeframe="long-term"
            ),
            MarketInsight(
                title="Interest Rate Sensitivity",
                description="Bond prices may be sensitive to interest rate changes. Monitor Fed policy.",
                confidence=0.75,
                impact="neutral",
                affected_assets=["TLT", "BND"],
                timeframe="medium-term"
            )
        ]
        
        return insights
    
    async def predict_proposal_outcome(self, proposal_text: str, voting_history: List[Dict]) -> Dict[str, Any]:
        """Predict the outcome of a governance proposal"""
        try:
            # Analyze proposal sentiment
            sentiment = await self.analyze_sentiment(proposal_text)
            
            # Simple prediction based on sentiment and historical patterns
            if sentiment.sentiment == 'positive' and sentiment.confidence > 0.7:
                predicted_outcome = 'pass'
                confidence = 0.75
            elif sentiment.sentiment == 'negative' and sentiment.confidence > 0.7:
                predicted_outcome = 'reject'
                confidence = 0.75
            else:
                predicted_outcome = 'uncertain'
                confidence = 0.50
            
            # Analyze historical voting patterns (simplified)
            if voting_history:
                recent_pass_rate = sum(1 for vote in voting_history[-10:] if vote.get('passed', False)) / min(10, len(voting_history))
            else:
                recent_pass_rate = 0.5
            
            # Adjust prediction based on historical patterns
            if recent_pass_rate > 0.7:
                confidence *= 1.1  # Increase confidence if community is generally supportive
            elif recent_pass_rate < 0.3:
                confidence *= 1.1  # Increase confidence if community is generally skeptical
            
            confidence = min(0.95, confidence)
            
            return {
                'predicted_outcome': predicted_outcome,
                'confidence': confidence,
                'sentiment_analysis': {
                    'sentiment': sentiment.sentiment,
                    'confidence': sentiment.confidence
                },
                'historical_context': {
                    'recent_pass_rate': recent_pass_rate,
                    'similar_proposals': len(voting_history)
                }
            }
            
        except Exception as e:
            logger.error(f"Error predicting proposal outcome: {str(e)}")
            return {
                'predicted_outcome': 'uncertain',
                'confidence': 0.5,
                'error': str(e)
            }
    
    async def generate_investment_report(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive AI-powered investment report"""
        try:
            report = {
                'generated_at': datetime.utcnow().isoformat(),
                'summary': {},
                'performance_analysis': {},
                'risk_assessment': {},
                'recommendations': [],
                'market_outlook': {}
            }
            
            # Portfolio summary
            total_value = portfolio_data.get('total_value', 0)
            total_invested = portfolio_data.get('total_invested', 0)
            current_return = ((total_value - total_invested) / total_invested * 100) if total_invested > 0 else 0
            
            report['summary'] = {
                'total_value': total_value,
                'total_invested': total_invested,
                'unrealized_gains': total_value - total_invested,
                'return_percentage': current_return,
                'risk_level': 'moderate'  # This would be calculated based on portfolio composition
            }
            
            # Performance analysis
            assets = portfolio_data.get('assets', [])
            if assets:
                asset_symbols = [asset['symbol'] for asset in assets]
                price_data = await self._get_price_data(asset_symbols, period="1y")
                
                if not price_data.empty:
                    returns = price_data.pct_change().dropna()
                    portfolio_weights = {asset['symbol']: asset.get('allocation', 0) / 100 for asset in assets}
                    
                    # Calculate portfolio metrics
                    portfolio_returns = (returns * pd.Series(portfolio_weights)).sum(axis=1)
                    annual_return = portfolio_returns.mean() * 252
                    annual_volatility = portfolio_returns.std() * np.sqrt(252)
                    sharpe_ratio = (annual_return - self.risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
                    
                    report['performance_analysis'] = {
                        'annual_return': annual_return,
                        'annual_volatility': annual_volatility,
                        'sharpe_ratio': sharpe_ratio,
                        'max_drawdown': self._calculate_max_drawdown(portfolio_returns),
                        'best_performing_asset': max(assets, key=lambda x: x.get('return', 0))['symbol'],
                        'worst_performing_asset': min(assets, key=lambda x: x.get('return', 0))['symbol']
                    }
            
            # Risk assessment
            report['risk_assessment'] = await self._assess_portfolio_risk(portfolio_data)
            
            # Generate recommendations
            recommendations = await self._generate_portfolio_recommendations(portfolio_data)
            report['recommendations'] = recommendations
            
            # Market outlook
            market_insights = await self.generate_market_insights()
            report['market_outlook'] = {
                'key_insights': [insight.__dict__ for insight in market_insights[:3]],
                'overall_sentiment': 'bullish',  # This would be calculated from insights
                'confidence': 0.75
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating investment report: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        try:
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.cummax()
            drawdown = (cumulative - running_max) / running_max
            return float(drawdown.min())
        except:
            return 0.0
    
    async def _assess_portfolio_risk(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess portfolio risk metrics"""
        try:
            assets = portfolio_data.get('assets', [])
            
            # Asset class diversification
            asset_classes = {}
            for asset in assets:
                asset_class = self._get_asset_class(asset.get('symbol', ''))
                asset_classes[asset_class] = asset_classes.get(asset_class, 0) + asset.get('allocation', 0)
            
            diversification_score = len(asset_classes) / 10  # Max 10 asset classes
            
            # Concentration risk
            max_allocation = max([asset.get('allocation', 0) for asset in assets]) if assets else 0
            concentration_risk = "High" if max_allocation > 20 else ("Medium" if max_allocation > 10 else "Low")
            
            # Geographic diversification
            geographic_diversity = "Medium"  # Simplified
            
            return {
                'diversification_score': diversification_score,
                'concentration_risk': concentration_risk,
                'geographic_diversity': geographic_diversity,
                'asset_class_breakdown': asset_classes,
                'overall_risk_level': 'moderate',
                'risk_score': 0.6  # Scale 0-1
            }
            
        except Exception as e:
            logger.error(f"Risk assessment error: {str(e)}")
            return {'error': str(e)}
    
    def _get_asset_class(self, symbol: str) -> str:
        """Categorize asset by class"""
        if symbol in ['BTC-USD', 'BTC', 'ETH-USD', 'ETH']:
            return 'cryptocurrency'
        elif symbol in ['SPY', 'QQQ', 'VTI', 'VXUS']:
            return 'equity'
        elif symbol in ['TLT', 'BND']:
            return 'fixed_income'
        elif symbol in ['GLD']:
            return 'commodity'
        elif symbol in ['VNQ']:
            return 'real_estate'
        else:
            return 'other'
    
    async def _generate_portfolio_recommendations(self, portfolio_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific portfolio recommendations"""
        recommendations = []
        
        assets = portfolio_data.get('assets', [])
        
        # Check for over-concentration
        for asset in assets:
            if asset.get('allocation', 0) > 15:
                recommendations.append({
                    'type': 'rebalance',
                    'priority': 'medium',
                    'description': f"Consider reducing {asset['symbol']} allocation (currently {asset['allocation']:.1f}%)",
                    'rationale': 'Concentration risk management'
                })
        
        # Check for missing asset classes
        current_classes = set([self._get_asset_class(asset['symbol']) for asset in assets])
        
        if 'fixed_income' not in current_classes:
            recommendations.append({
                'type': 'diversification',
                'priority': 'high',
                'description': 'Consider adding bond allocation for stability',
                'rationale': 'Portfolio lacks fixed income diversification'
            })
        
        if 'cryptocurrency' not in current_classes and len(assets) > 3:
            recommendations.append({
                'type': 'growth',
                'priority': 'low',
                'description': 'Consider small cryptocurrency allocation (5-10%)',
                'rationale': 'Potential for portfolio growth and diversification'
            })
        
        return recommendations