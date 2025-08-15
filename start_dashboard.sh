#!/bin/bash

# Load environment variables
export APCA_API_KEY_ID=PK4VEAIP7OP6KCJ1B3H3
export APCA_API_SECRET_KEY=0cgByYpmqjCpPUFPpH2hwkaVYuCH2lCeAyl6lfzU
export APCA_API_BASE_URL=https://paper-api.alpaca.markets
export FLASK_SECRET_KEY=dev-secret-key-change-in-production
export JWT_SECRET_KEY=dev-jwt-secret-change-in-production
export FLASK_ENV=development
export FLASK_DEBUG=False
export SKIP_AUTH=true
export CORS_ORIGINS="http://localhost:8765,http://127.0.0.1:8765"
export TRADING_MODE=paper
export DEFAULT_SYMBOL=SPY

# Kill any existing Flask processes
pkill -f flask_app.py

# Wait for process to terminate
sleep 2

# Start Flask dashboard
echo "Starting Flask dashboard with live trading data..."
python flask_app.py