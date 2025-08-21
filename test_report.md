
# Epic 1 Trading Dashboard Test Report

**Generated**: 2025-08-19T12:07:43.991501  
**Execution Time**: 3.34 seconds  
**Success Rate**: 100.0%  

## Summary
- **Total Tests**: 10
- **Passed**: ✅ 10
- **Failed**: ❌ 0

## Test Results

### ✅ Server Health Check
**Status**: PASS  
**Details**: Server responding with status healthy  
**Data**: ```json
{
  "status": "healthy",
  "timestamp": "2025-08-19T12:07:40.659415"
}
```  
**Timestamp**: 2025-08-19T12:07:40.659857  

### ✅ Dashboard Route /
**Status**: PASS  
**Details**: Route accessible, content verified  
**Timestamp**: 2025-08-19T12:07:40.684369  

### ✅ Dashboard Route /dashboard
**Status**: PASS  
**Details**: Route accessible, content verified  
**Timestamp**: 2025-08-19T12:07:40.686874  

### ✅ Dashboard Route /dashboard/professional
**Status**: PASS  
**Details**: Route accessible, content verified  
**Timestamp**: 2025-08-19T12:07:40.688527  

### ✅ Dashboard Route /dashboard/fixed
**Status**: PASS  
**Details**: Route accessible, content verified  
**Timestamp**: 2025-08-19T12:07:40.690298  

### ✅ Account API
**Status**: PASS  
**Details**: Balance: $97,522.37, Buying Power: $168,655.34  
**Data**: ```json
{
  "account_number": "PA32BMZJ0GJ0",
  "balance": 97522.37,
  "buying_power": 168655.34,
  "cash": 71132.97,
  "pattern_day_trader": false,
  "status": "ACTIVE",
  "success": true
}
```  
**Timestamp**: 2025-08-19T12:07:40.759727  

### ✅ Positions API
**Status**: PASS  
**Details**: Found 3 positions  
**Data**: ```json
{
  "count": 3,
  "sample": {
    "avg_entry_price": 179.834918,
    "cost_basis": 23378.53934,
    "current_price": 166.575,
    "market_value": 21654.75,
    "qty": 130,
    "side": "long",
    "symbol": "AMD",
    "unrealized_pl": -1723.78934,
    "unrealized_plpc": -7.3733834048847
  }
}
```  
**Timestamp**: 2025-08-19T12:07:40.828569  

### ✅ Chart Data AAPL 1Min
**Status**: PASS  
**Details**: 100 candles received  
**Timestamp**: 2025-08-19T12:07:40.906069  

### ✅ Chart Data AAPL 15Min
**Status**: PASS  
**Details**: 23 candles received  
**Timestamp**: 2025-08-19T12:07:40.981662  

### ✅ Chart Data AAPL 1Hour
**Status**: PASS  
**Details**: 100 candles received  
**Timestamp**: 2025-08-19T12:07:41.099104  

### ✅ Chart Data AAPL 1Day
**Status**: PASS  
**Details**: 22 candles received  
**Timestamp**: 2025-08-19T12:07:41.192781  

### ✅ Chart Data SPY 1Min
**Status**: PASS  
**Details**: 100 candles received  
**Timestamp**: 2025-08-19T12:07:41.273692  

### ✅ Chart Data SPY 15Min
**Status**: PASS  
**Details**: 25 candles received  
**Timestamp**: 2025-08-19T12:07:41.350484  

### ✅ Chart Data SPY 1Hour
**Status**: PASS  
**Details**: 100 candles received  
**Timestamp**: 2025-08-19T12:07:41.480845  

### ✅ Chart Data SPY 1Day
**Status**: PASS  
**Details**: 22 candles received  
**Timestamp**: 2025-08-19T12:07:41.562069  

### ✅ Signals API AAPL
**Status**: PASS  
**Details**: Endpoint accessible  
**Data**: ```json
{
  "message": "Signal generation pending - bot needs to be running",
  "signals": [],
  "success": true,
  "symbol": "AAPL"
}
```  
**Timestamp**: 2025-08-19T12:07:41.564642  

