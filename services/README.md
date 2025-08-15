# Unified Trading Bot Architecture

This directory contains the new unified architecture that replaces the previous duplicate and problematic implementations. The new architecture provides comprehensive solutions for the identified architectural issues.

## Architecture Overview

### Core Components

1. **`unified_data_manager.py`** - Main data management interface
2. **`database_abstraction.py`** - Thread-safe database operations with connection pooling  
3. **`memory_cache.py`** - Memory-managed caching with TTL and LRU eviction
4. **`circuit_breaker.py`** - API failure resilience patterns

## Key Improvements

### 1. Consolidated Data Management
- **Before**: Duplicate `realtime_manager.py` and `realtime_manager_flask.py` with inconsistent features
- **After**: Single `UnifiedDataManager` class with all features unified

### 2. Thread-Safe Database Operations
- **Before**: `check_same_thread=False` without proper connection management
- **After**: Connection pooling with WAL mode, proper locking, and resource management

### 3. Memory-Managed Caching
- **Before**: Unlimited price cache causing memory leaks
- **After**: TTL-based cache with size limits and automatic cleanup

### 4. API Failure Resilience
- **Before**: Basic try/catch with no pattern for handling API failures
- **After**: Circuit breaker pattern with automatic recovery and fallback

### 5. Comprehensive Error Handling
- **Before**: Inconsistent error handling across components
- **After**: Structured error handling with proper logging and recovery

## Usage Examples

### Basic Data Manager Usage

```python
from services.unified_data_manager import get_data_manager

# Get singleton instance
data_manager = get_data_manager()

# Get latest price (with caching and circuit breaker protection)
price = data_manager.get_latest_price('AAPL')

# Get historical data (with database caching)
df = data_manager.get_historical_data('AAPL', '1Min', start_hours_ago=24)

# Calculate indicators (with caching)
indicators = data_manager.calculate_indicators(df, config)

# Start real-time streaming
data_manager.start_data_stream(['AAPL', 'TSLA', 'MSFT'])

# Get system health
health = data_manager.get_system_health()
```

### Direct Database Operations

```python
from services.database_abstraction import get_database

db = get_database()

# Store historical data
df = pd.DataFrame(...)  # Your price data
db.store_historical_data('AAPL', '1Min', df)

# Get historical data with date range
data = db.get_historical_data('AAPL', '1Min', start_date, end_date)

# Get database statistics
stats = db.get_database_stats()
```

### Memory Cache Operations

```python
from services.memory_cache import cache_manager

# Get a cache instance
cache = cache_manager.get_cache('my_cache', max_size=1000, default_ttl=60.0)

# Cache operations
cache.set('key', 'value', ttl=30)  # Cache for 30 seconds
value = cache.get('key')
cache.delete('key')

# Get cache statistics
stats = cache.get_stats()
```

### Circuit Breaker Usage

```python
from services.circuit_breaker import circuit_manager

# Get a circuit breaker
breaker = circuit_manager.get_breaker('api_calls', failure_threshold=5)

# Use circuit breaker
try:
    result = breaker.call(some_api_function, arg1, arg2)
except CircuitBreakerError:
    # Handle when circuit is open
    print("Service temporarily unavailable")
```

## Configuration

### Database Configuration

The database abstraction layer automatically configures SQLite for optimal performance:

- **WAL Mode**: Better concurrency support
- **Connection Pooling**: Efficient resource usage
- **Automatic Indexes**: Optimized query performance
- **Memory Settings**: Tuned for performance

### Cache Configuration

Caches are configurable per use case:

```python
cache = cache_manager.get_cache(
    name='price_cache',
    max_size=10000,        # Maximum entries
    default_ttl=10.0,      # Default TTL in seconds
    cleanup_interval=30.0   # Cleanup frequency
)
```

### Circuit Breaker Configuration

Circuit breakers can be tuned for different services:

```python
breaker = circuit_manager.get_breaker(
    name='alpaca_api',
    failure_threshold=5,    # Failures before opening
    recovery_timeout=60,    # Seconds before retry
    expected_exception=Exception  # Exception types to catch
)
```

## Migration Guide

### From Old Architecture

