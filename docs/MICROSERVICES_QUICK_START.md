# Microservices Quick Start Guide

## Updated Architecture (9000 Port Range)

The microservices architecture has been updated to use the 9000 port range as requested:

### Port Mapping
- **API Gateway**: `localhost:9000` (Entry point for all requests)
- **Position Management**: `localhost:9001`
- **Trading Execution**: `localhost:9002` 
- **Signal Processing**: `localhost:9003`
- **Risk Management**: `localhost:9004`
- **Market Data**: `localhost:9005`
- **Historical Data**: `localhost:9006`
- **Analytics**: `localhost:9007`
- **Notification**: `localhost:9008`
- **Configuration**: `localhost:9009`
- **Health Monitor**: `localhost:9010`
- **Training Service**: `localhost:9011` (AI Collaborative Trading) ✨ NEW
- **Frontend**: `localhost:9100` (Main Trading Platform)

## Current Status

✅ **RUNNING SERVICES**:
- **Frontend Microservice (Port 9100)**: React-based frontend serving as main platform ✅ PRIMARY
- **Training Service (Port 9011)**: AI-powered collaborative trading service ✅ NEW

✅ **COMPLETED**:
- Updated `docker-compose.yml` with 9000 port range
- Updated API Gateway service URLs to use 9000 range
- Frontend microservice configured to connect to API Gateway (9000)
- Created comprehensive microservices documentation

⏳ **NEXT STEPS**:
- Start API Gateway service (port 9000)
- Start individual microservices (ports 9001-9010)
- Migrate APIs from Flask monolith to individual microservices
- Test full microservices integration

## Architecture Flow

**TARGET (Microservices)**:
```
Frontend Microservice (9100) → API Gateway (9000) → Individual Services (9001-9010)
```

**CURRENT (Microservices)**:
```
Frontend (9100) → API Gateway (9000) → Individual Services (9001-9011)
```

**The system is fully microservices-based with the Frontend on port 9100 as the main entry point.**

## Starting the System

### Current Working System
✅ **Primary Services**:
```bash
# Frontend Service (Port 9100) - Main Platform
# API Gateway (Port 9000) - Request Routing
# Training Service (Port 9011) - AI Collaboration
# Access: http://localhost:9100
```

### Full Microservices System (Target)

#### Option 1: Docker Compose (Recommended)
```bash
cd microservices
docker-compose up -d
```

#### Option 2: Individual Services (Development)
```bash
# Terminal 1: API Gateway (Required first)
cd microservices/services/api-gateway/app
python main.py

# Terminal 2: Frontend (Already running on 9100)
cd microservices/services/frontend/app  
python main.py

# Terminal 3: Position Management
cd microservices/services/position-management/app
python main.py

# Continue for other services...
```

## Service URLs

### Frontend Access
- **Main Dashboard**: http://localhost:9100
- **Portfolio**: http://localhost:9100/portfolio  
- **Trading**: http://localhost:9100/trading
- **Analytics**: http://localhost:9100/analytics
- **Config**: http://localhost:9100/config
- **Monitoring**: http://localhost:9100/monitoring

### API Gateway Routes
- **Base URL**: http://localhost:9000
- **Account API**: http://localhost:9000/api/account
- **Positions API**: http://localhost:9000/api/positions
- **Orders API**: http://localhost:9000/api/orders
- **Chart Data**: http://localhost:9000/api/chart/{symbol}
- **Signals**: http://localhost:9000/api/signals
- **Analytics**: http://localhost:9000/api/analytics/summary
- **Health**: http://localhost:9000/health

## Migration from Monolithic Flask App

### Current State
- Flask App (port 8765) contains all APIs consolidated
- Frontend was connecting directly to Flask App
- Works but not true microservices architecture

### Target State  
- Each API endpoint runs as separate microservice
- API Gateway routes requests to appropriate services
- True microservices architecture with independent scaling

### API Migration Plan

