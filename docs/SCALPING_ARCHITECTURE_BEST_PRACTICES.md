# Scalping Trading Bot - Architecture Best Practices

Based on industry standards and Alpaca's official examples, here are the key improvements needed:

## 🎯 Current Issues

1. **No Proper Position Tracking** - System doesn't track entry/exit pairs
2. **Incorrect P&L Calculation** - Using assumptions instead of actual cost basis
3. **Poor Order Management** - Multiple orders with same timestamp
4. **No State Machine** - Lacks clear state transitions for positions
5. **Missing Risk Controls** - No proper position sizing or stop losses

## ✅ Best Practices from Industry Leaders

### 1. **Position & Order Tracking (Alpaca Pattern)**

```python
class ScalpAlgo:
    def __init__(self, symbol):
        self.symbol = symbol
        self.state = 'TO_BUY'  # State machine
        self.entry_price = 0
        self.position_qty = 0
        self.order_id = None
        self.buy_time = None
        
    # States: TO_BUY → BUY_SUBMITTED → TO_SELL → SELL_SUBMITTED → TO_BUY
```

### 2. **Proper P&L Calculation**

```python
class Position:
    def __init__(self, symbol, entry_price, qty):
        self.symbol = symbol
        self.entry_price = entry_price
        self.qty = qty
        self.entry_time = datetime.now()
        
    def calculate_pnl(self, exit_price):
        # Actual P&L = (Exit Price - Entry Price) * Quantity - Fees
        gross_pnl = (exit_price - self.entry_price) * self.qty
        fees = (self.entry_price * self.qty * 0.001) + (exit_price * self.qty * 0.001)
        return gross_pnl - fees
```

### 3. **Order Management System**

```python
class OrderManager:
    def __init__(self):
        self.pending_orders = {}  # order_id: Order
        self.filled_orders = {}
        self.positions = {}  # symbol: Position
        
    def submit_order(self, symbol, side, qty):
        # Check for existing orders
        if self.has_pending_order(symbol, side):
            return None  # Don't duplicate
            
        # Submit and track
        order = api.submit_order(...)
        self.pending_orders[order.id] = order
        return order
```

### 4. **Risk Management**

```python
class RiskManager:
    def __init__(self, max_position_size=1000, max_loss_per_trade=50):
        self.max_position_size = max_position_size
        self.max_loss_per_trade = max_loss_per_trade
        self.daily_loss_limit = 500
        self.daily_loss = 0
        
    def can_trade(self, symbol, price, qty):
        # Check position size
        if price * qty > self.max_position_size:
            return False
            
        # Check daily loss
        if self.daily_loss >= self.daily_loss_limit:
            return False
            
        return True
```

### 5. **Real-time WebSocket Updates**

```python
async def on_trade_update(conn, channel, data):
    """Handle real-time order updates"""
    symbol = data.order['symbol']
    event = data.event
    
    if event == 'fill':
        if data.order['side'] == 'buy':
            # Track new position
            positions[symbol] = Position(
                symbol=symbol,
                entry_price=float(data.order['filled_avg_price']),
                qty=float(data.order['filled_qty'])
            )
        elif data.order['side'] == 'sell':
            # Calculate actual P&L
            position = positions.get(symbol)
            if position:
                pnl = position.calculate_pnl(float(data.order['filled_avg_price']))
                log_trade(symbol, pnl)
```

## 📊 Recommended Architecture

```
┌─────────────────────────────────────────────┐
│           WebSocket Manager                  │
│  (Real-time order/position updates)         │
└─────────────┬───────────────────────────────┘
              │
┌─────────────▼───────────────────────────────┐
│           Order Manager                      │
│  (Tracks orders, prevents duplicates)        │
└─────────────┬───────────────────────────────┘
              │
┌─────────────▼───────────────────────────────┐
│          Position Tracker                    │
│  (Entry/exit matching, P&L calculation)      │
└─────────────┬───────────────────────────────┘
              │
┌─────────────▼───────────────────────────────┐
│           Risk Manager                       │
│  (Position sizing, stop losses, limits)      │
└─────────────┬───────────────────────────────┘
              │
┌─────────────▼───────────────────────────────┐
│          Strategy Engine                     │
│  (Signal generation, entry/exit logic)       │
└─────────────────────────────────────────────┘
```

## 🚀 Implementation Steps

1. **Create Position Class** - Track entry price, quantity, timestamps
2. **Implement State Machine** - Clear state transitions for each symbol
3. **Add Order Deduplication** - Prevent multiple simultaneous orders
4. **Use WebSocket for Updates** - Real-time position/order tracking
5. **Calculate Real P&L** - Match sells to specific buy entries
6. **Add Risk Controls** - Position limits, stop losses, daily limits

## 📈 Performance Metrics to Track

- **Sharpe Ratio** - Risk-adjusted returns
- **Win Rate** - Percentage of profitable trades
- **Average Win/Loss** - Size of wins vs losses
- **Maximum Drawdown** - Largest peak-to-trough decline
- **Trade Frequency** - Trades per hour/day
- **Slippage** - Difference between expected and actual prices

## 🔧 Technical Optimizations

1. **Use asyncio** for concurrent symbol handling
2. **Implement circuit breakers** for error conditions
3. **Add exponential backoff** for API retries
4. **Use connection pooling** for database
5. **Implement proper logging** with correlation IDs
6. **Add health checks** and monitoring

## 📚 References

- [Alpaca Official Scalping Example](https://github.com/alpacahq/example-scalping)
- [High-Frequency Trading Architecture Guide](https://medium.com/@levitatingmonkofshambhala/mastering-high-frequency-trading-a-comprehensive-guide-to-architecture-technology-and-best-8774c9942fac)
- [Freqtrade - Professional Crypto Bot Framework](https://github.com/freqtrade/freqtrade)