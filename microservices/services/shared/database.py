"""
Shared Database Models and Configuration for all Microservices
"""

import os
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, 
    DateTime, ForeignKey, JSON, DECIMAL, BigInteger, 
    CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.sql import func
from contextlib import contextmanager

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trading_user:trading_pass@localhost:5432/trading_db")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Context manager for database sessions
@contextmanager
def get_db() -> Session:
    """Provide a transactional scope for database operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class Position(Base):
    """Position model for tracking trading positions."""
    __tablename__ = "positions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol = Column(String(10), nullable=False, index=True)
    quantity = Column(DECIMAL(18, 8), nullable=False)
    entry_price = Column(DECIMAL(18, 8), nullable=False)
    current_price = Column(DECIMAL(18, 8))
    market_value = Column(DECIMAL(18, 8))
    unrealized_pnl = Column(DECIMAL(18, 8))
    realized_pnl = Column(DECIMAL(18, 8), default=0)
    position_type = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default='OPEN', index=True)
    stop_loss = Column(DECIMAL(18, 8))
    take_profit = Column(DECIMAL(18, 8))
    trailing_stop_percent = Column(DECIMAL(5, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True))
    
    # Relationships
    orders = relationship("Order", back_populates="position", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("position_type IN ('LONG', 'SHORT')", name="check_position_type"),
        CheckConstraint("status IN ('OPEN', 'CLOSED', 'PENDING')", name="check_status"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "symbol": self.symbol,
            "quantity": float(self.quantity),
            "entry_price": float(self.entry_price),
            "current_price": float(self.current_price) if self.current_price else None,
            "market_value": float(self.market_value) if self.market_value else None,
            "unrealized_pnl": float(self.unrealized_pnl) if self.unrealized_pnl else None,
            "realized_pnl": float(self.realized_pnl),
            "position_type": self.position_type,
            "status": self.status,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "take_profit": float(self.take_profit) if self.take_profit else None,
            "trailing_stop_percent": float(self.trailing_stop_percent) if self.trailing_stop_percent else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


class Order(Base):
    """Order model for tracking trading orders."""
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    position_id = Column(UUID(as_uuid=True), ForeignKey('positions.id', ondelete='CASCADE'))
    symbol = Column(String(10), nullable=False, index=True)
    order_type = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(DECIMAL(18, 8), nullable=False)
    limit_price = Column(DECIMAL(18, 8))
    stop_price = Column(DECIMAL(18, 8))
    filled_quantity = Column(DECIMAL(18, 8), default=0)
    filled_avg_price = Column(DECIMAL(18, 8))
    status = Column(String(20), nullable=False, default='PENDING', index=True)
    alpaca_order_id = Column(String(100), unique=True, index=True)
    submitted_at = Column(DateTime(timezone=True))
    filled_at = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    position = relationship("Position", back_populates="orders")
    
    __table_args__ = (
        CheckConstraint("order_type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT', 'TRAILING_STOP')", 
                       name="check_order_type"),
        CheckConstraint("side IN ('BUY', 'SELL')", name="check_side"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "position_id": str(self.position_id) if self.position_id else None,
            "symbol": self.symbol,
            "order_type": self.order_type,
            "side": self.side,
            "quantity": float(self.quantity),
            "limit_price": float(self.limit_price) if self.limit_price else None,
            "stop_price": float(self.stop_price) if self.stop_price else None,
            "filled_quantity": float(self.filled_quantity),
            "filled_avg_price": float(self.filled_avg_price) if self.filled_avg_price else None,
            "status": self.status,
            "alpaca_order_id": self.alpaca_order_id,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Signal(Base):
    """Signal model for tracking trading signals."""
    __tablename__ = "signals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol = Column(String(10), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)
    strategy = Column(String(50), nullable=False)
    strength = Column(DECIMAL(5, 2))
    confidence = Column(DECIMAL(5, 2))
    indicators = Column(JSON)
    metadata = Column(JSON)
    executed = Column(Boolean, default=False, index=True)
    execution_price = Column(DECIMAL(18, 8))
    execution_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        CheckConstraint("signal_type IN ('BUY', 'SELL', 'HOLD', 'CLOSE')", name="check_signal_type"),
        CheckConstraint("strength >= 0 AND strength <= 100", name="check_strength"),
        CheckConstraint("confidence >= 0 AND confidence <= 100", name="check_confidence"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "strategy": self.strategy,
            "strength": float(self.strength) if self.strength else None,
            "confidence": float(self.confidence) if self.confidence else None,
            "indicators": self.indicators,
            "metadata": self.metadata,
            "executed": self.executed,
            "execution_price": float(self.execution_price) if self.execution_price else None,
            "execution_time": self.execution_time.isoformat() if self.execution_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RiskMetric(Base):
    """Risk metrics model for tracking portfolio risk."""
    __tablename__ = "risk_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_value = Column(DECIMAL(18, 8), nullable=False)
    total_exposure = Column(DECIMAL(18, 8), nullable=False)
    risk_score = Column(DECIMAL(5, 2))
    var_daily = Column(DECIMAL(18, 8))
    var_weekly = Column(DECIMAL(18, 8))
    sharpe_ratio = Column(DECIMAL(10, 4))
    max_drawdown = Column(DECIMAL(10, 4))
    win_rate = Column(DECIMAL(5, 2))
    profit_factor = Column(DECIMAL(10, 4))
    metadata = Column(JSON)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="check_risk_score"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "portfolio_value": float(self.portfolio_value),
            "total_exposure": float(self.total_exposure),
            "risk_score": float(self.risk_score) if self.risk_score else None,
            "var_daily": float(self.var_daily) if self.var_daily else None,
            "var_weekly": float(self.var_weekly) if self.var_weekly else None,
            "sharpe_ratio": float(self.sharpe_ratio) if self.sharpe_ratio else None,
            "max_drawdown": float(self.max_drawdown) if self.max_drawdown else None,
            "win_rate": float(self.win_rate) if self.win_rate else None,
            "profit_factor": float(self.profit_factor) if self.profit_factor else None,
            "metadata": self.metadata,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
        }


class MarketData(Base):
    """Market data model for caching price data."""
    __tablename__ = "market_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol = Column(String(10), nullable=False)
    timeframe = Column(String(10), nullable=False)
    open = Column(DECIMAL(18, 8), nullable=False)
    high = Column(DECIMAL(18, 8), nullable=False)
    low = Column(DECIMAL(18, 8), nullable=False)
    close = Column(DECIMAL(18, 8), nullable=False)
    volume = Column(BigInteger, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'timestamp', name='unique_market_data'),
        Index('idx_market_data_symbol_timeframe', 'symbol', 'timeframe'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": int(self.volume),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    api_key = Column(String(255), unique=True)
    api_secret_hash = Column(String(255))
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary (excluding sensitive data)."""
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AuditLog(Base):
    """Audit log model for tracking user actions."""
    __tablename__ = "audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    old_values = Column(JSON)
    new_values = Column(JSON)
    metadata = Column(JSON)
    ip_address = Column(INET)
    user_agent = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id) if self.entity_id else None,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "metadata": self.metadata,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Create all tables (only if they don't exist)
def init_database():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


# Database utility functions
class DatabaseService:
    """Database service for common operations."""
    
    @staticmethod
    def get_session() -> Session:
        """Get a new database session."""
        return SessionLocal()
    
    @staticmethod
    @contextmanager
    def session_scope():
        """Provide a transactional scope for database operations."""
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @staticmethod
    def create_position(session: Session, **kwargs) -> Position:
        """Create a new position."""
        position = Position(**kwargs)
        session.add(position)
        session.flush()
        return position
    
    @staticmethod
    def get_position(session: Session, position_id: str) -> Optional[Position]:
        """Get a position by ID."""
        return session.query(Position).filter(Position.id == position_id).first()
    
    @staticmethod
    def get_open_positions(session: Session) -> list[Position]:
        """Get all open positions."""
        return session.query(Position).filter(Position.status == 'OPEN').all()
    
    @staticmethod
    def create_order(session: Session, **kwargs) -> Order:
        """Create a new order."""
        order = Order(**kwargs)
        session.add(order)
        session.flush()
        return order
    
    @staticmethod
    def create_signal(session: Session, **kwargs) -> Signal:
        """Create a new signal."""
        signal = Signal(**kwargs)
        session.add(signal)
        session.flush()
        return signal
    
    @staticmethod
    def log_audit(session: Session, user_id: Optional[str], action: str, **kwargs) -> AuditLog:
        """Create an audit log entry."""
        audit = AuditLog(user_id=user_id, action=action, **kwargs)
        session.add(audit)
        session.flush()
        return audit