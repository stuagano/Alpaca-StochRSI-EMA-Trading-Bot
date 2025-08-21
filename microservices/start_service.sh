#!/bin/bash

# Individual service startup script for local development (no Docker)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if service name is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <service-name> [port]"
    echo ""
    echo "Available services:"
    echo "  position-management (default port: 8001)"
    echo "  trading-execution   (default port: 8002)"
    echo "  signal-processing   (default port: 8003)"
    echo "  risk-management     (default port: 8004)"
    echo "  api-gateway         (default port: 8000)"
    echo ""
    echo "Example: $0 position-management"
    echo "Example: $0 api-gateway 8080"
    exit 1
fi

SERVICE_NAME=$1
PORT=$2

# Set default ports
case $SERVICE_NAME in
    "position-management")
        DEFAULT_PORT=8001
        MODULE_PATH="services.position-management.app.main:app"
        ;;
    "trading-execution")
        DEFAULT_PORT=8002
        MODULE_PATH="services.trading-execution.app.main:app"
        ;;
    "signal-processing")
        DEFAULT_PORT=8003
        MODULE_PATH="services.signal-processing.app.main:app"
        ;;
    "risk-management")
        DEFAULT_PORT=8004
        MODULE_PATH="services.risk-management.app.main:app"
        ;;
    "api-gateway")
        DEFAULT_PORT=8000
        MODULE_PATH="services.api-gateway.app.main:app"
        ;;
    *)
        print_error "Unknown service: $SERVICE_NAME"
        exit 1
        ;;
esac

# Use provided port or default
if [ -z "$PORT" ]; then
    PORT=$DEFAULT_PORT
fi

print_status "Starting $SERVICE_NAME on port $PORT..."

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    print_warning "Port $PORT is already in use!"
    print_status "Checking what's running on port $PORT:"
    lsof -i :$PORT
    echo ""
    read -p "Kill existing process and continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Killing process on port $PORT..."
        kill -9 $(lsof -t -i:$PORT) 2>/dev/null || true
        sleep 2
    else
        print_error "Exiting..."
        exit 1
    fi
fi

# Set environment variables
export PORT=$PORT
export PYTHONPATH=$(pwd)
export POSITION_SERVICE_URL="http://localhost:8001"
export TRADING_SERVICE_URL="http://localhost:8002"
export SIGNAL_SERVICE_URL="http://localhost:8003"
export RISK_SERVICE_URL="http://localhost:8004"
export MARKET_DATA_SERVICE_URL="http://localhost:8005"

# Create data directories
mkdir -p data/$SERVICE_NAME

print_status "Environment variables set:"
print_status "  PORT: $PORT"
print_status "  PYTHONPATH: $PYTHONPATH"
print_status "  Service URLs configured for inter-service communication"

# Start the service
print_status "Executing: python -m uvicorn $MODULE_PATH --host 0.0.0.0 --port $PORT --reload"
echo ""
print_status "🚀 Starting $SERVICE_NAME..."
print_status "📍 Service will be available at: http://localhost:$PORT"
print_status "📖 API docs will be available at: http://localhost:$PORT/docs"
print_status "❤️  Health check: http://localhost:$PORT/health"
echo ""
print_warning "Press Ctrl+C to stop the service"
echo ""

# Start the service
python -m uvicorn $MODULE_PATH --host 0.0.0.0 --port $PORT --reload