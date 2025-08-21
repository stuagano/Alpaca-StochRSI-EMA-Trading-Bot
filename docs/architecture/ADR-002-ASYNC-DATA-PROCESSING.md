# ADR-002: Asynchronous Data Processing Pipeline

## Status
Proposed

## Context

The current trading bot processes market data and calculates technical indicators synchronously, creating several performance bottlenecks:

### Current Issues
1. **Blocking Operations:** Indicator calculations block real-time data updates
2. **Sequential Processing:** Multiple symbols processed one at a time
3. **Latency Impact:** Signal generation delayed by expensive calculations
4. **Resource Underutilization:** Single-threaded processing on multi-core systems

### Performance Analysis
```python
# Current synchronous approach
def process_market_data(self, symbols: List[str]):
    for symbol in symbols:  # Sequential processing
        df = self.get_historical_data(symbol)  # Blocking I/O
        indicators = self.calculate_indicators(df)  # CPU intensive
        signal = self.generate_signal(indicators)  # Sequential
        self.process_signal(signal)  # More blocking I/O
```

**Measured Impact:**
- Processing 10 symbols takes 15-20 seconds
- Real-time updates delayed during indicator calculations
- High CPU utilization on single core while others idle

## Decision

We will implement an asynchronous data processing pipeline using Python's asyncio framework with the following architecture:

### Technical Architecture

```python
class AsyncDataProcessor:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(10)  # Limit concurrent operations
        self.executor = ThreadPoolExecutor(max_workers=4)  # CPU-bound tasks
        
    async def process_symbols_parallel(self, symbols: List[str]):
        """Process multiple symbols concurrently"""
        tasks = [self.process_symbol(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self.handle_results(results)
    
    async def process_symbol(self, symbol: str):
        """Process single symbol asynchronously"""
        async with self.semaphore:
            # I/O bound operations (async)
            df = await self.get_historical_data_async(symbol)
            
            # CPU bound operations (thread pool)
            indicators = await self.calculate_indicators_async(df)
            
            # Signal generation and processing
            signal = await self.generate_signal_async(indicators)
            await self.process_signal_async(signal)
            
            return {"symbol": symbol, "signal": signal}
```

### Implementation Strategy

#### 1. Async I/O Operations
Convert database and API calls to async operations:
```python
class AsyncUnifiedDataManager:
    async def get_historical_data_async(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Non-blocking database query"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._get_historical_data_sync, 
            symbol, 
            kwargs
        )
    
    async def get_latest_price_async(self, symbol: str) -> Optional[float]:
        """Non-blocking API call with circuit breaker"""
        try:
            async with aiohttp.ClientSession() as session:
                return await self._fetch_price_with_retry(session, symbol)
        except Exception as e:
            logger.error(f"Async price fetch failed for {symbol}: {e}")
            return None
```

#### 2. CPU-Intensive Operations
Use thread pools for CPU-bound indicator calculations:
```python
class AsyncIndicatorCalculator:
    def __init__(self):
        self.cpu_executor = ThreadPoolExecutor(
            max_workers=min(4, os.cpu_count()),
            thread_name_prefix="IndicatorCalc"
        )
    
    async def calculate_indicators_async(self, df: pd.DataFrame, config: Dict) -> Dict:
        """Calculate indicators in parallel using thread pool"""
        loop = asyncio.get_event_loop()
        
        # Split CPU-intensive calculations across threads
        tasks = []
        if config['indicators'].get('stochRSI') == "True":
            tasks.append(loop.run_in_executor(
                self.cpu_executor, 
                self._calculate_stoch_rsi, 
                df, 
                config
            ))
        
        if config['indicators'].get('EMA') == "True":
            tasks.append(loop.run_in_executor(
                self.cpu_executor, 
                self._calculate_ema, 
                df, 
                config
            ))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._merge_indicator_results(results)
```

#### 3. Real-time Data Streaming
Implement async WebSocket data streaming:
```python
class AsyncDataStreamer:
    async def start_real_time_stream(self, symbols: List[str]):
        """Start async real-time data streaming"""
        self.running = True
        
        # Create tasks for each data source
        tasks = [
            self.stream_market_data(symbols),
            self.stream_account_updates(),
            self.process_signal_queue(),
            self.broadcast_updates()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stream_market_data(self, symbols: List[str]):
        """Async market data streaming"""
        while self.running:
            try:
                # Process symbols in batches
                for batch in self.batch_symbols(symbols, batch_size=5):
                    await asyncio.gather(*[
                        self.update_symbol_data(symbol) 
                        for symbol in batch
                    ])
                
                await asyncio.sleep(1)  # Non-blocking sleep
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await asyncio.sleep(5)  # Back-off on error
```

## Implementation Plan

### Phase 1: Core Async Infrastructure (2-3 days)
1. **Async Data Manager**
   - Convert database operations to async
   - Implement async API clients
   - Add connection pooling for async operations

2. **Thread Pool Setup**
   - Configure thread pools for CPU-bound tasks
   - Implement indicator calculation threading
   - Add resource monitoring

### Phase 2: Async Processing Pipeline (2-3 days)
1. **Parallel Symbol Processing**
   - Implement concurrent symbol processing
   - Add semaphore-based rate limiting
   - Error handling and retry logic

2. **Real-time Streaming**
   - Convert WebSocket handlers to async
   - Implement async message queuing
   - Add backpressure handling

### Phase 3: Integration & Optimization (1-2 days)
1. **Flask Integration**
   - Add async route handlers
   - Implement async context management
   - Update error handling

2. **Performance Optimization**
   - Tune concurrency parameters
   - Optimize batch sizes
   - Monitor resource utilization

