# Functional Testing Guide - Trading Bot

This guide shows you how to **functionally test** your trading bot to ensure it:
1. ✅ Fetches real data from Alpaca correctly
2. ✅ Calculates indicators properly
3. ✅ Generates correct trading signals
4. ✅ Makes sound trading decisions
5. ✅ Executes trades correctly (paper trading)

## 🎯 What These Tests Validate

### Unlike UI tests that just check if buttons exist, these tests verify:

- **Real Alpaca API integration** - Actual data fetching from your account
- **Technical indicators accuracy** - StochRSI, EMA calculations with real market data
- **Trading signal logic** - Buy/Sell signals are generated correctly
- **Risk management** - Position sizing, stop loss, take profit calculations
- **Complete trading pipeline** - Data → Indicators → Signal → Order
- **Actual order execution** - Places real orders on paper trading account

## 📋 Prerequisites

```bash
# Install testing dependencies
pip install pytest pytest-html pandas numpy

# Ensure Alpaca credentials are configured
# File: AUTH/authAlpaca.txt
```

## 🚀 Quick Start

### Run All Tests (Recommended First Run)

```bash
./run_functional_tests.sh
# Select option 4: All Functional Tests
```

### Or run directly with pytest

```bash
# All tests except paper trading
pytest tests/functional/ -v -s -m "not paper_trading"

# With HTML report
pytest tests/functional/ -v -s --html=test-report.html --self-contained-html
```

## 📊 Test Suites Breakdown

### 1️⃣ Alpaca Integration Tests
**File:** `tests/functional/test_alpaca_integration.py`

**What it tests:**
- ✅ Alpaca API credentials loaded correctly
- ✅ Can connect to Alpaca API
- ✅ Account is active and ready to trade
- ✅ Fetches current prices correctly
- ✅ Fetches historical bar data
- ✅ Data quality validation (no invalid prices, volumes)
- ✅ Crypto data fetching (BTC/USD)
- ✅ Current positions retrieval
- ✅ Open orders retrieval
- ✅ Market clock and trading hours

**Run:**
```bash
pytest tests/functional/test_alpaca_integration.py -v -s
```

**Expected Output:**
```
✓ Connected to Alpaca - Account Status: ACTIVE
✓ Account Active - Equity: $100,000.00
  Buying Power: $200,000.00
✓ Current price for AAPL: $178.45
✓ Fetched 100 bars for AAPL
  Latest Close: $178.45
  Volume: 1,234,567
✓ All 100 bars have valid data
```

### 2️⃣ Trading Strategy Tests
**File:** `tests/functional/test_trading_strategy.py`

**What it tests:**
- ✅ StochRSI calculation produces valid values (0-100)
- ✅ EMA calculation with real data
- ✅ Volume confirmation logic
- ✅ Indicators work with real market data
- ✅ BUY signals generated correctly (oversold conditions)
- ✅ SELL signals generated correctly (overbought conditions)
- ✅ Signals generated from real market data
- ✅ Position sizing calculations
- ✅ Stop loss calculations
- ✅ Take profit calculations
- ✅ Risk/Reward ratios

**Run:**
```bash
pytest tests/functional/test_trading_strategy.py -v -s
```

**Expected Output:**
```
✓ StochRSI K: 45.67, D: 43.21
✓ EMA 20: $178.23, EMA 50: $176.54
✓ Real data indicators for AAPL:
  StochRSI K: 52.34, D: 48.90
  EMA 20: $178.45
✓ BUY signal generated correctly
  Confidence: HIGH
✓ Position Sizing Test:
  Account Equity: $100,000.00
  Shares: 40
  Position Value: $7,138.00
✓ Stop Loss: $174.67
✓ Risk/Reward Ratio: 2.00
```

### 3️⃣ End-to-End Trading Flow Tests
**File:** `tests/functional/test_end_to_end_trading.py`

**What it tests:**
- ✅ Complete trading cycle (fetch → analyze → signal → order prep)
- ✅ Market status checking
- ✅ Account status validation
- ✅ Symbol analysis workflow
- ✅ Indicator calculation in pipeline
- ✅ Signal generation in pipeline
- ✅ Order validation logic
- ✅ Position size limits
- ✅ Signal-to-order pipeline
- ✅ Error handling (invalid symbols, insufficient data)
- ⚠️ **Optional:** Real paper trade execution

**Run (without executing trades):**
```bash
pytest tests/functional/test_end_to_end_trading.py -v -s -m "not paper_trading"
```

**Expected Output:**
```
============================================================
TESTING COMPLETE TRADING CYCLE (DRY RUN)
============================================================

1. Checking market status...
   Market is OPEN

2. Checking account...
   Account: ACTIVE
   Equity: $100,000.00
   Buying Power: $200,000.00

3. Getting symbols to analyze...
   Symbols: ['AAPL', 'TSLA']

4. Analyzing AAPL...
   Fetching market data...
   ✓ Fetched 200 bars
   Calculating indicators...
   ✓ Current Price: $178.45
   ✓ StochRSI K: 45.67, D: 43.21
   ✓ EMA 20: $178.23
   Generating trading signal...
   ✓ Signal: BUY
      🟢 BUY SIGNAL DETECTED
      Confidence: HIGH
      Position would be 56 shares
      Entry: $178.45
      Stop Loss: $174.67
      Position Value: $9,993.20

============================================================
✓ COMPLETE TRADING CYCLE VALIDATED
============================================================
```

