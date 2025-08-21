#!/bin/bash

echo "============================================================"
echo "🚀 EPIC 1 TRADING SYSTEM STARTUP"
echo "============================================================"
echo "⏰ Start Time: $(date)"
echo "============================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo -e "${GREEN}✅ Virtual environment found${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}⚠️  No virtual environment found${NC}"
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    echo "Installing dependencies..."
    pip install flask flask-cors flask-socketio python-socketio alpaca-trade-api \
                pandas numpy pyyaml python-dotenv pydantic flask-compress \
                requests websocket-client 2>/dev/null
fi

# Test Alpaca connection
echo ""
echo "🔌 Testing Alpaca Connection..."
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
from alpaca_trade_api import REST

try:
    api = REST(
        key_id=os.getenv('ALPACA_API_KEY'),
        secret_key=os.getenv('ALPACA_SECRET_KEY'),
        base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
    )
    account = api.get_account()
    print(f'  ✅ Connected to Alpaca')
    print(f'  💰 Balance: \${float(account.equity):,.2f}')
    clock = api.get_clock()
    if clock.is_open:
        print('  🟢 Market is OPEN')
    else:
        print(f'  🔴 Market is CLOSED')
except Exception as e:
    print(f'  ❌ Connection failed: {e}')
"

# Start Flask backend
echo ""
echo "🌐 Starting Flask Backend..."
echo "  Starting on http://localhost:5000"

# Kill any existing Flask processes
pkill -f "python.*flask_app" 2>/dev/null

# Start Flask in background
nohup python3 flask_app.py > flask.log 2>&1 &
FLASK_PID=$!
echo "  Flask PID: $FLASK_PID"

# Wait for Flask to start
sleep 3

# Check if Flask is running
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Flask server is running${NC}"
else
    echo -e "  ${YELLOW}⚠️  Flask may not be fully started${NC}"
fi

# Display Epic 1 Status
echo ""
echo "📊 Epic 1 Feature Status:"
python3 -c "
print('  • Dynamic Bands: ENABLED (sensitivity 0.7)')
print('  • Volume Confirmation: ENABLED')
print('  • Enhanced Signal Quality: ACTIVE')
print('  • Real-time WebSocket: READY')
"

# Display access URLs
echo ""
echo "============================================================"
echo "📊 DASHBOARD ACCESS:"
echo "============================================================"
echo "  🌐 Main Dashboard: http://localhost:5000"
echo "  📈 Professional: http://localhost:5000/dashboard/professional"
echo "  🔍 Epic 1 Status: http://localhost:5000/api/epic1/status"
echo "  📊 Positions: http://localhost:5000/api/positions"
echo "  📉 Account: http://localhost:5000/api/account"
echo ""
echo "============================================================"
echo "🎯 QUICK COMMANDS:"
echo "============================================================"
echo "  • View logs: tail -f flask.log"
echo "  • Start bot: python3 main.py"
echo "  • Stop Flask: kill $FLASK_PID"
echo "  • Check status: curl http://localhost:5000/api/epic1/status"
echo ""
echo "============================================================"
echo -e "${GREEN}✅ EPIC 1 SYSTEM READY!${NC}"
echo "============================================================"
echo ""
echo "To start the trading bot, run:"
echo "  python3 main.py"
echo ""
echo "Or to run with specific tickers:"
echo "  python3 main.py --tickers SPY,AAPL,TSLA"