# Epic: Trading Execution Engine
**Status**: 🔴 NOT STARTED  
**Priority**: CRITICAL  
**Dependencies**: Signal Generation (Complete), Alpaca API (Connected)

## Overview
The Trading Execution Engine is the core component that transforms trading signals into actual market orders. Currently, the system generates signals but lacks the ability to execute trades, manage positions, and handle order lifecycle.

---

## 🎯 User Story 1: Order Placement System
**As a** trader  
**I want** the bot to automatically place orders when signals are generated  
**So that** I can execute my strategy without manual intervention

### Acceptance Criteria:
- ✅ When a BUY signal is generated with strength > 70, place a market order
- ✅ When a SELL signal is generated with strength > 70, close the position
- ✅ Order size calculated based on account equity and risk parameters
- ✅ Pre-trade validation checks:
  - Account has sufficient buying power
  - Not exceeding max position size
  - Market is open
  - Symbol is tradeable
  - No existing pending orders for same symbol
- ✅ Order submission via Alpaca API
- ✅ Immediate order confirmation or rejection handling
- ✅ Log all order attempts with timestamps and details
- ✅ WebSocket notification to frontend on order placement

### Technical Requirements:
```python
class OrderExecutor:
    def execute_signal(signal):
        # Validate signal strength
        # Check account constraints
        # Calculate position size
        # Submit order to Alpaca
        # Handle response
        # Notify frontend
```

### Definition of Done:
- [ ] Unit tests for order validation logic
- [ ] Integration tests with Alpaca paper trading
- [ ] Order placement visible in Alpaca dashboard
- [ ] Frontend receives real-time order notifications
- [ ] Error handling for all failure scenarios

---

## 🎯 User Story 2: Position Management System
**As a** trader  
**I want** the bot to track and manage my open positions  
**So that** I can monitor exposure and make informed decisions

### Acceptance Criteria:
- ✅ Track all open positions in real-time
- ✅ Monitor position P&L continuously
- ✅ Prevent duplicate positions in same symbol
- ✅ Scale into positions (add to winners)
- ✅ Scale out of positions (partial exits)
- ✅ Maximum position limits:
  - No more than 10% of account in single position
  - No more than 5 concurrent positions
  - No more than 50% total account exposure
- ✅ Position state tracking:
  - PENDING_ENTRY
  - OPEN
  - PENDING_EXIT
  - CLOSED
- ✅ Position metadata:
  - Entry price, time, signal strength
  - Current price, unrealized P&L
  - Position age, target price, stop loss

### Technical Requirements:
```python
class PositionManager:
    def __init__(self):
        self.positions = {}
        self.max_positions = 5
        self.max_position_size = 0.10  # 10% of account
        
    def can_open_position(symbol):
        # Check position limits
        # Check existing positions
        # Return True/False with reason
        
    def update_position(symbol, order_data):
        # Update position state
        # Calculate metrics
        # Check exit conditions
```

### Definition of Done:
- [ ] Position tracking matches Alpaca account exactly
- [ ] Position limits enforced consistently
- [ ] Real-time P&L calculations accurate
- [ ] Position history stored in database
- [ ] Frontend displays all position details

---

## 🎯 User Story 3: Order Lifecycle Management
**As a** trader  
**I want** complete visibility and control over order lifecycle  
**So that** I can handle fills, rejections, and cancellations properly

### Acceptance Criteria:
- ✅ Order states tracked:
  - NEW
  - PENDING_NEW
  - ACCEPTED
  - PARTIALLY_FILLED
  - FILLED
  - CANCELLED
  - REJECTED
  - EXPIRED
- ✅ WebSocket stream for order updates
- ✅ Handle partial fills correctly
- ✅ Retry logic for rejected orders (with modifications)
- ✅ Order timeout handling (cancel if not filled in 60 seconds)
- ✅ Order modification capability (update limit price)
- ✅ Emergency cancel all orders function
- ✅ Order audit trail with all state changes

