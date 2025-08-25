#!/bin/bash

# Alpaca Trading Bot Frontend Dashboard Startup Script
# This script starts the complete shadcn/ui trading dashboard

echo "=========================================="
echo "🚀 Starting Alpaca Trading Dashboard"
echo "=========================================="

# Set the frontend directory
FRONTEND_DIR="/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot/frontend-shadcn"

# Check if directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

# Change to frontend directory
cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install --legacy-peer-deps
fi

# Check if port 9100 is already in use
if lsof -i :9100 > /dev/null 2>&1; then
    echo "⚠️  Port 9100 is already in use!"
    echo ""
    read -p "Kill existing process and restart? (y/n): " kill_existing
    if [ "$kill_existing" = "y" ]; then
        echo "🔄 Stopping existing server..."
        pkill -f "next dev -p 9100"
        sleep 2
    else
        echo "ℹ️  Using existing server on port 9100"
        echo ""
        echo "🌐 Dashboard URL: http://localhost:9100"
        echo "=========================================="
        exit 0
    fi
fi

echo ""
echo "🌐 Starting development server..."
echo "   Dashboard will be available at: http://localhost:9100"
echo ""

# Start the development server
npm run dev

echo ""
echo "=========================================="
echo "✅ Frontend dashboard started successfully!"
echo "🌐 Access your trading dashboard at:"
echo "   http://localhost:9100"
echo "=========================================="