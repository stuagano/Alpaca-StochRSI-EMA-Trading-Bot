#!/usr/bin/env python3
"""
Database configuration and connection management for Trading Execution Service
"""

import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy_utils import database_exists, create_database
from typing import Generator
import asyncio
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL from environment
DATABASE_URL = os.getenv(
    "TRADING_EXECUTION_DATABASE_URL",
    "postgresql://tradingbot:password@localhost:5432/trading_execution"
)

# Test database for testing
TEST_DATABASE_URL = os.getenv(
    "TEST_TRADING_EXECUTION_DATABASE_URL",
    "postgresql://tradingbot:password@localhost:5432/trading_execution_test"
)

class DatabaseService:
    """Database service for managing connections and sessions"""
    
    def __init__(self, database_url: str = DATABASE_URL, echo: bool = False):
        self.database_url = database_url
        self.echo = echo
        self._engine = None
        self._session_factory = None
        self._initialize()
    
    def _initialize(self):
        """Initialize database engine and session factory"""
        try:
            # Create database if it doesn't exist
            if not database_exists(self.database_url):
                create_database(self.database_url)
                logger.info(f"Created database: {self.database_url}")
            
            # Create engine with connection pooling
            self._engine = create_engine(
                self.database_url,
                echo=self.echo,
                pool_size=20,
                max_overflow=0,
                pool_pre_ping=True,
                pool_recycle=300,  # 5 minutes
                poolclass=QueuePool,
            )
            
            # Add connection event listeners for better error handling
            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                if 'sqlite' in self.database_url:
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()
            
            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            
            logger.info("Database service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database service: {e}")
            raise
    
    @property
    def engine(self):
        """Get database engine"""
        return self._engine
    
    @property
    def session_factory(self):
        """Get session factory"""
        return self._session_factory
    
    def create_tables(self, base=None):
        """Create all tables"""
        if base is None:
            from .models import Base
            base = Base
        
        try:
            base.metadata.create_all(self._engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self, base=None):
        """Drop all tables (use with caution!)"""
        if base is None:
            from .models import Base
            base = Base
        
        try:
            base.metadata.drop_all(self._engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup"""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """Get synchronous database session"""
        return self._session_factory()
    
    def close(self):
        """Close all connections"""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")
    
    def health_check(self) -> bool:
        """Check database health"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def get_connection_info(self) -> dict:
        """Get connection information for monitoring"""
        if not self._engine:
            return {"status": "not_initialized"}
        
        pool = self._engine.pool
        return {
            "status": "healthy" if self.health_check() else "unhealthy",
            "database_url": self.database_url.split('@')[-1],  # Hide credentials
            "pool_size": pool.size(),
            "checked_in_connections": pool.checkedin(),
            "checked_out_connections": pool.checkedout(),
            "overflow_connections": pool.overflow(),
            "invalid_connections": pool.invalid()
        }

# Global database service instance
db_service = DatabaseService()

# FastAPI dependency for getting database sessions
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions"""
    with db_service.get_session() as session:
        yield session

# Async database service for async operations
class AsyncDatabaseService:
    """Async database service for non-blocking operations"""
    
    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
    
    async def execute_in_threadpool(self, func, *args, **kwargs):
        """Execute database operation in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    
    async def health_check(self) -> bool:
        """Async database health check"""
        return await self.execute_in_threadpool(self.db_service.health_check)
    
    async def get_connection_info(self) -> dict:
        """Async get connection info"""
        return await self.execute_in_threadpool(self.db_service.get_connection_info)

# Global async database service
async_db_service = AsyncDatabaseService(db_service)

@lru_cache()
def get_database_service() -> DatabaseService:
    """Get cached database service instance"""
    return db_service

def init_database():
    """Initialize database with tables"""
    try:
        db_service.create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def reset_database():
    """Reset database (drop and recreate all tables)"""
    try:
        db_service.drop_tables()
        db_service.create_tables()
        logger.info("Database reset successfully")
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        raise

# Test database service for testing
class TestDatabaseService(DatabaseService):
    """Test database service with test database"""
    
    def __init__(self):
        super().__init__(database_url=TEST_DATABASE_URL, echo=False)
    
    def setup_test_data(self):
        """Set up test data"""
        # Override in tests if needed
        pass
    
    def cleanup_test_data(self):
        """Clean up test data"""
        try:
            self.drop_tables()
            self.create_tables()
        except Exception as e:
            logger.error(f"Failed to cleanup test data: {e}")

# Context manager for test database
@contextmanager
def test_database():
    """Context manager for test database"""
    test_db = TestDatabaseService()
    try:
        test_db.create_tables()
        yield test_db
    finally:
        test_db.cleanup_test_data()
        test_db.close()

# Migration utilities
class DatabaseMigration:
    """Database migration utilities"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    def create_indexes(self):
        """Create performance indexes"""
        with self.db_service.get_session() as session:
            # Order indexes
            session.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_user_symbol_status 
                ON orders (user_id, symbol, status);
            """)
            
            session.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_created_desc 
                ON orders (created_at DESC);
            """)
            
            session.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_alpaca_id 
                ON orders (alpaca_order_id) WHERE alpaca_order_id IS NOT NULL;
            """)
            
            # Order execution indexes
            session.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_order_timestamp 
                ON order_executions (order_id, timestamp DESC);
            """)
            
            session.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_symbol_timestamp 
                ON order_executions (symbol, timestamp DESC);
            """)
            
            logger.info("Performance indexes created")
    
    def add_columns(self, table_name: str, column_definitions: list):
        """Add new columns to existing table"""
        with self.db_service.get_session() as session:
            for column_def in column_definitions:
                try:
                    session.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
                    logger.info(f"Added column to {table_name}: {column_def}")
                except Exception as e:
                    logger.warning(f"Column may already exist: {e}")
    
    def migrate_data(self):
        """Perform data migrations if needed"""
        # Add migration logic here
        pass

# Initialize migration helper
migration = DatabaseMigration(db_service)

# Startup and shutdown handlers
async def startup_database():
    """Startup handler for database"""
    try:
        init_database()
        migration.create_indexes()
        logger.info("Database startup completed")
    except Exception as e:
        logger.error(f"Database startup failed: {e}")
        raise

async def shutdown_database():
    """Shutdown handler for database"""
    try:
        db_service.close()
        logger.info("Database shutdown completed")
    except Exception as e:
        logger.error(f"Database shutdown failed: {e}")