### Technical Requirements:
```python
class OrderLifecycleManager:
    def __init__(self):
        self.active_orders = {}
        self.order_history = []
        
    async def on_order_update(order_event):
        # Parse order update
        # Update order state
        # Trigger actions based on state
        # Notify position manager
        # Update frontend
        
    def handle_rejection(order, reason):
        # Log rejection reason
        # Determine if retryable
        # Modify order if needed
        # Resubmit or abandon
```

### Definition of Done:
- [ ] All order states handled correctly
- [ ] Order updates reflected in <100ms
- [ ] Rejection handling with smart retry
- [ ] Order history queryable
- [ ] Frontend shows real-time order status

---

## 🎯 User Story 4: Trade Execution Confirmation
**As a** trader  
**I want** confirmation that my trades were executed at expected prices  
**So that** I can verify strategy performance and detect issues

### Acceptance Criteria:
- ✅ Capture actual fill price vs expected price
- ✅ Calculate slippage on each trade
- ✅ Track execution speed (signal to fill time)
- ✅ Confirm position quantity matches order
- ✅ Verify account balance changes
- ✅ Alert if slippage > 0.5%
- ✅ Daily execution quality report
- ✅ Store all execution data for analysis

### Technical Requirements:
```python
class ExecutionMonitor:
    def verify_execution(order, fill):
        # Compare expected vs actual
        # Calculate slippage
        # Check position update
        # Verify account impact
        # Generate confirmation
        
    def generate_execution_report():
        # Daily statistics
        # Slippage analysis
        # Execution speed metrics
        # Failed orders summary
```

### Definition of Done:
- [ ] All trades have confirmation records
- [ ] Slippage tracking accurate
- [ ] Execution metrics dashboard
- [ ] Alerts for unusual executions
- [ ] Historical execution analysis available

---

## 🎯 User Story 5: Stop Loss & Take Profit Orders
**As a** trader  
**I want** automatic stop loss and take profit orders  
**So that** I can protect profits and limit losses

### Acceptance Criteria:
- ✅ Every position has a stop loss order
- ✅ Stop loss calculation methods:
  - Fixed percentage (default 2%)
  - ATR-based (1.5x ATR)
  - Support level based
  - Trailing stop option
- ✅ Take profit targets:
  - Fixed R:R ratio (default 2:1)
  - Resistance level based
  - Partial profit taking (50% at 1R, 50% at 2R)
- ✅ One-Cancels-Other (OCO) order support
- ✅ Stop/Target adjustment based on market conditions
- ✅ Protection against stop hunting (place beyond key levels)

### Technical Requirements:
```python
class RiskOrderManager:
    def place_protection_orders(position):
        # Calculate stop loss level
        # Calculate take profit level
        # Submit OCO order
        # Track order IDs
        
    def adjust_stops(position, market_data):
        # Trail stops if profitable
        # Widen stops if volatile
        # Tighten stops near target
```

### Definition of Done:
- [ ] Every position has protection orders
- [ ] Stops and targets visible on chart
- [ ] OCO orders working correctly
- [ ] Trailing stops functioning
- [ ] Risk/Reward metrics tracked

---

## 🎯 User Story 6: Trading Hours & Market State Management
**As a** trader  
**I want** the bot to respect market hours and trading halts  
**So that** orders are only placed when they can be executed

### Acceptance Criteria:
- ✅ Check market open/closed status before trading
- ✅ Handle pre-market and after-hours trading options
- ✅ Respect trading halts and circuit breakers
- ✅ Queue orders for market open if generated when closed
- ✅ Cancel open orders at market close
- ✅ Different behavior for crypto (24/7) vs stocks
- ✅ Holiday calendar integration
- ✅ Time zone handling (all times in ET)

### Technical Requirements:
```python
class MarketStateManager:
    def is_market_open():
        # Check current time vs market hours
        # Check for holidays
        # Check for halts
        
    def next_market_open():
        # Return datetime of next open
        
    def queue_for_open(order):
        # Store order for execution at open
```

### Definition of Done:
- [ ] No orders placed when market closed
- [ ] Orders queued and executed at open
- [ ] Holiday calendar accurate
- [ ] Trading halts respected
- [ ] Frontend shows market status

---

## 🎯 User Story 7: Order Error Recovery
**As a** trader  
**I want** the system to gracefully handle and recover from order errors  
**So that** temporary issues don't stop the trading strategy

