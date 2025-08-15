"""
Performance Configuration Loader and Manager.

This module loads and manages performance configuration settings
from YAML files and environment variables.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    redis_url: Optional[str] = None
    enable_compression: bool = True
    local_cache_size: int = 10000
    default_ttl: int = 300
    realtime_ttl: int = 10
    static_ttl: int = 3600


@dataclass
class DatabaseConfig:
    """Database optimization configuration."""
    connection_pool_size: int = 20
    connection_timeout: int = 30
    query_cache_size: int = 1000
    enable_query_optimization: bool = True
    batch_size: int = 100


@dataclass
class HttpConfig:
    """HTTP/API configuration."""
    max_connections: int = 100
    max_connections_per_host: int = 20
    connection_timeout: int = 30
    request_timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 1.0
    enable_compression: bool = True


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_second: float = 10.0
    burst_size: int = 20
    window_size: float = 60.0
    enable_per_endpoint_limits: bool = True


@dataclass
class WebSocketConfig:
    """WebSocket optimization configuration."""
    compression: bool = True
    buffer_size: int = 65536
    ping_interval: int = 25
    ping_timeout: int = 60
    max_message_queue: int = 10000
    reconnect_interval: float = 5.0
    max_reconnect_attempts: int = 10


@dataclass
class ThreadingConfig:
    """Threading and async configuration."""
    api_pool_workers: int = 20
    data_processing_workers: int = 10
    background_workers: int = 5
    max_concurrent_requests: int = 50


@dataclass
class MemoryConfig:
    """Memory management configuration."""
    enable_gc_optimization: bool = True
    gc_threshold_0: int = 700
    gc_threshold_1: int = 10
    gc_threshold_2: int = 10
    max_memory_usage_mb: int = 2048
    cleanup_interval: int = 300


@dataclass
class MonitoringConfig:
    """Monitoring and profiling configuration."""
    enable_performance_tracking: bool = True
    enable_memory_profiling: bool = False
    enable_request_profiling: bool = False
    stats_retention_count: int = 10000
    performance_log_interval: int = 60


@dataclass
class DataFetchingConfig:
    """Data fetching optimization configuration."""
    enable_batching: bool = True
    batch_timeout: float = 1.0
    max_batch_size: int = 100
    enable_streaming: bool = True
    stream_buffer_size: int = 1000


@dataclass
class ResponseConfig:
    """Response optimization configuration."""
    enable_etag_caching: bool = True
    enable_gzip_compression: bool = True
    gzip_compression_threshold: int = 1024
    compression_level: int = 6
    json_separators: tuple = (',', ':')
    float_precision: int = 4


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration."""
    enable_debug_logging: bool = False
    enable_request_logging: bool = True
    enable_performance_warnings: bool = True
    cache_ttl_multiplier: float = 1.0
    enable_aggressive_caching: bool = False
    enable_connection_pooling: bool = True


