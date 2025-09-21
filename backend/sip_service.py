"""
DecentralFund DAO - SIP (Systematic Investment Plan) Service
Handles automated recurring investments and token distribution
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SIPCreationRequest:
    """Request to create a new SIP plan"""
    user_id: str
    amount_per_installment: float
    frequency_days: int
    duration_months: Optional[int] = None
    auto_compound: bool = True
    preferred_currency: str = "USD"

@dataclass
class SIPPaymentResult:
    """Result of SIP payment processing"""
    success: bool
    payment_id: Optional[str] = None
    tokens_minted: float = 0.0
    transaction_hash: Optional[str] = None
    error_message: Optional[str] = None

class SIPService:
    """Service for managing Systematic Investment Plans"""
    
    def __init__(self, blockchain_service=None):
        self.blockchain = blockchain_service
        
        # SIP configuration
        self.min_investment = 10.0
        self.max_investment = 10000.0
        self.supported_frequencies = {
            'daily': 1,
            'weekly': 7,
            'monthly': 30
        }
        
        # Token price calculation (simplified for demo)
        self.base_token_price = 1.0  # 1 USD = 1 FUND token initially
        
    async def create_sip_plan(self, request: SIPCreationRequest) -> Dict[str, Any]:
        """Create a new SIP plan for a user"""
        try:
            # Validate request
            validation_result = await self._validate_sip_request(request)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error']
                }
            
            # For demo, create mock SIP plan
            sip_id = f"SIP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            logger.info(f"✅ SIP plan created: {sip_id} for user {request.user_id}")
            
            return {
                'success': True,
                'sip_id': sip_id,
                'first_payment': {
                    'payment_id': f"PAY-{sip_id}",
                    'tokens_minted': request.amount_per_installment,
                    'transaction_hash': f"0xdemo{hash(sip_id)}"
                },
                'next_payment_date': (datetime.utcnow() + timedelta(days=request.frequency_days)).isoformat(),
                'projected_returns': await self._calculate_projected_returns(request)
            }
                    
        except Exception as e:
            logger.error(f"Error creating SIP plan: {str(e)}")
            return {
                'success': False,
                'error': f'Internal error: {str(e)}'
            }
    
    async def _validate_sip_request(self, request: SIPCreationRequest) -> Dict[str, Any]:
        """Validate SIP creation request"""
        if request.amount_per_installment < self.min_investment:
            return {
                'valid': False,
                'error': f'Minimum investment is ${self.min_investment}'
            }
        
        if request.amount_per_installment > self.max_investment:
            return {
                'valid': False,
                'error': f'Maximum investment is ${self.max_investment}'
            }
        
        if request.frequency_days < 1:
            return {
                'valid': False,
                'error': 'Frequency must be at least 1 day'
            }
        
        if request.duration_months and request.duration_months < 1:
            return {
                'valid': False,
                'error': 'Duration must be at least 1 month'
            }
        
        return {'valid': True}
    
    async def _get_current_token_price(self) -> float:
        """Get current FUND token price"""
        # For demo, use base price with small random variation
        import random
        variation = random.uniform(-0.05, 0.05)  # ±5% variation
        return self.base_token_price * (1 + variation)
    
    async def _calculate_projected_returns(self, request) -> Dict[str, float]:
        """Calculate projected returns for a SIP plan"""
        # Assumptions for projection
        annual_return_rate = 0.12  # 12% annual return
        frequency_per_year = 12  # Monthly for simplification
        
        years = request.duration_months / 12 if request.duration_months else 5
        
        total_periods = int(frequency_per_year * years)
        monthly_rate = annual_return_rate / frequency_per_year
        
        # SIP future value formula
        if monthly_rate > 0:
            future_value = request.amount_per_installment * (
                ((1 + monthly_rate) ** total_periods - 1) / monthly_rate
            ) * (1 + monthly_rate)
        else:
            future_value = request.amount_per_installment * total_periods
        
        total_invested = request.amount_per_installment * total_periods
        projected_profit = future_value - total_invested
        
        return {
            'total_invested': total_invested,
            'projected_value': future_value,
            'projected_profit': projected_profit,
            'projected_return_percentage': (projected_profit / total_invested) * 100 if total_invested > 0 else 0,
            'projection_years': years
        }
    
    async def get_user_sip_plans(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all SIP plans for a user"""
        try:
            # For demo, return mock data
            return [
                {
                    'id': 'SIP-001',
                    'amount_per_installment': 500,
                    'currency': 'USD',
                    'frequency': 'Monthly',
                    'status': 'Active',
                    'start_date': '2024-01-15',
                    'total_invested': 4000,
                    'total_tokens_received': 4000,
                    'current_value': 4320,
                    'unrealized_gains': 320,
                    'return_percentage': 8.0,
                    'installments_paid': 8,
                    'recent_payments': [
                        {
                            'id': 'PAY-001',
                            'amount': 500,
                            'tokens_received': 500,
                            'payment_date': '2024-09-15',
                            'is_successful': True
                        }
                    ],
                    'projected_returns': {
                        'total_invested': 60000,
                        'projected_value': 75000,
                        'projected_profit': 15000,
                        'projected_return_percentage': 25.0,
                        'projection_years': 10
                    }
                }
            ]
        except Exception as e:
            logger.error(f"Error getting user SIP plans: {str(e)}")
            return []
    
    async def pause_sip_plan(self, sip_id: str, user_id: str) -> Dict[str, Any]:
        """Pause a SIP plan"""
        try:
            logger.info(f"⏸️ SIP plan paused: {sip_id}")
            return {
                'success': True,
                'message': 'SIP plan paused successfully'
            }
        except Exception as e:
            logger.error(f"Error pausing SIP plan: {str(e)}")
            return {'success': False, 'error': f'Internal error: {str(e)}'}
    
    async def resume_sip_plan(self, sip_id: str, user_id: str) -> Dict[str, Any]:
        """Resume a paused SIP plan"""
        try:
            logger.info(f"▶️ SIP plan resumed: {sip_id}")
            return {
                'success': True,
                'message': 'SIP plan resumed successfully',
                'next_payment_date': (datetime.utcnow() + timedelta(days=30)).isoformat()
            }
        except Exception as e:
            logger.error(f"Error resuming SIP plan: {str(e)}")
            return {'success': False, 'error': f'Internal error: {str(e)}'}
    
    async def cancel_sip_plan(self, sip_id: str, user_id: str) -> Dict[str, Any]:
        """Cancel a SIP plan"""
        try:
            logger.info(f"❌ SIP plan cancelled: {sip_id}")
            return {
                'success': True,
                'message': 'SIP plan cancelled successfully'
            }
        except Exception as e:
            logger.error(f"Error cancelling SIP plan: {str(e)}")
            return {'success': False, 'error': f'Internal error: {str(e)}'}
    
    async def get_sip_statistics(self) -> Dict[str, Any]:
        """Get platform-wide SIP statistics"""
        try:
            return {
                'active_sips': 1250,
                'total_invested': 5420000.0,
                'average_investment': 275.50,
                'new_sips_last_month': 150,
                'total_tokens_distributed': 5400000.0,
                'success_rate': 98.5
            }
        except Exception as e:
            logger.error(f"Error getting SIP statistics: {str(e)}")
            return {}