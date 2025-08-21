# Trading System Microservices Architecture

## 🚀 Quick Start

```bash
# Clone and setup
cd microservices
cp .env.example .env

# Start all services
docker-compose up -d

# Check service health
curl http://localhost:8000/health
```

## 🏗️ Service Architecture

### **Core Services**
- **API Gateway** (8000) - Request routing and authentication
- **Position Management** (8001) - Portfolio tracking and P&L
- **Trading Execution** (8002) - Order placement and execution
- **Signal Processing** (8003) - Trading signal generation
- **Risk Management** (8004) - Portfolio risk assessment

### **Data Services**
- **Market Data** (8005) - Real-time price feeds
- **Historical Data** (8006) - Historical price and volume data
- **Analytics** (8007) - Performance metrics and reporting
- **Notifications** (8008) - Alerts and webhook delivery

### **Infrastructure**
- **Redis** (6379) - Caching and message queue
- **PostgreSQL** (5432) - Primary database
- **InfluxDB** (8086) - Time-series data

## 📋 Service Status

| Service | Port | Status | Health | Documentation |
|---------|------|--------|--------|---------------|
| API Gateway | 8000 | ⏳ | `/health` | [API Docs](./services/api-gateway/README.md) |
| Position Mgmt | 8001 | ⏳ | `/health` | [API Docs](./services/position-management/README.md) |
| Trading Exec | 8002 | ⏳ | `/health` | [API Docs](./services/trading-execution/README.md) |
| Signal Process | 8003 | ⏳ | `/health` | [API Docs](./services/signal-processing/README.md) |
| Risk Mgmt | 8004 | ⏳ | `/health` | [API Docs](./services/risk-management/README.md) |

## 🛠️ Development

### **Local Development**
```bash
# Start individual service
cd services/position-management
python -m uvicorn main:app --reload --port 8001

# Run tests
pytest tests/

# Generate API docs
python generate_docs.py
```

### **Service Communication**
```python
# Example: Position service calling Risk service
import httpx

async def check_position_risk(position_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://risk-management:8004/risk/position/{position_id}"
        )
        return response.json()
```

## 📊 Monitoring

### **Service Health Dashboard**
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Service Discovery**: http://localhost:8500

### **Key Metrics**
- API response times
- Service availability
- Database performance
- Error rates

## 🚦 Deployment

### **Production Deployment**
```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose scale position-management=3
docker-compose scale trading-execution=2
```

### **Health Monitoring**
```bash
# Check all services
curl http://localhost:8000/health/all

# Individual service health
curl http://localhost:8001/health
```

---

## 📁 Directory Structure

```
microservices/
├── services/                   # Individual microservices
│   ├── api-gateway/           # Port 8000
│   ├── position-management/   # Port 8001
│   ├── trading-execution/     # Port 8002
│   ├── signal-processing/     # Port 8003
│   ├── risk-management/       # Port 8004
│   ├── market-data/          # Port 8005
│   ├── analytics/            # Port 8007
│   └── notifications/        # Port 8008
├── shared/                   # Shared libraries
├── infrastructure/           # Docker, K8s, monitoring
└── docs/                    # Documentation
```

Each service follows the same structure:
```
service-name/
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Data models
│   ├── routes/              # API endpoints
│   ├── services/            # Business logic
│   └── database.py          # Database connection
├── tests/                   # Service tests
├── Dockerfile              # Container definition
├── requirements.txt        # Dependencies
└── README.md               # Service documentation
```