"""
DecentralFund DAO - Configuration Settings
Centralized configuration management for all environment variables and settings
"""

import os
from typing import Optional, List
from pydantic import BaseSettings, validator
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "DecentralFund DAO"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # API Configuration
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "sqlite:///./decentralfund.db"
    TEST_DATABASE_URL: str = "sqlite:///./test.db"
    DATABASE_ECHO: bool = False
    
    # Blockchain Configuration
    WEB3_PROVIDER_URL: str = "http://localhost:8545"
    CHAIN_ID: int = 1337
    FUND_WALLET_ADDRESS: str = "0x742d35Cc6634C0532925a3b8D421327CF80A9da3"
    FUND_PRIVATE_KEY: str = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a2ef4d6d2f1e10e64a5"
    
    # Smart Contract Addresses (will be populated after deployment)
    GOVERNANCE_TOKEN_ADDRESS: Optional[str] = None
    PROPOSAL_MANAGER_ADDRESS: Optional[str] = None
    SIP_MANAGER_ADDRESS: Optional[str] = None
    FUND_MANAGER_REGISTRY_ADDRESS: Optional[str] = None
    DECENTRALFUND_ADDRESS: Optional[str] = None
    
    # External API Keys
    COINMARKETCAP_API_KEY: Optional[str] = None
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    COINGECKO_API_URL: str = "https://api.coingecko.com/api/v3"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: Optional[str] = None
    
    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".png", ".jpg", ".jpeg"]
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Email Configuration (for notifications)
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Security
    BCRYPT_ROUNDS: int = 12
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    
    # Business Logic
    MINIMUM_INVESTMENT: float = 10.0
    MAXIMUM_INVESTMENT: float = 10000.0
    DEFAULT_MANAGEMENT_FEE: float = 1.0  # 1%
    DEFAULT_PERFORMANCE_FEE: float = 15.0  # 15%
    MINIMUM_PROPOSAL_TOKENS: int = 100
    VOTING_DURATION_DAYS: int = 7
    MINIMUM_QUORUM: int = 1000
    MAX_FUND_MANAGERS: int = 7
    MANAGER_TERM_DURATION_DAYS: int = 90
    
    # Frontend Configuration
    STREAMLIT_THEME: str = "light"
    ENABLE_LIVE_UPDATES: bool = True
    REFRESH_INTERVAL_SECONDS: int = 30
    
    # Monitoring & Logging
    SENTRY_DSN: Optional[str] = None
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # Development & Testing
    SEED_DATABASE: bool = True
    MOCK_BLOCKCHAIN: bool = True
    ENABLE_PLAYGROUND: bool = True
    
    @validator('DATABASE_URL')
    def validate_database_url(cls, v):
        if not v:
            raise ValueError('DATABASE_URL is required')
        return v
    
    @validator('SECRET_KEY')
    def validate_secret_key(cls, v, values):
        if values.get('ENVIRONMENT') == 'production' and v == 'dev-secret-key-change-in-production':
            raise ValueError('SECRET_KEY must be changed in production')
        return v
    
    @validator('CORS_ORIGINS', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Global settings instance
settings = get_settings()

# Environment-specific configurations
class DevelopmentConfig(Settings):
    """Development environment configuration"""
    DEBUG = True
    DATABASE_ECHO = True
    LOG_LEVEL = "DEBUG"

class ProductionConfig(Settings):
    """Production environment configuration"""
    DEBUG = False
    DATABASE_ECHO = False
    LOG_LEVEL = "INFO"
    RATE_LIMIT_REQUESTS = 1000
    BCRYPT_ROUNDS = 15

class TestingConfig(Settings):
    """Testing environment configuration"""
    TESTING = True
    DATABASE_URL = "sqlite:///./test.db"
    SECRET_KEY = "test-secret-key"
    MOCK_BLOCKCHAIN = True

def get_config() -> Settings:
    """Get configuration based on environment"""
    env = os.getenv('ENVIRONMENT', 'development').lower()
    
    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()

# Database configuration helpers
def get_database_url() -> str:
    """Get database URL with proper formatting"""
    db_url = settings.DATABASE_URL
    
    # Handle SQLite URLs
    if db_url.startswith('sqlite'):
        return db_url
    
    # Handle PostgreSQL URLs for deployment
    if db_url.startswith('postgres://'):
        # Convert postgres:// to postgresql:// for SQLAlchemy 1.4+
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    return db_url

# Blockchain configuration helpers
def get_web3_config() -> dict:
    """Get Web3 configuration"""
    return {
        'provider_url': settings.WEB3_PROVIDER_URL,
        'chain_id': settings.CHAIN_ID,
        'fund_wallet': settings.FUND_WALLET_ADDRESS,
        'private_key': settings.FUND_PRIVATE_KEY
    }

# Contract addresses helper
def get_contract_addresses() -> dict:
    """Get all deployed contract addresses"""
    return {
        'governance_token': settings.GOVERNANCE_TOKEN_ADDRESS,
        'proposal_manager': settings.PROPOSAL_MANAGER_ADDRESS,
        'sip_manager': settings.SIP_MANAGER_ADDRESS,
        'fund_manager_registry': settings.FUND_MANAGER_REGISTRY_ADDRESS,
        'decentralfund': settings.DECENTRALFUND_ADDRESS
    }

# Logging configuration
def setup_logging():
    """Setup logging configuration"""
    import logging
    import sys
    
    # Set log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper())
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for production
    if settings.ENVIRONMENT == 'production':
        file_handler = logging.FileHandler('decentralfund.log')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy loggers
    logging.getLogger('web3').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

# API configuration
def get_api_config() -> dict:
    """Get API-specific configuration"""
    return {
        'title': settings.APP_NAME,
        'version': settings.VERSION,
        'debug': settings.DEBUG,
        'docs_url': '/docs' if settings.DEBUG else None,
        'redoc_url': '/redoc' if settings.DEBUG else None,
        'cors_origins': settings.CORS_ORIGINS,
        'rate_limit': {
            'enabled': settings.RATE_LIMIT_ENABLED,
            'requests': settings.RATE_LIMIT_REQUESTS,
            'window': settings.RATE_LIMIT_WINDOW
        }
    }

# Validation helpers
def validate_environment():
    """Validate environment configuration"""
    errors = []
    
    # Check required settings
    required_settings = [
        'SECRET_KEY',
        'DATABASE_URL',
        'WEB3_PROVIDER_URL'
    ]
    
    for setting in required_settings:
        if not getattr(settings, setting, None):
            errors.append(f'{setting} is required')
    
    # Production-specific validations
    if settings.ENVIRONMENT == 'production':
        if settings.SECRET_KEY == 'dev-secret-key-change-in-production':
            errors.append('SECRET_KEY must be changed in production')
        
        if not settings.DATABASE_URL.startswith('postgresql'):
            errors.append('PostgreSQL is required for production')
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True

# Initialize logging on import
setup_logging()