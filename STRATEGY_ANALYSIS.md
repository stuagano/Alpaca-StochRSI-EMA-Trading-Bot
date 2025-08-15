# Trading Strategy Analysis - Complete Breakdown

## 🎯 Strategy Overview
The bot implements a **multi-indicator momentum strategy** using three technical indicators:
- **StochRSI** (Stochastic Relative Strength Index)
- **Stochastic Oscillator** 
- **EMA** (Exponential Moving Average)

The strategy can operate in **5 different modes** based on configuration settings.

---

## 📊 Technical Indicators Deep Dive

### 1. StochRSI Signal Logic (`indicator.py:79-98`)
**Purpose**: Identifies oversold conditions using RSI momentum
```python
# Signal Trigger Conditions:
if k[i] > d[i] and k[i] < stochRSI_lower_band:
    signals.append(1)  # BUY SIGNAL
```

**Current Configuration**:
- RSI Length: 14 periods
- Stoch Length: 14 periods  
- K Period: 3 (smoothing)
- D Period: 3 (smoothing)
- **Lower Band: 35** (buy trigger threshold)
- Upper Band: 100

**Signal Logic**:
- ✅ **BUY** when: K line crosses above D line AND K is below 35 (oversold)
- 📈 **Theory**: Buy when momentum is turning up from oversold levels

### 2. Stochastic Oscillator Signal Logic (`indicator.py:62-77`)
**Purpose**: Classic momentum oscillator for overbought/oversold conditions
```python
# Signal Trigger Conditions:
if k[i] > d[i] and k[i] > stoch_lower_band and k[i - 1] < stoch_lower_band:
    signals.append(1)  # BUY SIGNAL
```

**Current Configuration**:
- K Length: 14 periods
- Smooth K: 3
- Smooth D: 3
- **Lower Band: 35** (buy threshold)
- Upper Band: 80

**Signal Logic**:
- ✅ **BUY** when: K > D AND K crosses above 35 threshold
- 📈 **Theory**: Buy when price momentum shifts from oversold to bullish

### 3. EMA Signal Logic (`indicator.py:158-166`)
**Purpose**: Trend-following using exponential moving average
```python
# Signal Generation:
prices['Signal_EMA'] = np.where(prices['EMA'] < prices['Close'], 1.0, 0.0)
```

**Current Configuration**:
- EMA Period: 9
- Smoothing: 2

**Signal Logic**:
- ✅ **BUY** when: Current price > EMA (price above trend line)
- 📈 **Theory**: Follow the trend - buy when price is above moving average

---

## 🎲 Trading Strategy Modes

### Mode 1: Stochastic Only (`main.py:49-67`)
- **Condition**: `stoch=True, stochRSI=False, ema=False`
- **Logic**: Uses only Stochastic oscillator signals
- **Entry**: K crosses above D when K > 35 and previous K < 35

### Mode 2: StochRSI Only (`main.py:69-89`) ⭐ **CURRENTLY ACTIVE**
- **Condition**: `stoch=False, stochRSI=True, ema=False`
- **Logic**: Uses only StochRSI signals
- **Entry**: K > D when K < 35 (oversold reversal)

### Mode 3: EMA Only (`main.py:91-109`)
- **Condition**: `stoch=False, stochRSI=False, ema=True`
- **Logic**: Simple trend following
- **Entry**: Price above EMA line

### Mode 4: All Three Indicators (`main.py:111-149`)
- **Condition**: `stoch=True, stochRSI=True, ema=True`
- **Logic**: **CONFLUENCE STRATEGY** - requires ALL 3 signals to align
- **Entry**: Must get buy signal from Stochastic AND StochRSI AND EMA
- **Strength**: Higher probability trades (3 confirmations)

### Mode 5: Stoch + StochRSI (`main.py:152+`)
- **Condition**: `stoch=True, stochRSI=True, ema=False`
- **Logic**: Requires both oscillators to signal
- **Entry**: Both Stochastic and StochRSI must trigger

---

## 💰 Risk Management System

### Position Sizing (`main.py:275-285`)
```python
cashToUse = investment_amount  # $10,000
buy_amount = cashToUse * (trade_cap_percent * 0.01)  # 5% = $500 per trade
targetPositionSize = buy_amount / price_coin
```

### Risk Parameters
- **Investment Amount**: $10,000 total capital
- **Trade Capital**: 5% per trade ($500)
- **Max Active Trades**: 10 positions
- **Stop Loss**: 0.2% (exit at 99.8% of entry price)
- **Trailing Stop**: 0.2% (follows price up, stops at -0.2%)
- **Profit Target**: 0.5% (exit at 100.5% of entry price)
- **Trailing Stop Activation**: 0.1% profit

### Trade Execution Logic
1. **Entry**: Market buy order when signal triggers
2. **Stop Loss**: Automatic at 0.2% loss
3. **Profit Target**: Automatic at 0.5% gain  
4. **Trailing Stop**: Activates after 0.1% profit, trails at 0.2%

---

## 🔄 Signal Processing Workflow

### 1. Data Collection (`main.py:28-37`)
```python
df = get_data(ticker, timeframe='1Minute', start_date=10)
```
- Fetches OHLC data for last 10 days
- Uses 1-minute timeframe
- Gets data from Alpaca API

### 2. Signal Calculation
- Calculates RSI (14-period)
- Applies StochRSI calculation on RSI values
- Generates buy signals based on thresholds

### 3. Signal Lookback (`main.py:74`)
```python
signal_list = list(df['StochRSI Signal'].iloc[-lookback_period:])
```
- Examines last 2 candles (`candle_lookback_period: 2`)
- Looks for any buy signal in recent history
- Executes trade if signal found

### 4. Position Management
- Checks if under max position limit
- Records trade in CSV files
- Sets up risk management orders

---

## 📈 Current Strategy Strengths

1. **Conservative Risk Management**: Small position sizes (5%) with tight stops
2. **Momentum Focus**: Targets oversold reversals with momentum confirmation
3. **Flexible Configuration**: 5 different strategy modes
4. **Automated Execution**: No manual intervention required
5. **Position Limits**: Prevents over-concentration

## ⚠️ Current Strategy Weaknesses

1. **No Sell Signal Logic**: Only has buy signals, relies purely on risk management for exits
2. **Short Timeframe**: 1-minute data may generate false signals
3. **Single Asset Focus**: Processes one ticker at a time
4. **No Market Context**: Ignores overall market conditions/trends
5. **Fixed Thresholds**: Doesn't adapt to volatility conditions

---

## 🎯 Key Learning Points for Dashboard

### What to Visualize:
1. **StochRSI K/D Lines** with 35 threshold line
2. **Signal Trigger Points** marked on charts
3. **Entry/Exit Reasoning** for each trade
4. **Risk Management Actions** (stops, targets)
5. **Signal Strength** relative to thresholds

### Educational Opportunities:
1. **Show why signals trigger** at specific threshold levels
2. **Demonstrate confluence** when multiple indicators align
3. **Explain risk management** decisions in real-time
4. **Track signal accuracy** and profitability by type

---

*This analysis provides the foundation for building an educational trading dashboard that shows exactly how and why the bot makes its trading decisions.*