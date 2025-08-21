"""
Production Configuration
Consolidated production-ready configuration system
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from utils.secure_config_manager import get_secure_config
import logging

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = field(default_factory=lambda: get_secure_config().get_database_url())
    pool_size: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False

@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = field(default_factory=lambda: get_secure_config().get_redis_config()['host'])
    port: int = field(default_factory=lambda: get_secure_config().get_redis_config()['port'])
    password: Optional[str] = field(default_factory=lambda: get_secure_config().get_redis_config().get('password'))
    db: int = field(default_factory=lambda: get_secure_config().get_redis_config()['db'])
    socket_timeout: int = 5
    health_check_interval: int = 30

@dataclass
class TradingConfig:
    """Trading configuration"""
    symbols: list = field(default_factory=lambda: ['AAPL', 'SPY', 'QQQ'])
    default_timeframe: str = '15Min'
    max_position_size: float = 10000.0
    risk_per_trade: float = 0.02
    stop_loss_percent: float = 2.0
    take_profit_percent: float = 4.0

@dataclass
class IndicatorConfig:
    """Technical indicator configuration"""
    stoch_rsi_period: int = 14
    stoch_rsi_k: int = 3
    stoch_rsi_d: int = 3
    ema_fast: int = 12
    ema_slow: int = 26
    atr_period: int = 14
    volume_lookback: int = 20

@dataclass
class WebSocketConfig:
    """WebSocket configuration"""
    host: str = '0.0.0.0'
    port: int = 8765
    update_interval: float = 1.0
    max_connections: int = 100
    compression: bool = True
    heartbeat_interval: int = 30

@dataclass
class APIConfig:
    """API configuration"""
    alpaca_key: str = field(default_factory=lambda: get_secure_config().get_alpaca_config()['api_key'])
    alpaca_secret: str = field(default_factory=lambda: get_secure_config().get_alpaca_config()['secret_key'])
    alpaca_base_url: str = field(default_factory=lambda: get_secure_config().get_alpaca_config()['base_url'])
    rate_limit_per_minute: int = 200
    timeout: int = 30

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_rotation: bool = True
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    structured_logging: bool = True

@dataclass
class SecurityConfig:
    """Security configuration"""
    jwt_secret: str = field(default_factory=lambda: get_secure_config().get_env_var('JWT_SECRET_KEY', required=True))
    jwt_expires: int = 3600
    bcrypt_rounds: int = 12
    rate_limit_enabled: bool = True
    cors_origins: list = field(default_factory=lambda: ['*'])

@dataclass
class ProductionConfig:
    """Master production configuration"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    indicators: IndicatorConfig = field(default_factory=IndicatorConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    api: APIConfig = field(default_factory=APIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # Environment
    environment: str = 'production'
    debug: bool = False
    testing: bool = False
    
    # Performance
    worker_processes: int = field(default_factory=lambda: int(os.getenv('WORKER_PROCESSES', '4')))
    max_requests: int = 1000
    timeout: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy access"""
        return {
            'database': {
                'url': self.database.url,
                'pool_size': self.database.pool_size,
                'pool_timeout': self.database.pool_timeout,
                'pool_recycle': self.database.pool_recycle,
                'echo': self.database.echo
            },
            'redis': {
                'host': self.redis.host,
                'port': self.redis.port,
                'password': self.redis.password,
                'db': self.redis.db,
                'socket_timeout': self.redis.socket_timeout,
                'health_check_interval': self.redis.health_check_interval
            },
            'trading': {
                'symbols': self.trading.symbols,
                'default_timeframe': self.trading.default_timeframe,
                'max_position_size': self.trading.max_position_size,
                'risk_per_trade': self.trading.risk_per_trade,
                'stop_loss_percent': self.trading.stop_loss_percent,
                'take_profit_percent': self.trading.take_profit_percent
            },
            'indicators': {
                'stoch_rsi_period': self.indicators.stoch_rsi_period,
                'stoch_rsi_k': self.indicators.stoch_rsi_k,
                'stoch_rsi_d': self.indicators.stoch_rsi_d,
                'ema_fast': self.indicators.ema_fast,
                'ema_slow': self.indicators.ema_slow,
                'atr_period': self.indicators.atr_period,
                'volume_lookback': self.indicators.volume_lookback
            },
            'websocket': {
                'host': self.websocket.host,
                'port': self.websocket.port,
                'update_interval': self.websocket.update_interval,
                'max_connections': self.websocket.max_connections,
                'compression': self.websocket.compression,
                'heartbeat_interval': self.websocket.heartbeat_interval
            },
            'api': {
                'alpaca_key': '[REDACTED]',  # Don't expose secrets in dict
                'alpaca_secret': '[REDACTED]',
                'alpaca_base_url': self.api.alpaca_base_url,
                'rate_limit_per_minute': self.api.rate_limit_per_minute,
                'timeout': self.api.timeout
            },
            'logging': {
                'level': self.logging.level,
                'format': self.logging.format,
                'file_rotation': self.logging.file_rotation,
                'max_file_size': self.logging.max_file_size,
                'backup_count': self.logging.backup_count,
                'structured_logging': self.logging.structured_logging
            },
            'security': {
                'jwt_secret': '[REDACTED]',
                'jwt_expires': self.security.jwt_expires,
                'bcrypt_rounds': self.security.bcrypt_rounds,
                'rate_limit_enabled': self.security.rate_limit_enabled,
                'cors_origins': self.security.cors_origins
            },
            'environment': self.environment,
            'debug': self.debug,
            'testing': self.testing,
            'worker_processes': self.worker_processes,
            'max_requests': self.max_requests,
            'timeout': self.timeout
        }
    
    def validate(self) -> bool:
        """Validate configuration"""
        try:
            # Validate required fields
            assert self.database.url, "Database URL is required"
            assert self.redis.host, "Redis host is required"
            assert self.api.alpaca_key, "Alpaca API key is required"
            assert self.api.alpaca_secret, "Alpaca secret key is required"
            assert self.security.jwt_secret, "JWT secret is required"
            
            # Validate ranges
            assert 1 <= self.database.pool_size <= 100, "Database pool size must be between 1 and 100"
            assert 1024 <= self.websocket.port <= 65535, "WebSocket port must be between 1024 and 65535"
            assert 0.1 <= self.websocket.update_interval <= 60, "Update interval must be between 0.1 and 60 seconds"
            assert 0.001 <= self.trading.risk_per_trade <= 0.1, "Risk per trade must be between 0.1% and 10%"
            
            logger.info("Configuration validation passed")
            return True
            
        except AssertionError as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error validating configuration: {e}")
            return False

# Global configuration instance
_config = None

def get_production_config() -> ProductionConfig:
    """Get the global production configuration"""
    global _config
    if _config is None:
        _config = ProductionConfig()
        if not _config.validate():
            raise ValueError("Invalid configuration")
    return _config

def reload_config():
    """Reload configuration (useful for testing)"""
    global _config
    _config = None
    return get_production_config()

# Backward compatibility function
def get_config() -> Dict[str, Any]:
    """Get configuration as dictionary for backward compatibility"""
    return get_production_config().to_dict()