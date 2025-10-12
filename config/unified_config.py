"""
Unified Configuration System

This module provides centralized configuration management with:
- Single configuration entry point
- Environment-based overrides  
- Validation and defaults
- Migration from existing config systems
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


@dataclass
class StochRSIConfig:
    """StochRSI indicator configuration."""
    enabled: bool = True
    lower_band: int = 35
    upper_band: int = 100
    K: int = 3
    D: int = 3
    rsi_length: int = 14
    stoch_length: int = 14
    source: str = "Close"
    dynamic_bands_enabled: bool = True
    atr_period: int = 14


@dataclass
class StochConfig:
    """Stochastic indicator configuration."""
    enabled: bool = True
    lower_band: int = 35
    upper_band: int = 80
    K_Length: int = 14
    smooth_K: int = 3
    smooth_D: int = 3


@dataclass
class EMAConfig:
    """EMA indicator configuration."""
    enabled: bool = True
    ema_period: int = 9
    fast_period: int = 10
    slow_period: int = 30
    source: str = "Close"
    smoothing: int = 2


@dataclass
class IndicatorsConfig:
    """Indicators configuration container."""
    stochRSI: StochRSIConfig = field(default_factory=StochRSIConfig)
    stoch: StochConfig = field(default_factory=StochConfig)
    EMA: EMAConfig = field(default_factory=EMAConfig)


@dataclass
class RiskManagementConfig:
    """Risk management configuration."""
    use_atr_stop_loss: bool = True
    atr_period: int = 14
    atr_multiplier: float = 2.0
    use_atr_position_sizing: bool = True
    max_position_size: float = 0.1  # 10% of portfolio max
    max_daily_loss: float = 0.05    # 5% daily loss limit
    max_drawdown: float = 0.15      # 15% max drawdown


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = "sqlite:///database/trading_data.db"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/trading_bot.log"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class APIConfig:
    """API configuration."""
    alpaca_auth_file: str = "AUTH/authAlpaca.txt"
    request_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    rate_limit_requests: int = 200
    rate_limit_window: int = 60  # seconds


# Epic 1 Configuration Classes
@dataclass
class DynamicStochRSIConfig:
    """Epic 1 Dynamic StochRSI configuration with adaptive bands."""
    enabled: bool = True
    enable_adaptive_bands: bool = True
    volatility_window: int = 20
    base_volatility_window: int = 100
    min_lower_band: int = 10
    max_lower_band: int = 30
    min_upper_band: int = 70
    max_upper_band: int = 90
    default_lower_band: int = 20
    default_upper_band: int = 80
    band_adjustment_sensitivity: float = 1.0
    enable_trend_filtering: bool = True


@dataclass
class VolumeConfirmationConfig:
    """Epic 1 Volume Confirmation system configuration."""
    enabled: bool = True
    confirmation_threshold: float = 1.2
    volume_ma_period: int = 20
    enable_relative_volume: bool = True
    relative_volume_threshold: float = 1.5
    volume_trend_periods: int = 5
    require_volume_confirmation: bool = True
    min_signal_gap_seconds: int = 300
    require_confirmation: bool = True
    confirmation_window: int = 3
    volume_strength_levels: Dict[str, float] = field(default_factory=lambda: {
        'very_low': -2.0,
        'low': -1.0,
        'normal': 0.0,
        'high': 1.0,
        'very_high': 2.0
    })


@dataclass
class MultiTimeframeConfig:
    """Epic 1 Multi-timeframe validation configuration."""
    enabled: bool = True
    timeframes: List[str] = field(default_factory=lambda: ['15m', '1h', '1d'])
    enable_real_time_validation: bool = True
    consensus_threshold: float = 0.75
    enable_performance_tracking: bool = True
    max_concurrent_validations: int = 10
    auto_update_interval: int = 60000  # milliseconds
    timeframe_weights: Dict[str, float] = field(default_factory=lambda: {
        '15m': 0.3,
        '1h': 0.4,
        '1d': 0.3
    })
    trend_analysis_periods: Dict[str, int] = field(default_factory=lambda: {
        '15m': 20,
        '1h': 20,
        '1d': 20
    })


@dataclass
class SignalQualityConfig:
    """Epic 1 Signal Quality assessment configuration."""
    enabled: bool = True
    enable_quality_filtering: bool = True
    minimum_quality_score: float = 0.6
    quality_weights: Dict[str, float] = field(default_factory=lambda: {
        'volatility': 0.25,
        'volume_consistency': 0.20,
        'data_completeness': 0.25,
        'signal_reliability': 0.20,
        'data_freshness': 0.10
    })
    volatility_penalty_multiplier: float = 5.0
    max_volatility_penalty: float = 0.3
    volume_consistency_bonus_threshold: float = 0.5
    volume_bonus_multiplier: float = 0.1
    enable_recommendations: bool = True


@dataclass
class Epic1PerformanceConfig:
    """Epic 1 Performance tracking and optimization configuration."""
    enabled: bool = True
    track_signal_outcomes: bool = True
    enable_adaptive_learning: bool = True
    performance_window_days: int = 30
    min_trades_for_analysis: int = 10
    enable_strategy_comparison: bool = True
    auto_parameter_optimization: bool = False
    optimization_frequency_hours: int = 24


@dataclass
class Epic1Config:
    """Epic 1 feature configuration container."""
    enabled: bool = True
    dynamic_stochrsi: DynamicStochRSIConfig = field(default_factory=DynamicStochRSIConfig)
    volume_confirmation: VolumeConfirmationConfig = field(default_factory=VolumeConfirmationConfig)
    multi_timeframe: MultiTimeframeConfig = field(default_factory=MultiTimeframeConfig)
    signal_quality: SignalQualityConfig = field(default_factory=SignalQualityConfig)
    performance: Epic1PerformanceConfig = field(default_factory=Epic1PerformanceConfig)
    
    # Integration settings
    require_epic1_consensus: bool = False
    fallback_to_epic0: bool = True
    enable_enhanced_websocket: bool = True
    enable_epic1_api_endpoints: bool = True


@dataclass
class TradingConfig:
    """Core trading configuration."""
    # General settings
    start_date: str = "10 days ago"
    end_date: str = "1 Jan, 2023"
    timeframe: str = "1Min"
    candle_lookback_period: int = 2
    investment_amount: int = 10000
    max_trades_active: int = 10
    trade_capital_percent: int = 5
    stop_loss: float = 0.2
    trailing_stop: float = 0.2
    activate_trailing_stop_loss_at: float = 0.1
    limit_price: float = 0.5
    exchange: str = "CBSE"
    sleep_time_between_trades: int = 60
    extended_hours: bool = True
    strategy: str = "StochRSI"
    symbols: List[str] = field(default_factory=lambda: ["BTCUSD", "ETHUSD", "SOLUSD"])

    # Crypto-specific settings
    crypto_only: bool = True  # Only trade cryptocurrency pairs
    market_type: str = "crypto"  # "crypto" or "stock"

    # Component configurations
    indicators: IndicatorsConfig = field(default_factory=IndicatorsConfig)
    risk_management: RiskManagementConfig = field(default_factory=RiskManagementConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    api: APIConfig = field(default_factory=APIConfig)


class UnifiedConfigManager:
    """
    Unified configuration manager with validation, environment overrides, and migration support.
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self._config: Optional[TradingConfig] = None
        self._config_lock = threading.RLock()
        
        # Config file paths
        self.yaml_config_path = self.config_dir / "config.yml"
        self.unified_config_path = self.config_dir / "unified_config.yml"
        self.legacy_config_path = Path("AUTH/ConfigFile.txt")
        
        logger.info(f"Configuration manager initialized with config_dir: {config_dir}")
    
    def load_config(self, force_reload: bool = False) -> TradingConfig:
        """Load configuration with caching and validation."""
        with self._config_lock:
            if self._config is not None and not force_reload:
                return self._config
            
            # Try to load from unified config first
            if self.unified_config_path.exists():
                config = self._load_from_yaml(self.unified_config_path)
            elif self.yaml_config_path.exists():
                config = self._load_from_yaml(self.yaml_config_path)
            elif self.legacy_config_path.exists():
                config = self._migrate_from_legacy()
            else:
                logger.warning("No configuration file found, using defaults")
                config = TradingConfig()
            
            # Apply environment overrides
            config = self._apply_environment_overrides(config)
            
            # Validate configuration
            self._validate_config(config)
            
            # Cache the config
            self._config = config
            
            # Save as unified config for future use
            self._save_unified_config(config)
            
            logger.info("Configuration loaded successfully")
            return config
    
    def _load_from_yaml(self, file_path: Path) -> TradingConfig:
        """Load configuration from YAML file."""
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            
            # Convert nested dictionaries to dataclass instances
            config_dict = self._convert_nested_config(data)
            
            return TradingConfig(**config_dict)
            
        except Exception as e:
            logger.error(f"Error loading YAML config from {file_path}: {e}")
            raise
    
    def _convert_nested_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert nested dictionary configuration to dataclass format."""
        config_dict = data.copy()
        
        # Handle indicators
        if 'indicators' in config_dict:
            indicators_data = config_dict['indicators']
            
            # Convert to new format if needed
            stochrsi_data = indicators_data.get('stochRSI', {})
            if isinstance(stochrsi_data, dict) and 'enabled' in stochrsi_data:
                config_dict['indicators'] = IndicatorsConfig(
                    stochRSI=StochRSIConfig(**stochrsi_data),
                    stoch=StochConfig(**indicators_data.get('stoch', {})),
                    EMA=EMAConfig(**indicators_data.get('EMA', {}))
                )
            else:
                # Legacy format conversion
                config_dict['indicators'] = self._convert_legacy_indicators(indicators_data)
        
        # Handle other nested configs
        if 'risk_management' in config_dict:
            config_dict['risk_management'] = RiskManagementConfig(**config_dict['risk_management'])
        
        if 'database' in config_dict:
            config_dict['database'] = DatabaseConfig(**config_dict['database'])
        
        if 'logging' in config_dict:
            config_dict['logging'] = LoggingConfig(**config_dict['logging'])
        
        if 'api' in config_dict:
            config_dict['api'] = APIConfig(**config_dict['api'])
        
        # Remove any Epic1 configuration sections for simplified crypto scalping
        config_dict.pop('epic1', None)
        config_dict.pop('volume_confirmation', None)
        
        return config_dict
    
    def _convert_legacy_indicators(self, indicators_data: Dict[str, Any]) -> IndicatorsConfig:
        """Convert legacy indicator format to new format."""
        stochrsi_config = StochRSIConfig()
        stoch_config = StochConfig()
        ema_config = EMAConfig()
        
        # Convert StochRSI
        if 'stochRSI' in indicators_data:
            stochrsi_enabled = indicators_data['stochRSI'] == "True"
            stochrsi_params = indicators_data.get('stochRSI_params', {})
            
            stochrsi_config = StochRSIConfig(
                enabled=stochrsi_enabled,
                lower_band=stochrsi_params.get('lower_band', 35),
                upper_band=stochrsi_params.get('upper_band', 100),
                K=stochrsi_params.get('K', 3),
                D=stochrsi_params.get('D', 3),
                rsi_length=stochrsi_params.get('rsi_length', 14),
                stoch_length=stochrsi_params.get('stoch_length', 14),
                source=stochrsi_params.get('source', 'Close')
            )
        
        # Convert Stochastic
        if 'stoch' in indicators_data:
            stoch_enabled = indicators_data['stoch'] == "True"
            stoch_params = indicators_data.get('stoch_params', {})
            
            stoch_config = StochConfig(
                enabled=stoch_enabled,
                lower_band=stoch_params.get('lower_band', 35),
                upper_band=stoch_params.get('upper_band', 80),
                K_Length=stoch_params.get('K_Length', 14),
                smooth_K=stoch_params.get('smooth_K', 3),
                smooth_D=stoch_params.get('smooth_D', 3)
            )
        
        # Convert EMA
        if 'EMA' in indicators_data:
            ema_enabled = indicators_data['EMA'] == "True"
            ema_params = indicators_data.get('EMA_params', {})
            
            ema_config = EMAConfig(
                enabled=ema_enabled,
                ema_period=ema_params.get('ema_period', 9),
                fast_period=ema_params.get('fast_period', 10),
                slow_period=ema_params.get('slow_period', 30),
                source=ema_params.get('source', 'Close'),
                smoothing=ema_params.get('smoothing', 2)
            )
        
        return IndicatorsConfig(
            stochRSI=stochrsi_config,
            stoch=stoch_config,
            EMA=ema_config
        )
    
    def _migrate_from_legacy(self) -> TradingConfig:
        """Migrate from legacy JSON configuration format."""
        logger.info("Migrating from legacy configuration format")
        
        try:
            with open(self.legacy_config_path, 'r') as f:
                legacy_data = json.load(f)
            
            # Convert legacy format to new format
            config_dict = {}
            
            # Map legacy keys to new keys
            key_mapping = {
                'investment_amount': 'investment_amount',
                'max_trades_active': 'max_trades_active',
                'trade_capital_percent': 'trade_capital_percent',
                'stop_loss': 'stop_loss',
                'trailing_stop': 'trailing_stop',
                'limit_price': 'limit_price',
                'start_date': 'start_date',
                'timeframe': 'timeframe',
                'candle_lookback_period': 'candle_lookback_period',
                'sleep_time_between_trades': 'sleep_time_between_trades'
            }
            
            for legacy_key, new_key in key_mapping.items():
                if legacy_key in legacy_data:
                    config_dict[new_key] = legacy_data[legacy_key]
            
            # Convert indicators
            if 'indicators' in legacy_data:
                config_dict['indicators'] = self._convert_legacy_indicators(legacy_data['indicators'])
            
            # Set defaults for new fields
            config_dict.setdefault('strategy', 'StochRSI')
            config_dict.setdefault('extended_hours', True)
            config_dict.setdefault('exchange', 'CBSE')
            
            config = TradingConfig(**config_dict)
            
            logger.info("Legacy configuration migrated successfully")
            return config
            
        except Exception as e:
            logger.error(f"Error migrating legacy configuration: {e}")
            raise
    
    def _apply_environment_overrides(self, config: TradingConfig) -> TradingConfig:
        """Apply environment variable overrides to configuration."""
        env_prefix = "TRADING_BOT_"
        
        # Define environment variable mappings
        env_mappings = {
            f"{env_prefix}INVESTMENT_AMOUNT": ("investment_amount", int),
            f"{env_prefix}MAX_TRADES": ("max_trades_active", int),
            f"{env_prefix}STOP_LOSS": ("stop_loss", float),
            f"{env_prefix}TRAILING_STOP": ("trailing_stop", float),
            f"{env_prefix}STRATEGY": ("strategy", str),
            f"{env_prefix}TIMEFRAME": ("timeframe", str),
            f"{env_prefix}LOG_LEVEL": ("logging.level", str),
            f"{env_prefix}DB_URL": ("database.url", str),
        }
        
        config_dict = asdict(config)
        
        for env_var, (config_path, value_type) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Handle nested config paths
                    if '.' in config_path:
                        keys = config_path.split('.')
                        nested_dict = config_dict
                        for key in keys[:-1]:
                            if key not in nested_dict:
                                nested_dict[key] = {}
                            nested_dict = nested_dict[key]
                        nested_dict[keys[-1]] = value_type(env_value)
                    else:
                        config_dict[config_path] = value_type(env_value)
                    
                    logger.info(f"Applied environment override: {env_var} = {env_value}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid environment value for {env_var}: {e}")
        
        # Reconstruct config object
        return self._dict_to_config(config_dict)
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> TradingConfig:
        """Convert dictionary back to TradingConfig object."""
        # Handle nested dataclasses
        if 'indicators' in config_dict and isinstance(config_dict['indicators'], dict):
            indicators_data = config_dict['indicators']
            config_dict['indicators'] = IndicatorsConfig(
                stochRSI=StochRSIConfig(**indicators_data.get('stochRSI', {})),
                stoch=StochConfig(**indicators_data.get('stoch', {})),
                EMA=EMAConfig(**indicators_data.get('EMA', {}))
            )
        
        if 'risk_management' in config_dict and isinstance(config_dict['risk_management'], dict):
            config_dict['risk_management'] = RiskManagementConfig(**config_dict['risk_management'])
        
        if 'database' in config_dict and isinstance(config_dict['database'], dict):
            config_dict['database'] = DatabaseConfig(**config_dict['database'])
        
        if 'logging' in config_dict and isinstance(config_dict['logging'], dict):
            config_dict['logging'] = LoggingConfig(**config_dict['logging'])
        
        if 'api' in config_dict and isinstance(config_dict['api'], dict):
            config_dict['api'] = APIConfig(**config_dict['api'])

        # Remove Epic1 configuration for simplified crypto scalping
        config_dict.pop('epic1', None)
        
        return TradingConfig(**config_dict)
    
    def _validate_config(self, config: TradingConfig) -> None:
        """Validate configuration values."""
        errors = []
        
        # Validate trading parameters
        if config.investment_amount <= 0:
            errors.append("investment_amount must be positive")
        
        if config.max_trades_active <= 0:
            errors.append("max_trades_active must be positive")
        
        if not (0 < config.trade_capital_percent <= 100):
            errors.append("trade_capital_percent must be between 0 and 100")
        
        if not (0 < config.stop_loss <= 1):
            errors.append("stop_loss must be between 0 and 1")
        
        if not (0 < config.trailing_stop <= 1):
            errors.append("trailing_stop must be between 0 and 1")
        
        # Validate timeframe
        valid_timeframes = ["1Min", "5Min", "15Min", "1Hour", "1Day"]
        if config.timeframe not in valid_timeframes:
            errors.append(f"timeframe must be one of {valid_timeframes}")
        
        # Validate strategy
        valid_strategies = ["StochRSI", "MACrossover", "crypto_scalping"]
        if config.strategy not in valid_strategies:
            errors.append(f"strategy must be one of {valid_strategies}")

        # Validate symbols
        if not config.symbols or len(config.symbols) == 0:
            errors.append("At least one symbol must be specified")
        
        # Validate indicator parameters
        if config.indicators.stochRSI.enabled:
            if not (0 < config.indicators.stochRSI.lower_band < config.indicators.stochRSI.upper_band <= 100):
                errors.append("StochRSI bands must be 0 < lower_band < upper_band <= 100")
        
        if config.indicators.stoch.enabled:
            if not (0 < config.indicators.stoch.lower_band < config.indicators.stoch.upper_band <= 100):
                errors.append("Stochastic bands must be 0 < lower_band < upper_band <= 100")
        
        if errors:
            error_msg = "Configuration validation errors:\n" + "\n".join(f"- {error}" for error in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.debug("Configuration validation passed")
    
    def _save_unified_config(self, config: TradingConfig) -> None:
        """Save configuration as unified YAML format."""
        try:
            config_dict = asdict(config)
            
            with open(self.unified_config_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            logger.debug(f"Unified configuration saved to {self.unified_config_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save unified configuration: {e}")
    
    def save_config(self, config: TradingConfig) -> None:
        """Save configuration to file."""
        with self._config_lock:
            self._config = config
            self._save_unified_config(config)
    
    def get_legacy_format(self, config: Optional[TradingConfig] = None) -> Dict[str, Any]:
        """Get configuration in legacy JSON format for backward compatibility."""
        if config is None:
            config = self.load_config()
        
        # Convert to legacy format
        legacy_config = {
            "investment_amount": config.investment_amount,
            "max_trades_active": config.max_trades_active,
            "trade_capital_percent": config.trade_capital_percent,
            "stop_loss": config.stop_loss,
            "trailing_stop": config.trailing_stop,
            "limit_price": config.limit_price,
            "start_date": config.start_date,
            "timeframe": config.timeframe,
            "candle_lookback_period": config.candle_lookback_period,
            "sleep_time_between_trades": config.sleep_time_between_trades,
            "symbols": config.symbols,
            "indicators": {
                "stochRSI": "True" if config.indicators.stochRSI.enabled else "False",
                "stochRSI_params": asdict(config.indicators.stochRSI),
                "stoch": "True" if config.indicators.stoch.enabled else "False", 
                "stoch_params": asdict(config.indicators.stoch),
                "EMA": "True" if config.indicators.EMA.enabled else "False",
                "EMA_params": asdict(config.indicators.EMA)
            }
        }
        
        return legacy_config
    
    def reload_config(self) -> TradingConfig:
        """Reload configuration from file."""
        return self.load_config(force_reload=True)


# Global configuration manager instance
_config_manager: Optional[UnifiedConfigManager] = None
_config_lock = threading.RLock()


def get_config_manager() -> UnifiedConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    
    with _config_lock:
        if _config_manager is None:
            _config_manager = UnifiedConfigManager()
        return _config_manager


def get_config() -> TradingConfig:
    """Get the current configuration."""
    return get_config_manager().load_config()


def reload_config() -> TradingConfig:
    """Reload configuration from file."""
    return get_config_manager().reload_config()


def get_legacy_config() -> Dict[str, Any]:
    """Get configuration in legacy format for backward compatibility."""
    return get_config_manager().get_legacy_format()