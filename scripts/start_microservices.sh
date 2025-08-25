#!/bin/bash

# Start Microservices Trading System
# This script builds and starts all microservices using Docker Compose

echo "🚀 Starting Microservices Trading System"
echo "========================================"

# Change to microservices directory
cd "$(dirname "$0")/../microservices" || exit 1

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose >/dev/null 2>&1 && ! docker compose version >/dev/null 2>&1; then
    echo "❌ Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Use docker compose or docker-compose based on what's available
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
fi

echo "📋 Services that will be started:"
echo "  - PostgreSQL Database (port 5432)"
echo "  - Redis Cache (port 6379)"
echo "  - API Gateway (port 8000)"
echo "  - Position Management (port 8001)"
echo "  - Trading Execution (port 8002)"
echo "  - Signal Processing (port 8003)"
echo "  - Risk Management (port 8004)"
echo "  - Market Data (port 8005)"
echo "  - Historical Data (port 8006)"
echo "  - Analytics (port 8007)"
echo "  - Notification (port 8008)"
echo "  - Configuration (port 8009)"
echo "  - Health Monitor (port 8010)"
echo "  - Frontend Dashboard (port 3000)"
echo ""

# Stop any existing containers
echo "🧹 Stopping existing containers..."
$DOCKER_COMPOSE_CMD down --remove-orphans

# Build all services
echo "🔨 Building all services..."
$DOCKER_COMPOSE_CMD build --no-cache

# Start infrastructure services first
echo "🗄️  Starting infrastructure services..."
$DOCKER_COMPOSE_CMD up -d postgres redis

# Wait for database to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
while ! $DOCKER_COMPOSE_CMD exec postgres pg_isready -U trading_user >/dev/null 2>&1; do
    sleep 2
    echo "   Still waiting for PostgreSQL..."
done
echo "✅ PostgreSQL is ready"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
while ! $DOCKER_COMPOSE_CMD exec redis redis-cli ping >/dev/null 2>&1; do
    sleep 2
    echo "   Still waiting for Redis..."
done
echo "✅ Redis is ready"

# Start core services
echo "🚀 Starting core microservices..."
$DOCKER_COMPOSE_CMD up -d \
    position-management \
    trading-execution \
    signal-processing \
    risk-management \
    market-data

# Wait a bit for core services to start
sleep 10

# Start analytics and data services
echo "📊 Starting analytics and data services..."
$DOCKER_COMPOSE_CMD up -d \
    historical-data \
    analytics \
    notification \
    configuration

# Wait a bit more
sleep 10

# Start monitoring and gateway
echo "🛡️  Starting monitoring and gateway services..."
$DOCKER_COMPOSE_CMD up -d \
    health-monitor \
    api-gateway

# Wait for gateway to be ready
sleep 5

# Start frontend
echo "🌐 Starting frontend dashboard..."
$DOCKER_COMPOSE_CMD up -d frontend

# Show status
echo ""
echo "📊 Container Status:"
$DOCKER_COMPOSE_CMD ps

# Wait for all services to be healthy
echo ""
echo "⏳ Waiting for all services to be healthy..."
sleep 30

# Check service health
echo ""
echo "🔍 Checking service health..."

# Health check function
check_service() {
    local service_name=$1
    local port=$2
    local endpoint=${3:-"/health"}
    
    if curl -sf "http://localhost:$port$endpoint" >/dev/null 2>&1; then
        echo "✅ $service_name (port $port) - Healthy"
        return 0
    else
        echo "❌ $service_name (port $port) - Not responding"
        return 1
    fi
}

# Check all services
healthy_count=0
total_services=12

check_service "API Gateway" 8000 && ((healthy_count++))
check_service "Position Management" 8001 && ((healthy_count++))
check_service "Trading Execution" 8002 && ((healthy_count++))
check_service "Signal Processing" 8003 && ((healthy_count++))
check_service "Risk Management" 8004 && ((healthy_count++))
check_service "Market Data" 8005 && ((healthy_count++))
check_service "Historical Data" 8006 && ((healthy_count++))
check_service "Analytics" 8007 && ((healthy_count++))
check_service "Notification" 8008 && ((healthy_count++))
check_service "Configuration" 8009 && ((healthy_count++))
check_service "Health Monitor" 8010 && ((healthy_count++))
check_service "Frontend" 3000 && ((healthy_count++))

echo ""
echo "📈 Health Summary: $healthy_count/$total_services services healthy"

if [ $healthy_count -eq $total_services ]; then
    echo "🎉 All services started successfully!"
    echo ""
    echo "🌐 Access Points:"
    echo "  • Frontend Dashboard: http://localhost:3000"
    echo "  • API Gateway: http://localhost:8000"
    echo "  • API Documentation: http://localhost:8000/docs"
    echo "  • Health Monitor: http://localhost:8010/system/health"
    echo ""
    echo "📚 Useful Commands:"
    echo "  • View logs: $DOCKER_COMPOSE_CMD logs -f [service_name]"
    echo "  • Stop all: $DOCKER_COMPOSE_CMD down"
    echo "  • Restart service: $DOCKER_COMPOSE_CMD restart [service_name]"
    echo ""
    echo "🔍 To run integration tests:"
    echo "  cd ../tests && python -m pytest test_microservices_integration.py -v"
    
elif [ $healthy_count -gt $((total_services / 2)) ]; then
    echo "⚠️  Most services started, but some may need more time or have issues."
    echo "   Check logs with: $DOCKER_COMPOSE_CMD logs [service_name]"
    
else
    echo "❌ Many services failed to start. Check the logs:"
    echo "   $DOCKER_COMPOSE_CMD logs"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "  • Ensure ports 3000, 5432, 6379, 8000-8010 are available"
    echo "  • Check Docker resources (memory, disk space)"
    echo "  • Verify .env file has required environment variables"
    exit 1
fi

echo ""
echo "🎯 Epic 3 - Microservices Architecture: COMPLETE! ✅"