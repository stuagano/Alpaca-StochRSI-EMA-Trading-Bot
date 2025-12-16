#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     CRYPTO 24/7 TRADING BOT - TEST SUITE                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🌍 24/7 CRYPTO MARKET - ALWAYS OPEN${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found${NC}"
    echo "Install with: pip install -r requirements-test.txt"
    exit 1
fi

echo -e "${GREEN}✓${NC} pytest found"
echo ""

# Show menu
echo "Select test suite to run:"
echo ""
echo "  ${GREEN}1) Quick Crypto Validation${NC} (Fast - tests crypto access)"
echo "  ${GREEN}2) Complete Crypto Test Suite${NC} (Recommended)"
echo "  ${GREEN}3) Crypto + All Functional Tests${NC} (Comprehensive)"
echo "  ${YELLOW}4) Paper Trading Execution Test${NC} (⚠️  Places real paper trades)"
echo ""
echo "  0) Exit"
echo ""

read -p "Enter choice [0-4]: " choice

case $choice in
    1)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "Running: QUICK CRYPTO VALIDATION"
        echo "═══════════════════════════════════════════════════════════"
        echo ""
        pytest tests/functional/test_crypto_trading.py::TestCryptoMarketAccess -v -s
        ;;
    2)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "Running: COMPLETE CRYPTO TEST SUITE"
        echo "═══════════════════════════════════════════════════════════"
        echo ""
        echo "This will test:"
        echo "  ✓ 24/7 market access (no hours restrictions)"
        echo "  ✓ Weekend & overnight trading"
        echo "  ✓ Crypto pair connectivity"
        echo "  ✓ Real-time price fetching"
        echo "  ✓ Volatility measurement"
        echo "  ✓ Signal generation"
        echo "  ✓ Risk management for crypto"
        echo ""
        pytest tests/functional/test_crypto_trading.py -v -s --tb=short
        ;;
    3)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "Running: CRYPTO + ALL FUNCTIONAL TESTS"
        echo "═══════════════════════════════════════════════════════════"
        echo ""
        pytest tests/functional/ -v -s --tb=short -m "not paper_trading" \
               --html=test-reports/crypto-tests.html --self-contained-html
        echo ""
        echo -e "${GREEN}✓${NC} Test report saved to: test-reports/crypto-tests.html"
        ;;
    4)
        echo ""
        echo -e "${YELLOW}⚠️  WARNING: PAPER TRADING TEST${NC}"
        echo "This will place REAL orders on your paper trading account"
        echo "Testing with crypto pairs (BTC/USD or ETH/USD)"
        echo ""
        read -p "Are you sure? (type 'yes' to continue): " confirm

        if [ "$confirm" == "yes" ]; then
            echo ""
            echo "═══════════════════════════════════════════════════════════"
            echo "Running: PAPER TRADING EXECUTION TEST (CRYPTO)"
            echo "═══════════════════════════════════════════════════════════"
            pytest tests/functional/test_end_to_end_trading.py::TestRealTradeExecution::test_paper_trade_execution \
                   -v -s --tb=short -m "paper_trading"
        else
            echo "Cancelled."
        fi
        ;;
    0)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📚 Documentation:"
echo "  • Crypto Guide: CRYPTO-247-TRADING-GUIDE.md"
echo "  • Testing Guide: FUNCTIONAL-TESTING-GUIDE.md"
echo "  • Quick Start: TESTING-QUICKSTART.md"
echo ""
echo "🚀 To start crypto trading:"
echo "  python main.py"
echo ""
