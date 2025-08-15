"""
Advanced Performance Optimizer for Trading Bot Application.

This module provides comprehensive performance improvements including:
- Advanced caching strategies with Redis support
- Database query optimization and connection pooling
- Async/await patterns for API calls
- Batch processing for multiple operations
- Resource pooling management
- Memory usage optimization
- Query result optimization
"""

import asyncio
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Callable, Union, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict, deque
import json
import gzip
import pickle
from datetime import datetime, timedelta
import weakref

# Performance monitoring imports
import psutil
import gc

# Database and caching imports
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    
try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except ImportError:
    AIOREDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    operation_name: str
    start_time: float
    end_time: float
    duration: float
    memory_before: float
    memory_after: float
    cache_hits: int = 0
    cache_misses: int = 0
    batch_size: int = 0
    
    @property
    def memory_delta(self) -> float:
        """Memory usage change in MB."""
        return self.memory_after - self.memory_before


class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self, max_metrics: int = 10000):
        self.metrics: deque = deque(maxlen=max_metrics)
        self._lock = threading.RLock()
        self.operation_stats = defaultdict(list)
    
    def start_operation(self, operation_name: str) -> Dict[str, Any]:
        """Start tracking an operation."""
        return {
            'operation_name': operation_name,
            'start_time': time.perf_counter(),
            'memory_before': self._get_memory_usage()
        }
    
    def end_operation(self, context: Dict[str, Any], **kwargs) -> PerformanceMetrics:
        """End tracking an operation and record metrics."""
        end_time = time.perf_counter()
        memory_after = self._get_memory_usage()
        
        metrics = PerformanceMetrics(
            operation_name=context['operation_name'],
            start_time=context['start_time'],
            end_time=end_time,
            duration=end_time - context['start_time'],
            memory_before=context['memory_before'],
            memory_after=memory_after,
            **kwargs
        )
        
        with self._lock:
            self.metrics.append(metrics)
            self.operation_stats[metrics.operation_name].append(metrics.duration)
        
        return metrics
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, float]:
        """Get statistics for a specific operation."""
        with self._lock:
            durations = self.operation_stats.get(operation_name, [])
            if not durations:
                return {}
            
            durations = list(durations)[-1000:]  # Last 1000 operations
            
            return {
                'count': len(durations),
                'avg_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'total_duration': sum(durations)
            }
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall performance statistics."""
        with self._lock:
            if not self.metrics:
                return {}
            
            recent_metrics = list(self.metrics)[-1000:]  # Last 1000 operations
            
            total_duration = sum(m.duration for m in recent_metrics)
            total_memory_delta = sum(m.memory_delta for m in recent_metrics)
            cache_hits = sum(m.cache_hits for m in recent_metrics)
            cache_misses = sum(m.cache_misses for m in recent_metrics)
            
            return {
                'total_operations': len(recent_metrics),
                'total_duration': total_duration,
                'avg_duration': total_duration / len(recent_metrics),
                'total_memory_delta': total_memory_delta,
                'cache_hit_rate': cache_hits / (cache_hits + cache_misses) * 100 if (cache_hits + cache_misses) > 0 else 0,
                'operations_by_type': {op: len(stats) for op, stats in self.operation_stats.items()}
            }


class AdvancedCacheStrategy:
    """Advanced caching with multiple strategies and Redis support."""
    
    def __init__(self, redis_url: Optional[str] = None, enable_compression: bool = True):
        self.enable_compression = enable_compression
        self.local_cache = {}
        self.cache_stats = defaultdict(int)
        self._lock = threading.RLock()
        
        # Redis setup
        self.redis_client = None
        self.aio_redis_client = None
        if redis_url and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False)
                self.redis_client.ping()  # Test connection
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis: {e}")
                self.redis_client = None
    
    async def get_async_redis(self) -> Optional[Any]:
        """Get async Redis client."""
        if not AIOREDIS_AVAILABLE or not self.redis_client:
            return None
            
        if not self.aio_redis_client:
            try:
                self.aio_redis_client = aioredis.from_url(
                    self.redis_client.connection_pool.connection_kwargs['host']
                )
            except Exception as e:
                logger.warning(f"Failed to initialize async Redis: {e}")
                return None
        
        return self.aio_redis_client
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize and optionally compress value."""
        data = pickle.dumps(value)
        if self.enable_compression and len(data) > 1024:  # Compress if > 1KB
            data = gzip.compress(data)
        return data
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize and decompress value."""
        try:
            # Try decompression first
            if self.enable_compression:
                try:
                    data = gzip.decompress(data)
                except gzip.BadGzipFile:
                    pass  # Not compressed
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Failed to deserialize cache value: {e}")
            return None
    
    def get(self, key: str, ttl_check: bool = True) -> Tuple[Any, bool]:
        """
        Get value from cache with multi-level lookup.
        
        Returns:
            Tuple of (value, cache_hit)
        """
        # Check local cache first
        with self._lock:
            if key in self.local_cache:
                entry = self.local_cache[key]
                if not ttl_check or entry['expires'] > time.time():
                    self.cache_stats['local_hits'] += 1
                    return entry['value'], True
                else:
                    del self.local_cache[key]
        
        # Check Redis cache
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    value = self._deserialize_value(data)
                    if value is not None:
                        # Store in local cache for faster access
                        self._store_local(key, value, ttl=300)  # 5 minute local TTL
                        self.cache_stats['redis_hits'] += 1
                        return value, True
            except Exception as e:
                logger.debug(f"Redis get failed for {key}: {e}")
        
        self.cache_stats['misses'] += 1
        return None, False
    
    async def get_async(self, key: str, ttl_check: bool = True) -> Tuple[Any, bool]:
        """Async version of get."""
        # Check local cache first
        value, hit = self.get(key, ttl_check)
        if hit:
            return value, hit
        
        # Check async Redis
        redis_client = await self.get_async_redis()
        if redis_client:
            try:
                data = await redis_client.get(key)
                if data:
                    value = self._deserialize_value(data)
                    if value is not None:
                        self._store_local(key, value, ttl=300)
                        self.cache_stats['redis_hits'] += 1
                        return value, True
            except Exception as e:
                logger.debug(f"Async Redis get failed for {key}: {e}")
        
        self.cache_stats['misses'] += 1
        return None, False
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with multi-level storage."""
        success = False
        
        # Store in local cache
        self._store_local(key, value, ttl or 3600)
        success = True
        
        # Store in Redis
        if self.redis_client:
            try:
                data = self._serialize_value(value)
                if ttl:
                    self.redis_client.setex(key, ttl, data)
                else:
                    self.redis_client.set(key, data)
                self.cache_stats['redis_sets'] += 1
            except Exception as e:
                logger.debug(f"Redis set failed for {key}: {e}")
        
        return success
    
    async def set_async(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Async version of set."""
        # Store in local cache
        self._store_local(key, value, ttl or 3600)
        
        # Store in async Redis
        redis_client = await self.get_async_redis()
        if redis_client:
            try:
                data = self._serialize_value(value)
                if ttl:
                    await redis_client.setex(key, ttl, data)
                else:
                    await redis_client.set(key, data)
                self.cache_stats['redis_sets'] += 1
            except Exception as e:
                logger.debug(f"Async Redis set failed for {key}: {e}")
        
        return True
    
    def _store_local(self, key: str, value: Any, ttl: int) -> None:
        """Store value in local cache."""
        with self._lock:
            # Clean up expired entries occasionally
            if len(self.local_cache) % 100 == 0:
                self._cleanup_local_cache()
            
            # Limit local cache size
            if len(self.local_cache) > 10000:
                # Remove oldest 20% of entries
                items = list(self.local_cache.items())
                items.sort(key=lambda x: x[1]['created'])
                for k, _ in items[:2000]:
                    del self.local_cache[k]
            
            self.local_cache[key] = {
                'value': value,
                'expires': time.time() + ttl,
                'created': time.time()
            }
    
    def _cleanup_local_cache(self) -> None:
        """Remove expired entries from local cache."""
        current_time = time.time()
        expired_keys = [
            k for k, v in self.local_cache.items()
            if v['expires'] <= current_time
        ]
        for key in expired_keys:
            del self.local_cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = sum([
                self.cache_stats['local_hits'],
                self.cache_stats['redis_hits'],
                self.cache_stats['misses']
            ])
            
            return {
                'local_cache_size': len(self.local_cache),
                'total_requests': total_requests,
                'hit_rate': (self.cache_stats['local_hits'] + self.cache_stats['redis_hits']) / total_requests * 100 if total_requests > 0 else 0,
                'local_hit_rate': self.cache_stats['local_hits'] / total_requests * 100 if total_requests > 0 else 0,
                'redis_available': self.redis_client is not None,
                **dict(self.cache_stats)
            }


class DatabaseOptimizer:
    """Database query optimization and connection pooling."""
    
    def __init__(self, max_connections: int = 20):
        self.max_connections = max_connections
        self.connection_pool = []
        self.active_connections = 0
        self._lock = threading.RLock()
        self.query_cache = AdvancedCacheStrategy()
        self.prepared_statements = {}
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool."""
        connection = None
        try:
            with self._lock:
                if self.connection_pool:
                    connection = self.connection_pool.pop()
                elif self.active_connections < self.max_connections:
                    # Create new connection (placeholder - implement with actual DB)
                    connection = self._create_connection()
                    self.active_connections += 1
                else:
                    # Wait for available connection
                    await asyncio.sleep(0.1)
                    connection = self.connection_pool.pop() if self.connection_pool else None
            
            if connection:
                yield connection
            else:
                raise Exception("No database connection available")
                
        finally:
            if connection:
                with self._lock:
                    self.connection_pool.append(connection)
    
    def _create_connection(self):
        """Create new database connection (implement with actual DB)."""
        # Placeholder - implement with actual database connection
        return f"connection_{self.active_connections}"
    
    def optimize_query(self, query: str, params: Optional[Tuple] = None) -> str:
        """Optimize SQL query."""
        # Basic query optimization patterns
        optimized = query.strip()
        
        # Add indexes hints for common patterns
        if "WHERE symbol =" in optimized and "ORDER BY timestamp" in optimized:
            optimized = optimized.replace(
                "ORDER BY timestamp",
                "ORDER BY timestamp USE INDEX (idx_symbol_timestamp)"
            )
        
        # Cache prepared statements
        query_hash = hash((optimized, params))
        if query_hash not in self.prepared_statements:
            self.prepared_statements[query_hash] = {
                'query': optimized,
                'params': params,
                'usage_count': 0
            }
        
        self.prepared_statements[query_hash]['usage_count'] += 1
        
        return optimized
    
    async def execute_cached_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        cache_ttl: int = 300
    ) -> Any:
        """Execute query with caching."""
        cache_key = f"query_{hash((query, params))}"
        
        # Check cache first
        result, hit = await self.query_cache.get_async(cache_key)
        if hit:
            return result
        
        # Execute query
        async with self.get_connection() as conn:
            # Placeholder for actual query execution
            result = f"query_result_{time.time()}"
        
        # Cache result
        await self.query_cache.set_async(cache_key, result, cache_ttl)
        
        return result
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        with self._lock:
            return {
                'active_connections': self.active_connections,
                'available_connections': len(self.connection_pool),
                'max_connections': self.max_connections,
                'pool_utilization': (self.active_connections - len(self.connection_pool)) / self.max_connections * 100,
                'prepared_statements': len(self.prepared_statements)
            }