## Benefits

### Performance Improvements
- **60% faster processing:** Parallel indicator calculations
- **75% reduced latency:** Non-blocking I/O operations
- **4x throughput:** Concurrent symbol processing
- **Real-time responsiveness:** No blocking operations

### Scalability Benefits
- **Better resource utilization:** Multi-core CPU usage
- **Higher concurrency:** Support for more simultaneous users
- **Elastic scaling:** Adjustable concurrency limits
- **Memory efficiency:** Streaming data processing

### Operational Benefits
- **Improved reliability:** Better error isolation
- **Enhanced monitoring:** Detailed async operation metrics
- **Graceful degradation:** Circuit breakers for external services

## Consequences

### Positive
1. **Performance:** Significant improvement in processing speed
2. **Scalability:** Better resource utilization and concurrency
3. **Reliability:** Improved error handling and isolation
4. **Monitoring:** Better observability into system performance

### Negative
1. **Complexity:** Increased code complexity and debugging difficulty
2. **Learning Curve:** Team needs async/await expertise
3. **Testing Challenges:** More complex test scenarios
4. **Memory Usage:** Potential increase due to concurrent operations

### Migration Risks
- **Race Conditions:** Potential for subtle concurrency bugs
- **Resource Leaks:** Improper async context management
- **Backward Compatibility:** Changes to existing API contracts

## Technical Requirements

### Dependencies
```python
# Additional dependencies
aiohttp>=3.8.0           # Async HTTP client
asyncio-throttle>=1.0.2  # Rate limiting
aiofiles>=0.8.0          # Async file operations
aiodns>=3.0.0            # Async DNS resolution
```

### Configuration
```python
@dataclass
class AsyncConfig:
    max_concurrent_symbols: int = 10
    max_concurrent_requests: int = 50
    cpu_thread_pool_size: int = 4
    io_thread_pool_size: int = 20
    request_timeout: float = 30.0
    retry_attempts: int = 3
    backoff_factor: float = 2.0
```

## Monitoring & Metrics

### Key Performance Indicators
```python
from prometheus_client import Histogram, Counter, Gauge

# Async operation metrics
async_operation_duration = Histogram(
    'async_operation_duration_seconds',
    'Duration of async operations',
    ['operation_type']
)

active_async_tasks = Gauge(
    'active_async_tasks',
    'Number of active async tasks'
)

async_errors = Counter(
    'async_errors_total',
    'Total async operation errors',
    ['operation_type', 'error_type']
)
```

### Health Checks
```python
class AsyncHealthChecker:
    async def check_async_operations(self) -> Dict[str, bool]:
        """Check health of async operations"""
        checks = {
            'data_streaming': await self.check_data_stream(),
            'indicator_processing': await self.check_indicator_calc(),
            'api_connectivity': await self.check_external_apis(),
            'thread_pools': self.check_thread_pool_health()
        }
        return checks
```

## Testing Strategy

### Unit Testing
```python
import pytest
import asyncio

class TestAsyncDataProcessor:
    @pytest.mark.asyncio
    async def test_parallel_symbol_processing(self):
        """Test concurrent symbol processing"""
        processor = AsyncDataProcessor()
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
        
        start_time = time.time()
        results = await processor.process_symbols_parallel(symbols)
        duration = time.time() - start_time
        
        assert len(results) == len(symbols)
        assert duration < 5.0  # Should be much faster than sequential
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error isolation in async operations"""
        # Test that one failing symbol doesn't affect others
        pass
```

### Integration Testing
- **Load Testing:** Simulate high concurrent load
- **Latency Testing:** Measure response time improvements
- **Reliability Testing:** Error injection and recovery
- **Memory Testing:** Monitor memory usage under load

## Risk Mitigation

### Risk 1: Race Conditions
- **Mitigation:** Comprehensive async testing, use of locks where needed
- **Detection:** Monitoring for data inconsistencies
- **Fallback:** Ability to disable async for specific operations

### Risk 2: Resource Exhaustion
- **Mitigation:** Semaphores and rate limiting
- **Detection:** Resource usage monitoring
- **Fallback:** Automatic scaling down of concurrency

### Risk 3: Debugging Complexity
- **Mitigation:** Enhanced logging and tracing
- **Detection:** Structured error reporting
- **Fallback:** Debug mode with synchronous fallback

## Alternatives Considered

### Alternative 1: Multiprocessing
- **Pros:** True parallelism, process isolation
- **Cons:** Higher memory usage, complex IPC, harder to debug

### Alternative 2: Celery Task Queue
- **Pros:** Mature solution, good monitoring
- **Cons:** Additional infrastructure, complexity, latency overhead

### Alternative 3: Keep Synchronous with Threading
- **Pros:** Simpler implementation, familiar patterns
- **Cons:** GIL limitations, less efficient I/O handling

## Success Criteria

### Performance Targets
- [ ] Symbol processing time reduced by 60%
- [ ] Real-time update latency under 100ms
- [ ] Support for 50+ concurrent symbol streams
- [ ] CPU utilization across all cores

### Reliability Targets
- [ ] 99.9% async operation success rate
- [ ] Zero data corruption from race conditions
- [ ] Graceful handling of external API failures
- [ ] Memory usage increase under 20%

### Operational Targets
- [ ] Comprehensive async operation monitoring
- [ ] Automated performance alerts
- [ ] Easy debugging and troubleshooting
- [ ] Smooth rollback capability

---

**Decision Date:** 2025-08-21  
**Status:** Proposed  
**Stakeholders:** Development Team, Trading Operations  
**Dependencies:** ADR-001 (Database Connection Pooling)  
**Next Review:** After Phase 1 implementation