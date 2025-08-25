#!/bin/bash
# Trading Training CLI Launcher

echo "🎯 Trading Training System"
echo "=========================="
echo ""
echo "Available commands:"
echo "  backtest   - Run strategy backtests"
echo "  collaborate - Start collaborative decision session"
echo "  compare    - Compare multiple strategies" 
echo "  learn      - Full learning session (backtest + decision)"
echo ""
echo "Examples:"
echo "  python cli_trainer.py backtest --symbol AAPL --days 180"
echo "  python cli_trainer.py collaborate --symbol TSLA"
echo "  python cli_trainer.py compare --symbol SPY"
echo "  python cli_trainer.py learn --symbol MSFT"
echo ""

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 [command] [options]"
    echo "For help: python cli_trainer.py --help"
else
    python cli_trainer.py "$@"
fi
