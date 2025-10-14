# Testing Quick Start 🚀

## You asked: "How do I test that my bot is actually working correctly?"

Here's your answer in **3 simple steps**:

---

## Step 1: Install Test Dependencies (2 minutes)

```bash
# UI testing
npm install

# Functional testing
pip install -r requirements-test.txt
```

---

## Step 2: Run Functional Tests (5 minutes)

**This tests the IMPORTANT stuff - your actual trading logic!**

```bash
./run_functional_tests.sh
```

Select option **4** (All Functional Tests)

### What This Tests:
✅ Alpaca API connection works
✅ Real market data is fetched correctly
✅ Technical indicators (StochRSI, EMA) calculate properly
✅ Trading signals (BUY/SELL) are generated logically
✅ Risk management (stops, position sizing) is correct
✅ Complete pipeline: Data → Indicators → Signal → Order

### Expected Result:
```
✓ Connected to Alpaca - Account Status: ACTIVE
✓ Current price for AAPL: $178.45
✓ StochRSI K: 45.67, D: 43.21
✓ Signal for AAPL: BUY
✓ Position sizing calculated correctly
✓ COMPLETE TRADING CYCLE VALIDATED

===============================================
30 passed in 45.2s
===============================================
```

---

## Step 3: Test With Real Paper Trades (Optional but Recommended)

**⚠️ This places REAL orders on your paper trading account (then cancels them)**

```bash
./run_functional_tests.sh
```

Select option **5** (Paper Trading Execution Test)

Type `yes` to confirm

### What This Does:
1. Verifies you're in paper trading mode ✅
2. Places a 1-share test order 📊
3. Confirms order was accepted ✅
4. Immediately cancels it ❌
5. Validates the order lifecycle worked 🎯

---

## Bonus: UI Tests (Optional)

Test that the dashboard interface works:

```bash
# Static tests (fast, no backend needed)
npx playwright test static-dashboard.spec.js --headed
```

You'll see a browser open and tests run automatically. All 12 tests should pass ✅

---

## 🎯 What Success Looks Like

### ✅ All Tests Pass:
Your bot is:
- Connecting to Alpaca correctly ✅
- Fetching real market data ✅
- Calculating indicators accurately ✅
- Making logical trading decisions ✅
- Managing risk properly ✅
- Ready for paper trading ✅

### ❌ Some Tests Fail:
Check the error messages. Common issues:
- **"Failed to connect"** → Check `AUTH/authAlpaca.txt` credentials
- **"Account not active"** → Verify Alpaca account
- **"Invalid symbol"** → Symbol doesn't exist or market closed
- **Import errors** → Run `pip install -r requirements-test.txt`

---

## 📚 Want More Details?

- **Functional Testing:** See [FUNCTIONAL-TESTING-GUIDE.md](FUNCTIONAL-TESTING-GUIDE.md)
- **UI Testing:** See [TESTING.md](TESTING.md)
- **Complete Overview:** See [COMPLETE-TESTING-SUMMARY.md](COMPLETE-TESTING-SUMMARY.md)

---

## 🔥 Critical: Before Live Trading

✅ All functional tests pass
✅ Paper trading execution test succeeds
✅ Run bot in paper mode for 24+ hours
✅ Review ALL trades made
✅ Verify P&L is positive or breakeven
✅ No errors in logs

**Only then** consider live trading with small amounts!

---

## Quick Commands Reference

```bash
# Functional tests (MOST IMPORTANT)
./run_functional_tests.sh

# Or directly with pytest
pytest tests/functional/ -v -s

# UI tests
npm test

# Static UI tests only (fast)
npx playwright test static-dashboard.spec.js

# Paper trading test (careful!)
pytest -m paper_trading -v -s
```

---

**That's it!** Now you can confidently test your trading bot's logic with real market data. 🎉
