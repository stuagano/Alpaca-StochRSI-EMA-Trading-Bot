import yaml
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional
from enum import Enum
import os


class RiskLevel(Enum):
    """Risk level configurations"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class PositionSizingMethod(Enum):
    """Position sizing methods"""
    FIXED_PERCENTAGE = "fixed_percentage"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    KELLY_CRITERION = "kelly_criterion"
    RISK_PARITY = "risk_parity"
    ATR_BASED = "atr_based"
    ADAPTIVE = "adaptive"


class StopLossMethod(Enum):
    """Stop loss calculation methods"""
    PERCENTAGE = "percentage"
    ATR_BASED = "atr_based"
    VOLATILITY_BASED = "volatility_based"
    SUPPORT_RESISTANCE = "support_resistance"
    ADAPTIVE = "adaptive"


class TrailingStopMethod(Enum):
    """Trailing stop methods"""
    PERCENTAGE = "percentage"
    ATR_BASED = "atr_based"
    VOLATILITY_BASED = "volatility_based"
    ADAPTIVE = "adaptive"


class RiskConfig(BaseModel):
    """
    Comprehensive risk management configuration
    """
    
    # ============================================================================
    # PORTFOLIO-LEVEL RISK LIMITS
    # ============================================================================
    
    # Maximum portfolio exposure (percentage of total portfolio value)
    max_portfolio_exposure: float = Field(
        default=0.95,
        ge=0.1,
        le=1.0,
        description="Maximum portfolio exposure as fraction (0.95 = 95%)"
    )
    
    # Maximum daily loss as percentage of portfolio
    max_daily_loss: float = Field(
        default=0.05,
        ge=0.01,
        le=0.20,
        description="Maximum daily loss as fraction (0.05 = 5%)"
    )
    
    # Maximum drawdown before emergency stop
    max_drawdown: float = Field(
        default=0.15,
        ge=0.05,
        le=0.50,
        description="Maximum drawdown as fraction (0.15 = 15%)"
    )
    
    # Maximum number of open positions
    max_positions: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of open positions"
    )
    
    # Maximum correlation exposure (percentage of portfolio in correlated assets)
    max_correlation_exposure: float = Field(
        default=0.60,
        ge=0.1,
        le=1.0,
        description="Maximum correlation exposure as fraction (0.60 = 60%)"
    )
    
    # ============================================================================
    # POSITION-LEVEL RISK LIMITS
    # ============================================================================
    
    # Maximum single position size as percentage of portfolio
    max_position_size: float = Field(
        default=0.20,
        ge=0.01,
        le=0.50,
        description="Maximum single position size as fraction (0.20 = 20%)"
    )
    
    # Minimum position size as percentage of portfolio
    min_position_size: float = Field(
        default=0.001,
        ge=0.0001,
        le=0.10,
        description="Minimum position size as fraction (0.001 = 0.1%)"
    )
    
    # Default risk per trade
    default_risk_per_trade: float = Field(
        default=0.02,
        ge=0.001,
        le=0.10,
        description="Default risk per trade as fraction (0.02 = 2%)"
    )
    
    # ============================================================================
    # STOP LOSS CONFIGURATION
    # ============================================================================
    
    # Use ATR-based stop losses
    use_atr_stop_loss: bool = Field(
        default=True,
        description="Use ATR-based stop loss calculation"
    )
    
    # ATR period for calculations
    atr_period: int = Field(
        default=14,
        ge=5,
        le=50,
        description="ATR calculation period in days"
    )
    
    # ATR multiplier for stop loss distance
    atr_multiplier: float = Field(
        default=2.0,
        ge=0.5,
        le=10.0,
        description="ATR multiplier for stop loss distance"
    )
    
    # Default stop loss distance (when ATR not available)
    default_stop_loss_distance: float = Field(
        default=0.05,
        ge=0.01,
        le=0.50,
        description="Default stop loss distance as fraction (0.05 = 5%)"
    )
    
    # Minimum stop loss distance
    min_stop_loss_distance: float = Field(
        default=0.005,
        ge=0.001,
        le=0.10,
        description="Minimum stop loss distance as fraction (0.005 = 0.5%)"
    )
    
    # Maximum stop loss distance
    max_stop_loss_distance: float = Field(
        default=0.20,
        ge=0.05,
        le=0.50,
        description="Maximum stop loss distance as fraction (0.20 = 20%)"
    )
    
    # Stop loss calculation method
    stop_loss_method: StopLossMethod = Field(
        default=StopLossMethod.ATR_BASED,
        description="Method for calculating stop losses"
    )
    
    # ============================================================================
    # TRAILING STOP CONFIGURATION
    # ============================================================================
    
    # Enable trailing stops
    enable_trailing_stops: bool = Field(
        default=True,
        description="Enable trailing stop functionality"
    )
    
    # Trailing stop distance
    trailing_stop_distance: float = Field(
        default=0.03,
        ge=0.005,
        le=0.20,
        description="Trailing stop distance as fraction (0.03 = 3%)"
    )
    
    # Profit threshold to activate trailing stop
    trailing_activation_threshold: float = Field(
        default=0.02,
        ge=0.005,
        le=0.50,
        description="Profit threshold to activate trailing stop (0.02 = 2%)"
    )
    
    # Trailing stop method
    trailing_stop_method: TrailingStopMethod = Field(
        default=TrailingStopMethod.PERCENTAGE,
        description="Method for calculating trailing stops"
    )
    
    # ============================================================================
    # POSITION SIZING CONFIGURATION
    # ============================================================================
    
    # Use ATR-based position sizing
    use_atr_position_sizing: bool = Field(
        default=True,
        description="Use ATR-based position sizing"
    )
    
    # Position sizing method
    position_sizing_method: PositionSizingMethod = Field(
        default=PositionSizingMethod.VOLATILITY_ADJUSTED,
        description="Default position sizing method"
    )
    
    # Target portfolio volatility for volatility-adjusted sizing
    target_portfolio_volatility: float = Field(
        default=0.15,
        ge=0.05,
        le=0.50,
        description="Target portfolio volatility for sizing (0.15 = 15%)"
    )
    
    # Kelly fraction multiplier (for Kelly criterion sizing)
    kelly_fraction_multiplier: float = Field(
        default=0.5,
        ge=0.1,
        le=1.0,
        description="Kelly fraction multiplier for conservative Kelly sizing"
    )
    
    # ============================================================================
    # CORRELATION AND CONCENTRATION LIMITS
    # ============================================================================
    
    # Maximum correlation threshold
    max_correlation_threshold: float = Field(
        default=0.7,
        ge=0.1,
        le=0.95,
        description="Maximum correlation threshold for new positions"
    )
    
    # Maximum sector concentration
    max_sector_concentration: float = Field(
        default=0.40,
        ge=0.1,
        le=0.80,
        description="Maximum sector concentration as fraction (0.40 = 40%)"
    )
    
    # Maximum single stock concentration
    max_single_stock_concentration: float = Field(
        default=0.15,
        ge=0.05,
        le=0.50,
        description="Maximum single stock concentration (0.15 = 15%)"
    )
    
    # ============================================================================
    # VOLATILITY AND VAR LIMITS
    # ============================================================================
    
    # Maximum portfolio VaR (95% confidence)
    max_portfolio_var_95: float = Field(
        default=0.10,
        ge=0.02,
        le=0.30,
        description="Maximum portfolio VaR 95% as fraction (0.10 = 10%)"
    )
    
    # Maximum portfolio volatility (annualized)
    max_portfolio_volatility: float = Field(
        default=0.30,
        ge=0.10,
        le=1.0,
        description="Maximum portfolio volatility (0.30 = 30%)"
    )
    
    # VaR calculation method
    var_calculation_method: str = Field(
        default="historical",
        description="VaR calculation method (historical, parametric, monte_carlo)"
    )
    
    # VaR lookback period
    var_lookback_period: int = Field(
        default=252,
        ge=30,
        le=1000,
        description="VaR calculation lookback period in days"
    )
    
    # ============================================================================
    # LIQUIDITY RISK LIMITS
    # ============================================================================
    
    # Minimum liquidity score for new positions
    min_liquidity_score: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum liquidity score for new positions (0-1 scale)"
    )
    
    # Maximum illiquid position percentage
    max_illiquid_exposure: float = Field(
        default=0.20,
        ge=0.0,
        le=0.50,
        description="Maximum exposure to illiquid assets (0.20 = 20%)"
    )
    
    # ============================================================================
    # EMERGENCY STOP CONDITIONS
    # ============================================================================
    
    # Enable emergency stop functionality
    enable_emergency_stop: bool = Field(
        default=True,
        description="Enable emergency stop functionality"
    )
    
    # Emergency stop VaR threshold
    emergency_stop_var_threshold: float = Field(
        default=0.20,
        ge=0.10,
        le=0.50,
        description="VaR threshold for emergency stop (0.20 = 20%)"
    )
    
    # Emergency stop drawdown threshold
    emergency_stop_drawdown_threshold: float = Field(
        default=0.25,
        ge=0.10,
        le=0.50,
        description="Drawdown threshold for emergency stop (0.25 = 25%)"
    )
    
    # Emergency stop daily loss threshold
    emergency_stop_daily_loss_threshold: float = Field(
        default=0.10,
        ge=0.05,
        le=0.30,
        description="Daily loss threshold for emergency stop (0.10 = 10%)"
    )
    
    # ============================================================================
    # MONITORING AND ALERTING
    # ============================================================================
    
    # Risk monitoring frequency (seconds)
    risk_monitoring_frequency: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Risk monitoring frequency in seconds"
    )
    
    # Enable risk alerts
    enable_risk_alerts: bool = Field(
        default=True,
        description="Enable risk alerting system"
    )
    
    # Alert thresholds as percentage of limits
    alert_threshold_warning: float = Field(
        default=0.75,
        ge=0.5,
        le=0.95,
        description="Warning alert threshold as fraction of limit (0.75 = 75%)"
    )
    
    alert_threshold_critical: float = Field(
        default=0.90,
        ge=0.8,
        le=0.99,
        description="Critical alert threshold as fraction of limit (0.90 = 90%)"
    )
    
    # ============================================================================
    # BACKTESTING AND VALIDATION
    # ============================================================================
    
    # Enable backtesting validation
    enable_backtesting_validation: bool = Field(
        default=True,
        description="Enable backtesting for strategy validation"
    )
    
    # Minimum backtesting period (days)
    min_backtesting_period: int = Field(
        default=252,
        ge=60,
        le=2520,
        description="Minimum backtesting period in days"
    )
    
    # Required backtesting Sharpe ratio
    min_backtesting_sharpe: float = Field(
        default=0.5,
        ge=0.0,
        le=3.0,
        description="Minimum required Sharpe ratio from backtesting"
    )
    
    # ============================================================================
    # ADVANCED FEATURES
    # ============================================================================
    
    # Enable machine learning risk models
    enable_ml_risk_models: bool = Field(
        default=False,
        description="Enable machine learning risk models"
    )
    
    # Enable regime detection
    enable_regime_detection: bool = Field(
        default=False,
        description="Enable market regime detection"
    )
    
    # Enable stress testing
    enable_stress_testing: bool = Field(
        default=True,
        description="Enable portfolio stress testing"
    )
    
    # Stress test scenarios
    stress_test_scenarios: Dict[str, float] = Field(
        default={
            "market_crash": -0.20,
            "volatility_spike": 2.0,
            "sector_rotation": -0.15,
            "interest_rate_shock": -0.10
        },
        description="Stress test scenarios and impact factors"
    )
    
    # ============================================================================
    # VALIDATION METHODS
    # ============================================================================
    
    @validator('max_position_size')
    def validate_max_position_size(cls, v, values):
        """Ensure max position size is reasonable"""
        if 'max_portfolio_exposure' in values and v > values['max_portfolio_exposure']:
            raise ValueError("Max position size cannot exceed max portfolio exposure")
        return v
    
    @validator('min_stop_loss_distance')
    def validate_stop_loss_distances(cls, v, values):
        """Ensure stop loss distances are logical"""
        if 'max_stop_loss_distance' in values and v >= values['max_stop_loss_distance']:
            raise ValueError("Minimum stop loss distance must be less than maximum")
        return v
    
    @validator('trailing_activation_threshold')
    def validate_trailing_threshold(cls, v, values):
        """Ensure trailing activation threshold is reasonable"""
        if 'trailing_stop_distance' in values and v <= values['trailing_stop_distance']:
            raise ValueError("Trailing activation threshold should be larger than trailing distance")
        return v
    
    @validator('alert_threshold_critical')
    def validate_alert_thresholds(cls, v, values):
        """Ensure alert thresholds are logical"""
        if 'alert_threshold_warning' in values and v <= values['alert_threshold_warning']:
            raise ValueError("Critical alert threshold must be higher than warning threshold")
        return v
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def get_risk_level(self) -> RiskLevel:
        """Determine the risk level based on current configuration"""
        
        risk_score = 0
        
        # Score based on key metrics
        if self.max_daily_loss >= 0.08:
            risk_score += 3
        elif self.max_daily_loss >= 0.05:
            risk_score += 2
        else:
            risk_score += 1
        
        if self.max_position_size >= 0.25:
            risk_score += 3
        elif self.max_position_size >= 0.15:
            risk_score += 2
        else:
            risk_score += 1
        
        if self.default_risk_per_trade >= 0.05:
            risk_score += 3
        elif self.default_risk_per_trade >= 0.025:
            risk_score += 2
        else:
            risk_score += 1
        
        # Classify risk level
        if risk_score <= 4:
            return RiskLevel.CONSERVATIVE
        elif risk_score <= 7:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.AGGRESSIVE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return self.dict()
    
    def save_to_file(self, file_path: str) -> bool:
        """Save configuration to YAML file"""
        try:
            config_dict = self.dict()
            
            # Convert enums to strings for YAML serialization
            for key, value in config_dict.items():
                if hasattr(value, 'value'):
                    config_dict[key] = value.value
            
            with open(file_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Failed to save risk config: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'RiskConfig':
        """Load configuration from YAML file"""
        try:
            with open(file_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Convert string enum values back to enums
            if 'stop_loss_method' in config_data:
                config_data['stop_loss_method'] = StopLossMethod(config_data['stop_loss_method'])
            if 'trailing_stop_method' in config_data:
                config_data['trailing_stop_method'] = TrailingStopMethod(config_data['trailing_stop_method'])
            if 'position_sizing_method' in config_data:
                config_data['position_sizing_method'] = PositionSizingMethod(config_data['position_sizing_method'])
            
            return cls(**config_data)
            
        except Exception as e:
            print(f"Failed to load risk config: {e}")
            return cls()  # Return default config
    
    @classmethod
    def create_preset(cls, risk_level: RiskLevel) -> 'RiskConfig':
        """Create preset configuration for different risk levels"""
        
        if risk_level == RiskLevel.CONSERVATIVE:
            return cls(
                max_portfolio_exposure=0.80,
                max_daily_loss=0.03,
                max_drawdown=0.10,
                max_positions=5,
                max_position_size=0.10,
                default_risk_per_trade=0.015,
                trailing_stop_distance=0.015,
                trailing_activation_threshold=0.025,
                max_correlation_exposure=0.40,
                max_sector_concentration=0.30
            )
        
        elif risk_level == RiskLevel.MODERATE:
            return cls(
                max_portfolio_exposure=0.90,
                max_daily_loss=0.05,
                max_drawdown=0.15,
                max_positions=8,
                max_position_size=0.15,
                default_risk_per_trade=0.02,
                trailing_stop_distance=0.025,
                trailing_activation_threshold=0.035,
                max_correlation_exposure=0.60,
                max_sector_concentration=0.40
            )
        
        elif risk_level == RiskLevel.AGGRESSIVE:
            return cls(
                max_portfolio_exposure=0.95,
                max_daily_loss=0.08,
                max_drawdown=0.20,
                max_positions=12,
                max_position_size=0.25,
                default_risk_per_trade=0.03,
                trailing_stop_distance=0.035,
                trailing_activation_threshold=0.045,
                max_correlation_exposure=0.70,
                max_sector_concentration=0.50
            )
        
        else:  # CUSTOM or default
            return cls()


# Global configuration instance
_risk_config = None

def get_risk_config() -> RiskConfig:
    """Get the global risk configuration instance"""
    global _risk_config
    if _risk_config is None:
        config_file = os.path.join('risk_management', 'risk_config.yml')
        if os.path.exists(config_file):
            _risk_config = RiskConfig.load_from_file(config_file)
        else:
            _risk_config = RiskConfig()
            # Save default config
            _risk_config.save_to_file(config_file)
    return _risk_config

def set_risk_config(config: RiskConfig) -> None:
    """Set the global risk configuration instance"""
    global _risk_config
    _risk_config = config

def create_default_config_file() -> bool:
    """Create a default risk configuration file"""
    try:
        config = RiskConfig()
        config_file = os.path.join('risk_management', 'risk_config.yml')
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        return config.save_to_file(config_file)
        
    except Exception as e:
        print(f"Failed to create default config file: {e}")
        return False

def create_preset_configs() -> bool:
    """Create preset configuration files for different risk levels"""
    try:
        risk_levels = [RiskLevel.CONSERVATIVE, RiskLevel.MODERATE, RiskLevel.AGGRESSIVE]
        
        for risk_level in risk_levels:
            config = RiskConfig.create_preset(risk_level)
            config_file = os.path.join('risk_management', f'risk_config_{risk_level.value}.yml')
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            
            config.save_to_file(config_file)
        
        return True
        
    except Exception as e:
        print(f"Failed to create preset configs: {e}")
        return False