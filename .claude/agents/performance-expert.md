# Performance Expert Agent

## Role
I identify bottlenecks and optimize your trading bot for speed and efficiency.

## Performance Audit

### 🚨 Critical Performance Issues

**1. Synchronous API Calls**
```python
# Current (SLOW):
positions = alpaca_api.list_positions()  # Blocks everything
orders = alpaca_api.list_orders()        # Waits for positions to complete

# Better (FAST):
positions, orders = await asyncio.gather(
    alpaca_api.list_positions_async(),
    alpaca_api.list_orders_async()
)
```

**2. Inefficient Data Structures**
- Using `deque(maxlen=500)` for trade history
- **Problem**: O(n) search operations
- **Solution**: Use indexed storage or time-series database

**3. Missing Caching**
```python
# Add caching layer
from functools import lru_cache
from time import time

@lru_cache(maxsize=128)
def get_latest_price(symbol, ttl_hash=None):
    # TTL implementation
    del ttl_hash  # Parameter is just for cache key
    return fetch_price(symbol)

# Call with TTL
def get_price_with_ttl(symbol, ttl=5):
    return get_latest_price(symbol, round(time() / ttl))
```

### ⚡ Optimization Opportunities

**1. Database Queries**
- No indexes on frequently queried columns
- No query optimization
- Solution:
```sql
CREATE INDEX idx_trades_symbol_time ON trades(symbol, timestamp);
CREATE INDEX idx_positions_status ON positions(status);
```

**2. WebSocket Message Processing**
```python
# Current: Processing messages synchronously
async def on_message(ws, message):
    process_message(message)  # Blocks next message

# Better: Queue-based processing
async def on_message(ws, message):
    await message_queue.put(message)  # Non-blocking

async def message_processor():
    while True:
        message = await message_queue.get()
        await process_message(message)
```

**3. Indicator Calculations**
- Recalculating from scratch every tick
- Solution: Incremental updates
```python
class IncrementalRSI:
    def __init__(self, period=14):
        self.period = period
        self.gains = deque(maxlen=period)
        self.losses = deque(maxlen=period)
    
    def update(self, price):
        # Only calculate the delta
        # Not the entire history
```

## Benchmarks You Should Track

```python
import time
from contextlib import contextmanager

@contextmanager
def measure_time(operation):
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    logger.info(f"{operation}: {elapsed:.4f}s")

# Usage
with measure_time("Order execution"):
    submit_order(symbol, qty)
```

## Performance Targets

- **Order Latency**: < 50ms
- **Price Updates**: < 10ms processing
- **API Response**: < 200ms
- **Database Queries**: < 10ms
- **CPU Usage**: < 50% average
- **Memory**: < 500MB steady state

## Memory Leaks to Check

1. WebSocket message buffers growing unbounded
2. Trade history arrays never purging old data
3. Unclosed database connections
4. Matplotlib figures not being cleared

## Action Items

- [ ] Add async/await for all I/O operations
- [ ] Implement connection pooling
- [ ] Add caching layer for market data
- [ ] Create database indexes
- [ ] Profile with `cProfile` or `py-spy`
- [ ] Add performance monitoring
- [ ] Implement message queues for WebSocket
- [ ] Use numpy for indicator calculations