| API Endpoint | Current (Flask 8765) | Target Microservice |
|--------------|---------------------|-------------------|
| `/api/account` | ✅ Flask | → Position Management (9001) |
| `/api/positions` | ✅ Flask | → Position Management (9001) |
| `/api/orders` | ✅ Flask | → Trading Execution (9002) |
| `/api/chart/*` | ✅ Flask | → Market Data (9005) |
| `/api/signals` | ✅ Flask | → Signal Processing (9003) |
| `/api/analytics/*` | ✅ Flask | → Analytics (9007) |
| `/api/config` | ✅ Flask | → Configuration (9009) |
| `/api/monitoring/*` | ✅ Flask | → Health Monitor (9010) |

## Testing the System

### Current Working System
```bash
# Test Frontend Microservice (Currently Active)
curl http://localhost:9100/health
# Response: {"service":"frontend","status":"healthy"...}

# Test Frontend Pages (Currently Active)
curl -s -o /dev/null -w "Dashboard: %{http_code}\n" http://localhost:9100/
curl -s -o /dev/null -w "Portfolio: %{http_code}\n" http://localhost:9100/portfolio
curl -s -o /dev/null -w "Trading: %{http_code}\n" http://localhost:9100/trading
curl -s -o /dev/null -w "Analytics: %{http_code}\n" http://localhost:9100/analytics
curl -s -o /dev/null -w "Config: %{http_code}\n" http://localhost:9100/config
curl -s -o /dev/null -w "Monitoring: %{http_code}\n" http://localhost:9100/monitoring

# Test Flask Monolith APIs (Currently Active)
curl http://localhost:8765/health
curl http://localhost:8765/api/account
curl http://localhost:8765/api/positions
```

### Full Microservices System (When API Gateway is running)
```bash
# Test API Gateway
curl http://localhost:9000/health

# Test individual microservices
curl http://localhost:9001/health  # Position Management
curl http://localhost:9002/health  # Trading Execution
curl http://localhost:9003/health  # Signal Processing
# etc...

# Test API Gateway routing
curl http://localhost:9000/api/account
curl http://localhost:9000/api/positions
curl http://localhost:9000/api/market_status
```

## Development Workflow

### 1. Local Development Setup
```bash
# Clone and setup
git clone <repo>
cd microservices

# Install dependencies for each service
pip install -r requirements.txt
```

### 2. Environment Variables
```bash
# Set required environment variables
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"
export ALPACA_BASE_URL="https://paper-api.alpaca.markets"
export DATABASE_URL="postgresql://user:pass@localhost:5432/trading_db"
```

### 3. Database Setup
```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Run migrations (if any)
# Each service handles its own database schema
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   - Make sure ports 9000-9010 and 9100 are available
   - Check with: `lsof -i :9000` etc.

2. **Service Discovery**
   - In Docker: Services communicate using service names
   - Locally: Use localhost with specific ports

3. **Environment Variables**
   - Each service needs proper environment configuration
   - Check docker-compose.yml for required variables

4. **Database Connections**
   - Services need PostgreSQL and Redis running
   - Connection strings must be properly configured

### Logs and Debugging
```bash
# Docker logs
docker-compose logs -f api-gateway
docker-compose logs -f frontend

# Individual service logs
tail -f /path/to/service/logs
```

## Benefits of Microservices Architecture

✅ **Scalability**: Scale individual services based on load
✅ **Isolation**: Service failures don't cascade  
✅ **Technology Diversity**: Each service can use optimal tech stack
✅ **Development Teams**: Teams can work independently on services
✅ **Deployment**: Deploy services independently
✅ **Monitoring**: Granular monitoring and metrics per service

## Next Steps

1. **Complete Migration**: Move all Flask APIs to individual microservices
2. **Service Implementation**: Implement missing microservice functionality
3. **Load Balancing**: Add load balancing for high-traffic services
4. **Service Mesh**: Consider Istio for advanced traffic management
5. **Monitoring**: Implement distributed tracing and monitoring
6. **CI/CD**: Setup automated deployment pipelines per service