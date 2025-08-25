# 🧭 Navigation Guide - Trading Platform

## 📍 Main Entry Point

**URL:** http://localhost:9100/  
**Description:** Modern React frontend with navigation to all services and dashboards

## 🎯 Primary Services & Navigation

### 1. Frontend Service (Main Portal)
- **URL:** http://localhost:9100/
- **Purpose:** Central navigation and modern UI
- **Features:**
  - React-based frontend with real-time updates
  - Visual service map with status indicators
  - Quick health checks for all microservices
  - Direct links to all dashboards and services
  - WebSocket connections for live data

### 2. AI Training Platform (NEW!)
- **Direct Service:** http://localhost:9011
- **API Docs:** http://localhost:9011/docs
- **Via API Gateway:** http://localhost:9000/training
- **Features:**
  - Collaborative human-AI trading decisions
  - Strategy backtesting (4 built-in strategies)
  - Training scenarios (Bull/Bear/Volatile markets)
  - Real-time market analysis
  - Performance analytics
  - WebSocket support for live collaboration

### 3. Live Trading Dashboard
- **Via Frontend:** http://localhost:9100/trading
- **Purpose:** Real-time trading with StochRSI signals
- **Features:**
  - Live market data streaming
  - Position management
  - Automated trading controls
  - Signal monitoring

### 4. Enhanced Trading View
- **Via Frontend:** http://localhost:9100/charts
- **Purpose:** Advanced charting and analysis
- **Features:**
  - Lightweight Charts integration
  - Technical indicators
  - Portfolio analytics
  - Real-time updates

### 5. Backtesting Suite
- **Via Frontend:** http://localhost:9100/backtest
- **Purpose:** Historical strategy testing
- **Features:**
  - Strategy performance analysis
  - Historical data testing
  - Optimization tools

## 🔧 Microservices Architecture (Ports 9000-9100)

| Service | Port | Endpoint | Description |
|---------|------|----------|-------------|
| API Gateway | 9000 | /health | Central routing & auth |
| Position Management | 9001 | /health | Portfolio tracking |
| Trading Execution | 9002 | /health | Order execution |
| Signal Processing | 9003 | /health | Technical analysis |
| Risk Management | 9004 | /health | Risk controls |
| Market Data | 9005 | /health | Live data feeds |
| Historical Data | 9006 | /health | Historical storage |
| Analytics | 9007 | /health | Performance metrics |
| Notification | 9008 | /health | Alerts & messaging |
| Configuration | 9009 | /health | System settings |
| Health Monitor | 9010 | /health | Service monitoring |
| **Training (NEW)** | 9011 | /health | AI training service |
| Frontend | 9100 | / | React frontend |

## 🚀 Quick Access URLs

### Primary Access Points
- **Main Frontend:** http://localhost:9100/
- **API Gateway:** http://localhost:9000/
- **Training Service:** http://localhost:9011/

### Microservices (Direct Access)
- API Gateway: http://localhost:9000
- Training API Docs: http://localhost:9011/docs
- Training Service: http://localhost:9011
- Frontend Service: http://localhost:9100

### API Documentation
- Training Service API: http://localhost:9011/docs
- API Gateway Swagger: http://localhost:9000/docs

## 🔍 Service Health Check

To check the health of all services:
1. Navigate to http://localhost:9100/
2. Access the service status panel
3. View real-time status of all microservices

## 📊 Training Service Endpoints

### REST API
- `GET /health` - Service health check
- `GET /api/strategies` - Available trading strategies
- `POST /api/backtest` - Run strategy backtest
- `GET /api/collaborate/current/{symbol}` - Current market analysis
- `POST /api/collaborate/decision` - Submit collaborative decision
- `POST /api/strategies/compare` - Compare multiple strategies
- `GET /api/scenarios` - Training scenarios
- `GET /api/metrics/performance` - Performance metrics

### WebSocket
- `ws://localhost:9011/ws/collaborate/{symbol}` - Real-time collaboration

## 🔧 Starting Services

### Start Everything with Docker Compose
```bash
cd microservices
docker-compose up
```

### Start Training Service Only
```bash
# With Docker
docker-compose up training

# Or locally
./scripts/start_training_service.sh
```

## 📝 Notes

- The Frontend service on port 9100 serves as the main web interface
- Microservices (9000-9011) handle specific functionality
- The new Training service (9011) provides AI-powered collaborative trading
- All services can be accessed through the API Gateway (9000) or directly
- The frontend provides a modern React-based interface with real-time updates

## 🎯 Recommended Workflow

1. **Start here:** http://localhost:9100/ (Main Frontend)
2. **For AI Training:** Access via frontend or directly at http://localhost:9011
3. **For Live Trading:** Access trading features through the frontend
4. **For API Access:** Use http://localhost:9011/docs for Training API documentation
5. **For Health Monitoring:** Use the service status panel in the frontend