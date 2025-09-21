"""
DecentralFund DAO - Database Connection Management
SQLAlchemy async database connection and session management
"""

import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import event, text
import asyncio

from backend.config import settings, get_database_url

logger = logging.getLogger(__name__)

# Create declarative base
Base = declarative_base()

class DatabaseManager:
    """Database connection and session manager"""
    
    def __init__(self):
        self.engine = None
        self.async_session_factory = None
        self.sync_session_factory = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database engine and session factory"""
        if self._initialized:
            return
        
        database_url = get_database_url()
        logger.info(f"🗄️ Initializing database connection: {database_url.split('@')[-1] if '@' in database_url else database_url}")
        
        # Convert sync URL to async URL
        if database_url.startswith('sqlite'):
            async_url = database_url.replace('sqlite:///', 'sqlite+aiosqlite:///')
            
            # SQLite-specific engine configuration
            self.engine = create_async_engine(
                async_url,
                echo=settings.DATABASE_ECHO,
                pool_pre_ping=True,
                poolclass=StaticPool,
                connect_args={
                    "check_same_thread": False,
                }
            )
        elif database_url.startswith('postgresql'):
            async_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
            
            # PostgreSQL-specific engine configuration
            self.engine = create_async_engine(
                async_url,
                echo=settings.DATABASE_ECHO,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                pool_recycle=3600
            )
        else:
            raise ValueError(f"Unsupported database URL: {database_url}")
        
        # Create session factory
        self.async_session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Setup database event listeners
        self._setup_event_listeners()
        
        self._initialized = True
        logger.info("✅ Database connection initialized successfully")
    
    def _setup_event_listeners(self):
        """Setup database event listeners for optimization"""
        
        @event.listens_for(self.engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance"""
            if 'sqlite' in str(self.engine.url):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=1000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.close()
    
    async def create_tables(self):
        """Create all database tables"""
        if not self._initialized:
            await self.initialize()
        
        logger.info("🏗️ Creating database tables...")
        
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise
    
    async def drop_tables(self):
        """Drop all database tables (for testing)"""
        if not self._initialized:
            await self.initialize()
        
        logger.warning("🗑️ Dropping all database tables...")
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("✅ Database tables dropped")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session context manager"""
        if not self._initialized:
            await self.initialize()
        
        async with self.async_session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {str(e)}")
                raise
            finally:
                await session.close()
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False
    
    async def close(self):
        """Close database engine"""
        if self.engine:
            await self.engine.dispose()
            logger.info("✅ Database connection closed")

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions
async def init_database():
    """Initialize database and create tables"""
    await db_manager.initialize()
    await db_manager.create_tables()

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session (dependency for FastAPI)"""
    async with db_manager.get_session() as session:
        yield session

async def close_database():
    """Close database connections"""
    await db_manager.close()

# Database utilities
async def execute_sql(query: str, params: dict = None) -> any:
    """Execute raw SQL query"""
    async with db_manager.get_session() as session:
        result = await session.execute(text(query), params or {})
        await session.commit()
        return result

async def execute_sql_fetch(query: str, params: dict = None) -> list:
    """Execute SQL query and fetch results"""
    async with db_manager.get_session() as session:
        result = await session.execute(text(query), params or {})
        return result.fetchall()

