#!/usr/bin/env python3
"""
Risk Management Service Data Models
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

Base = declarative_base()

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(str, Enum):
    POSITION_SIZE = "position_size"
    PORTFOLIO_EXPOSURE = "portfolio_exposure"
    STOP_LOSS_HIT = "stop_loss_hit"
    DRAWDOWN = "drawdown"
    VOLATILITY = "volatility"
    CORRELATION = "correlation"

# SQLAlchemy Models
class RiskEventDB(Base):
    __tablename__ = "risk_events"

    id = Column(String, primary_key=True, index=True)
    event_type = Column(String, nullable=False)  # alert_type
    risk_level = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)  # position, portfolio, symbol
    entity_id = Column(String, nullable=False)
    
    title = Column(String, nullable=False)
    description = Column(Text)
    
    # Risk metrics
    risk_score = Column(Float)
    threshold_breached = Column(Float)
    current_value = Column(Float)
    
    # Context data
    metadata = Column(JSON)
    recommendations = Column(JSON)
    
    # Status
    is_active = Column(Boolean, default=True)
    acknowledged = Column(Boolean, default=False)
    resolved = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))

class RiskMetricsDB(Base):
    __tablename__ = "risk_metrics"

    id = Column(String, primary_key=True, index=True)
    portfolio_id = Column(String, default="default")
    
    # Portfolio metrics
    total_value = Column(Float, nullable=False)
    total_risk_exposure = Column(Float)
    max_drawdown = Column(Float)
    var_95 = Column(Float)  # Value at Risk 95%
    var_99 = Column(Float)  # Value at Risk 99%
    
    # Position metrics
    largest_position_pct = Column(Float)
    concentration_risk = Column(Float)
    sector_concentration = Column(JSON)
    
    # Volatility metrics
    portfolio_volatility = Column(Float)
    beta = Column(Float)
    sharpe_ratio = Column(Float)
    
    # Risk limits
    position_limit_breaches = Column(Integer, default=0)
    exposure_limit_breaches = Column(Integer, default=0)
    
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

# Pydantic Models for API
class RiskLimits(BaseModel):
    """Risk limits configuration"""
    max_position_size_pct: float = Field(default=10.0, description="Max position size as % of portfolio")
    max_portfolio_exposure_pct: float = Field(default=95.0, description="Max portfolio exposure %")
    max_sector_exposure_pct: float = Field(default=25.0, description="Max sector exposure %")
    max_drawdown_pct: float = Field(default=15.0, description="Max allowable drawdown %")
    var_limit_pct: float = Field(default=5.0, description="Value at Risk limit %")
    min_cash_pct: float = Field(default=5.0, description="Minimum cash percentage")
    max_leverage: float = Field(default=1.0, description="Maximum leverage ratio")

class PositionRisk(BaseModel):
    """Risk assessment for a single position"""
    position_id: str
    symbol: str
    current_value: float
    
    # Size risk
    position_size_pct: float = Field(..., description="Position size as % of portfolio")
    is_oversized: bool = Field(..., description="Exceeds position size limit")
    
    # Price risk
    distance_to_stop_loss: Optional[float] = Field(None, description="% distance to stop loss")
    distance_to_take_profit: Optional[float] = Field(None, description="% distance to take profit")
    potential_loss: float = Field(..., description="Maximum potential loss")
    
    # Market risk
    volatility: Optional[float] = Field(None, description="Historical volatility")
    beta: Optional[float] = Field(None, description="Beta vs market")
    
    # Risk scores
    liquidity_risk: float = Field(..., ge=0, le=100, description="Liquidity risk score")
    price_risk: float = Field(..., ge=0, le=100, description="Price risk score")
    overall_risk: float = Field(..., ge=0, le=100, description="Overall risk score")
    risk_level: RiskLevel
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class PortfolioRisk(BaseModel):
    """Risk assessment for entire portfolio"""
    portfolio_id: str = "default"
    total_value: float
    
    # Exposure metrics
    total_exposure_pct: float = Field(..., description="Total market exposure %")
    cash_pct: float = Field(..., description="Cash percentage")
    leverage_ratio: float = Field(..., description="Current leverage ratio")
    
    # Concentration risk
    largest_position_pct: float = Field(..., description="Largest position %")
    top_5_positions_pct: float = Field(..., description="Top 5 positions %")
    concentration_risk_score: float = Field(..., ge=0, le=100)
    
    # Sector/correlation risk
    sector_exposures: Dict[str, float] = Field(default_factory=dict)
    sector_concentration_risk: float = Field(..., ge=0, le=100)
    correlation_risk: float = Field(..., ge=0, le=100)
    
    # Volatility and VaR
    portfolio_volatility: Optional[float] = Field(None, description="Annualized volatility")
    var_95: Optional[float] = Field(None, description="Value at Risk 95%")
    var_99: Optional[float] = Field(None, description="Value at Risk 99%")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")
    
    # Performance metrics
    beta: Optional[float] = Field(None, description="Portfolio beta")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    
    # Overall risk assessment
    overall_risk_score: float = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    
    # Risk events
    active_alerts: int = Field(default=0)
    critical_alerts: int = Field(default=0)
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    calculated_at: datetime = Field(default_factory=datetime.now)

class RiskEvent(BaseModel):
    """Risk event/alert"""
    id: str
    event_type: AlertType
    risk_level: RiskLevel
    entity_type: str  # position, portfolio, symbol
    entity_id: str
    
    title: str
    description: str
    
    # Risk metrics
    risk_score: Optional[float] = Field(None, ge=0, le=100)
    threshold_breached: Optional[float] = None
    current_value: Optional[float] = None
    
    # Context
    metadata: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    
    # Status
    is_active: bool = True
    acknowledged: bool = False
    resolved: bool = False
    
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

class RiskEventCreate(BaseModel):
    """Create new risk event"""
    event_type: AlertType
    risk_level: RiskLevel
    entity_type: str
    entity_id: str
    title: str
    description: str
    risk_score: Optional[float] = None
    threshold_breached: Optional[float] = None
    current_value: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)

class RiskEventUpdate(BaseModel):
    """Update risk event status"""
    acknowledged: Optional[bool] = None
    resolved: Optional[bool] = None
    is_active: Optional[bool] = None

class RiskAssessmentRequest(BaseModel):
    """Request for risk assessment"""
    portfolio_id: str = "default"
    positions: List[Dict[str, Any]] = Field(..., description="List of positions to assess")
    include_portfolio_metrics: bool = True
    include_position_details: bool = True

class RiskReport(BaseModel):
    """Comprehensive risk report"""
    portfolio_risk: PortfolioRisk
    position_risks: List[PositionRisk]
    active_events: List[RiskEvent]
    risk_trends: Dict[str, Any] = Field(default_factory=dict)
    
    # Summary metrics
    total_positions: int
    high_risk_positions: int
    positions_exceeding_limits: int
    
    # Compliance
    limit_breaches: List[str] = Field(default_factory=list)
    compliance_score: float = Field(..., ge=0, le=100)
    
    generated_at: datetime = Field(default_factory=datetime.now)

class RiskConfiguration(BaseModel):
    """Risk management configuration"""
    portfolio_id: str = "default"
    limits: RiskLimits
    
    # Alert thresholds
    position_size_alert_pct: float = 8.0
    exposure_alert_pct: float = 90.0
    volatility_alert_threshold: float = 30.0
    drawdown_alert_pct: float = 10.0
    
    # Monitoring settings
    enable_real_time_monitoring: bool = True
    alert_email: Optional[str] = None
    alert_webhook: Optional[str] = None
    
    # Risk scoring weights
    position_size_weight: float = 0.3
    volatility_weight: float = 0.25
    concentration_weight: float = 0.2
    liquidity_weight: float = 0.15
    correlation_weight: float = 0.1

class RiskMetrics(BaseModel):
    """Detailed risk metrics"""
    portfolio_id: str = "default"
    
    # Basic metrics
    total_value: float
    total_risk_exposure: float
    max_drawdown: Optional[float] = None
    
    # VaR metrics
    var_95: Optional[float] = None
    var_99: Optional[float] = None
    expected_shortfall: Optional[float] = None
    
    # Concentration metrics
    largest_position_pct: float
    concentration_risk: float
    herfindahl_index: Optional[float] = None
    
    # Volatility metrics
    portfolio_volatility: Optional[float] = None
    downside_deviation: Optional[float] = None
    beta: Optional[float] = None
    
    # Performance risk
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_consecutive_losses: Optional[int] = None
    
    # Compliance metrics
    position_limit_breaches: int = 0
    exposure_limit_breaches: int = 0
    
    calculated_at: datetime = Field(default_factory=datetime.now)

class StressTestScenario(BaseModel):
    """Stress testing scenario"""
    name: str
    description: str
    market_shock_pct: float = Field(..., description="Market-wide price shock %")
    volatility_multiplier: float = Field(default=2.0, description="Volatility increase multiplier")
    correlation_increase: float = Field(default=0.2, description="Correlation increase")
    liquidity_reduction_pct: float = Field(default=50.0, description="Liquidity reduction %")

class StressTestResult(BaseModel):
    """Stress test results"""
    scenario: StressTestScenario
    
    # Impact metrics
    portfolio_value_change_pct: float
    portfolio_value_change_usd: float
    positions_at_risk: int
    margin_call_risk: bool
    
    # Risk metrics under stress
    stressed_var_95: float
    stressed_max_drawdown: float
    time_to_liquidation_days: Optional[int] = None
    
    # Position impacts
    worst_affected_positions: List[Dict[str, Any]]
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    
    tested_at: datetime = Field(default_factory=datetime.now)