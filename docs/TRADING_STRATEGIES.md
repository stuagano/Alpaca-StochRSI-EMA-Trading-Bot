# Trading Strategies Documentation

## 📊 Strategy Overview

The trading system implements multiple sophisticated strategies that can operate independently or in coordination through the Multi-Strategy Manager.

## 🎯 Core Trading Strategies

### 1. StochRSI-EMA Strategy
**File**: `main.py`, `indicator.py`
**Type**: Momentum + Trend Following

#### Indicators Used
- **Stochastic RSI (StochRSI)**
  - Period: 14 (configurable)
  - Smoothing K: 3
  - Smoothing D: 3
  - Overbought: 80
  - Oversold: 20

- **Exponential Moving Averages (EMA)**
  - Fast EMA: 12 periods
  - Slow EMA: 26 periods
  - Signal EMA: 9 periods

#### Entry Conditions
```python
LONG ENTRY:
- StochRSI K crosses above D (bullish crossover)
- StochRSI < 80 (not overbought)
- Price > EMA(12) (trend confirmation)
- Volume > 20-period average (volume confirmation)

SHORT ENTRY:
- StochRSI K crosses below D (bearish crossover)
- StochRSI > 20 (not oversold)
- Price < EMA(12) (trend confirmation)
- Volume > 20-period average
```

#### Exit Conditions
```python
LONG EXIT:
- StochRSI > 80 (overbought)
- Price hits stop loss (2% default)
- Price hits take profit (5% default)
- Trailing stop triggered

SHORT EXIT:
- StochRSI < 20 (oversold)
- Price hits stop loss
- Price hits take profit
- Trailing stop triggered
```

### 2. Crypto Scalping Strategy
**File**: `strategies/crypto_scalping_strategy.py`
**Type**: High-Frequency Scalping

#### Key Parameters
```python
{
    "timeframe": "1m",           # 1-minute bars
    "profit_target": 0.003,       # 0.3% profit target
    "stop_loss": 0.002,           # 0.2% stop loss
    "position_size": 0.1,         # 10% of capital per trade
    "max_positions": 5,           # Maximum concurrent positions
    "min_volume": 100000          # Minimum volume filter
}
```

#### Entry Logic
```python
def generate_signal(self, data):
    # RSI Divergence
    if rsi < 30 and price > previous_low:
        return "BUY"  # Bullish divergence
    
    # MACD Crossover
    if macd_line > signal_line and previous_macd < previous_signal:
        return "BUY"  # Bullish MACD crossover
    
    # Volume Spike
    if volume > volume_avg * 2 and price_change > 0:
        return "BUY"  # Volume breakout
```

#### Risk Management
- Maximum 5 concurrent positions
- Position sizing based on ATR (Average True Range)
- Dynamic stop-loss adjustment
- Time-based exits (close after 15 minutes)

### 3. Multi-Timeframe Strategy
**File**: `strategies/multi_strategy_manager.py`
**Type**: Confluence Trading

#### Timeframe Analysis
```python
TIMEFRAMES = {
    "1m": {"weight": 0.1},   # Micro trend
    "5m": {"weight": 0.2},   # Short-term
    "15m": {"weight": 0.3},  # Medium-term
    "1h": {"weight": 0.4}    # Primary trend
}
```

#### Signal Aggregation
```python
def calculate_composite_signal(signals):
    total_score = 0
    for timeframe, signal in signals.items():
        weight = TIMEFRAMES[timeframe]["weight"]
        total_score += signal * weight
    
    if total_score > 0.6:
        return "STRONG_BUY"
    elif total_score > 0.3:
        return "BUY"
    elif total_score < -0.6:
        return "STRONG_SELL"
    elif total_score < -0.3:
        return "SELL"
    else:
        return "NEUTRAL"
```

## 📈 Technical Indicators

### Implemented Indicators

#### 1. Stochastic RSI
```python
def calculate_stoch_rsi(prices, period=14, smooth_k=3, smooth_d=3):
    # Calculate RSI
    rsi = calculate_rsi(prices, period)
    
    # Calculate Stochastic of RSI
    stoch = (rsi - rsi.rolling(period).min()) / 
            (rsi.rolling(period).max() - rsi.rolling(period).min())
    
    # Smooth with moving averages
    k = stoch.rolling(smooth_k).mean() * 100
    d = k.rolling(smooth_d).mean()
    
    return k, d
```

#### 2. MACD (Moving Average Convergence Divergence)
```python
def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram
```

#### 3. Bollinger Bands
```python
def calculate_bollinger_bands(prices, period=20, std_dev=2):
    sma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    return upper_band, sma, lower_band
```

#### 4. Volume Weighted Average Price (VWAP)
```python
def calculate_vwap(prices, volumes):
    cumulative_pv = (prices * volumes).cumsum()
    cumulative_volume = volumes.cumsum()
    vwap = cumulative_pv / cumulative_volume
    
    return vwap
```

## 🎲 Risk Management

### Position Sizing Algorithms

#### 1. Kelly Criterion
```python
def kelly_position_size(win_rate, avg_win, avg_loss):
    """
    f = (p * b - q) / b
    where:
    f = fraction of capital to bet
    p = probability of winning
    b = odds (avg_win / avg_loss)
    q = probability of losing (1 - p)
    """
    b = avg_win / avg_loss
    q = 1 - win_rate
    f = (win_rate * b - q) / b
    
    # Apply Kelly fraction (usually 25% of full Kelly)
    return min(f * 0.25, 0.02)  # Max 2% per trade
```

