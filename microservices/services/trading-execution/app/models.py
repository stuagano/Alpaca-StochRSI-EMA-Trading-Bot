#!/usr/bin/env python3
"""
Trading Execution Service Data Models
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

Base = declarative_base()

# Enums
class OrderStatus(str, Enum):
    PENDING = "pending"
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    DONE_FOR_DAY = "done_for_day"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REPLACED = "replaced"
    PENDING_CANCEL = "pending_cancel"
    PENDING_REPLACE = "pending_replace"
    ACCEPTED = "accepted"
    PENDING_NEW = "pending_new"
    ACCEPTED_FOR_BIDDING = "accepted_for_bidding"
    STOPPED = "stopped"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    CALCULATED = "calculated"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"  # Good Till Canceled
    OPG = "opg"  # Opening
    CLS = "cls"  # Closing
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill

class OrderClass(str, Enum):
    SIMPLE = "simple"
    BRACKET = "bracket"
    OCO = "oco"  # One Cancels Other
    OTO = "oto"  # One Triggers Other

# SQLAlchemy Models
class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    alpaca_order_id = Column(String, unique=True, nullable=True, index=True)
    client_order_id = Column(String, unique=True, nullable=True, index=True)
    
    # Order Details
    symbol = Column(String, nullable=False, index=True)
    asset_id = Column(String, nullable=True)
    asset_class = Column(String, default="us_equity")
    quantity = Column(Integer, nullable=False)
    notional = Column(Float, nullable=True)  # Dollar amount for fractional shares
    side = Column(String, nullable=False)  # buy/sell
    order_type = Column(String, nullable=False)  # market, limit, etc.
    time_in_force = Column(String, default=TimeInForce.DAY)
    order_class = Column(String, default=OrderClass.SIMPLE)
    
    # Price Information
    limit_price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)
    trail_price = Column(Float, nullable=True)
    trail_percent = Column(Float, nullable=True)
    
    # Execution Details
    filled_qty = Column(Integer, default=0)
    filled_avg_price = Column(Float, nullable=True)
    status = Column(String, default=OrderStatus.PENDING, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    filled_at = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional Information
    extended_hours = Column(Boolean, default=False)
    legs = relationship("OrderLegDB", back_populates="parent_order", cascade="all, delete-orphan")
    
    # Strategy and Risk
    strategy = Column(String, nullable=True)
    risk_category = Column(String, nullable=True)
    max_risk_amount = Column(Float, nullable=True)
    
    # Commission and Fees
    commission = Column(Float, default=0.0)
    fees = Column(Float, default=0.0)
    
    # Metadata
    notes = Column(Text, nullable=True)
    source = Column(String, default="trading-execution-service")
    
    # Error handling
    reject_reason = Column(String, nullable=True)
    cancel_reason = Column(String, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_orders_user_status', 'user_id', 'status'),
        Index('idx_orders_symbol_created', 'symbol', 'created_at'),
        Index('idx_orders_status_updated', 'status', 'updated_at'),
    )

class OrderLegDB(Base):
    __tablename__ = "order_legs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    parent_order = relationship("OrderDB", back_populates="legs")
    
    # Leg Details
    symbol = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    side = Column(String, nullable=False)
    
    # Price Information for bracket orders
    limit_price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OrderExecutionDB(Base):
    __tablename__ = "order_executions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    alpaca_execution_id = Column(String, unique=True, nullable=True)
    
    # Execution Details
    symbol = Column(String, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    side = Column(String, nullable=False)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Commission and Fees
    commission = Column(Float, default=0.0)
    fees = Column(Float, default=0.0)

# Pydantic Models for API
class OrderBase(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)", min_length=1, max_length=10)
    quantity: Optional[int] = Field(None, gt=0, description="Number of shares")
    notional: Optional[float] = Field(None, gt=0, description="Dollar amount for fractional shares")
    side: OrderSide = Field(..., description="Order side (buy/sell)")
    order_type: OrderType = Field(OrderType.MARKET, description="Order type")
    time_in_force: TimeInForce = Field(TimeInForce.DAY, description="Time in force")
    limit_price: Optional[float] = Field(None, gt=0, description="Limit price")
    stop_price: Optional[float] = Field(None, gt=0, description="Stop price")
    trail_price: Optional[float] = Field(None, gt=0, description="Trail price")
    trail_percent: Optional[float] = Field(None, gt=0, le=100, description="Trail percent")
    extended_hours: bool = Field(False, description="Allow extended hours trading")
    client_order_id: Optional[str] = Field(None, description="Client-provided order ID")
    order_class: OrderClass = Field(OrderClass.SIMPLE, description="Order class")
    take_profit_limit_price: Optional[float] = Field(None, description="Take profit limit price")
    stop_loss_stop_price: Optional[float] = Field(None, description="Stop loss stop price")
    stop_loss_limit_price: Optional[float] = Field(None, description="Stop loss limit price")
    
    @validator('quantity', 'notional')
    def quantity_or_notional_required(cls, v, values):
        if 'quantity' in values and 'notional' in values:
            if not values.get('quantity') and not values.get('notional'):
                raise ValueError('Either quantity or notional must be specified')
            if values.get('quantity') and values.get('notional'):
                raise ValueError('Cannot specify both quantity and notional')
        return v
    
    @validator('limit_price')
    def limit_price_required_for_limit_orders(cls, v, values):
        if values.get('order_type') in [OrderType.LIMIT, OrderType.STOP_LIMIT] and not v:
            raise ValueError(f'Limit price required for {values.get("order_type")} orders')
        return v
    
    @validator('stop_price')
    def stop_price_required_for_stop_orders(cls, v, values):
        if values.get('order_type') in [OrderType.STOP, OrderType.STOP_LIMIT] and not v:
            raise ValueError(f'Stop price required for {values.get("order_type")} orders')
        return v

class OrderCreate(OrderBase):
    """Model for creating a new order"""
    strategy: Optional[str] = Field(None, description="Trading strategy name")
    risk_category: Optional[str] = Field(None, description="Risk category")
    max_risk_amount: Optional[float] = Field(None, description="Maximum risk amount")
    notes: Optional[str] = Field(None, max_length=1000, description="Order notes")

class OrderUpdate(BaseModel):
    """Model for updating an order (modify)"""
    quantity: Optional[int] = Field(None, gt=0, description="New quantity")
    limit_price: Optional[float] = Field(None, gt=0, description="New limit price")
    stop_price: Optional[float] = Field(None, gt=0, description="New stop price")
    time_in_force: Optional[TimeInForce] = Field(None, description="New time in force")

class Order(OrderBase):
    """Complete order model with all fields"""
    id: str
    user_id: str
    alpaca_order_id: Optional[str] = None
    asset_id: Optional[str] = None
    asset_class: str = "us_equity"
    filled_qty: int = 0
    filled_avg_price: Optional[float] = None
    status: OrderStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    strategy: Optional[str] = None
    risk_category: Optional[str] = None
    max_risk_amount: Optional[float] = None
    commission: float = 0.0
    fees: float = 0.0
    notes: Optional[str] = None
    source: str = "trading-execution-service"
    reject_reason: Optional[str] = None
    cancel_reason: Optional[str] = None
    
    # Computed properties
    @property
    def remaining_qty(self) -> int:
        """Remaining quantity to be filled"""
        return (self.quantity or 0) - self.filled_qty
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_active(self) -> bool:
        """Check if order is still active"""
        active_statuses = {OrderStatus.PENDING, OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED, 
                          OrderStatus.ACCEPTED, OrderStatus.PENDING_NEW}
        return self.status in active_statuses
    
    @property
    def fill_percentage(self) -> float:
        """Percentage of order filled"""
        if not self.quantity:
            return 0.0
        return (self.filled_qty / self.quantity) * 100
    
    class Config:
        from_attributes = True

class OrderExecution(BaseModel):
    """Model for order execution/fill"""
    id: str
    order_id: str
    alpaca_execution_id: Optional[str] = None
    symbol: str
    quantity: int
    price: float
    side: OrderSide
    timestamp: datetime
    commission: float = 0.0
    fees: float = 0.0
    created_at: datetime
    
    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    """Standard response for order operations"""
    success: bool
    message: str
    order_id: Optional[str] = None
    alpaca_order_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

class OrderListFilter(BaseModel):
    """Filters for listing orders"""
    symbols: Optional[List[str]] = Field(None, description="Filter by symbols")
    status: Optional[List[OrderStatus]] = Field(None, description="Filter by status")
    side: Optional[OrderSide] = Field(None, description="Filter by side")
    order_type: Optional[OrderType] = Field(None, description="Filter by order type")
    strategy: Optional[str] = Field(None, description="Filter by strategy")
    limit: int = Field(100, ge=1, le=500, description="Number of orders to return")
    offset: int = Field(0, ge=0, description="Number of orders to skip")
    start_time: Optional[datetime] = Field(None, description="Start time filter")
    end_time: Optional[datetime] = Field(None, description="End time filter")

class OrderStats(BaseModel):
    """Order statistics and metrics"""
    total_orders: int
    active_orders: int
    filled_orders: int
    canceled_orders: int
    rejected_orders: int
    total_volume: float
    total_value: float
    avg_fill_price: Optional[float]
    success_rate: float
    calculated_at: datetime = Field(default_factory=datetime.now)

class MarketDataQuote(BaseModel):
    """Market data quote model"""
    symbol: str
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    last_price: Optional[float] = None
    last_size: Optional[int] = None
    timestamp: datetime
    
class AccountInfo(BaseModel):
    """Alpaca account information"""
    id: str
    account_number: str
    status: str
    currency: str
    buying_power: float
    regt_buying_power: float
    daytrading_buying_power: float
    cash: float
    portfolio_value: float
    equity: float
    last_equity: float
    multiplier: int
    day_trade_count: int
    pattern_day_trader: bool
    trading_blocked: bool
    transfers_blocked: bool
    account_blocked: bool
    created_at: datetime
    trade_suspended_by_user: bool
    shorting_enabled: bool
    long_market_value: float
    short_market_value: float
    accrued_fees: float
    pending_transfer_in: Optional[float] = None

class WebSocketMessage(BaseModel):
    """WebSocket message structure"""
    type: str  # order_update, execution, account_update, etc.
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = None

class BulkOrderCreate(BaseModel):
    """Model for creating multiple orders at once"""
    orders: List[OrderCreate] = Field(..., min_items=1, max_items=50)
    
class BulkOrderResponse(BaseModel):
    """Response for bulk order operations"""
    success: bool
    message: str
    results: List[OrderResponse]
    total_orders: int
    successful_orders: int
    failed_orders: int