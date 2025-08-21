#!/usr/bin/env python3
"""
Position Management Service Data Models
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

Base = declarative_base()

class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"

class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"

# SQLAlchemy Models
class PositionDB(Base):
    __tablename__ = "positions"

    id = Column(String, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    side = Column(String, nullable=False)  # long/short
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float)
    entry_time = Column(DateTime(timezone=True), server_default=func.now())
    exit_time = Column(DateTime(timezone=True))
    exit_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float)
    status = Column(String, default=PositionStatus.OPEN)
    strategy = Column(String)
    risk_amount = Column(Float)
    market_value = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    notes = Column(Text)
    broker_order_id = Column(String)
    commission = Column(Float, default=0.0)

# Pydantic Models for API
class PositionBase(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)")
    quantity: int = Field(..., gt=0, description="Number of shares")
    side: PositionSide = Field(..., description="Position side (long/short)")
    entry_price: float = Field(..., gt=0, description="Entry price per share")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    strategy: Optional[str] = Field(None, description="Trading strategy used")
    notes: Optional[str] = Field(None, description="Additional notes")

class PositionCreate(PositionBase):
    """Model for creating a new position"""
    broker_order_id: Optional[str] = Field(None, description="Broker order ID")

class PositionUpdate(BaseModel):
    """Model for updating an existing position"""
    current_price: Optional[float] = Field(None, description="Current market price")
    stop_loss: Optional[float] = Field(None, description="New stop loss price")
    take_profit: Optional[float] = Field(None, description="New take profit price")
    notes: Optional[str] = Field(None, description="Updated notes")

class Position(PositionBase):
    """Complete position model with all fields"""
    id: str
    current_price: Optional[float] = None
    entry_time: datetime
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: Optional[float] = None
    status: PositionStatus
    risk_amount: Optional[float] = None
    market_value: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    broker_order_id: Optional[str] = None
    commission: float = 0.0
    
    # Computed properties
    @property
    def is_profitable(self) -> bool:
        """Check if position is currently profitable"""
        return self.unrealized_pnl > 0 if self.unrealized_pnl else False
    
    @property
    def risk_reward_ratio(self) -> Optional[float]:
        """Calculate risk/reward ratio"""
        if not self.stop_loss or not self.take_profit:
            return None
        
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        
        return reward / risk if risk > 0 else None
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """Calculate unrealized P&L percentage"""
        if not self.current_price:
            return 0.0
        
        if self.side == PositionSide.LONG:
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            return ((self.entry_price - self.current_price) / self.entry_price) * 100

    class Config:
        from_attributes = True

class PortfolioMetrics(BaseModel):
    """Portfolio-level metrics and statistics"""
    total_positions: int = Field(..., description="Total number of positions")
    open_positions: int = Field(..., description="Number of open positions")
    closed_positions: int = Field(..., description="Number of closed positions")
    long_positions: int = Field(..., description="Number of long positions")
    short_positions: int = Field(..., description="Number of short positions")
    
    total_market_value: float = Field(..., description="Total portfolio market value")
    total_unrealized_pnl: float = Field(..., description="Total unrealized P&L")
    total_realized_pnl: float = Field(..., description="Total realized P&L")
    total_pnl: float = Field(..., description="Total P&L (realized + unrealized)")
    
    largest_position_value: float = Field(..., description="Largest position by value")
    largest_position_pct: float = Field(..., description="Largest position as % of portfolio")
    portfolio_concentration: float = Field(..., description="Portfolio concentration ratio")
    
    avg_position_size: float = Field(..., description="Average position size")
    avg_entry_price: float = Field(..., description="Average entry price")
    avg_hold_time_hours: float = Field(..., description="Average holding time in hours")
    
    win_rate: float = Field(..., description="Win rate percentage")
    profit_factor: float = Field(..., description="Profit factor (gross profit / gross loss)")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio if calculable")
    
    positions_at_risk: int = Field(..., description="Positions approaching stop loss")
    positions_near_target: int = Field(..., description="Positions near take profit")
    
    calculated_at: datetime = Field(default_factory=datetime.now, description="Calculation timestamp")

class RiskMetrics(BaseModel):
    """Risk assessment metrics for a position or portfolio"""
    position_id: Optional[str] = None
    risk_level: str = Field(..., description="Low, Medium, High")
    risk_score: float = Field(..., ge=0, le=100, description="Risk score 0-100")
    
    value_at_risk: float = Field(..., description="Value at risk amount")
    var_percentage: float = Field(..., description="VaR as percentage of portfolio")
    
    stop_loss_distance: Optional[float] = Field(None, description="Distance to stop loss")
    take_profit_distance: Optional[float] = Field(None, description="Distance to take profit")
    
    risk_reward_ratio: Optional[float] = Field(None, description="Risk/reward ratio")
    position_size_pct: float = Field(..., description="Position size as % of portfolio")
    
    warnings: List[str] = Field(default_factory=list, description="Risk warnings")
    recommendations: List[str] = Field(default_factory=list, description="Risk recommendations")
    
    calculated_at: datetime = Field(default_factory=datetime.now)

class PositionSummary(BaseModel):
    """Summary view of positions for dashboard"""
    symbol: str
    quantity: int
    side: PositionSide
    entry_price: float
    current_price: Optional[float]
    unrealized_pnl: float
    unrealized_pnl_pct: float
    market_value: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_level: str
    days_held: int

class PositionHistory(BaseModel):
    """Historical position data for analytics"""
    position_id: str
    symbol: str
    timestamp: datetime
    price: float
    unrealized_pnl: float
    market_value: float
    event_type: str  # price_update, level_change, etc.

class BulkPositionUpdate(BaseModel):
    """Model for bulk position updates"""
    position_ids: List[str]
    updates: PositionUpdate

class PositionAlert(BaseModel):
    """Model for position-based alerts"""
    position_id: str
    alert_type: str  # stop_loss_hit, take_profit_hit, risk_warning
    message: str
    severity: str  # info, warning, critical
    triggered_at: datetime
    acknowledged: bool = False