1. **Update Imports**:
   ```python
   # Old
   from realtime_manager import get_data_manager
   # New  
   from services.unified_data_manager import get_data_manager
   ```

2. **Run Migration Script**:
   ```bash
   python migrate_to_unified_architecture.py
   ```

3. **Test New Architecture**:
   - All existing interfaces are preserved
   - Enhanced with new features automatically
   - Monitor logs for any issues

### API Compatibility

The new `UnifiedDataManager` maintains full API compatibility with the old implementations:

- `get_latest_price(symbol)` - Enhanced with caching and circuit breaker
- `get_historical_data(...)` - Enhanced with database caching
- `get_account_info()` - Enhanced with circuit breaker protection
- `get_positions()` - Enhanced with circuit breaker protection
- `calculate_indicators(...)` - Enhanced with caching
- `start_data_stream(...)` - Enhanced with better error handling
- `stop_data_stream()` - Enhanced with proper cleanup

## Monitoring and Health Checks

### System Health

```python
health = data_manager.get_system_health()
# Returns:
# {
#     'api_initialized': bool,
#     'streaming': bool, 
#     'last_update': str,
#     'cache_stats': {...},
#     'database_stats': {...},
#     'circuit_breakers': {...}
# }
```

### Cache Statistics

```python
stats = cache_manager.get_all_stats()
# Per-cache statistics including hit rates, evictions, etc.
```

### Database Statistics

```python
stats = db.get_database_stats()
# Connection pool status, table sizes, performance metrics
```

### Circuit Breaker Status

```python
status = circuit_manager.get_status()
# Current state of all circuit breakers
```

## Performance Characteristics

### Database Operations
- **Connection Pooling**: 10 connections by default
- **WAL Mode**: Better concurrent read/write performance
- **Optimized Queries**: Proper indexing for common operations

### Memory Cache
- **LRU Eviction**: Efficient memory usage
- **TTL Cleanup**: Background thread removes expired entries
- **Thread-Safe**: Concurrent access with RLock protection

### Circuit Breaker
- **Low Overhead**: Minimal performance impact when closed
- **Fast Failure**: Immediate response when open
- **Automatic Recovery**: Self-healing behavior

## Thread Safety

All components are designed for thread-safe operation:

- **Database**: Connection pooling with proper locking
- **Cache**: RLock protection for all operations  
- **Circuit Breaker**: Thread-safe state management
- **Data Manager**: Singleton pattern with thread-safe initialization

## Error Handling

Comprehensive error handling at all levels:

- **Database Errors**: Connection retry, transaction rollback
- **API Errors**: Circuit breaker protection, fallback to cache
- **Cache Errors**: Graceful degradation, cleanup on failure
- **Memory Errors**: Automatic cleanup, size limits

## Cleanup and Resource Management

Proper resource cleanup is handled automatically:

```python
# Manual cleanup if needed
from services.unified_data_manager import cleanup_data_manager
from services.database_abstraction import close_database
from services.memory_cache import cache_manager

cleanup_data_manager()
close_database() 
cache_manager.shutdown_all()
```

## Best Practices

1. **Use Singleton Pattern**: Always use `get_data_manager()` for data access
2. **Monitor Health**: Regularly check `get_system_health()` 
3. **Handle Exceptions**: Expect `CircuitBreakerError` during API issues
4. **Configure Appropriately**: Tune cache sizes and TTLs for your use case
5. **Clean Shutdown**: Call cleanup functions on application exit

## Troubleshooting

### Common Issues

1. **Database Lock Errors**: 
   - Check connection pool configuration
   - Ensure proper cleanup on shutdown

2. **Memory Usage**: 
   - Monitor cache statistics
   - Adjust cache sizes if needed

3. **API Failures**:
   - Check circuit breaker status
   - Verify API credentials

4. **Performance Issues**:
   - Run performance benchmarks
   - Check database statistics
   - Monitor cache hit rates

### Debug Logging

Enable debug logging for detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

Planned improvements:

1. **Metrics Export**: Prometheus/InfluxDB integration
2. **Health Endpoints**: HTTP health check endpoints
3. **Configuration**: External configuration file support
4. **Backup/Restore**: Database backup automation
5. **Clustering**: Multi-instance coordination