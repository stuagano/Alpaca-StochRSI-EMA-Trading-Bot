#!/bin/bash

# Position Management Service Startup Script
# Handles development and production environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Position Management Service${NC}"

# Function to check if a service is running
check_service() {
    local service_name=$1
    local host=$2
    local port=$3
    
    echo -e "${YELLOW}Checking ${service_name} at ${host}:${port}...${NC}"
    
    for i in {1..30}; do
        if nc -z "$host" "$port" 2>/dev/null; then
            echo -e "${GREEN}✅ ${service_name} is ready${NC}"
            return 0
        fi
        echo "Waiting for ${service_name}... ($i/30)"
        sleep 2
    done
    
    echo -e "${RED}❌ ${service_name} is not available${NC}"
    return 1
}

# Environment setup
export PYTHONPATH="${PYTHONPATH}:$(pwd)/app"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
source venv/bin/activate

# Install/upgrade dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Determine environment
if [ "$1" = "production" ] || [ "$NODE_ENV" = "production" ]; then
    echo -e "${BLUE}🏭 Starting in PRODUCTION mode${NC}"
    
    # Production environment variables
    export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://trading_user:trading_pass@postgres:5432/trading_db}"
    export REDIS_URL="${REDIS_URL:-redis://redis:6379}"
    export JWT_SECRET="${JWT_SECRET:-$(openssl rand -base64 32)}"
    export SQL_ECHO="false"
    export LOG_LEVEL="INFO"
    
    # Check dependencies
    check_service "PostgreSQL" "${DATABASE_HOST:-postgres}" "${DATABASE_PORT:-5432}"
    check_service "Redis" "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}"
    
    # Start with Gunicorn for production
    exec gunicorn app.main:app \
        --worker-class uvicorn.workers.UvicornWorker \
        --workers 4 \
        --bind 0.0.0.0:8002 \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
        --timeout 120 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 100

elif [ "$1" = "docker" ]; then
    echo -e "${BLUE}🐳 Starting in DOCKER mode${NC}"
    
    # Wait for services in Docker environment
    check_service "PostgreSQL" "postgres" "5432"
    check_service "Redis" "redis" "6379"
    
    # Start with Uvicorn for Docker
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8002 \
        --workers 1 \
        --log-level info

else
    echo -e "${BLUE}🔧 Starting in DEVELOPMENT mode${NC}"
    
    # Development environment variables
    export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./position_management.db}"
    export REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
    export JWT_SECRET="${JWT_SECRET:-dev-secret-key-change-in-production}"
    export SQL_ECHO="true"
    export LOG_LEVEL="DEBUG"
    
    # Optional dependency checks for development
    if command -v nc >/dev/null; then
        if [ "${DATABASE_URL}" != *"sqlite"* ]; then
            check_service "PostgreSQL" "localhost" "5432" || echo -e "${YELLOW}⚠️  PostgreSQL not available, falling back to SQLite${NC}"
        fi
        check_service "Redis" "localhost" "6379" || echo -e "${YELLOW}⚠️  Redis not available, WebSocket scaling disabled${NC}"
    fi
    
    # Start with auto-reload for development
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8002 \
        --reload \
        --reload-dir app \
        --log-level debug
fi