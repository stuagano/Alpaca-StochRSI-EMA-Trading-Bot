import json
import os
import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import copy

@dataclass
class TradingConfig:
    """Trading strategy configuration"""
    # Strategy settings
    strategy_mode: str = "stochastic_rsi_only"  # Current active strategy
    position_size_percentage: float = 5.0
    max_positions: int = 3
    enable_stop_loss: bool = True
    stop_loss_percentage: float = 5.0
    enable_take_profit: bool = True
    take_profit_percentage: float = 5.0
    enable_trailing_stop: bool = True
    trailing_stop_percentage: float = 2.0
    
    # Risk management
    max_daily_loss_percentage: float = 10.0
    max_drawdown_percentage: float = 20.0
    risk_per_trade_percentage: float = 2.0
    correlation_threshold: float = 0.7
    volatility_threshold: float = 0.3
    
    # Market hours
    market_open_hour: int = 9
    market_open_minute: int = 30
    market_close_hour: int = 16
    market_close_minute: int = 0
    enable_premarket: bool = False
    enable_afterhours: bool = False

@dataclass
class IndicatorConfig:
    """Technical indicator configuration"""
    # StochRSI settings
    stoch_rsi_period: int = 14
    stoch_rsi_k_period: int = 3
    stoch_rsi_d_period: int = 3
    stoch_rsi_oversold: float = 35.0
    stoch_rsi_overbought: float = 80.0
    
    # Stochastic settings
    stoch_k_period: int = 14
    stoch_d_period: int = 3
    stoch_oversold: float = 35.0
    stoch_overbought: float = 80.0
    
    # EMA settings
    ema_period: int = 9
    ema_fast_period: int = 12
    ema_slow_period: int = 26
    ema_signal_period: int = 9
    
    # RSI settings
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    
    # Additional indicators
    bollinger_period: int = 20
    bollinger_std: float = 2.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

@dataclass
class AlpacaConfig:
    """Alpaca API configuration"""
    base_url: str = "https://paper-api.alpaca.markets"
    api_key: str = ""
    api_secret: str = ""
    paper_trading: bool = True
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0

@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_path: str = "trading_bot.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    max_backups: int = 7
    connection_pool_size: int = 5

@dataclass
class LoggingConfig:
    """Logging configuration"""
    log_level: str = "INFO"
    log_dir: str = "logs"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_database_logging: bool = True
    enable_performance_logging: bool = True

@dataclass
class UIConfig:
    """User interface configuration"""
    # Flask settings
    flask_host: str = "127.0.0.1"
    flask_port: int = 5000
    flask_debug: bool = False
    
    # Streamlit settings
    streamlit_port: int = 8501
    streamlit_theme: str = "dark"
    
    # Chart settings
    chart_theme: str = "dark"
    chart_height: int = 600
    auto_refresh_seconds: int = 10

@dataclass
class NotificationConfig:
    """Notification settings"""
    enable_email: bool = False
    email_smtp_server: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_recipients: list = None
    
    enable_discord: bool = False
    discord_webhook_url: str = ""
    
    enable_telegram: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

