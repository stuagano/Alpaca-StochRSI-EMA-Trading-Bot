# System Architecture Documentation

## 🏗️ Architecture Overview

The Alpaca StochRSI-EMA Trading Bot is a modular, microservices-based trading system that combines technical analysis, real-time market data, and automated execution through the Alpaca API.

## 📊 System Components

### 1. **Unified Trading Service** (`unified_trading_service_with_frontend.py`)
- **Port**: 9000 (Primary)
- **Purpose**: Consolidates all microservices into a single, manageable service
- **Features**:
  - FastAPI backend with async support
  - WebSocket connections for real-time data
  - Static file serving for frontend
  - Integrated trading logic
  - Background auto-trading tasks

### 2. **Frontend Trading Interface** (`frontend-shadcn/`)
- **Port**: 9100 (Development)
- **Framework**: Next.js with React
- **Features**:
  - Real-time portfolio visualization
  - Interactive trading charts (TradingView Lightweight Charts)
  - Market screener and asset selector
  - Live P&L tracking
  - WebSocket data streaming
  - Responsive design with Tailwind CSS

### 3. **Trading Strategies** (`strategies/`)
- **StochRSI-EMA Strategy**: Primary momentum-based strategy
- **Crypto Scalping Strategy**: High-frequency crypto trading
- **Multi-Strategy Manager**: Orchestrates multiple strategies

## 🔌 API Architecture

### REST Endpoints

#### Core Trading APIs
```
GET  /api/positions          # Get all open positions
GET  /api/account            # Account information
POST /api/orders             # Place new orders
GET  /api/orders             # List active orders
DELETE /api/orders/{id}      # Cancel order
```

#### Market Data APIs
```
GET  /api/quotes/{symbol}    # Real-time quotes
GET  /api/bars/{symbol}      # Historical price bars
GET  /api/snapshot/{symbol}  # Market snapshot
GET  /api/news/{symbol}      # Market news
```

#### Crypto-Specific APIs
```
GET  /api/crypto/assets      # Available crypto pairs
GET  /api/crypto/positions   # Crypto positions
POST /api/crypto/orders      # Crypto orders
GET  /api/crypto/quotes/{symbol}  # Crypto quotes
GET  /api/crypto/signals/{symbol} # Trading signals
```

#### System Management APIs
```
GET  /health                 # Service health check
GET  /api/status             # System status
GET  /api/metrics            # Performance metrics
POST /api/backtest           # Run backtest
```

### WebSocket Connections

#### Real-Time Data Streams
```
ws://localhost:9000/ws/trading    # Crypto trading updates
ws://localhost:9000/api/stream    # Stock market updates
```

**WebSocket Message Format:**
```json
{
  "type": "update|trade|quote|error",
  "data": {
    "symbol": "AAPL",
    "price": 150.25,
    "volume": 1000,
    "timestamp": "2025-01-01T12:00:00Z"
  }
}
```

## 🏭 Service Architecture (Microservices Mode)

When running in full microservices mode:

### Service Topology
```
┌─────────────────────────────────────────────┐
│            Frontend (9100)                  │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│          API Gateway (9000)                 │
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼───┐    ┌────▼────┐    ┌────▼────┐
│Trading│    │Position │    │ Market  │
│ Exec  │    │ Mgmt    │    │  Data   │
│ 9002  │    │  9001   │    │  9005   │
└───┬───┘    └────┬────┘    └────┬────┘
    │              │              │
┌───▼───┐    ┌────▼────┐    ┌────▼────┐
│Signal │    │  Risk   │    │Historical│
│Process│    │  Mgmt   │    │  Data   │
│ 9003  │    │  9004   │    │  9006   │
└───────┘    └─────────┘    └─────────┘
```

### Service Responsibilities

| Service | Port | Responsibility |
|---------|------|----------------|
| API Gateway | 9000 | Request routing, authentication |
| Position Management | 9001 | Portfolio tracking, P&L calculation |
| Trading Execution | 9002 | Order placement, Alpaca integration |
| Signal Processing | 9003 | Technical indicators, signal generation |
| Risk Management | 9004 | Position sizing, stop-loss management |
| Market Data | 9005 | Live quotes, real-time feeds |
| Historical Data | 9006 | Price history, data storage |
| Analytics | 9007 | Performance metrics, reporting |
| Notification | 9008 | Alerts, email/SMS notifications |
| Configuration | 9009 | System settings, parameters |
| Health Monitor | 9010 | Service health, monitoring |
| Training Service | 9011 | AI/ML model training |
| Crypto Trading | 9012 | 24/7 cryptocurrency trading |

