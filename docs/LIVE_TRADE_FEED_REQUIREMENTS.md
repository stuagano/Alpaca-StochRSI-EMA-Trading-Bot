# Live Trade Feed Technical Requirements

## Current Issues Identified

### 1. Data Source Mismatch
- **Frontend expects**: `/api/trade-log` endpoint with executed trade history
- **Backend provides**: `/api/crypto/positions` endpoint with current positions only
- **Impact**: Trade feed shows "No trades executed yet" because endpoint doesn't exist

### 2. WebSocket Integration Missing
- **Available**: WebSocket endpoints `/ws/trading` and `/api/stream` in backend
- **Missing**: Frontend WebSocket connection for real-time updates
- **Impact**: No real-time trade notifications, relies on 2-second polling

### 3. Trade History Storage Gap
- **Required**: Persistent storage of executed trades with P&L calculations
- **Current**: Only current positions are tracked
- **Impact**: No historical performance metrics or profit tracking

## Technical Requirements

### Backend Requirements

#### 1. Trade Logging System
```python
# Required: /api/trade-log endpoint
GET /api/trade-log
Response: {
  "trades": [
    {
      "id": "trade-123",
      "symbol": "AVAXUSD", 
      "side": "buy|sell",
      "qty": 10.5,
      "price": 24.55,
      "value": 257.78,
      "profit": 8.60,        # For sell orders only
      "profit_percent": 3.34, # For sell orders only  
      "timestamp": "2025-09-05T23:22:16Z",
      "status": "filled"
    }
  ],
  "metrics": {
    "session_profit": 128.45,
    "total_trades_today": 15,
    "win_rate": 0.73,
    "avg_profit_per_trade": 8.56
  }
}
```

#### 2. Trade Execution Hooks
```python
# Required: Automatic trade logging on every order fill
async def on_order_filled(order):
    trade_record = {
        "id": generate_trade_id(),
        "symbol": order.symbol,
        "side": order.side,
        "qty": float(order.qty),
        "price": float(order.filled_avg_price),
        "value": float(order.qty) * float(order.filled_avg_price),
        "timestamp": datetime.utcnow().isoformat(),
        "status": "filled"
    }
    
    # Calculate P&L for sell orders
    if order.side == 'sell':
        trade_record["profit"] = calculate_pnl(order)
        trade_record["profit_percent"] = calculate_pnl_percent(order)
    
    # Store in database/memory
    await store_trade(trade_record)
    
    # Broadcast via WebSocket
    await broadcast_trade_update(trade_record)
```

#### 3. WebSocket Real-Time Updates
```python
# Required: Broadcast trade updates to connected clients
@app.websocket("/ws/trading")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    # Send real-time updates when trades execute
    # Format: {"type": "trade_update", "data": trade_record}
```

### Frontend Requirements

#### 1. WebSocket Connection
```typescript
// Required: Real-time WebSocket connection in TradingContext
useEffect(() => {
  const ws = new WebSocket('ws://localhost:9000/ws/trading')
  
  ws.onmessage = (event) => {
    const update = JSON.parse(event.data)
    if (update.type === 'trade_update') {
      setTrades(prev => [update.data, ...prev].slice(0, 50))
      updateMetrics(update.data)
    }
  }
  
  return () => ws.close()
}, [])
```

#### 2. Correct API Endpoint
```typescript
// Required: Update TradingContext to use correct endpoint
const refreshTrades = async () => {
  try {
    setIsLoading(true)
    const response = await fetch('http://localhost:9000/api/trade-log') // ✅ Correct endpoint
    const data = await response.json()
    
    if (data.trades && Array.isArray(data.trades)) {
      setTrades(data.trades.slice(0, 50))
      setMetrics(data.metrics)
    }
  } catch (error) {
    console.error('Failed to fetch trades:', error)
  } finally {
    setIsLoading(false)
  }
}
```

### Data Storage Requirements

#### 1. Trade History Table
```sql
CREATE TABLE trade_history (
    id VARCHAR(50) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side ENUM('buy', 'sell') NOT NULL,
    qty DECIMAL(18,8) NOT NULL,
    price DECIMAL(18,8) NOT NULL, 
    value DECIMAL(18,2) NOT NULL,
    profit DECIMAL(18,2) NULL,      -- Only for sell orders
    profit_percent DECIMAL(8,4) NULL, -- Only for sell orders
    timestamp DATETIME NOT NULL,
    status VARCHAR(20) DEFAULT 'filled',
    INDEX idx_symbol_timestamp (symbol, timestamp),
    INDEX idx_timestamp (timestamp DESC)
);
```

#### 2. Session Metrics Cache
```python
# Required: In-memory session tracking
class SessionMetrics:
    def __init__(self):
        self.session_start = datetime.utcnow()
        self.total_profit = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.current_streak = 0
        self.best_streak = 0
        
    def update_on_trade(self, trade):
        self.total_trades += 1
        if trade.get('profit'):
            self.total_profit += trade['profit']
            if trade['profit'] > 0:
                self.winning_trades += 1
                self.current_streak += 1
                self.best_streak = max(self.best_streak, self.current_streak)
            else:
                self.current_streak = 0
```

## Implementation Priority

### Phase 1 (Critical - Fix Current Issues)
1. ✅ **Add `/api/trade-log` endpoint** to unified_trading_service_with_frontend.py
2. ✅ **Implement trade logging** on every order execution
3. ✅ **Add profit/loss calculation** for sell orders

### Phase 2 (Real-Time Updates)
1. **Enable WebSocket broadcasting** for trade updates
2. **Update TradingContext** to use WebSocket connection
3. **Add connection status indicators** in UI

### Phase 3 (Performance & Storage)
1. **Add persistent database** for trade history
2. **Implement trade archiving** for old records
3. **Add performance analytics** dashboard

## Success Criteria

- ✅ LiveTradeFeed shows executed trades immediately after execution
- ✅ Real-time P&L calculations display correctly
- ✅ WebSocket connection shows "Connected" status
- ✅ Session metrics update automatically
- ✅ No "No trades executed yet" message when trades exist
- ✅ Trade history persists across browser refreshes

## Testing Requirements

1. **Execute test trade** and verify it appears in feed within 1 second
2. **Refresh browser** and verify trades persist
3. **Check WebSocket connection** shows connected status
4. **Verify P&L calculations** match actual Alpaca trade results
5. **Test with multiple rapid trades** (scalping scenario)

This technical requirements document addresses all the current gaps and provides a clear implementation path to fix the live trade feed issues.