class ConfigManager:
    """Enhanced configuration management system"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.logger = logging.getLogger(__name__)
        
        # Ensure config directory exists
        os.makedirs(config_dir, exist_ok=True)
        
        # Configuration file paths
        self.config_files = {
            'trading': os.path.join(config_dir, 'trading.json'),
            'indicators': os.path.join(config_dir, 'indicators.json'),
            'alpaca': os.path.join(config_dir, 'alpaca.json'),
            'database': os.path.join(config_dir, 'database.json'),
            'logging': os.path.join(config_dir, 'logging.json'),
            'ui': os.path.join(config_dir, 'ui.json'),
            'notifications': os.path.join(config_dir, 'notifications.json')
        }
        
        # Configuration objects
        self._configs = {
            'trading': TradingConfig(),
            'indicators': IndicatorConfig(),
            'alpaca': AlpacaConfig(),
            'database': DatabaseConfig(),
            'logging': LoggingConfig(),
            'ui': UIConfig(),
            'notifications': NotificationConfig()
        }
        
        # Load configurations
        self._load_all_configs()
        
    def _load_all_configs(self):
        """Load all configuration files"""
        for config_name in self._configs.keys():
            self._load_config(config_name)
    
    def _load_config(self, config_name: str):
        """Load a specific configuration"""
        try:
            config_file = self.config_files[config_name]
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                # Update config object with loaded data
                config_class = type(self._configs[config_name])
                self._configs[config_name] = config_class(**data)
                
                self.logger.debug(f"Loaded {config_name} configuration from {config_file}")
            else:
                # Create default configuration file
                self._save_config(config_name)
                self.logger.info(f"Created default {config_name} configuration at {config_file}")
                
        except Exception as e:
            self.logger.error(f"Failed to load {config_name} configuration: {e}")
            # Keep default configuration
    
    def _save_config(self, config_name: str):
        """Save a specific configuration"""
        try:
            config_file = self.config_files[config_name]
            config_data = asdict(self._configs[config_name])
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=4, default=str)
            
            self.logger.debug(f"Saved {config_name} configuration to {config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save {config_name} configuration: {e}")
    
    def get_config(self, config_name: str) -> Union[TradingConfig, IndicatorConfig, AlpacaConfig, 
                                                   DatabaseConfig, LoggingConfig, UIConfig, 
                                                   NotificationConfig]:
        """Get a configuration object"""
        if config_name not in self._configs:
            raise ValueError(f"Unknown configuration: {config_name}")
        return self._configs[config_name]
    
    def update_config(self, config_name: str, updates: Dict[str, Any], save: bool = True):
        """Update configuration with new values"""
        try:
            if config_name not in self._configs:
                raise ValueError(f"Unknown configuration: {config_name}")
            
            config = self._configs[config_name]
            
            # Update configuration attributes
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                    self.logger.debug(f"Updated {config_name}.{key} = {value}")
                else:
                    self.logger.warning(f"Unknown configuration key: {config_name}.{key}")
            
            if save:
                self._save_config(config_name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update {config_name} configuration: {e}")
            return False
    
    def save_all_configs(self):
        """Save all configurations to files"""
        for config_name in self._configs.keys():
            self._save_config(config_name)
    
    def reload_config(self, config_name: str):
        """Reload a configuration from file"""
        self._load_config(config_name)
    
    def reload_all_configs(self):
        """Reload all configurations from files"""
        self._load_all_configs()
    
    def get_config_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all configurations"""
        summary = {}
        for name, config in self._configs.items():
            summary[name] = asdict(config)
        return summary
    
    def backup_configs(self, backup_dir: str = None):
        """Create backup of all configuration files"""
        if backup_dir is None:
            backup_dir = os.path.join(self.config_dir, 'backups')
        
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_subdir = os.path.join(backup_dir, f'config_backup_{timestamp}')
        os.makedirs(backup_subdir, exist_ok=True)
        
        try:
            for config_name, config_file in self.config_files.items():
                if os.path.exists(config_file):
                    backup_file = os.path.join(backup_subdir, os.path.basename(config_file))
                    with open(config_file, 'r') as src, open(backup_file, 'w') as dst:
                        dst.write(src.read())
            
            self.logger.info(f"Configuration backup created at {backup_subdir}")
            return backup_subdir
            
        except Exception as e:
            self.logger.error(f"Failed to create configuration backup: {e}")
            return None
    
    def restore_configs(self, backup_dir: str):
        """Restore configurations from backup"""
        try:
            for config_name, config_file in self.config_files.items():
                backup_file = os.path.join(backup_dir, os.path.basename(config_file))
                if os.path.exists(backup_file):
                    with open(backup_file, 'r') as src, open(config_file, 'w') as dst:
                        dst.write(src.read())
            
            # Reload configurations
            self._load_all_configs()
            
            self.logger.info(f"Configurations restored from {backup_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore configurations: {e}")
            return False
    
    def validate_config(self, config_name: str) -> Dict[str, Any]:
        """Validate configuration and return validation results"""
        validation_results = {'valid': True, 'errors': [], 'warnings': []}
        
        try:
            config = self._configs[config_name]
            
            if config_name == 'trading':
                # Validate trading configuration
                if config.position_size_percentage <= 0 or config.position_size_percentage > 100:
                    validation_results['errors'].append("Position size percentage must be between 0 and 100")
                
                if config.max_positions <= 0:
                    validation_results['errors'].append("Maximum positions must be greater than 0")
                
                if config.stop_loss_percentage <= 0 or config.stop_loss_percentage > 50:
                    validation_results['warnings'].append("Stop loss percentage seems unusual")
            
            elif config_name == 'indicators':
                # Validate indicator configuration
                if config.stoch_rsi_period <= 0:
                    validation_results['errors'].append("StochRSI period must be positive")
                
                if config.ema_period <= 0:
                    validation_results['errors'].append("EMA period must be positive")
            
            elif config_name == 'alpaca':
                # Validate Alpaca configuration
                if not config.api_key or not config.api_secret:
                    validation_results['errors'].append("API credentials are required")
                
                if not config.base_url:
                    validation_results['errors'].append("Base URL is required")
            
            # Set overall validity
            validation_results['valid'] = len(validation_results['errors']) == 0
            
        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Validation error: {e}")
        
        return validation_results
    
    def validate_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Validate all configurations"""
        results = {}
        for config_name in self._configs.keys():
            results[config_name] = self.validate_config(config_name)
        return results

# Global configuration manager instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get singleton configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_trading_config() -> TradingConfig:
    """Get trading configuration"""
    return get_config_manager().get_config('trading')

def get_indicator_config() -> IndicatorConfig:
    """Get indicator configuration"""
    return get_config_manager().get_config('indicators')

def get_alpaca_config() -> AlpacaConfig:
    """Get Alpaca configuration"""
    return get_config_manager().get_config('alpaca')

def get_database_config() -> DatabaseConfig:
    """Get database configuration"""
    return get_config_manager().get_config('database')

def get_logging_config() -> LoggingConfig:
    """Get logging configuration"""
    return get_config_manager().get_config('logging')

def get_ui_config() -> UIConfig:
    """Get UI configuration"""
    return get_config_manager().get_config('ui')

def get_notification_config() -> NotificationConfig:
    """Get notification configuration"""
    return get_config_manager().get_config('notifications')