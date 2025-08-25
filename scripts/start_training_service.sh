#!/bin/bash

echo "🎯 Starting Training Service Locally"
echo "===================================="

# Set working directory
cd "$(dirname "$0")/.."

# Export environment variables
export DATABASE_PATH="training/database/trading_training.db"
export REDIS_URL="redis://localhost:6379"
export PORT=9011

# Check if training_engine.py exists in microservice
if [ ! -f "microservices/services/training/app/training_engine.py" ]; then
    echo "📦 Copying training_engine.py to microservice..."
    cp training/training_engine.py microservices/services/training/app/
fi

# Check if database directory exists
if [ ! -d "microservices/services/training/database" ]; then
    echo "📁 Copying database schema to microservice..."
    cp -r training/database microservices/services/training/
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
pip install -q fastapi uvicorn aioredis httpx pandas yfinance ta python-socketio aiosqlite

# Start the service
echo "🚀 Starting Training Service on port 9011..."
echo "   Dashboard will be available at: http://localhost:9011/docs"
echo "   Press Ctrl+C to stop"
echo ""

cd microservices/services/training
python -m uvicorn app.main:app --host 0.0.0.0 --port 9011 --reload