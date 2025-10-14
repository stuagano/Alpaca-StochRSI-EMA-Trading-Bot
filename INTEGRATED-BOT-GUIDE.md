# 🚀 Integrated Crypto Bot + Dashboard

## What's New?

The dashboard is now **fully integrated** with your crypto trading bot! When you click "DOUBLE DOWN!" in the dashboard, it actually affects the bot's position sizing for real trades.

## Quick Start

### Option 1: Trading Bot + Unified Dashboard (RECOMMENDED)
```bash
# Terminal 1 – trading engine
python main.py

# Terminal 2 – Flask dashboard/API
python backend/api/run.py
```

This setup runs:
- ✅ The crypto trading bot (24/7 trading)
- ✅ Dashboard server on http://localhost:5001
- ✅ Both processes sharing state through the unified services layer

**What you get:**
- Real-time P&L from actual bot trades
- Position multiplier that affects actual trade sizing
- Trade log shows real bot activity
- Start/Stop buttons control the actual bot

### Option 2: Legacy One-Process Runner (ARCHIVED)

The combined script `crypto_bot_with_dashboard.py` now lives in `archive/legacy_2025Q4/`. You can reference it for historical context, but the supported flow is Option 1.

## How the Integration Works

### Position Multiplier (FEELING LUCKY!)

1. **Dashboard**: Click "🚀 DOUBLE DOWN! 🚀"
2. **Multiplier Updates**: 1x → 2x → 4x → 8x → 16x → 32x → 64x → 128x
3. **Bot Adjusts**: Next trade uses the multiplied position size

**Example:**
- Base position size: $150
- You press DOUBLE DOWN 3 times (8x)
- Next trade size: $1,200 (8 × $150)

### What's Connected

| Dashboard Feature | Connected to Bot? | What It Does |
|-------------------|-------------------|--------------|
| Account Info | ✅ Yes | Shows actual Alpaca account |
| P&L Display | ✅ Yes | Shows actual unrealized P&L from bot positions |
| Positions Table | ✅ Yes | Shows actual positions the bot opened |
| DOUBLE DOWN Button | ✅ Yes | **Multiplies the bot's next trade size** |
| Start/Stop Buttons | ✅ Yes | Controls the actual bot's trading loop |
| Trade Log | ✅ Yes | Shows actual bot trades as they execute |
| Auto Refresh | ✅ Yes | Updates every 5 seconds with real data |

## Dashboard Features

### 🎰 Position Multiplier
- **Default**: 1x (normal trading)
- **Max**: 128x (insane mode!)
- **How it works**: Multiplies `max_position_size` for the next trade
- **Warning**: Higher multipliers = higher risk!

### 📊 Real-Time Data
- Account equity
- Buying power
- Total P&L (unrealized)
- Active positions with entry prices
- Recent trade activity

### 🎮 Bot Controls
- **Start Trading**: Enables the bot to take new positions
- **Stop Trading**: Stops new trades (keeps existing positions)
- **Refresh**: Manually update all data

## Technical Details

### How Position Multiplier Works

The integrated bot patches the `_execute_entry` method:

```python
# Without multiplier
max_position_size = $150

# With 4x multiplier
max_position_size = $150 × 4 = $600

# Trade execution uses the multiplied size
quantity = position_size / price
```

### Trade Logging

Every trade the bot makes:
1. Executes via Alpaca API
2. Logs to bot's internal log
3. **Also logs to dashboard trade feed**
4. Shows in "Recent Activity" with timestamp

### State Sharing

Global variables shared between Flask and bot:
- `crypto_bot` - The actual bot instance
- `trading_client` - Alpaca API client
- `position_multiplier` - Current multiplier (dashboard ↔ bot)
- `trade_log` - Recent trades
- `bot_running` - Trading enabled/disabled

## Configuration

Edit `config/unified_config.yml` to adjust:

```yaml
crypto_only: true
market_type: crypto
investment_amount: 10000
max_trades_active: 15

symbols:
  - BTC/USD
  - ETH/USD
  - SOL/USD
  # ... more crypto pairs

risk_management:
  max_position_size: 0.15  # 15% of capital per trade
  max_daily_loss: 0.08      # 8% max daily loss
```

## Risk Management

### Built-in Safeguards

Even with high multipliers, the bot has limits:

1. **Max Position Size Cap**: Never exceeds available capital
2. **Max Concurrent Positions**: 15 positions max
3. **Daily Loss Limit**: Stops at 8% daily loss
4. **Stop Loss**: Each position has automatic stop loss
5. **Alpaca Minimum**: Each order must be at least $10

### Recommended Multipliers

| Multiplier | Risk Level | Use Case |
|------------|-----------|----------|
| 1x | 🟢 Low | Normal trading |
| 2x-4x | 🟡 Medium | High conviction signals |
| 8x-16x | 🟠 High | Very high conviction |
| 32x-128x | 🔴 Extreme | YOLO mode (not recommended!) |

## Troubleshooting

### Dashboard shows "Not connected"
- Make sure both `python main.py` and `python backend/api/run.py` are running

### Multiplier not affecting trades
- Check console for log: `🎰 Using Nx multiplier: $X → $Y`
- Verify bot is actually executing trades (check Recent Activity)

### No trades executing
- Check `config/unified_config.yml` symbols are correct format (BTC/USD not BTCUSD)
- Verify bot_running = True in dashboard
- Check console for error messages

### Positions not showing
- Wait 5 seconds for auto-refresh
- Click "Refresh Data" manually
- Check if bot has actually opened positions

## Example Session

```
1. Start trading engine: python main.py
2. In a new terminal, launch dashboard: python backend/api/run.py
3. Open dashboard: http://localhost:5001
4. Watch bot start trading with 1x multiplier
5. See a good signal? Click DOUBLE DOWN! (2x)
6. See another good signal? Click again! (4x)
7. Trade executes with 4x size
8. Watch P&L update in real-time
9. Getting nervous? Click RESET (back to 1x)
10. Stop trading? Click STOP TRADING
```

## Next Steps

1. Monitor the bot for a few hours
2. Test the DOUBLE DOWN feature with small multipliers (2x-4x)
3. Check the trade log to see actual execution
4. Review P&L and adjust configuration
5. Once confident, run 24/7 for crypto markets!

---

**Warning**: Crypto is volatile! Start with small capital and low multipliers until you understand the bot's behavior.

**Pro Tip**: The bot logs everything to `logs/crypto_trade_timeline.log` for analysis.
