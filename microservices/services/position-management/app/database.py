#!/usr/bin/env python3
"""
Production Database Configuration for Position Management Service
Supports both PostgreSQL (production) and SQLite (development)
"""

import os
import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Configure structured logging
logger = structlog.get_logger(__name__)

# Database configuration with fallback
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://trading_user:trading_pass@localhost:5432/trading_db"
)

# Fallback to SQLite for development
if not DATABASE_URL.startswith(("postgresql", "sqlite")):
    DATABASE_URL = "sqlite+aiosqlite:///./position_management.db"
    logger.warning("Using SQLite fallback database")

# Database engine configuration
engine_kwargs = {
    "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
    "future": True,
}

# PostgreSQL-specific configuration
if DATABASE_URL.startswith("postgresql"):
    engine_kwargs.update({
        "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "40")),
        "pool_pre_ping": True,
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
        "poolclass": QueuePool,
        "connect_args": {
            "server_settings": {
                "application_name": "position_management_service",
                "jit": "off",  # Disable JIT for better performance with small queries
            },
            "command_timeout": 30,
            "statement_timeout": 30000,  # 30 seconds
        }
    })
# SQLite-specific configuration
elif DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "poolclass": StaticPool,
        "connect_args": {
            "check_same_thread": False,
            "timeout": 30,
        }
    })

# Create async engine
engine = create_async_engine(DATABASE_URL, **engine_kwargs)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Database monitoring
@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries for monitoring."""
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log query execution time."""
    total = time.time() - context._query_start_time
    if total > 0.5:  # Log queries taking more than 500ms
        logger.warning("Slow query detected", 
                      duration=total, 
                      statement=statement[:200])

async def get_db() -> AsyncSession:
    """Dependency to get async database session with proper error handling."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e))
            raise
        finally:
            await session.close()

async def init_db():
    """Initialize database tables with proper error handling."""
    from .models import Base
    
    try:
        # Test database connection first
        async with engine.begin() as conn:
            # Check if we can connect
            await conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database initialized successfully", database_url=DATABASE_URL.split('@')[0])
        
        # Create default admin user if none exists
        await _create_default_admin()
        
    except Exception as e:
        logger.error("❌ Database initialization failed", error=str(e), database_url=DATABASE_URL.split('@')[0])
        raise

async def close_db():
    """Close database connections gracefully."""
    try:
        await engine.dispose()
        logger.info("🔌 Database connections closed successfully")
    except Exception as e:
        logger.error("Error closing database connections", error=str(e))

async def health_check() -> dict:
    """Perform database health check."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return {
                "status": "healthy",
                "database": "connected",
                "engine": str(engine.url).split('@')[0]
            }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

async def _create_default_admin():
    """Create default admin user if none exists."""
    try:
        # Import here to avoid circular imports
        import sys
        sys.path.append('/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot/microservices/services')
        
        from shared.database import User
        from shared.auth import AuthService
        
        async with AsyncSessionLocal() as session:
            # Check if any admin users exist
            result = await session.execute(
                select(User).where(User.is_admin == True)
            )
            admin_exists = result.scalar_one_or_none()
            
            if not admin_exists:
                # Create default admin user
                admin_user = User(
                    username="admin",
                    email="admin@trading-bot.com",
                    password_hash=AuthService.hash_password("admin123"),
                    is_admin=True,
                    is_active=True
                )
                
                session.add(admin_user)
                await session.commit()
                
                logger.info("Default admin user created", username="admin")
                
    except ImportError:
        logger.warning("Could not create default admin user - shared auth module not available")
    except Exception as e:
        logger.error("Error creating default admin user", error=str(e))

# Connection pooling utilities
async def get_pool_status() -> dict:
    """Get connection pool status for monitoring."""
    try:
        pool = engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
        }
    except Exception as e:
        logger.error("Error getting pool status", error=str(e))
        return {"error": str(e)}

# Import required modules
import time
from sqlalchemy import text, select