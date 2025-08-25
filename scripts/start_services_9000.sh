#!/bin/bash
#
# Start Microservices with 9000-range Ports
# ==========================================
# This script starts all microservices using ports 9000-9100
# and loads Alpaca API credentials from .env file

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot"
cd "$PROJECT_ROOT"

echo -e "${GREEN}Starting Microservices with 9000-range Ports${NC}"
echo "============================================="

# Load environment variables from .env
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ Loading .env file${NC}"
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}✗ .env file not found!${NC}"
    exit 1
fi

# Verify Alpaca credentials are loaded
if [ -z "$APCA_API_KEY_ID" ]; then
    echo -e "${YELLOW}⚠ Warning: APCA_API_KEY_ID not set - will use mock data${NC}"
else
    echo -e "${GREEN}✓ Alpaca API credentials loaded${NC}"
fi

# Export service URLs for 9000-range ports
export API_GATEWAY_URL="http://localhost:9000"
export POSITION_SERVICE_URL="http://localhost:9001"
export TRADING_SERVICE_URL="http://localhost:9002"
export SIGNAL_SERVICE_URL="http://localhost:9003"
export RISK_SERVICE_URL="http://localhost:9004"
export MARKET_DATA_SERVICE_URL="http://localhost:9005"
export HISTORICAL_DATA_SERVICE_URL="http://localhost:9006"
export ANALYTICS_SERVICE_URL="http://localhost:9007"
export NOTIFICATION_SERVICE_URL="http://localhost:9008"
export CONFIG_SERVICE_URL="http://localhost:9009"
export HEALTH_MONITOR_URL="http://localhost:9010"
export FRONTEND_URL="http://localhost:9100"

# Kill any existing services on these ports
echo -e "\n${YELLOW}Stopping existing services...${NC}"
for port in 9000 9001 9002 9003 9004 9005 9006 9007 9008 9009 9010 9100; do
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done

sleep 2

# Function to start a service
start_service() {
    local service_name=$1
    local service_path=$2
    local port=$3
    
    echo -e "\n${GREEN}Starting $service_name on port $port...${NC}"
    
    cd "$PROJECT_ROOT/$service_path"
    
    # Check if main_simple.py exists, otherwise use main.py
    if [ -f "main_simple.py" ]; then
        nohup python main_simple.py > "/tmp/${service_name}.log" 2>&1 &
    elif [ -f "main.py" ]; then
        nohup python main.py > "/tmp/${service_name}.log" 2>&1 &
    else
        echo -e "${RED}✗ No main file found for $service_name${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ $service_name started (PID: $!)${NC}"
    sleep 1
}

# Start core services first
start_service "api-gateway" "microservices/services/api-gateway/app" 9000
start_service "trading-execution" "microservices/services/trading-execution/app" 9002
start_service "position-management" "microservices/services/position-management/app" 9001
start_service "analytics" "microservices/services/analytics/app" 9007

# Start frontend
start_service "frontend" "microservices/services/frontend/app" 9100

# Optional: Start other services as needed
# start_service "signal-processing" "microservices/services/signal-processing/app" 9003
# start_service "risk-management" "microservices/services/risk-management/app" 9004
# start_service "market-data" "microservices/services/market-data/app" 9005
# start_service "historical-data" "microservices/services/historical-data/app" 9006
# start_service "notification" "microservices/services/notification/app" 9008
# start_service "configuration" "microservices/services/configuration/app" 9009
# start_service "health-monitor" "microservices/services/health-monitor/app" 9010

echo -e "\n${GREEN}=============================================${NC}"
echo -e "${GREEN}Services Started Successfully!${NC}"
echo -e "${GREEN}=============================================${NC}"

echo -e "\n${YELLOW}Service URLs:${NC}"
echo "  API Gateway:       http://localhost:9000"
echo "  Frontend:          http://localhost:9100"
echo "  Trading:           http://localhost:9100/trading"
echo "  Analytics:         http://localhost:9100/analytics"
echo ""
echo -e "${YELLOW}API Endpoints:${NC}"
echo "  Health Check:      curl http://localhost:9000/health"
echo "  Chart Data:        curl http://localhost:9000/api/chart/AAPL"
echo "  Account Info:      curl http://localhost:9000/api/account"
echo ""
echo -e "${YELLOW}View Logs:${NC}"
echo "  tail -f /tmp/api-gateway.log"
echo "  tail -f /tmp/trading-execution.log"
echo "  tail -f /tmp/frontend.log"
echo ""
echo -e "${GREEN}Data Source: ${NC}"
if [ -n "$APCA_API_KEY_ID" ]; then
    echo -e "  Using ${GREEN}Alpaca API${NC} for real market data"
else
    echo -e "  Using ${YELLOW}Mock Data${NC} (set APCA_API_KEY_ID in .env for real data)"
fi