class BatchProcessor:
    """Batch processing for multiple operations."""
    
    def __init__(self, max_batch_size: int = 100, max_wait_time: float = 1.0):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.pending_operations = defaultdict(list)
        self.batch_timers = {}
        self._lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="BatchProcessor")
    
    async def add_operation(
        self,
        operation_type: str,
        operation_data: Any,
        callback: Optional[Callable] = None
    ) -> Any:
        """Add operation to batch queue."""
        future = asyncio.Future()
        
        with self._lock:
            self.pending_operations[operation_type].append({
                'data': operation_data,
                'future': future,
                'callback': callback,
                'timestamp': time.time()
            })
            
            # Start timer if not already running
            if operation_type not in self.batch_timers:
                self.batch_timers[operation_type] = asyncio.create_task(
                    self._wait_and_process(operation_type)
                )
            
            # Process immediately if batch is full
            if len(self.pending_operations[operation_type]) >= self.max_batch_size:
                await self._process_batch(operation_type)
        
        return await future
    
    async def _wait_and_process(self, operation_type: str) -> None:
        """Wait for max time then process batch."""
        try:
            await asyncio.sleep(self.max_wait_time)
            await self._process_batch(operation_type)
        except asyncio.CancelledError:
            pass
        finally:
            with self._lock:
                if operation_type in self.batch_timers:
                    del self.batch_timers[operation_type]
    
    async def _process_batch(self, operation_type: str) -> None:
        """Process a batch of operations."""
        with self._lock:
            operations = self.pending_operations[operation_type].copy()
            self.pending_operations[operation_type].clear()
            
            # Cancel timer
            if operation_type in self.batch_timers:
                self.batch_timers[operation_type].cancel()
                del self.batch_timers[operation_type]
        
        if not operations:
            return
        
        try:
            # Process batch based on operation type
            if operation_type == 'price_fetch':
                results = await self._process_price_batch(operations)
            elif operation_type == 'indicator_calc':
                results = await self._process_indicator_batch(operations)
            elif operation_type == 'database_write':
                results = await self._process_database_batch(operations)
            else:
                results = await self._process_generic_batch(operations)
            
            # Set results for futures
            for i, operation in enumerate(operations):
                if i < len(results):
                    operation['future'].set_result(results[i])
                    if operation['callback']:
                        operation['callback'](results[i])
                else:
                    operation['future'].set_exception(Exception("Batch processing failed"))
                    
        except Exception as e:
            # Set exception for all futures
            for operation in operations:
                if not operation['future'].done():
                    operation['future'].set_exception(e)
    
    async def _process_price_batch(self, operations: List[Dict]) -> List[Any]:
        """Process price fetch batch."""
        symbols = [op['data']['symbol'] for op in operations]
        # Batch API call for multiple symbols
        results = []
        for symbol in symbols:
            # Placeholder - implement actual batch price fetching
            results.append({'symbol': symbol, 'price': 100.0 + hash(symbol) % 50})
        return results
    
    async def _process_indicator_batch(self, operations: List[Dict]) -> List[Any]:
        """Process indicator calculation batch."""
        # Group by similar parameters for efficient calculation
        grouped = defaultdict(list)
        for i, op in enumerate(operations):
            key = (op['data']['indicator_type'], str(op['data'].get('params', {})))
            grouped[key].append((i, op))
        
        results = [None] * len(operations)
        
        for (indicator_type, params), group in grouped.items():
            # Calculate indicators for the group
            for i, (original_index, op) in enumerate(group):
                # Placeholder calculation
                results[original_index] = {
                    'indicator': indicator_type,
                    'value': hash(str(op['data'])) % 100
                }
        
        return results
    
    async def _process_database_batch(self, operations: List[Dict]) -> List[Any]:
        """Process database write batch."""
        # Batch database operations
        results = []
        for op in operations:
            # Placeholder - implement actual batch database operations
            results.append({'status': 'success', 'id': hash(str(op['data']))})
        return results
    
    async def _process_generic_batch(self, operations: List[Dict]) -> List[Any]:
        """Process generic batch operations."""
        results = []
        for op in operations:
            results.append({'processed': True, 'data': op['data']})
        return results
    
    def get_batch_stats(self) -> Dict[str, Any]:
        """Get batch processing statistics."""
        with self._lock:
            return {
                'pending_batches': len(self.pending_operations),
                'active_timers': len(self.batch_timers),
                'pending_operations': {
                    op_type: len(ops) for op_type, ops in self.pending_operations.items()
                },
                'executor_threads': self.executor._threads,
                'max_batch_size': self.max_batch_size,
                'max_wait_time': self.max_wait_time
            }