## 🔥 Paper Trading Execution Test

**⚠️ WARNING:** This places **REAL orders** on your paper trading account

```bash
pytest tests/functional/test_end_to_end_trading.py::TestRealTradeExecution::test_paper_trade_execution -v -s -m "paper_trading"
```

**What it does:**
1. Verifies you're in paper trading mode (safety check)
2. Places a small test order (1 share)
3. Confirms order was accepted
4. Immediately cancels the order
5. Validates the entire order lifecycle

**Expected Output:**
```
============================================================
PAPER TRADING TEST - REAL ORDER EXECUTION
============================================================

1. Checking if we can trade AAPL...
   Current Price: $178.45
   Buying Power: $200,000.00

2. Placing TEST paper trade order...
   ⚠️  This will place a REAL order on paper account
   ✓ Order placed successfully!
   Order ID: abc-123-def-456
   Status: pending_new

3. Canceling test order...
   ✓ Order canceled

============================================================
✓ PAPER TRADE EXECUTION TEST COMPLETED
============================================================
```

## 📈 Understanding Test Results

### ✅ All Tests Pass
Your bot is:
- Connecting to Alpaca correctly
- Fetching valid market data
- Calculating indicators accurately
- Generating logical trading signals
- Making sound risk management decisions

### ❌ Test Failures - What They Mean

#### "Failed to connect to Alpaca API"
- Check `AUTH/authAlpaca.txt` credentials
- Verify API keys are valid
- Check internet connection

#### "Account is not active"
- Your Alpaca account may need verification
- Check Alpaca dashboard

#### "Failed to fetch historical bars"
- Symbol may not exist or be tradeable
- Market may be closed (check market hours)
- API rate limiting

#### "StochRSI calculation failed"
- Insufficient data (need at least 30 bars)
- Data contains NaN or invalid values

#### "Signal generation failed"
- Indicator calculation failed first
- Invalid data in DataFrame
- Strategy logic error

## 🔍 Debugging Failed Tests

### Run with verbose output
```bash
pytest tests/functional/test_alpaca_integration.py::TestAlpacaConnection::test_alpaca_api_connection -v -s
```

### Stop on first failure
```bash
pytest tests/functional/ -x -v -s
```

### Run specific test class
```bash
pytest tests/functional/test_trading_strategy.py::TestIndicatorCalculations -v -s
```

### Run specific test function
```bash
pytest tests/functional/test_alpaca_integration.py::TestMarketDataFetching::test_fetch_current_price -v -s
```

### Get full traceback
```bash
pytest tests/functional/ -v -s --tb=long
```

## 📊 Generating Test Reports

### HTML Report
```bash
pytest tests/functional/ --html=test-reports/functional-tests.html --self-contained-html
```

Then open `test-reports/functional-tests.html` in browser

### JUnit XML (for CI/CD)
```bash
pytest tests/functional/ --junitxml=test-reports/junit.xml
```

## 🎯 Testing Workflow

### Before Running Live Trading

1. **Run all functional tests**
   ```bash
   ./run_functional_tests.sh
   # Select option 4
   ```

2. **Verify all tests pass** ✅

3. **Run paper trading test**
   ```bash
   ./run_functional_tests.sh
   # Select option 5
   ```

4. **Monitor paper trading for 24 hours**

5. **Review results and P&L**

6. **Only then consider live trading** (if profitable)

## 🔒 Safety Features

All tests include safety checks:
- ✅ Verify paper trading URL before any orders
- ✅ Small position sizes (1 share) for execution tests
- ✅ Limit orders instead of market orders
- ✅ Immediate cancellation after execution test
- ✅ Double confirmation for paper trading tests

## 📝 Adding Your Own Tests

Create new test file:
```python
# tests/functional/test_custom.py
import pytest
from trading_bot import TradingBot

class TestCustomLogic:
    def test_my_feature(self):
        # Your test code
        assert True
```

Run it:
```bash
pytest tests/functional/test_custom.py -v -s
```

## 🆘 Common Issues

### "ModuleNotFoundError"
```bash
# Make sure you're in project root
cd /path/to/trading-bot

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-html
```

### "No tests collected"
```bash
# Make sure test files start with test_
# Make sure test functions start with test_
# Run from project root directory
```

### "Alpaca API errors"
- Verify you're using correct credentials
- Check if API keys are active in Alpaca dashboard
- Ensure you have paper trading enabled

## 📚 Next Steps

After all tests pass:

1. **Run backtesting** to validate strategy historically
2. **Monitor paper trading** for real-time validation
3. **Review logs** for any warnings or errors
4. **Optimize parameters** based on results
5. **Document your findings**

## 🎓 Best Practices

✅ **Run tests before every trading session**
✅ **Run tests after any code changes**
✅ **Keep tests up to date with strategy changes**
✅ **Review test output carefully**
✅ **Never skip paper trading validation**
✅ **Monitor test execution time (slow = API issues)**
✅ **Save test reports for historical reference**

---

## Quick Reference

```bash
# Run all tests
pytest tests/functional/ -v -s

# Run specific suite
pytest tests/functional/test_alpaca_integration.py -v -s

# With HTML report
pytest tests/functional/ --html=report.html --self-contained-html

# Stop on first failure
pytest tests/functional/ -x

# Paper trading test (careful!)
pytest -m paper_trading -v -s

# Run using menu
./run_functional_tests.sh
```

**Remember:** These tests validate your actual trading logic with real data. Take failures seriously!