### Acceptance Criteria:
- ✅ Automatic retry for network errors (3 attempts)
- ✅ Handle insufficient buying power by reducing size
- ✅ Handle pattern day trader restrictions
- ✅ Queue orders if rate limited
- ✅ Alternative order types if market order rejected
- ✅ Notification system for critical errors
- ✅ Manual override capability
- ✅ Error categorization and appropriate responses

### Error Categories:
1. **Retryable**: Network timeout, rate limit, temporary API issues
2. **Adjustable**: Insufficient funds, position size too large
3. **Fatal**: Invalid symbol, account restricted, API key invalid
4. **Waiting Required**: Market closed, trading halt

### Technical Requirements:
```python
class OrderErrorHandler:
    def handle_error(order, error):
        error_type = classify_error(error)
        
        if error_type == 'RETRYABLE':
            return retry_order(order)
        elif error_type == 'ADJUSTABLE':
            return modify_and_retry(order)
        elif error_type == 'FATAL':
            return abort_and_notify(order)
        elif error_type == 'WAITING':
            return queue_for_later(order)
```

### Definition of Done:
- [ ] All error types handled appropriately
- [ ] Retry logic working with backoff
- [ ] Error notifications sent
- [ ] Error metrics tracked
- [ ] Recovery success rate > 80%

---

## 🚀 Implementation Priority:
1. **Order Placement System** (Critical - without this, no trading)
2. **Position Management System** (Critical - prevent overexposure)
3. **Stop Loss & Take Profit Orders** (Critical - risk management)
4. **Order Lifecycle Management** (High - handle real-world scenarios)
5. **Trading Hours Management** (High - prevent invalid orders)
6. **Trade Execution Confirmation** (Medium - performance tracking)
7. **Order Error Recovery** (Medium - robustness)

---

## 📊 Success Metrics:
- Order execution success rate > 95%
- Slippage < 0.1% on average
- Position tracking 100% accurate
- Stop loss execution rate 100%
- System uptime > 99.9% during market hours
- Error recovery success rate > 80%
- Zero unauthorized trades
- All trades have audit trail

---

## 🧪 Testing Requirements:

### Unit Tests:
- Order validation logic
- Position size calculations
- Stop loss/take profit calculations
- Market hours checking
- Error classification

### Integration Tests:
- Alpaca API order placement
- WebSocket order updates
- Position synchronization
- OCO order execution
- Error recovery scenarios

### End-to-End Tests:
- Complete signal to execution flow
- Position lifecycle from entry to exit
- Multiple concurrent positions
- Market close handling
- Error recovery with retry

### Performance Tests:
- Order execution latency < 100ms
- Handle 100 signals per minute
- Position updates < 50ms
- WebSocket message processing < 10ms

---

## 📝 Documentation Requirements:
- Order execution flow diagram
- Position state machine diagram
- Error handling decision tree
- API integration guide
- Configuration parameters guide
- Troubleshooting guide
- Trading logs format specification

---

## 🔧 Configuration Parameters:
```yaml
trading_execution:
  max_positions: 5
  max_position_size_pct: 10
  max_account_exposure_pct: 50
  min_signal_strength: 70
  
  stop_loss:
    default_pct: 2.0
    atr_multiplier: 1.5
    use_trailing: true
    trailing_pct: 1.0
    
  take_profit:
    risk_reward_ratio: 2.0
    partial_exits:
      - level: 1.0
        size_pct: 50
      - level: 2.0
        size_pct: 50
        
  order_management:
    timeout_seconds: 60
    retry_attempts: 3
    retry_delay_seconds: 5
    slippage_alert_pct: 0.5
    
  market_hours:
    trade_premarket: false
    trade_afterhours: false
    queue_when_closed: true
    cancel_at_close: true
```

---

## 🎯 Definition of Done for Epic:
- [ ] All user stories implemented and tested
- [ ] Paper trading validated for 1 week without errors
- [ ] Live trading validated with small positions
- [ ] Documentation complete
- [ ] Monitoring and alerting configured
- [ ] Performance metrics meeting targets
- [ ] Code review completed
- [ ] Security audit passed