# Migration utilities
class DatabaseMigration:
    """Database migration utilities"""
    
    @staticmethod
    async def create_indexes():
        """Create database indexes for performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_wallet_address ON users(wallet_address)",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_votes_proposal_id ON votes(proposal_id)",
            "CREATE INDEX IF NOT EXISTS idx_votes_user_id ON votes(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type)",
            "CREATE INDEX IF NOT EXISTS idx_sip_plans_user_id ON sip_plans(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_sip_plans_status ON sip_plans(status)",
            "CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status)",
            "CREATE INDEX IF NOT EXISTS idx_proposals_type ON proposals(proposal_type)",
            "CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_portfolio_performance_date ON portfolio_performance(date)",
            "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id, is_read)"
        ]
        
        for index_sql in indexes:
            try:
                await execute_sql(index_sql)
                logger.info(f"✅ Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                logger.warning(f"Index creation failed: {str(e)}")
    
    @staticmethod
    async def seed_initial_data():
        """Seed database with initial data"""
        from backend.database.models import SystemConfig
        
        async with db_manager.get_session() as session:
            # Check if data already exists
            existing_config = await session.execute(
                text("SELECT COUNT(*) FROM system_config")
            )
            
            if existing_config.scalar() > 0:
                logger.info("Database already seeded, skipping...")
                return
            
            # Initial system configuration
            initial_configs = [
                {
                    'config_key': 'management_fee_percentage',
                    'config_value': {'value': 1.0, 'min': 0.1, 'max': 3.0},
                    'config_type': 'fee',
                    'description': 'Annual management fee percentage',
                    'requires_community_approval': True
                },
                {
                    'config_key': 'performance_fee_percentage',
                    'config_value': {'value': 15.0, 'min': 5.0, 'max': 30.0},
                    'config_type': 'fee',
                    'description': 'Performance fee percentage on profits',
                    'requires_community_approval': True
                },
                {
                    'config_key': 'minimum_quorum',
                    'config_value': {'value': 1000, 'min': 100, 'max': 10000},
                    'config_type': 'governance',
                    'description': 'Minimum voting power required for valid proposals',
                    'requires_community_approval': True
                },
                {
                    'config_key': 'voting_duration_hours',
                    'config_value': {'value': 168, 'min': 24, 'max': 336},  # 7 days default
                    'config_type': 'governance',
                    'description': 'Duration of voting period in hours',
                    'requires_community_approval': True
                },
                {
                    'config_key': 'max_asset_allocation_percentage',
                    'config_value': {'value': 10.0, 'min': 5.0, 'max': 20.0},
                    'config_type': 'risk',
                    'description': 'Maximum allocation percentage for any single asset',
                    'requires_community_approval': True
                }
            ]
            
            for config_data in initial_configs:
                config_sql = text("""
                    INSERT INTO system_config 
                    (id, config_key, config_value, config_type, description, requires_community_approval, is_active, created_at)
                    VALUES (:id, :config_key, :config_value, :config_type, :description, :requires_community_approval, :is_active, datetime('now'))
                """)
                
                import uuid
                import json
                
                await session.execute(config_sql, {
                    'id': str(uuid.uuid4()),
                    'config_key': config_data['config_key'],
                    'config_value': json.dumps(config_data['config_value']),
                    'config_type': config_data['config_type'],
                    'description': config_data['description'],
                    'requires_community_approval': config_data['requires_community_approval'],
                    'is_active': True
                })
            
            await session.commit()
            logger.info("✅ Initial system configuration seeded")

# Connection testing
async def test_database_connection():
    """Test database connection and basic operations"""
    try:
        logger.info("🧪 Testing database connection...")
        
        # Initialize database
        await init_database()
        
        # Test health check
        is_healthy = await db_manager.health_check()
        if not is_healthy:
            raise Exception("Database health check failed")
        
        # Test basic operations
        async with db_manager.get_session() as session:
            # Test SELECT
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            if test_value != 1:
                raise Exception("Basic SELECT test failed")
        
        logger.info("✅ Database connection test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {str(e)}")
        return False

# Backup and restore utilities
class DatabaseBackup:
    """Database backup and restore utilities"""
    
    @staticmethod
    async def backup_to_file(filepath: str):
        """Backup database to file (SQLite only)"""
        if not settings.DATABASE_URL.startswith('sqlite'):
            raise NotImplementedError("Backup only supported for SQLite")
        
        import shutil
        import os
        
        db_path = settings.DATABASE_URL.replace('sqlite:///', '')
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, filepath)
            logger.info(f"✅ Database backed up to {filepath}")
        else:
            raise FileNotFoundError(f"Database file not found: {db_path}")
    
    @staticmethod
    async def restore_from_file(filepath: str):
        """Restore database from file (SQLite only)"""
        if not settings.DATABASE_URL.startswith('sqlite'):
            raise NotImplementedError("Restore only supported for SQLite")
        
        import shutil
        import os
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Backup file not found: {filepath}")
        
        db_path = settings.DATABASE_URL.replace('sqlite:///', '')
        
        # Close existing connections
        await db_manager.close()
        
        # Replace database file
        shutil.copy2(filepath, db_path)
        
        # Reinitialize
        await db_manager.initialize()
        
        logger.info(f"✅ Database restored from {filepath}")

# Export commonly used items
__all__ = [
    'Base',
    'DatabaseManager',
    'db_manager',
    'init_database',
    'get_db_session',
    'close_database',
    'execute_sql',
    'execute_sql_fetch',
    'DatabaseMigration',
    'test_database_connection',
    'DatabaseBackup'
]