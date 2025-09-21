"""
DecentralFund DAO - Security Service
Handles authentication, authorization, input validation, and security measures
"""

import asyncio
import logging
import hashlib
import secrets
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re
import json

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import select, update, delete, and_, or_, func

from backend.connection import get_db_session
from backend.models_comprehensive import User, Transaction, TransactionType
from backend.config import settings

logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = "your-secret-key-change-in-production"  # Should be from environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token scheme
security = HTTPBearer()

@dataclass
class SecurityEvent:
    """Security event for monitoring"""
    event_type: str
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    details: Dict[str, Any]
    severity: str  # low, medium, high, critical
    timestamp: datetime

@dataclass
class RiskAssessment:
    """Risk assessment for transactions"""
    risk_score: float  # 0-1 scale
    risk_level: str  # low, medium, high, critical
    risk_factors: List[str]
    recommendations: List[str]
    approved: bool

class SecurityService:
    """Service for handling security and authentication"""
    
    def __init__(self):
        self.security_events = []  # In production, store in database
        self.failed_attempts = {}  # Track failed login attempts
        self.blocked_ips = set()  # Blocked IP addresses
        
        # Rate limiting
        self.rate_limits = {}  # IP -> {endpoint: {count: int, reset_time: datetime}}
        
        # Input validation patterns
        self.validation_patterns = {
            'wallet_address': re.compile(r'^0x[a-fA-F0-9]{40}$'),
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'username': re.compile(r'^[a-zA-Z0-9_]{3,20}$'),
            'amount': re.compile(r'^\d+(\.\d{1,2})?$'),
            'proposal_id': re.compile(r'^[a-zA-Z0-9-_]{1,50}$')
        }
        
        logger.info("🔒 Security Service initialized")
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None
    
    async def authenticate_user(self, wallet_address: str, signature: str, message: str) -> Optional[User]:
        """Authenticate user using wallet signature"""
        try:
            # Verify signature (simplified for demo)
            if not self._verify_wallet_signature(wallet_address, signature, message):
                return None
            
            async with get_db_session() as session:
                # Get or create user
                user_result = await session.execute(
                    select(User).where(User.wallet_address == wallet_address)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    # Create new user
                    user = User(
                        wallet_address=wallet_address,
                        username=f"user_{wallet_address[:8]}",
                        is_verified=True
                    )
                    session.add(user)
                    await session.commit()
                
                # Update last login
                user.last_login = datetime.utcnow()
                await session.commit()
                
                return user
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None
    
    def _verify_wallet_signature(self, wallet_address: str, signature: str, message: str) -> bool:
        """Verify wallet signature (simplified for demo)"""
        # In production, use proper signature verification
        # For demo, accept any signature
        return True
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
        """Get current authenticated user"""
        try:
            token = credentials.credentials
            payload = self.verify_token(token)
            
            if payload is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            async with get_db_session() as session:
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if user is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                
                return user
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def validate_input(self, field: str, value: Any, field_type: str) -> Tuple[bool, str]:
        """Validate input data"""
        try:
            if field_type == 'wallet_address':
                if not isinstance(value, str) or not self.validation_patterns['wallet_address'].match(value):
                    return False, "Invalid wallet address format"
            
            elif field_type == 'email':
                if not isinstance(value, str) or not self.validation_patterns['email'].match(value):
                    return False, "Invalid email format"
            
            elif field_type == 'username':
                if not isinstance(value, str) or not self.validation_patterns['username'].match(value):
                    return False, "Username must be 3-20 characters, alphanumeric and underscores only"
            
            elif field_type == 'amount':
                if not isinstance(value, (int, float)) or value <= 0:
                    return False, "Amount must be a positive number"
                if value > 1000000:  # $1M max
                    return False, "Amount exceeds maximum limit"
            
            elif field_type == 'proposal_id':
                if not isinstance(value, str) or not self.validation_patterns['proposal_id'].match(value):
                    return False, "Invalid proposal ID format"
            
            elif field_type == 'voting_option':
                if not isinstance(value, str) or len(value) > 200:
                    return False, "Invalid voting option"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Input validation error: {str(e)}")
            return False, "Validation error"
    
    def sanitize_input(self, value: str) -> str:
        """Sanitize user input to prevent XSS"""
        if not isinstance(value, str):
            return str(value)
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', value)
        sanitized = sanitized.strip()
        
        return sanitized
    
    async def check_rate_limit(self, ip_address: str, endpoint: str, limit: int = 100, window_minutes: int = 60) -> bool:
        """Check if request is within rate limit"""
        try:
            current_time = datetime.utcnow()
            window_start = current_time - timedelta(minutes=window_minutes)
            
            # Clean old entries
            if ip_address in self.rate_limits:
                for ep in list(self.rate_limits[ip_address].keys()):
                    if self.rate_limits[ip_address][ep]['reset_time'] < window_start:
                        del self.rate_limits[ip_address][ep]
            
            # Initialize rate limit tracking
            if ip_address not in self.rate_limits:
                self.rate_limits[ip_address] = {}
            
            if endpoint not in self.rate_limits[ip_address]:
                self.rate_limits[ip_address][endpoint] = {
                    'count': 0,
                    'reset_time': current_time + timedelta(minutes=window_minutes)
                }
            
            # Check limit
            if self.rate_limits[ip_address][endpoint]['count'] >= limit:
                return False
            
            # Increment counter
            self.rate_limits[ip_address][endpoint]['count'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}")
            return True  # Allow on error
    
    async def assess_transaction_risk(
        self, 
        user_id: str, 
        transaction_type: TransactionType, 
        amount: float, 
        metadata: Dict[str, Any]
    ) -> RiskAssessment:
        """Assess risk level of a transaction"""
        try:
            risk_factors = []
            risk_score = 0.0
            
            # Amount-based risk
            if amount > 100000:  # $100K+
                risk_factors.append("High transaction amount")
                risk_score += 0.3
            elif amount > 10000:  # $10K+
                risk_factors.append("Medium transaction amount")
                risk_score += 0.1
            
            # Transaction type risk
            if transaction_type == TransactionType.WITHDRAWAL:
                risk_factors.append("Withdrawal transaction")
                risk_score += 0.2
            
            # User history risk
            async with get_db_session() as session:
                # Check recent transaction frequency
                recent_transactions_result = await session.execute(
                    select(func.count(Transaction.id))
                    .where(
                        and_(
                            Transaction.user_id == user_id,
                            Transaction.initiated_at >= datetime.utcnow() - timedelta(hours=24)
                        )
                    )
                )
                recent_count = recent_transactions_result.scalar() or 0
                
                if recent_count > 10:
                    risk_factors.append("High transaction frequency")
                    risk_score += 0.2
                
                # Check for suspicious patterns
                if recent_count > 50:
                    risk_factors.append("Extremely high transaction frequency")
                    risk_score += 0.4
            
            # Geographic risk (simplified)
            if 'ip_address' in metadata:
                # In production, check against known risky IP ranges
                pass
            
            # Time-based risk
            current_hour = datetime.utcnow().hour
            if current_hour < 6 or current_hour > 22:  # Unusual hours
                risk_factors.append("Transaction during unusual hours")
                risk_score += 0.1
            
            # Determine risk level
            if risk_score >= 0.7:
                risk_level = "critical"
                approved = False
            elif risk_score >= 0.5:
                risk_level = "high"
                approved = False
            elif risk_score >= 0.3:
                risk_level = "medium"
                approved = True
            else:
                risk_level = "low"
                approved = True
            
            # Generate recommendations
            recommendations = []
            if risk_score >= 0.5:
                recommendations.append("Manual review required")
            if amount > 50000:
                recommendations.append("Consider splitting into smaller transactions")
            if recent_count > 20:
                recommendations.append("Monitor for unusual activity")
            
            return RiskAssessment(
                risk_score=risk_score,
                risk_level=risk_level,
                risk_factors=risk_factors,
                recommendations=recommendations,
                approved=approved
            )
            
        except Exception as e:
            logger.error(f"Risk assessment error: {str(e)}")
            return RiskAssessment(0.5, "medium", ["Assessment error"], ["Manual review required"], False)
    
    async def log_security_event(
        self, 
        event_type: str, 
        user_id: Optional[str], 
        ip_address: str, 
        user_agent: str, 
        details: Dict[str, Any], 
        severity: str = "medium"
    ):
        """Log security event for monitoring"""
        try:
            event = SecurityEvent(
                event_type=event_type,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                severity=severity,
                timestamp=datetime.utcnow()
            )
            
            self.security_events.append(event)
            
            # In production, store in database
            logger.warning(f"Security event: {event_type} - {severity} - {details}")
            
            # Alert on critical events
            if severity == "critical":
                await self._send_security_alert(event)
                
        except Exception as e:
            logger.error(f"Error logging security event: {str(e)}")
    
    async def _send_security_alert(self, event: SecurityEvent):
        """Send security alert for critical events"""
        # In production, send to security team
        logger.critical(f"SECURITY ALERT: {event.event_type} - {event.details}")
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for storage"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def validate_wallet_ownership(self, wallet_address: str, signature: str, message: str) -> bool:
        """Validate wallet ownership through signature"""
        # In production, implement proper signature verification
        return True
    
    async def check_user_permissions(self, user: User, required_permission: str) -> bool:
        """Check if user has required permission"""
        try:
            # Basic permission checking
            if required_permission == "create_proposal":
                return user.governance_tokens >= 100
            
            elif required_permission == "vote":
                return user.governance_tokens >= 1
            
            elif required_permission == "fund_manager":
                return user.role.value == "fund_manager"
            
            elif required_permission == "admin":
                return user.role.value == "admin"
            
            return False
            
        except Exception as e:
            logger.error(f"Permission check error: {str(e)}")
            return False
    
    async def audit_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Audit a transaction for compliance"""
        try:
            async with get_db_session() as session:
                transaction_result = await session.execute(
                    select(Transaction).where(Transaction.id == transaction_id)
                )
                transaction = transaction_result.scalar_one_or_none()
                
                if not transaction:
                    return {"success": False, "error": "Transaction not found"}
                
                # Basic audit checks
                audit_results = {
                    "transaction_id": transaction_id,
                    "audit_timestamp": datetime.utcnow().isoformat(),
                    "checks": []
                }
                
                # Amount validation
                if transaction.amount > 0:
                    audit_results["checks"].append({
                        "check": "amount_positive",
                        "status": "pass",
                        "details": "Transaction amount is positive"
                    })
                else:
                    audit_results["checks"].append({
                        "check": "amount_positive",
                        "status": "fail",
                        "details": "Transaction amount is not positive"
                    })
                
                # Currency validation
                if transaction.currency in ["USD", "FUND"]:
                    audit_results["checks"].append({
                        "check": "currency_valid",
                        "status": "pass",
                        "details": f"Currency {transaction.currency} is valid"
                    })
                else:
                    audit_results["checks"].append({
                        "check": "currency_valid",
                        "status": "fail",
                        "details": f"Currency {transaction.currency} is not supported"
                    })
                
                # Timestamp validation
                if transaction.initiated_at <= datetime.utcnow():
                    audit_results["checks"].append({
                        "check": "timestamp_valid",
                        "status": "pass",
                        "details": "Transaction timestamp is valid"
                    })
                else:
                    audit_results["checks"].append({
                        "check": "timestamp_valid",
                        "status": "fail",
                        "details": "Transaction timestamp is in the future"
                    })
                
                # Overall audit status
                failed_checks = [c for c in audit_results["checks"] if c["status"] == "fail"]
                audit_results["overall_status"] = "pass" if not failed_checks else "fail"
                audit_results["failed_checks"] = len(failed_checks)
                
                return audit_results
                
        except Exception as e:
            logger.error(f"Audit error: {str(e)}")
            return {"success": False, "error": f"Audit failed: {str(e)}"}
    
    async def get_security_statistics(self) -> Dict[str, Any]:
        """Get security statistics"""
        try:
            # Count security events by type
            event_counts = {}
            for event in self.security_events:
                event_type = event.event_type
                if event_type not in event_counts:
                    event_counts[event_type] = 0
                event_counts[event_type] += 1
            
            # Count by severity
            severity_counts = {}
            for event in self.security_events:
                severity = event.severity
                if severity not in severity_counts:
                    severity_counts[severity] = 0
                severity_counts[severity] += 1
            
            # Recent events (last 24 hours)
            recent_events = [
                event for event in self.security_events
                if event.timestamp >= datetime.utcnow() - timedelta(hours=24)
            ]
            
            return {
                "total_events": len(self.security_events),
                "recent_events_24h": len(recent_events),
                "event_counts_by_type": event_counts,
                "event_counts_by_severity": severity_counts,
                "blocked_ips": len(self.blocked_ips),
                "rate_limited_ips": len(self.rate_limits),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting security statistics: {str(e)}")
            return {}
