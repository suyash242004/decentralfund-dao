# backend/connection.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from backend.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

async def get_db_session():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_database():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # Import comprehensive models
        from backend.models_comprehensive import Base
        await conn.run_sync(Base.metadata.create_all)
        
        # Create indexes
        from backend.models_comprehensive import create_indexes
        indexes = create_indexes()
        for index in indexes:
            try:
                await conn.execute(index)
            except Exception as e:
                print(f"Index creation warning: {e}")