#### 2. Fixed Risk Model
```python
def fixed_risk_position_size(account_value, risk_percent, stop_loss_distance):
    """
    Position Size = (Account * Risk%) / Stop Loss Distance
    """
    risk_amount = account_value * risk_percent
    position_size = risk_amount / stop_loss_distance
    
    return position_size
```

#### 3. Volatility-Based Sizing
```python
def volatility_position_size(account_value, atr, multiplier=2):
    """
    Size positions inversely to volatility
    """
    base_risk = account_value * 0.01  # 1% base risk
    position_size = base_risk / (atr * multiplier)
    
    return position_size
```

### Stop Loss Strategies

#### 1. ATR-Based Stop Loss
```python
def atr_stop_loss(entry_price, atr, multiplier=2, is_long=True):
    if is_long:
        return entry_price - (atr * multiplier)
    else:
        return entry_price + (atr * multiplier)
```

#### 2. Percentage Stop Loss
```python
def percentage_stop_loss(entry_price, percent=0.02, is_long=True):
    if is_long:
        return entry_price * (1 - percent)
    else:
        return entry_price * (1 + percent)
```

#### 3. Trailing Stop Loss
```python
def trailing_stop_loss(current_price, highest_price, trail_percent=0.02):
    """
    Trails behind the highest price achieved
    """
    stop_price = highest_price * (1 - trail_percent)
    return max(stop_price, current_stop)  # Never lower the stop
```

## 🔄 Order Execution

### Order Types

#### 1. Market Orders
```python
def place_market_order(symbol, qty, side):
    order = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": "market",
        "time_in_force": "gtc"
    }
    return alpaca.submit_order(**order)
```

#### 2. Limit Orders
```python
def place_limit_order(symbol, qty, side, limit_price):
    order = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": "limit",
        "limit_price": limit_price,
        "time_in_force": "gtc"
    }
    return alpaca.submit_order(**order)
```

#### 3. Bracket Orders
```python
def place_bracket_order(symbol, qty, side, take_profit, stop_loss):
    order = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": "market",
        "time_in_force": "gtc",
        "order_class": "bracket",
        "take_profit": {"limit_price": take_profit},
        "stop_loss": {"stop_price": stop_loss}
    }
    return alpaca.submit_order(**order)
```

## 📊 Performance Metrics

### Key Performance Indicators

#### 1. Sharpe Ratio
```python
def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    excess_returns = returns - risk_free_rate/252  # Daily risk-free
    return np.sqrt(252) * excess_returns.mean() / excess_returns.std()
```

#### 2. Maximum Drawdown
```python
def calculate_max_drawdown(equity_curve):
    cumulative = (1 + equity_curve).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    return drawdown.min()
```

#### 3. Win Rate
```python
def calculate_win_rate(trades):
    winning_trades = len([t for t in trades if t.profit > 0])
    total_trades = len(trades)
    return winning_trades / total_trades if total_trades > 0 else 0
```

#### 4. Profit Factor
```python
def calculate_profit_factor(trades):
    gross_profit = sum([t.profit for t in trades if t.profit > 0])
    gross_loss = abs(sum([t.profit for t in trades if t.profit < 0]))
    return gross_profit / gross_loss if gross_loss > 0 else float('inf')
```

## 🔍 Strategy Optimization

### Parameter Optimization
```python
OPTIMIZATION_PARAMS = {
    "stoch_rsi_period": range(10, 20),
    "ema_fast": range(8, 15),
    "ema_slow": range(20, 30),
    "stop_loss": [0.01, 0.015, 0.02, 0.025],
    "take_profit": [0.03, 0.04, 0.05, 0.06]
}
```

### Walk-Forward Analysis
```python
def walk_forward_optimization(data, window_size=252, step_size=21):
    """
    Rolling window optimization
    """
    results = []
    for i in range(0, len(data) - window_size, step_size):
        train_data = data[i:i+window_size]
        test_data = data[i+window_size:i+window_size+step_size]
        
        # Optimize on training data
        best_params = optimize_parameters(train_data)
        
        # Test on out-of-sample data
        performance = backtest(test_data, best_params)
        results.append(performance)
    
    return results
```

## 🤖 Machine Learning Integration

### Feature Engineering
```python
FEATURES = [
    "returns_1d", "returns_5d", "returns_20d",
    "volume_ratio", "rsi", "macd_signal",
    "bb_position", "atr", "vwap_distance",
    "market_cap", "pe_ratio", "sentiment_score"
]
```

### Model Training Pipeline
```python
def train_ml_model(features, labels):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42
    )
    
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5
    )
    
    model.fit(X_train, y_train)
    accuracy = model.score(X_test, y_test)
    
    return model, accuracy
```

## 📝 Strategy Configuration

### Configuration File Structure
```yaml
# strategies/config.yaml
strategies:
  stoch_rsi_ema:
    enabled: true
    timeframe: "5m"
    indicators:
      stoch_rsi:
        period: 14
        smooth_k: 3
        smooth_d: 3
      ema:
        fast: 12
        slow: 26
    risk:
      max_position_size: 0.1
      stop_loss: 0.02
      take_profit: 0.05
      
  crypto_scalping:
    enabled: true
    pairs: ["BTC/USD", "ETH/USD"]
    timeframe: "1m"
    risk:
      max_positions: 5
      position_size: 0.05
```

## 🔮 Future Strategy Enhancements

### Planned Additions
1. **Options Strategies**: Covered calls, protective puts
2. **Pairs Trading**: Statistical arbitrage
3. **Market Making**: Bid-ask spread capture
4. **Sentiment Analysis**: News and social media integration
5. **Reinforcement Learning**: Deep Q-learning for adaptive strategies

---

*These strategies are continuously optimized based on market conditions and performance metrics. Always backtest thoroughly before live deployment.*