## 🔄 Data Flow Architecture

### Order Execution Flow
```
1. Frontend → Place Order Request
2. API Gateway → Validate & Route
3. Risk Management → Check Limits
4. Trading Execution → Submit to Alpaca
5. Position Management → Update Portfolio
6. WebSocket → Broadcast Update
7. Frontend → Display Confirmation
```

### Market Data Flow
```
1. Alpaca API → Market Data Service
2. Market Data → Signal Processing
3. Signal Processing → Generate Signals
4. Signals → Trading Execution
5. WebSocket → Frontend Updates
```

## 🗄️ Data Storage

### PostgreSQL Database
- **Trades Table**: Historical trades
- **Positions Table**: Current positions
- **Signals Table**: Generated signals
- **Metrics Table**: Performance metrics
- **Configuration Table**: System settings

### Redis Cache
- Real-time quotes
- Session management
- WebSocket connections
- Rate limiting

## 🔐 Security Architecture

### Authentication & Authorization
- API key authentication for Alpaca
- JWT tokens for user sessions
- Role-based access control (RBAC)
- Secure WebSocket connections

### Data Security
- Environment variable configuration
- Encrypted credentials storage
- HTTPS/WSS in production
- Input validation and sanitization

## 🚀 Deployment Architecture

### Docker Containerization
```dockerfile
# Each service has its own container
frontend/
├── Dockerfile
└── docker-compose.yml

services/
├── trading-execution/Dockerfile
├── market-data/Dockerfile
└── ...
```

### Kubernetes Deployment (Production)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trading-bot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: trading-bot
```

## 📈 Scalability Design

### Horizontal Scaling
- Stateless service design
- Load balancing with nginx
- Database connection pooling
- Redis for distributed caching

### Performance Optimization
- Async/await for I/O operations
- WebSocket for real-time updates
- Batch processing for historical data
- Query optimization with indexes

## 🔍 Monitoring & Observability

### Metrics Collection
- Prometheus metrics endpoint
- Custom trading metrics
- Performance counters
- Error tracking

### Logging Architecture
```
Application Logs → Structured JSON → Log Aggregator → Analysis
```

### Health Checks
- `/health` endpoint per service
- Database connectivity checks
- External API availability
- WebSocket connection status

## 🔄 Integration Points

### External APIs
1. **Alpaca Trading API**
   - REST API for orders/positions
   - WebSocket for real-time data
   - Historical data endpoints

2. **Market Data Providers**
   - Primary: Alpaca Data API
   - Backup: Yahoo Finance (fallback)

3. **Notification Services**
   - Email: SMTP integration
   - SMS: Twilio (optional)
   - Discord/Slack webhooks

## 🎯 Design Patterns

### Architectural Patterns
- **Microservices**: Service isolation
- **Event-Driven**: WebSocket messaging
- **Repository Pattern**: Data access layer
- **Strategy Pattern**: Trading strategies
- **Observer Pattern**: Real-time updates

### Code Organization
```
project/
├── frontend-shadcn/     # React frontend
├── services/            # Microservices
├── strategies/          # Trading algorithms
├── indicators/          # Technical indicators
├── risk_management/     # Risk controls
├── backtesting/        # Strategy testing
├── utils/              # Shared utilities
└── tests/              # Test suites
```

## 📝 Configuration Management

### Environment Variables
```bash
# Trading Configuration
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Service Configuration
FRONTEND_PORT=9100
API_PORT=9000
WEBSOCKET_PORT=9000

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/trading
REDIS_URL=redis://localhost:6379
```

### Dynamic Configuration
- Runtime parameter updates
- Feature flags
- A/B testing support
- Strategy parameter tuning

## 🔮 Future Architecture Considerations

### Planned Enhancements
1. **Multi-Exchange Support**: Binance, Coinbase integration
2. **Machine Learning Pipeline**: AI-powered predictions
3. **Distributed Computing**: Apache Spark for backtesting
4. **GraphQL API**: Flexible data queries
5. **Event Sourcing**: Complete audit trail
6. **CQRS Pattern**: Separate read/write models

### Technology Stack Evolution
- **Current**: Python, FastAPI, React, PostgreSQL
- **Future Considerations**: 
  - Rust for performance-critical components
  - Kubernetes for orchestration
  - Apache Kafka for event streaming
  - TimescaleDB for time-series data

---

*This architecture is designed for scalability, maintainability, and performance. It supports both development simplicity (unified service) and production robustness (microservices).*