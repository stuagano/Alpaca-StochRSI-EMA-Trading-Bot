"""
Memory-efficient cache with TTL (Time To Live) and size limits.
"""
import time
import threading
from typing import Any, Optional, Dict, Tuple
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """Cache entry with timestamp and value."""
    
    def __init__(self, value: Any, ttl: Optional[float] = None):
        self.value = value
        self.timestamp = time.time()
        self.ttl = ttl
        self.access_count = 1
        self.last_access = self.timestamp
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl
    
    def access(self) -> Any:
        """Access the cached value and update statistics."""
        self.access_count += 1
        self.last_access = time.time()
        return self.value


class MemoryCache:
    """
    Thread-safe memory cache with TTL and LRU eviction.
    
    Features:
    - TTL (Time To Live) support for automatic expiration
    - LRU (Least Recently Used) eviction when size limit reached
    - Thread-safe operations
    - Memory usage monitoring
    - Cleanup thread for expired entries
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        cleanup_interval: float = 60.0,
        name: str = "MemoryCache"
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.name = name
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'cleanup_runs': 0
        }
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            daemon=True,
            name=f"{name}_cleanup"
        )
        self._running = True
        self._cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired():
                del self._cache[key]
                self._stats['misses'] += 1
                self._stats['expirations'] += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._stats['hits'] += 1
            
            return entry.access()
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (overrides default_ttl)
        """
        with self._lock:
            # Use provided TTL or default
            effective_ttl = ttl if ttl is not None else self.default_ttl
            
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            
            # Check size limit and evict if necessary
            while len(self._cache) >= self.max_size:
                self._evict_lru()
            
            # Add new entry
            self._cache[key] = CacheEntry(value, effective_ttl)
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            logger.info(f"Cache {self.name} cleared")
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'name': self.name,
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': round(hit_rate, 2),
                'evictions': self._stats['evictions'],
                'expirations': self._stats['expirations'],
                'cleanup_runs': self._stats['cleanup_runs']
            }
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                self._stats['expirations'] += 1
            
            if expired_keys:
                logger.debug(f"Cache {self.name} cleaned up {len(expired_keys)} expired entries")
            
            return len(expired_keys)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._cache:
            key, _ = self._cache.popitem(last=False)  # Remove first (oldest) item
            self._stats['evictions'] += 1
            logger.debug(f"Cache {self.name} evicted LRU entry: {key}")
    
    def _cleanup_worker(self) -> None:
        """Background thread to clean up expired entries."""
        while self._running:
            try:
                time.sleep(self.cleanup_interval)
                if self._running:
                    self.cleanup_expired()
                    with self._lock:
                        self._stats['cleanup_runs'] += 1
            except Exception as e:
                logger.error(f"Error in cache cleanup worker: {e}")
    
    def shutdown(self) -> None:
        """Shutdown the cache and cleanup thread."""
        self._running = False
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        logger.info(f"Cache {self.name} shutdown complete")


class CacheManager:
    """Manages multiple named caches."""
    
    def __init__(self):
        self._caches: Dict[str, MemoryCache] = {}
        self._lock = threading.RLock()
    
    def get_cache(
        self,
        name: str,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        cleanup_interval: float = 60.0
    ) -> MemoryCache:
        """Get or create a named cache."""
        with self._lock:
            if name not in self._caches:
                self._caches[name] = MemoryCache(
                    max_size=max_size,
                    default_ttl=default_ttl,
                    cleanup_interval=cleanup_interval,
                    name=name
                )
            return self._caches[name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        with self._lock:
            return {name: cache.get_stats() for name, cache in self._caches.items()}
    
    def shutdown_all(self) -> None:
        """Shutdown all caches."""
        with self._lock:
            for cache in self._caches.values():
                cache.shutdown()
            self._caches.clear()


# Global cache manager
cache_manager = CacheManager()