class ResourcePoolManager:
    """Manage various resource pools for optimal performance."""
    
    def __init__(self):
        self.thread_pools = {}
        self.memory_pools = {}
        self.resource_stats = defaultdict(int)
        self._lock = threading.RLock()
        
        # Create default pools
        self.thread_pools['api_calls'] = ThreadPoolExecutor(
            max_workers=20, thread_name_prefix="APIPool"
        )
        self.thread_pools['data_processing'] = ThreadPoolExecutor(
            max_workers=10, thread_name_prefix="DataPool"
        )
        self.thread_pools['background_tasks'] = ThreadPoolExecutor(
            max_workers=5, thread_name_prefix="BackgroundPool"
        )
    
    def get_thread_pool(self, pool_name: str) -> ThreadPoolExecutor:
        """Get or create thread pool."""
        with self._lock:
            if pool_name not in self.thread_pools:
                self.thread_pools[pool_name] = ThreadPoolExecutor(
                    max_workers=10, thread_name_prefix=f"{pool_name}Pool"
                )
            return self.thread_pools[pool_name]
    
    async def execute_with_pool(
        self,
        pool_name: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with specific thread pool."""
        pool = self.get_thread_pool(pool_name)
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(pool, func, *args, **kwargs)
            self.resource_stats[f"{pool_name}_success"] += 1
            return result
        except Exception as e:
            self.resource_stats[f"{pool_name}_error"] += 1
            raise e
    
    async def execute_batch_with_pool(
        self,
        pool_name: str,
        func: Callable,
        items: List[Any],
        max_concurrent: int = 10
    ) -> List[Any]:
        """Execute batch of operations with pool and concurrency limit."""
        pool = self.get_thread_pool(pool_name)
        loop = asyncio.get_event_loop()
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_item(item):
            async with semaphore:
                try:
                    result = await loop.run_in_executor(pool, func, item)
                    self.resource_stats[f"{pool_name}_batch_success"] += 1
                    return result
                except Exception as e:
                    self.resource_stats[f"{pool_name}_batch_error"] += 1
                    logger.error(f"Batch execution error: {e}")
                    return None
        
        tasks = [execute_item(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if not isinstance(r, Exception)]
    
    def optimize_memory_usage(self) -> Dict[str, Any]:
        """Optimize memory usage and return statistics."""
        # Force garbage collection
        collected = gc.collect()
        
        # Get memory statistics
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'garbage_collected': collected,
            'memory_usage_mb': memory_info.rss / 1024 / 1024,
            'memory_percent': process.memory_percent(),
            'open_files': len(process.open_files()) if hasattr(process, 'open_files') else 0
        }
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get comprehensive resource statistics."""
        with self._lock:
            thread_stats = {}
            for name, pool in self.thread_pools.items():
                thread_stats[name] = {
                    'max_workers': pool._max_workers,
                    'active_threads': len(pool._threads) if hasattr(pool, '_threads') else 0
                }
            
            return {
                'thread_pools': thread_stats,
                'resource_stats': dict(self.resource_stats),
                'memory_stats': self.optimize_memory_usage()
            }
    
    def shutdown(self) -> None:
        """Shutdown all resource pools."""
        with self._lock:
            for pool in self.thread_pools.values():
                pool.shutdown(wait=True)
            self.thread_pools.clear()


class PerformanceOptimizer:
    """Main performance optimizer class."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.monitor = PerformanceMonitor()
        self.cache = AdvancedCacheStrategy(redis_url)
        self.db_optimizer = DatabaseOptimizer()
        self.batch_processor = BatchProcessor()
        self.resource_manager = ResourcePoolManager()
        
        # Performance settings
        self.optimization_settings = {
            'enable_caching': True,
            'enable_batching': True,
            'enable_compression': True,
            'cache_ttl': 300,
            'batch_size': 100,
            'max_concurrent': 20
        }
        
        logger.info("Performance optimizer initialized")
    
    def track_performance(self, operation_name: str):
        """Decorator to track operation performance."""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                context = self.monitor.start_operation(operation_name)
                try:
                    result = await func(*args, **kwargs)
                    self.monitor.end_operation(context, cache_hits=1 if hasattr(result, '_from_cache') else 0)
                    return result
                except Exception as e:
                    self.monitor.end_operation(context, cache_hits=0, cache_misses=1)
                    raise e
            
            def sync_wrapper(*args, **kwargs):
                context = self.monitor.start_operation(operation_name)
                try:
                    result = func(*args, **kwargs)
                    self.monitor.end_operation(context, cache_hits=1 if hasattr(result, '_from_cache') else 0)
                    return result
                except Exception as e:
                    self.monitor.end_operation(context, cache_hits=0, cache_misses=1)
                    raise e
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    async def optimize_data_fetch(
        self,
        symbols: List[str],
        fetch_func: Callable,
        cache_key_prefix: str = "data",
        ttl: int = 300
    ) -> Dict[str, Any]:
        """Optimize data fetching with caching and batching."""
        results = {}
        cache_hits = 0
        cache_misses = 0
        
        # Check cache for all symbols
        cached_symbols = set()
        for symbol in symbols:
            cache_key = f"{cache_key_prefix}_{symbol}"
            value, hit = await self.cache.get_async(cache_key)
            if hit:
                results[symbol] = value
                cached_symbols.add(symbol)
                cache_hits += 1
            else:
                cache_misses += 1
        
        # Fetch missing symbols in batch
        missing_symbols = [s for s in symbols if s not in cached_symbols]
        if missing_symbols:
            if self.optimization_settings['enable_batching']:
                # Use batch processing
                batch_results = await self.resource_manager.execute_batch_with_pool(
                    'api_calls',
                    fetch_func,
                    missing_symbols,
                    max_concurrent=self.optimization_settings['max_concurrent']
                )
                
                # Cache and store results
                for i, symbol in enumerate(missing_symbols):
                    if i < len(batch_results) and batch_results[i] is not None:
                        results[symbol] = batch_results[i]
                        cache_key = f"{cache_key_prefix}_{symbol}"
                        await self.cache.set_async(cache_key, batch_results[i], ttl)
            else:
                # Fetch individually
                for symbol in missing_symbols:
                    try:
                        result = await self.resource_manager.execute_with_pool(
                            'api_calls', fetch_func, symbol
                        )
                        results[symbol] = result
                        cache_key = f"{cache_key_prefix}_{symbol}"
                        await self.cache.set_async(cache_key, result, ttl)
                    except Exception as e:
                        logger.error(f"Failed to fetch data for {symbol}: {e}")
        
        # Add performance metadata
        results['_performance'] = {
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'total_symbols': len(symbols),
            'cache_hit_rate': cache_hits / len(symbols) * 100 if symbols else 0
        }
        
        return results
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        return {
            'monitor': self.monitor.get_overall_stats(),
            'cache': self.cache.get_stats(),
            'database': self.db_optimizer.get_pool_stats(),
            'batch_processor': self.batch_processor.get_batch_stats(),
            'resource_manager': self.resource_manager.get_resource_stats(),
            'settings': self.optimization_settings
        }
    
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update optimization settings."""
        self.optimization_settings.update(settings)
        logger.info(f"Updated optimization settings: {settings}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up performance optimizer...")
        self.resource_manager.shutdown()
        # Cache cleanup happens automatically
        logger.info("Performance optimizer cleanup complete")


# Global performance optimizer instance
_performance_optimizer: Optional[PerformanceOptimizer] = None
_optimizer_lock = threading.RLock()


def get_performance_optimizer(redis_url: Optional[str] = None) -> PerformanceOptimizer:
    """Get singleton performance optimizer instance."""
    global _performance_optimizer
    
    with _optimizer_lock:
        if _performance_optimizer is None:
            _performance_optimizer = PerformanceOptimizer(redis_url)
        return _performance_optimizer


def cleanup_performance_optimizer() -> None:
    """Clean up singleton performance optimizer."""
    global _performance_optimizer
    
    with _optimizer_lock:
        if _performance_optimizer is not None:
            _performance_optimizer.cleanup()
            _performance_optimizer = None