"""
Redis Caching Service
High-performance caching layer for trading data and API responses
"""

import redis
import json
import pickle
import logging
import hashlib
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
import numpy as np
from utils.secure_config_manager import get_secure_config

logger = logging.getLogger(__name__)

@dataclass
class CacheStats:
    """Cache statistics tracking"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

class RedisCache:
    """High-performance Redis caching service for trading data"""
    
    def __init__(self, namespace: str = "trading_bot"):
        self.namespace = namespace
        self.config = get_secure_config().get_redis_config()
        self.client = None
        self.stats = CacheStats()
        self._connect()
    
    def _connect(self):
        """Establish Redis connection with retry logic"""
        try:
            self.client = redis.Redis(
                host=self.config['host'],
                port=self.config['port'],
                password=self.config.get('password'),
                db=self.config['db'],
                decode_responses=False,  # Handle binary data
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.client.ping()
            logger.info(f"Redis connection established: {self.config['host']}:{self.config['port']}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
    
    def _generate_key(self, key: str, category: str = "general") -> str:
        """Generate namespaced cache key"""
        return f"{self.namespace}:{category}:{key}"
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage"""
        try:
            # Handle pandas DataFrames and Series
            if isinstance(data, (pd.DataFrame, pd.Series)):
                return pickle.dumps(data)
            
            # Handle numpy arrays
            elif isinstance(data, np.ndarray):
                return pickle.dumps(data)
            
            # Handle standard JSON-serializable data
            elif isinstance(data, (dict, list, str, int, float, bool, type(None))):
                return json.dumps(data, default=str).encode('utf-8')
            
            # Fallback to pickle for complex objects
            else:
                return pickle.dumps(data)
                
        except Exception as e:
            logger.error(f"Failed to serialize data: {e}")
            raise
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from Redis"""
        try:
            # Try JSON first (more efficient for simple data)
            try:
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
            
            # Fallback to pickle for complex data
            return pickle.loads(data)
            
        except Exception as e:
            logger.error(f"Failed to deserialize data: {e}")
            raise
    
    def get(self, key: str, category: str = "general") -> Optional[Any]:
        """Get data from cache"""
        if not self.client:
            self.stats.errors += 1
            return None
        
        try:
            redis_key = self._generate_key(key, category)
            data = self.client.get(redis_key)
            
            if data is None:
                self.stats.misses += 1
                return None
            
            self.stats.hits += 1
            return self._deserialize_data(data)
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.stats.errors += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600, category: str = "general") -> bool:
        """Set data in cache with TTL"""
        if not self.client:
            self.stats.errors += 1
            return False
        
        try:
            redis_key = self._generate_key(key, category)
            serialized_data = self._serialize_data(value)
            
            result = self.client.setex(redis_key, ttl, serialized_data)
            
            if result:
                self.stats.sets += 1
                return True
            else:
                self.stats.errors += 1
                return False
                
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            self.stats.errors += 1
            return False
    
    def delete(self, key: str, category: str = "general") -> bool:
        """Delete data from cache"""
        if not self.client:
            return False
        
        try:
            redis_key = self._generate_key(key, category)
            result = self.client.delete(redis_key)
            
            if result:
                self.stats.deletes += 1
                return True
            return False
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            self.stats.errors += 1
            return False
    
    def exists(self, key: str, category: str = "general") -> bool:
        """Check if key exists in cache"""
        if not self.client:
            return False
        
        try:
            redis_key = self._generate_key(key, category)
            return bool(self.client.exists(redis_key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    def get_ttl(self, key: str, category: str = "general") -> int:
        """Get TTL for a key"""
        if not self.client:
            return -1
        
        try:
            redis_key = self._generate_key(key, category)
            return self.client.ttl(redis_key)
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return -1
    
    def clear_category(self, category: str) -> int:
        """Clear all keys in a category"""
        if not self.client:
            return 0
        
        try:
            pattern = self._generate_key("*", category)
            keys = self.client.keys(pattern)
            
            if keys:
                deleted_count = self.client.delete(*keys)
                self.stats.deletes += deleted_count
                return deleted_count
            return 0
            
        except Exception as e:
            logger.error(f"Cache clear category error for {category}: {e}")
            self.stats.errors += 1
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'hits': self.stats.hits,
            'misses': self.stats.misses,
            'sets': self.stats.sets,
            'deletes': self.stats.deletes,
            'errors': self.stats.errors,
            'hit_rate': self.stats.hit_rate,
            'connected': self.client is not None
        }
    
    def flush_all(self) -> bool:
        """Flush all cache data (use with caution)"""
        if not self.client:
            return False
        
        try:
            self.client.flushdb()
            logger.warning("Redis cache flushed - all data cleared")
            return True
        except Exception as e:
            logger.error(f"Cache flush error: {e}")
            return False

class TradingDataCache:
    """Specialized caching for trading data with intelligent TTL"""
    
    def __init__(self):
        self.cache = RedisCache(namespace="trading_data")
        
        # TTL configurations for different data types
        self.ttl_config = {
            'market_data': 60,      # 1 minute for live market data
            'indicators': 300,      # 5 minutes for calculated indicators
            'historical': 3600,     # 1 hour for historical data
            'account': 30,          # 30 seconds for account info
            'positions': 15,        # 15 seconds for positions
            'orders': 10,           # 10 seconds for order data
            'signals': 60,          # 1 minute for trading signals
            'risk_data': 120,       # 2 minutes for risk calculations
        }
    
    def _generate_data_key(self, symbol: str, timeframe: str, data_type: str, **kwargs) -> str:
        """Generate standardized key for trading data"""
        base_key = f"{symbol}_{timeframe}_{data_type}"
        
        # Add additional parameters to key if provided
        if kwargs:
            param_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
            base_key = f"{base_key}_{param_str}"
        
        return base_key
    
    def cache_market_data(self, symbol: str, timeframe: str, data: pd.DataFrame) -> bool:
        """Cache market data (OHLCV)"""
        key = self._generate_data_key(symbol, timeframe, "market")
        ttl = self.ttl_config['market_data']
        return self.cache.set(key, data, ttl, "market_data")
    
    def get_market_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Get cached market data"""
        key = self._generate_data_key(symbol, timeframe, "market")
        return self.cache.get(key, "market_data")
    
    def cache_indicators(self, symbol: str, timeframe: str, indicator_name: str, 
                        data: Dict[str, Any], **params) -> bool:
        """Cache calculated indicators"""
        key = self._generate_data_key(symbol, timeframe, f"indicator_{indicator_name}", **params)
        ttl = self.ttl_config['indicators']
        return self.cache.set(key, data, ttl, "indicators")
    
    def get_indicators(self, symbol: str, timeframe: str, indicator_name: str, **params) -> Optional[Dict[str, Any]]:
        """Get cached indicators"""
        key = self._generate_data_key(symbol, timeframe, f"indicator_{indicator_name}", **params)
        return self.cache.get(key, "indicators")
    
    def cache_signal(self, symbol: str, timeframe: str, strategy: str, signal_data: Dict[str, Any]) -> bool:
        """Cache trading signal"""
        key = self._generate_data_key(symbol, timeframe, f"signal_{strategy}")
        ttl = self.ttl_config['signals']
        
        # Add timestamp to signal data
        signal_data['cached_at'] = datetime.utcnow().isoformat()
        
        return self.cache.set(key, signal_data, ttl, "signals")
    
    def get_signal(self, symbol: str, timeframe: str, strategy: str) -> Optional[Dict[str, Any]]:
        """Get cached trading signal"""
        key = self._generate_data_key(symbol, timeframe, f"signal_{strategy}")
        return self.cache.get(key, "signals")
    
    def cache_account_data(self, account_data: Dict[str, Any]) -> bool:
        """Cache account information"""
        key = "account_info"
        ttl = self.ttl_config['account']
        return self.cache.set(key, account_data, ttl, "account")
    
    def get_account_data(self) -> Optional[Dict[str, Any]]:
        """Get cached account information"""
        key = "account_info"
        return self.cache.get(key, "account")
    
    def cache_positions(self, positions_data: List[Dict[str, Any]]) -> bool:
        """Cache positions data"""
        key = "positions"
        ttl = self.ttl_config['positions']
        return self.cache.set(key, positions_data, ttl, "positions")
    
    def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached positions data"""
        key = "positions"
        return self.cache.get(key, "positions")
    
    def invalidate_symbol_data(self, symbol: str):
        """Invalidate all cached data for a symbol"""
        categories = ["market_data", "indicators", "signals"]
        for category in categories:
            pattern_key = f"{symbol}_*"
            try:
                # Get all keys matching pattern
                pattern = self.cache._generate_key(f"{symbol}_*", category)
                keys = self.cache.client.keys(pattern) if self.cache.client else []
                
                if keys:
                    self.cache.client.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} cache entries for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error invalidating cache for {symbol}: {e}")
    
    def get_cache_summary(self) -> Dict[str, Any]:
        """Get comprehensive cache summary"""
        if not self.cache.client:
            return {"error": "Redis not connected"}
        
        try:
            summary = {
                "stats": self.cache.get_stats(),
                "categories": {},
                "memory_usage": {}
            }
            
            # Get category-specific stats
            for category in self.ttl_config.keys():
                pattern = self.cache._generate_key("*", category)
                keys = self.cache.client.keys(pattern)
                summary["categories"][category] = {
                    "key_count": len(keys),
                    "ttl_setting": self.ttl_config[category]
                }
            
            # Get Redis memory info
            info = self.cache.client.info("memory")
            summary["memory_usage"] = {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B")
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting cache summary: {e}")
            return {"error": str(e)}

# Global cache instances
_redis_cache = None
_trading_cache = None

def get_redis_cache() -> RedisCache:
    """Get global Redis cache instance"""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache

def get_trading_cache() -> TradingDataCache:
    """Get global trading data cache instance"""
    global _trading_cache
    if _trading_cache is None:
        _trading_cache = TradingDataCache()
    return _trading_cache

# Cache decorator for function results
def cache_result(ttl: int = 300, category: str = "function_cache"):
    """Decorator to cache function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_redis_cache()
            
            # Generate cache key from function name and arguments
            key_data = {
                'function': func.__name__,
                'args': args,
                'kwargs': kwargs
            }
            key_hash = hashlib.md5(str(key_data).encode()).hexdigest()
            cache_key = f"{func.__name__}_{key_hash}"
            
            # Try to get from cache
            result = cache.get(cache_key, category)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl, category)
            
            return result
        return wrapper
    return decorator