@dataclass
class PerformanceConfig:
    """Complete performance configuration."""
    caching: CacheConfig = field(default_factory=CacheConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    http: HttpConfig = field(default_factory=HttpConfig)
    rate_limiting: RateLimitConfig = field(default_factory=RateLimitConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    threading: ThreadingConfig = field(default_factory=ThreadingConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    data_fetching: DataFetchingConfig = field(default_factory=DataFetchingConfig)
    response: ResponseConfig = field(default_factory=ResponseConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    development: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    production: EnvironmentConfig = field(default_factory=lambda: EnvironmentConfig(
        enable_debug_logging=False,
        enable_request_logging=False,
        enable_performance_warnings=False,
        cache_ttl_multiplier=1.0,
        enable_aggressive_caching=True,
        enable_connection_pooling=True
    ))
    
    def get_environment_config(self) -> EnvironmentConfig:
        """Get configuration for current environment."""
        env = os.getenv('FLASK_ENV', 'development').lower()
        if env == 'production':
            return self.production
        else:
            return self.development


class PerformanceConfigLoader:
    """Load and manage performance configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[PerformanceConfig] = None
        self._config_cache_time: float = 0
        self._cache_ttl: float = 300  # Cache config for 5 minutes
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        current_dir = Path(__file__).parent
        config_file = current_dir / 'performance.yml'
        return str(config_file)
    
    def load_config(self, force_reload: bool = False) -> PerformanceConfig:
        """Load performance configuration from file and environment."""
        current_time = os.path.getmtime(self.config_path) if os.path.exists(self.config_path) else 0
        
        # Check if we need to reload
        if (self._config is None or 
            force_reload or 
            current_time > self._config_cache_time):
            
            try:
                self._config = self._load_from_file()
                self._apply_environment_overrides()
                self._config_cache_time = current_time
                logger.info("Performance configuration loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load performance configuration: {e}")
                if self._config is None:
                    # Return default configuration if load fails
                    self._config = PerformanceConfig()
                    logger.warning("Using default performance configuration")
        
        return self._config
    
    def _load_from_file(self) -> PerformanceConfig:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Performance config file not found: {self.config_path}")
            return PerformanceConfig()
        
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or 'performance' not in config_data:
                logger.warning("Invalid performance configuration format")
                return PerformanceConfig()
            
            perf_data = config_data['performance']
            
            # Create configuration objects from loaded data
            return PerformanceConfig(
                caching=self._create_cache_config(perf_data.get('caching', {})),
                database=self._create_database_config(perf_data.get('database', {})),
                http=self._create_http_config(perf_data.get('http', {})),
                rate_limiting=self._create_rate_limit_config(perf_data.get('rate_limiting', {})),
                websocket=self._create_websocket_config(perf_data.get('websocket', {})),
                threading=self._create_threading_config(perf_data.get('threading', {})),
                memory=self._create_memory_config(perf_data.get('memory', {})),
                monitoring=self._create_monitoring_config(perf_data.get('monitoring', {})),
                data_fetching=self._create_data_fetching_config(perf_data.get('data_fetching', {})),
                response=self._create_response_config(perf_data.get('response', {})),
                circuit_breaker=self._create_circuit_breaker_config(perf_data.get('circuit_breaker', {})),
                development=self._create_environment_config(perf_data.get('development', {})),
                production=self._create_environment_config(perf_data.get('production', {}))
            )
            
        except Exception as e:
            logger.error(f"Error parsing performance configuration file: {e}")
            return PerformanceConfig()
    
    def _create_cache_config(self, data: Dict[str, Any]) -> CacheConfig:
        """Create cache configuration from data."""
        return CacheConfig(
            redis_url=data.get('redis_url'),
            enable_compression=data.get('enable_compression', True),
            local_cache_size=data.get('local_cache_size', 10000),
            default_ttl=data.get('default_ttl', 300),
            realtime_ttl=data.get('realtime_ttl', 10),
            static_ttl=data.get('static_ttl', 3600)
        )
    
    def _create_database_config(self, data: Dict[str, Any]) -> DatabaseConfig:
        """Create database configuration from data."""
        return DatabaseConfig(
            connection_pool_size=data.get('connection_pool_size', 20),
            connection_timeout=data.get('connection_timeout', 30),
            query_cache_size=data.get('query_cache_size', 1000),
            enable_query_optimization=data.get('enable_query_optimization', True),
            batch_size=data.get('batch_size', 100)
        )
    
    def _create_http_config(self, data: Dict[str, Any]) -> HttpConfig:
        """Create HTTP configuration from data."""
        return HttpConfig(
            max_connections=data.get('max_connections', 100),
            max_connections_per_host=data.get('max_connections_per_host', 20),
            connection_timeout=data.get('connection_timeout', 30),
            request_timeout=data.get('request_timeout', 30),
            max_retries=data.get('max_retries', 3),
            backoff_factor=data.get('backoff_factor', 1.0),
            enable_compression=data.get('enable_compression', True)
        )
    
    def _create_rate_limit_config(self, data: Dict[str, Any]) -> RateLimitConfig:
        """Create rate limiting configuration from data."""
        return RateLimitConfig(
            requests_per_second=data.get('requests_per_second', 10.0),
            burst_size=data.get('burst_size', 20),
            window_size=data.get('window_size', 60.0),
            enable_per_endpoint_limits=data.get('enable_per_endpoint_limits', True)
        )
    
    def _create_websocket_config(self, data: Dict[str, Any]) -> WebSocketConfig:
        """Create WebSocket configuration from data."""
        return WebSocketConfig(
            compression=data.get('compression', True),
            buffer_size=data.get('buffer_size', 65536),
            ping_interval=data.get('ping_interval', 25),
            ping_timeout=data.get('ping_timeout', 60),
            max_message_queue=data.get('max_message_queue', 10000),
            reconnect_interval=data.get('reconnect_interval', 5.0),
            max_reconnect_attempts=data.get('max_reconnect_attempts', 10)
        )
    
    def _create_threading_config(self, data: Dict[str, Any]) -> ThreadingConfig:
        """Create threading configuration from data."""
        return ThreadingConfig(
            api_pool_workers=data.get('api_pool_workers', 20),
            data_processing_workers=data.get('data_processing_workers', 10),
            background_workers=data.get('background_workers', 5),
            max_concurrent_requests=data.get('max_concurrent_requests', 50)
        )
    
    def _create_memory_config(self, data: Dict[str, Any]) -> MemoryConfig:
        """Create memory configuration from data."""
        return MemoryConfig(
            enable_gc_optimization=data.get('enable_gc_optimization', True),
            gc_threshold_0=data.get('gc_threshold_0', 700),
            gc_threshold_1=data.get('gc_threshold_1', 10),
            gc_threshold_2=data.get('gc_threshold_2', 10),
            max_memory_usage_mb=data.get('max_memory_usage_mb', 2048),
            cleanup_interval=data.get('cleanup_interval', 300)
        )
    
    def _create_monitoring_config(self, data: Dict[str, Any]) -> MonitoringConfig:
        """Create monitoring configuration from data."""
        return MonitoringConfig(
            enable_performance_tracking=data.get('enable_performance_tracking', True),
            enable_memory_profiling=data.get('enable_memory_profiling', False),
            enable_request_profiling=data.get('enable_request_profiling', False),
            stats_retention_count=data.get('stats_retention_count', 10000),
            performance_log_interval=data.get('performance_log_interval', 60)
        )
    
    def _create_data_fetching_config(self, data: Dict[str, Any]) -> DataFetchingConfig:
        """Create data fetching configuration from data."""
        return DataFetchingConfig(
            enable_batching=data.get('enable_batching', True),
            batch_timeout=data.get('batch_timeout', 1.0),
            max_batch_size=data.get('max_batch_size', 100),
            enable_streaming=data.get('enable_streaming', True),
            stream_buffer_size=data.get('stream_buffer_size', 1000)
        )
    
    def _create_response_config(self, data: Dict[str, Any]) -> ResponseConfig:
        """Create response configuration from data."""
        return ResponseConfig(
            enable_etag_caching=data.get('enable_etag_caching', True),
            enable_gzip_compression=data.get('enable_gzip_compression', True),
            gzip_compression_threshold=data.get('gzip_compression_threshold', 1024),
            compression_level=data.get('compression_level', 6),
            json_separators=tuple(data.get('json_separators', [',', ':'])),
            float_precision=data.get('float_precision', 4)
        )
    
    def _create_circuit_breaker_config(self, data: Dict[str, Any]) -> CircuitBreakerConfig:
        """Create circuit breaker configuration from data."""
        return CircuitBreakerConfig(
            failure_threshold=data.get('failure_threshold', 5),
            recovery_timeout=data.get('recovery_timeout', 60.0),
            half_open_max_calls=data.get('half_open_max_calls', 3)
        )
    
    def _create_environment_config(self, data: Dict[str, Any]) -> EnvironmentConfig:
        """Create environment configuration from data."""
        return EnvironmentConfig(
            enable_debug_logging=data.get('enable_debug_logging', False),
            enable_request_logging=data.get('enable_request_logging', True),
            enable_performance_warnings=data.get('enable_performance_warnings', True),
            cache_ttl_multiplier=data.get('cache_ttl_multiplier', 1.0),
            enable_aggressive_caching=data.get('enable_aggressive_caching', False),
            enable_connection_pooling=data.get('enable_connection_pooling', True)
        )
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        if not self._config:
            return
        
        # Redis URL override
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            self._config.caching.redis_url = redis_url
        
        # Performance tracking override
        if os.getenv('DISABLE_PERFORMANCE_TRACKING', '').lower() in ('true', '1', 'yes'):
            self._config.monitoring.enable_performance_tracking = False
        
        # Memory profiling override (for debugging)
        if os.getenv('ENABLE_MEMORY_PROFILING', '').lower() in ('true', '1', 'yes'):
            self._config.monitoring.enable_memory_profiling = True
        
        # WebSocket compression override
        if os.getenv('DISABLE_WEBSOCKET_COMPRESSION', '').lower() in ('true', '1', 'yes'):
            self._config.websocket.compression = False
        
        # Cache TTL multiplier for different environments
        ttl_multiplier = os.getenv('CACHE_TTL_MULTIPLIER')
        if ttl_multiplier:
            try:
                multiplier = float(ttl_multiplier)
                self._config.caching.default_ttl = int(self._config.caching.default_ttl * multiplier)
                self._config.caching.realtime_ttl = int(self._config.caching.realtime_ttl * multiplier)
                self._config.caching.static_ttl = int(self._config.caching.static_ttl * multiplier)
            except ValueError:
                logger.warning(f"Invalid CACHE_TTL_MULTIPLIER value: {ttl_multiplier}")
    
    def get_config(self) -> PerformanceConfig:
        """Get current performance configuration."""
        return self.load_config()
    
    def reload_config(self) -> PerformanceConfig:
        """Force reload configuration."""
        return self.load_config(force_reload=True)


# Global configuration loader instance
_config_loader: Optional[PerformanceConfigLoader] = None


def get_performance_config() -> PerformanceConfig:
    """Get global performance configuration."""
    global _config_loader
    if _config_loader is None:
        _config_loader = PerformanceConfigLoader()
    return _config_loader.get_config()


def reload_performance_config() -> PerformanceConfig:
    """Reload global performance configuration."""
    global _config_loader
    if _config_loader is None:
        _config_loader = PerformanceConfigLoader()
    return _config_loader.reload_config()