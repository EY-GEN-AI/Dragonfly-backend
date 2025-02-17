from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from backend.core.config import settings
import logging
import os
from typing import Optional, AsyncGenerator

class PostgresDB:
    engine: Optional[AsyncEngine] = None
    async_session: Optional[async_sessionmaker[AsyncSession]] = None

    @classmethod
    async def connect_db(cls) -> None:
        """Connect to PostgreSQL database"""
        try:
            if cls.engine is None:
                logging.info("Connecting to PostgreSQL...")
                
                # Modify connection string to use asyncpg
                connection_string = os.getenv('POSTGRES_URL', settings.POSTGRES_URL)
                
                # Ensure the connection string uses asyncpg driver
                if not connection_string.startswith('postgresql+asyncpg://'):
                    connection_string = connection_string.replace('postgresql://', 'postgresql+asyncpg://')
                
                if not connection_string:
                    raise ValueError("PostgreSQL connection string not provided")

                logging.info(f"Connecting to {connection_string}")
                print(f"Connecting to {connection_string}  posttgres")

                # Create async engine with additional SSL parameters for Azure Cosmos
                cls.engine = create_async_engine(
                    connection_string,
                    echo=False,  # Set to True for SQL logging
                    pool_size=10,
                    max_overflow=20,
                    pool_timeout=30,
                    pool_recycle=1800,  # 30 minutes
                    pool_pre_ping=True,
                    connect_args={
                        "ssl": True,
                        "server_settings": {
                            "application_name": "YourAppName"
                        }
                    }
                )

                # Create async session factory
                cls.async_session = async_sessionmaker(
                    cls.engine, 
                    expire_on_commit=False, 
                    class_=AsyncSession
                )

                logging.info("Successfully connected to PostgreSQL")

        except Exception as e:
            logging.error(f"PostgreSQL connection error: {str(e)}")
            if cls.engine:
                await cls.close_db()
            raise

    @classmethod
    async def close_db(cls) -> None:
        """Close PostgreSQL connection"""
        if cls.engine:
            await cls.engine.dispose()
            cls.engine = None
            cls.async_session = None
            logging.info("PostgreSQL connection closed")

    @classmethod
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session"""
        if cls.async_session is None:
            await cls.connect_db()
        
        async with cls.async_session() as session:
            try:
                yield session
            finally:
                await session.close()

    @classmethod
    def is_connected(cls) -> bool:
        """Check if connected to database"""
        return cls.engine is not None and cls.async_session is not None

    @classmethod
    async def ping(cls) -> bool:
        """Test database connection"""
        try:
            if cls.engine:
                async with cls.engine.connect() as conn:
                    await conn.execute("SELECT 1")
                return True
            return False
        except Exception as e:
            logging.error(f"PostgreSQL ping error: {str(e)}")
            return False

# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    """Base class for SQLAlchemy declarative models"""
    pass