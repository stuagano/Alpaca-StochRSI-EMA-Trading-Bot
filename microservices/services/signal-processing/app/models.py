#!/usr/bin/env python3
"""
Signal Processing Service Data Models
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

Base = declarative_base()

class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    
class SignalStrength(str, Enum):
    WEAK = "weak"      # 30-50
    MODERATE = "moderate"  # 50-70
    STRONG = "strong"   # 70-85
    VERY_STRONG = "very_strong"  # 85-100

class IndicatorType(str, Enum):
    STOCH_RSI = "stoch_rsi"
    EMA = "ema"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER = "bollinger_bands"
    VOLUME = "volume"
    SMA = "sma"

# SQLAlchemy Models
class SignalDB(Base):
    __tablename__ = "signals"

    id = Column(String, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    signal_type = Column(String, nullable=False)  # buy/sell/hold
    strength = Column(Float, nullable=False)  # 0-100
    confidence = Column(Float, nullable=False)  # 0-100
    strategy = Column(String, nullable=False)
    timeframe = Column(String, nullable=False)  # 1m, 5m, 15m, 1h, 1d
    
    # Price data
    price = Column(Float, nullable=False)
    volume = Column(Integer)
    
    # Indicator values
    stoch_rsi_k = Column(Float)
    stoch_rsi_d = Column(Float)
    ema_short = Column(Float)
    ema_long = Column(Float)
    rsi = Column(Float)
    
    # Signal metadata
    indicators_used = Column(JSON)  # List of indicators that triggered
    conditions_met = Column(JSON)   # Specific conditions satisfied
    
    # Risk parameters
    suggested_stop_loss = Column(Float)
    suggested_take_profit = Column(Float)
    risk_reward_ratio = Column(Float)
    position_size_pct = Column(Float)
    
    # Timing
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    valid_until = Column(DateTime(timezone=True))
    executed_at = Column(DateTime(timezone=True))
    
    # Status tracking
    is_executed = Column(Boolean, default=False)
    execution_price = Column(Float)
    execution_order_id = Column(String)
    
    # Performance tracking
    accuracy_score = Column(Float)  # How accurate this signal was
    outcome = Column(String)  # profit, loss, pending
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Pydantic Models for API
class TechnicalIndicators(BaseModel):
    """Technical indicator values for signal generation"""
    stoch_rsi_k: Optional[float] = Field(None, description="Stochastic RSI %K value")
    stoch_rsi_d: Optional[float] = Field(None, description="Stochastic RSI %D value")
    ema_short: Optional[float] = Field(None, description="Short EMA value")
    ema_long: Optional[float] = Field(None, description="Long EMA value")
    rsi: Optional[float] = Field(None, description="RSI value")
    macd: Optional[float] = Field(None, description="MACD value")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    bb_upper: Optional[float] = Field(None, description="Bollinger Band upper")
    bb_lower: Optional[float] = Field(None, description="Bollinger Band lower")
    volume_ratio: Optional[float] = Field(None, description="Volume vs average ratio")

class MarketData(BaseModel):
    """Market data for signal processing"""
    symbol: str = Field(..., description="Stock symbol")
    price: float = Field(..., description="Current price")
    volume: Optional[int] = Field(None, description="Current volume")
    bid: Optional[float] = Field(None, description="Bid price")
    ask: Optional[float] = Field(None, description="Ask price")
    spread: Optional[float] = Field(None, description="Bid-ask spread")
    timestamp: datetime = Field(default_factory=datetime.now)

class SignalRequest(BaseModel):
    """Request to generate trading signal"""
    symbol: str = Field(..., description="Stock symbol to analyze")
    timeframe: str = Field(default="5m", description="Timeframe (1m, 5m, 15m, 1h, 1d)")
    strategy: str = Field(default="stoch_rsi_ema", description="Strategy to use")
    market_data: Optional[MarketData] = Field(None, description="Current market data")
    indicators: Optional[TechnicalIndicators] = Field(None, description="Pre-calculated indicators")

class TradingSignal(BaseModel):
    """Generated trading signal"""
    id: str
    symbol: str
    signal_type: SignalType
    strength: float = Field(..., ge=0, le=100, description="Signal strength 0-100")
    confidence: float = Field(..., ge=0, le=100, description="Confidence level 0-100")
    strategy: str
    timeframe: str
    
    # Market context
    price: float
    volume: Optional[int] = None
    
    # Technical indicators
    indicators_used: List[str] = Field(default_factory=list)
    conditions_met: List[str] = Field(default_factory=list)
    
    # Risk management
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    position_size_pct: Optional[float] = None
    
    # Timing
    generated_at: datetime
    valid_until: Optional[datetime] = None
    
    # Execution status
    is_executed: bool = False
    execution_price: Optional[float] = None
    execution_order_id: Optional[str] = None
    
    @property
    def strength_category(self) -> SignalStrength:
        """Categorize signal strength"""
        if self.strength >= 85:
            return SignalStrength.VERY_STRONG
        elif self.strength >= 70:
            return SignalStrength.STRONG
        elif self.strength >= 50:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    @property
    def is_actionable(self) -> bool:
        """Check if signal is strong enough to act on"""
        return self.strength >= 70 and self.confidence >= 75
    
    class Config:
        from_attributes = True

class SignalUpdate(BaseModel):
    """Update signal execution status"""
    is_executed: Optional[bool] = None
    execution_price: Optional[float] = None
    execution_order_id: Optional[str] = None
    outcome: Optional[str] = None
    accuracy_score: Optional[float] = None

class SignalAnalysis(BaseModel):
    """Detailed signal analysis"""
    signal_id: str
    analysis_type: str
    timeframe_analysis: Dict[str, Any]
    trend_analysis: Dict[str, Any]
    momentum_analysis: Dict[str, Any]
    volume_analysis: Dict[str, Any]
    risk_analysis: Dict[str, Any]
    recommendation: str
    confidence_factors: List[str]
    risk_factors: List[str]
    generated_at: datetime

class SignalPerformance(BaseModel):
    """Signal performance metrics"""
    strategy: str
    timeframe: str
    total_signals: int
    executed_signals: int
    profitable_signals: int
    
    accuracy_rate: float = Field(..., description="% of profitable signals")
    average_strength: float
    average_confidence: float
    
    avg_profit: float
    avg_loss: float
    profit_factor: float
    
    best_performing_symbols: List[str]
    worst_performing_symbols: List[str]
    
    calculated_at: datetime

class BulkSignalRequest(BaseModel):
    """Request to generate signals for multiple symbols"""
    symbols: List[str] = Field(..., description="List of symbols to analyze")
    timeframe: str = Field(default="5m")
    strategy: str = Field(default="stoch_rsi_ema")
    min_strength: float = Field(default=70, description="Minimum signal strength")
    max_signals: int = Field(default=50, description="Maximum signals to return")

class SignalFilter(BaseModel):
    """Filter criteria for signal queries"""
    symbol: Optional[str] = None
    signal_type: Optional[SignalType] = None
    min_strength: Optional[float] = Field(None, ge=0, le=100)
    max_strength: Optional[float] = Field(None, ge=0, le=100)
    strategy: Optional[str] = None
    timeframe: Optional[str] = None
    is_executed: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

class SignalSummary(BaseModel):
    """Summary of signals for dashboard"""
    total_signals_today: int
    buy_signals: int
    sell_signals: int
    hold_signals: int
    
    avg_strength: float
    avg_confidence: float
    
    strong_signals: int  # strength >= 70
    executed_signals: int
    execution_rate: float
    
    top_symbols: List[Dict[str, Any]]
    latest_signals: List[TradingSignal]
    
    generated_at: datetime