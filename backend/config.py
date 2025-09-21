# backend/config.py
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl
from pathlib import Path
from typing import Optional, List

class Settings(BaseSettings):
    # Web / DB
    APP_NAME: str = "DecentralFund DAO Backend"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database (sqlite by default for local dev)
    DATABASE_URL: str = "sqlite+aiosqlite:///./decentralfund.db"

    # Web3 / blockchain
    WEB3_PROVIDER_URL: str = "http://127.0.0.1:8545"
    CHAIN_ID: int = 1  # Ethereum mainnet
    FUND_WALLET_ADDRESS: Optional[str] = None
    FUND_PRIVATE_KEY: Optional[str] = None
    GAS_PRICE_GWEI: int = 20

    # Contract addresses (will be set after deployment)
    GOVERNANCE_TOKEN_ADDRESS: Optional[str] = None
    PROPOSAL_MANAGER_ADDRESS: Optional[str] = None
    SIP_MANAGER_ADDRESS: Optional[str] = None
    FUND_MANAGER_REGISTRY_ADDRESS: Optional[str] = None
    DECENTRALFUND_ADDRESS: Optional[str] = None

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent
    ARTIFACTS_DIR: Path = BASE_DIR / "artifacts"

    # App behavior
    CORS_ORIGINS: List[str] = [
        "http://localhost:8501", 
        "http://localhost:3000",
        "http://127.0.0.1:8501",
        "http://127.0.0.1:3000"
    ]

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Services
    OPENAI_API_KEY: Optional[str] = None

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_BURST: int = 200

    # Governance
    MIN_PROPOSAL_TOKENS: int = 100
    DEFAULT_QUORUM_PERCENTAGE: float = 0.1
    MAX_VOTING_DURATION_DAYS: int = 30

    # SIP Configuration
    MIN_SIP_AMOUNT: float = 10.0
    MAX_SIP_AMOUNT: float = 10000.0

    # Portfolio Configuration
    MAX_SINGLE_ASSET_ALLOCATION: float = 0.15
    REBALANCING_THRESHOLD: float = 0.05

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from environment

settings = Settings()
