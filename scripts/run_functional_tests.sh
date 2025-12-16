#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     TRADING BOT FUNCTIONAL TEST SUITE                    ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found${NC}"
    echo "Install with: pip install pytest pytest-html"
    exit 1
fi

echo -e "${GREEN}✓${NC} pytest found"
echo ""

# Show menu
echo "Select test suite to run:"
echo ""
echo "  1) Alpaca Integration Tests (API, Data Fetching)"
echo "  2) Trading Strategy Tests (Indicators, Signals)"
echo "  3) End-to-End Trading Flow Tests (Complete Pipeline)"
echo "  4) All Functional Tests (Recommended)"
echo "  5) Paper Trading Execution Test (⚠️  Places real paper trades)"
echo ""
echo "  0) Exit"
echo ""

read -p "Enter choice [0-5]: " choice

case $choice in
    1)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "Running: ALPACA INTEGRATION TESTS"
        echo "═══════════════════════════════════════════════════════════"
        pytest tests/functional/test_alpaca_integration.py -v -s --tb=short
        ;;
    2)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "Running: TRADING STRATEGY TESTS"
        echo "═══════════════════════════════════════════════════════════"
        pytest tests/functional/test_trading_strategy.py -v -s --tb=short
        ;;
    3)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "Running: END-TO-END TRADING FLOW TESTS"
        echo "═══════════════════════════════════════════════════════════"
        pytest tests/functional/test_end_to_end_trading.py -v -s --tb=short -m "not paper_trading"
        ;;
    4)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "Running: ALL FUNCTIONAL TESTS"
        echo "═══════════════════════════════════════════════════════════"
        pytest tests/functional/ -v -s --tb=short -m "not paper_trading" \
               --html=test-reports/functional-tests.html --self-contained-html
        echo ""
        echo -e "${GREEN}✓${NC} Test report saved to: test-reports/functional-tests.html"
        ;;
    5)
        echo ""
        echo -e "${YELLOW}⚠️  WARNING: PAPER TRADING TEST${NC}"
        echo "This will place REAL orders on your paper trading account"
        echo ""
        read -p "Are you sure? (type 'yes' to continue): " confirm

        if [ "$confirm" == "yes" ]; then
            echo ""
            echo "═══════════════════════════════════════════════════════════"
            echo "Running: PAPER TRADING EXECUTION TEST"
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
echo "To run specific test classes:"
echo "  pytest tests/functional/test_alpaca_integration.py::TestAlpacaConnection -v -s"
echo ""
echo "To run with HTML report:"
echo "  pytest tests/functional/ --html=report.html --self-contained-html"
echo ""
echo "To run and stop on first failure:"
echo "  pytest tests/functional/ -x"
echo ""