### ✅ Signals API SPY
**Status**: PASS  
**Details**: Endpoint accessible  
**Data**: ```json
{
  "message": "Signal generation pending - bot needs to be running",
  "signals": [],
  "success": true,
  "symbol": "SPY"
}
```  
**Timestamp**: 2025-08-19T12:07:41.567090  

### ✅ Bot Status API
**Status**: PASS  
**Details**: Status: ready  
**Data**: ```json
{
  "bot_id": "epic1-stoch-rsi-bot",
  "last_signal": null,
  "status": "ready",
  "success": true,
  "timestamp": "2025-08-19T12:07:41.568525",
  "trades_today": 0,
  "uptime": "0m"
}
```  
**Timestamp**: 2025-08-19T12:07:41.569021  

### ✅ Bot Start API
**Status**: PASS  
**Details**: Response: Trading bot started successfully  
**Data**: ```json
{
  "bot_id": "epic1-stoch-rsi-bot",
  "features": {
    "dynamic_stoch_rsi": true,
    "signal_quality": true,
    "volume_confirmation": true
  },
  "message": "Trading bot started successfully",
  "status": "running",
  "success": true,
  "timestamp": "2025-08-19T12:07:41.570794"
}
```  
**Timestamp**: 2025-08-19T12:07:41.571219  

### ✅ Bot Stop API
**Status**: PASS  
**Details**: Response: Trading bot stopped successfully  
**Data**: ```json
{
  "message": "Trading bot stopped successfully",
  "status": "stopped",
  "success": true,
  "timestamp": "2025-08-19T12:07:41.573436"
}
```  
**Timestamp**: 2025-08-19T12:07:41.573821  

### ✅ WebSocket Connection
**Status**: PASS  
**Details**: Successfully connected  
**Timestamp**: 2025-08-19T12:07:41.749481  

### ✅ WebSocket Subscription
**Status**: PASS  
**Details**: Subscribed to AAPL  
**Data**: ```json
{
  "symbol": "AAPL",
  "message": "Subscribed to AAPL"
}
```  
**Timestamp**: 2025-08-19T12:07:41.750522  

### ⚠️ WebSocket Disconnect
**Status**: INFO  
**Details**: Disconnected  
**Timestamp**: 2025-08-19T12:07:43.751446  

### ✅ Debug Endpoint /debug/positions
**Status**: PASS  
**Details**: Endpoint accessible  
**Timestamp**: 2025-08-19T12:07:43.759807  

### ✅ Debug Endpoint /health
**Status**: PASS  
**Details**: Endpoint accessible  
**Timestamp**: 2025-08-19T12:07:43.761995  

### ✅ Performance /api/account
**Status**: PASS  
**Details**: Response time: 69ms  
**Timestamp**: 2025-08-19T12:07:43.831056  

### ✅ Performance /api/positions
**Status**: PASS  
**Details**: Response time: 72ms  
**Timestamp**: 2025-08-19T12:07:43.903485  

### ✅ Performance /api/v2/chart-data/AAPL?timeframe=15Min&limit=100
**Status**: PASS  
**Details**: Response time: 84ms  
**Timestamp**: 2025-08-19T12:07:43.987585  

### ✅ Performance /api/signals/current?symbol=AAPL
**Status**: PASS  
**Details**: Response time: 4ms  
**Timestamp**: 2025-08-19T12:07:43.991468  

### ⚠️ Performance Summary
**Status**: INFO  
**Details**: Average response time: 57ms  
**Data**: ```json
{
  "/api/account": 69.04292106628418,
  "/api/positions": 72.39484786987305,
  "/api/v2/chart-data/AAPL?timeframe=15Min&limit=100": 84.05613899230957,
  "/api/signals/current?symbol=AAPL": 3.8499832153320312
}
```  
**Timestamp**: 2025-08-19T12:07:43.991477  

