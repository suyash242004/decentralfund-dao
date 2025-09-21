"""
DecentralFund DAO - Database Models
SQLAlchemy models for all entities in the decentralized fund ecosystem
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
import uuid

Base = declarative_base()

# Enums
class UserRole(enum.Enum):
    INVESTOR = "investor"
    FUND_MANAGER = "fund_manager"
    ADMIN = "admin"
    AUDITOR = "auditor"

class ProposalStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"

class ProposalType(enum.Enum):
    PORTFOLIO_CHANGE = "portfolio_change"
    FUND_MANAGER_ELECTION = "fund_manager_election"
    FEE_STRUCTURE = "fee_structure"
    RISK_PARAMETERS = "risk_parameters"
    NEW_ASSET_CLASS = "new_asset_class"
    GOVERNANCE_CHANGE = "governance_change"

class SIPStatus(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class TransactionType(enum.Enum):
    SIP_INVESTMENT = "sip_investment"
    WITHDRAWAL = "withdrawal"
    REBALANCING = "rebalancing"
    FEE_PAYMENT = "fee_payment"
    REWARD_DISTRIBUTION = "reward_distribution"

class AssetType(enum.Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    BOND = "bond"
    COMMODITY = "commodity"
    REIT = "reit"
    INDEX = "index"
    STABLECOIN = "stablecoin"
    NFT = "nft"
    CARBON_CREDIT = "carbon_credit"

# User Management
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_address = Column(String(42), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    username = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(200))
    country = Column(String(100))
    preferred_currency = Column(String(10), default="USD")
    role = Column(SQLEnum(UserRole), default=UserRole.INVESTOR)
    
    # Governance tokens
    governance_tokens = Column(Float, default=0.0)
    voting_power = Column(Float, default=0.0)  # Quadratic voting power
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    kyc_completed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime)
    
    # Relationships
    sip_plans = relationship("SIPPlan", back_populates="user")
    votes = relationship("Vote", back_populates="user")
    portfolio = relationship("UserPortfolio", back_populates="user", uselist=False)
    transactions = relationship("Transaction", back_populates="user")
    proposals_created = relationship("Proposal", back_populates="creator")

class FundManager(Base):
    __tablename__ = "fund_managers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Credentials
    experience_years = Column(Integer)
    education = Column(Text)
    certifications = Column(JSON)  # List of certifications
    previous_performance = Column(JSON)  # Historical performance data
    
    # Current status
    is_elected = Column(Boolean, default=False)
    election_date = Column(DateTime)
    term_end_date = Column(DateTime)
    total_votes_received = Column(Integer, default=0)
    
    # Performance metrics
    portfolio_return = Column(Float, default=0.0)
    risk_adjusted_return = Column(Float, default=0.0)
    assets_under_management = Column(Float, default=0.0)
    
    # Strategy
    investment_philosophy = Column(Text)
    risk_tolerance = Column(String(50))
    specialization = Column(JSON)  # Asset classes they specialize in
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    managed_assets = relationship("PortfolioAsset", back_populates="fund_manager")

# SIP (Systematic Investment Plan) Management
class SIPPlan(Base):
    __tablename__ = "sip_plans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # SIP Details
    amount_per_installment = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    frequency = Column(String(20))  # daily, weekly, monthly
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)  # Optional, for fixed-term SIPs
    
    # Auto-investment settings
    auto_invest = Column(Boolean, default=True)
    compound_returns = Column(Boolean, default=True)
    
    # Status
    status = Column(SQLEnum(SIPStatus), default=SIPStatus.ACTIVE)
    total_invested = Column(Float, default=0.0)
    total_tokens_received = Column(Float, default=0.0)
    next_payment_date = Column(DateTime)
    
    # Performance
    current_value = Column(Float, default=0.0)
    unrealized_gains = Column(Float, default=0.0)
    realized_gains = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sip_plans")
    payments = relationship("SIPPayment", back_populates="sip_plan")

class SIPPayment(Base):
    __tablename__ = "sip_payments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sip_plan_id = Column(String, ForeignKey("sip_plans.id"), nullable=False)
    
    # Payment details
    amount = Column(Float, nullable=False)
    currency = Column(String(10))
    payment_date = Column(DateTime, default=func.now())
    transaction_hash = Column(String(100))  # Blockchain transaction hash
    
    # Token details
    tokens_received = Column(Float)
    token_price_at_purchase = Column(Float)
    
    # Status
    is_successful = Column(Boolean, default=False)
    failure_reason = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime)
    
    # Relationships
    sip_plan = relationship("SIPPlan", back_populates="payments")

# Portfolio Management
class UserPortfolio(Base):
    __tablename__ = "user_portfolios"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Portfolio metrics
    total_invested = Column(Float, default=0.0)
    current_value = Column(Float, default=0.0)
    unrealized_gains = Column(Float, default=0.0)
    realized_gains = Column(Float, default=0.0)
    total_return_percentage = Column(Float, default=0.0)
    
    # Risk metrics
    portfolio_beta = Column(Float, default=1.0)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    volatility = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_rebalanced = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="portfolio")
    assets = relationship("PortfolioAsset", back_populates="portfolio")

class PortfolioAsset(Base):
    __tablename__ = "portfolio_assets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String, ForeignKey("user_portfolios.id"), nullable=False)
    fund_manager_id = Column(String, ForeignKey("fund_managers.id"))
    
    # Asset details
    asset_symbol = Column(String(20), nullable=False)
    asset_name = Column(String(200))
    asset_type = Column(SQLEnum(AssetType))
    
    # Holdings
    quantity = Column(Float, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float)
    total_invested = Column(Float, nullable=False)
    current_value = Column(Float)
    
    # Performance
    unrealized_gains = Column(Float, default=0.0)
    realized_gains = Column(Float, default=0.0)
    return_percentage = Column(Float, default=0.0)
    
    # Allocation
    target_allocation_percentage = Column(Float)  # Target allocation from community voting
    current_allocation_percentage = Column(Float)
    
    # Timestamps
    purchased_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    portfolio = relationship("UserPortfolio", back_populates="assets")
    fund_manager = relationship("FundManager", back_populates="managed_assets")

# DAO Governance
class Proposal(Base):
    __tablename__ = "proposals"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Proposal details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    proposal_type = Column(SQLEnum(ProposalType), nullable=False)
    
    # Voting details
    voting_start_date = Column(DateTime, nullable=False)
    voting_end_date = Column(DateTime, nullable=False)
    minimum_quorum = Column(Integer, default=1000)  # Minimum votes required
    
    # Options (JSON array of voting options)
    voting_options = Column(JSON, nullable=False)
    
    # Status
    status = Column(SQLEnum(ProposalStatus), default=ProposalStatus.DRAFT)
    total_votes = Column(Integer, default=0)
    total_voting_power = Column(Float, default=0.0)
    
    # Results
    winning_option = Column(String(200))
    execution_date = Column(DateTime)
    execution_transaction_hash = Column(String(100))
    
    # Metadata
    ipfs_hash = Column(String(100))  # IPFS hash for detailed proposal data
    category = Column(String(100))
    tags = Column(JSON)  # Array of tags for categorization
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="proposals_created")
    votes = relationship("Vote", back_populates="proposal")

class Vote(Base):
    __tablename__ = "votes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    proposal_id = Column(String, ForeignKey("proposals.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Vote details
    selected_option = Column(String(200), nullable=False)
    voting_power_used = Column(Float, nullable=False)  # Quadratic voting power
    governance_tokens_staked = Column(Float, nullable=False)
    
    # Delegation (if vote was delegated)
    is_delegated = Column(Boolean, default=False)
    delegated_from_user_id = Column(String, ForeignKey("users.id"))
    
    # Transaction
    transaction_hash = Column(String(100))
    block_number = Column(Integer)
    
    # Timestamps
    voted_at = Column(DateTime, default=func.now())
    
    # Relationships
    proposal = relationship("Proposal", back_populates="votes")
    user = relationship("User", back_populates="votes")
    delegated_from = relationship("User", foreign_keys=[delegated_from_user_id])

# Transaction History
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Transaction details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    
    # Asset details (for trading transactions)
    asset_symbol = Column(String(20))
    asset_quantity = Column(Float)
    asset_price = Column(Float)
    
    # Blockchain details
    transaction_hash = Column(String(100), unique=True)
    block_number = Column(Integer)
    gas_fee = Column(Float)
    
    # Status
    is_successful = Column(Boolean, default=True)
    failure_reason = Column(Text)
    
    # Metadata
    description = Column(Text)
    metadata = Column(JSON)  # Additional transaction-specific data
    
    # Timestamps
    initiated_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="transactions")

# Market Data Cache
class MarketData(Base):
    __tablename__ = "market_data"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Asset identification
    symbol = Column(String(20), nullable=False, index=True)
    name = Column(String(200))
    asset_type = Column(SQLEnum(AssetType))
    
    # Price data
    current_price = Column(Float, nullable=False)
    price_change_24h = Column(Float)
    price_change_percentage_24h = Column(Float)
    market_cap = Column(Float)
    volume_24h = Column(Float)
    
    # Technical indicators
    sma_50 = Column(Float)  # 50-day Simple Moving Average
    sma_200 = Column(Float)  # 200-day Simple Moving Average
    rsi = Column(Float)  # Relative Strength Index
    bollinger_upper = Column(Float)
    bollinger_lower = Column(Float)
    
    # Fundamental data (for stocks)
    pe_ratio = Column(Float)
    dividend_yield = Column(Float)
    earnings_per_share = Column(Float)
    
    # Data source and quality
    data_source = Column(String(100))
    data_quality_score = Column(Float)  # 0-1 score
    
    # Timestamps
    last_updated = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())

# AI Analysis Results
class AIAnalysis(Base):
    __tablename__ = "ai_analysis"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Analysis type
    analysis_type = Column(String(100), nullable=False)  # sentiment, portfolio_optimization, risk_assessment
    input_data_hash = Column(String(100))  # Hash of input data for caching
    
    # Results
    analysis_results = Column(JSON, nullable=False)
    confidence_score = Column(Float)
    
    # Context
    market_conditions = Column(JSON)
    community_sentiment = Column(String(20))  # positive, negative, neutral
    
    # Model information
    model_version = Column(String(50))
    model_parameters = Column(JSON)
    
    # Timestamps
    analyzed_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime)  # When this analysis becomes stale

# System Configuration
class SystemConfig(Base):
    __tablename__ = "system_config"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Configuration key-value pairs
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(JSON, nullable=False)
    config_type = Column(String(50))  # governance, risk, fee, technical
    
    # Description and validation
    description = Column(Text)
    validation_rules = Column(JSON)  # Rules for validating config changes
    
    # Change tracking
    previous_value = Column(JSON)
    changed_by_proposal_id = Column(String, ForeignKey("proposals.id"))
    
    # Status
    is_active = Column(Boolean, default=True)
    requires_community_approval = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    effective_date = Column(DateTime)

# Asset Registry (Supported Assets)
class SupportedAsset(Base):
    __tablename__ = "supported_assets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Asset identification
    symbol = Column(String(20), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    asset_type = Column(SQLEnum(AssetType), nullable=False)
    
    # Trading details
    is_tradeable = Column(Boolean, default=True)
    minimum_investment = Column(Float, default=1.0)
    maximum_allocation_percentage = Column(Float, default=10.0)  # Max % of portfolio
    
    # Contract details (for crypto/DeFi)
    contract_address = Column(String(42))
    blockchain_network = Column(String(50))
    decimal_places = Column(Integer, default=18)
    
    # Data sources
    price_feed_url = Column(String(500))
    data_provider = Column(String(100))
    
    # Community approval
    approved_by_proposal_id = Column(String, ForeignKey("proposals.id"))
    community_approval_date = Column(DateTime)
    
    # Risk parameters
    risk_score = Column(Float)  # 1-10 scale
    volatility_score = Column(Float)
    liquidity_score = Column(Float)
    
    # Status
    is_active = Column(Boolean, default=True)
    delisting_date = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# Performance Analytics
class PortfolioPerformance(Base):
    __tablename__ = "portfolio_performance"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String, ForeignKey("user_portfolios.id"), nullable=False)
    
    # Performance metrics
    date = Column(DateTime, nullable=False)
    total_value = Column(Float, nullable=False)
    daily_return = Column(Float)
    cumulative_return = Column(Float)
    
    # Risk metrics
    daily_volatility = Column(Float)
    beta = Column(Float)
    alpha = Column(Float)
    sharpe_ratio = Column(Float)
    
    # Benchmark comparison
    benchmark_return = Column(Float)  # S&P 500 or custom benchmark
    excess_return = Column(Float)  # Portfolio return - benchmark return
    
    # Asset allocation snapshot
    asset_allocation = Column(JSON)  # Snapshot of allocation percentages
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())

# Fee Tracking
class FeeTransaction(Base):
    __tablename__ = "fee_transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Fee details
    fee_type = Column(String(50), nullable=False)  # management, performance, entry, exit
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    fee_percentage = Column(Float)  # What percentage was applied
    
    # Related transaction
    related_transaction_id = Column(String, ForeignKey("transactions.id"))
    
    # Distribution (how fee is distributed)
    fund_manager_share = Column(Float)
    treasury_share = Column(Float)
    burn_amount = Column(Float)  # Tokens burned from fees
    
    # Timestamps
    collected_at = Column(DateTime, default=func.now())
    distributed_at = Column(DateTime)

# Notification System
class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Notification details
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50))  # vote, rebalance, performance, sip
    
    # Status
    is_read = Column(Boolean, default=False)
    is_urgent = Column(Boolean, default=False)
    
    # Actions
    action_url = Column(String(500))  # Optional URL for action
    action_label = Column(String(100))  # Optional action button label
    
    # Metadata
    metadata = Column(JSON)  # Additional notification-specific data
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    read_at = Column(DateTime)
    expires_at = Column(DateTime)

# Database indexes and constraints
def create_indexes():
    """Create database indexes for performance optimization"""
    # This would typically be handled by migrations, but included for completeness
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_wallet_address ON users(wallet_address)",
        "CREATE INDEX IF NOT EXISTS idx_votes_proposal_id ON votes(proposal_id)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_portfolio_performance_date ON portfolio_performance(date)",
        "CREATE INDEX IF NOT EXISTS idx_sip_payments_date ON sip_payments(payment_date)",
        "CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status)",
        "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id, is_read)"
    ]
    return indexes