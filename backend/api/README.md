# Flask Trading Bot API

## Overview

This is the refactored Flask application for the Alpaca StochRSI EMA Trading Bot. It provides a modern, modular web interface and API for controlling and monitoring the trading bot.

## Architecture

### Application Factory Pattern
- **Location**: `backend/api/__init__.py`
- **Purpose**: Creates Flask app instances with proper configuration
- **Benefits**: Easy testing, multiple configurations, better organization

### Blueprint Structure
```
backend/api/
├── blueprints/
│   ├── dashboard.py    # Web interface routes
│   ├── api.py          # Core API endpoints
│   ├── trading.py      # Trading operations
│   ├── pnl.py          # P&L tracking
│   └── websocket_events.py  # Real-time updates
├── services/
│   ├── trading_service.py   # Trading business logic
│   ├── pnl_service.py        # P&L calculations
│   └── alpaca_client.py      # Alpaca API wrapper
└── utils/
    ├── decorators.py    # Route decorators
    ├── validators.py    # Input validation
    └── error_handlers.py # Error handling
```

## Running the Application

### Quick Start
```bash
# Run with defaults (localhost:5001)
python backend/api/run.py

# Run with custom settings
python backend/api/run.py --host 0.0.0.0 --port 8080 --env production
```

### Command Line Options
- `--host`: Host to bind to (default: localhost)
- `--port`: Port to listen on (default: 5001)
- `--env`: Environment (development/production/testing)
- `--debug`: Enable debug mode

## API Endpoints

### Dashboard Routes
- `GET /` - Main dashboard
- `GET /simple` - Simplified view
- `GET /advanced` - Advanced view with all features

### Core API (v1)
- `GET /api/v1/status` - System status
- `GET /api/v1/account` - Account information
- `GET /api/v1/positions` - Current positions
- `GET /api/v1/signals` - Trading signals
- `GET /api/v1/orders` - Order history
- `GET /api/v1/symbols` - Tracked symbols

### Trading Operations
- `POST /api/v1/trading/start` - Start automated trading
- `POST /api/v1/trading/stop` - Stop automated trading
- `POST /api/v1/trading/buy` - Place buy order
- `POST /api/v1/trading/sell` - Place sell order
- `POST /api/v1/trading/close/<symbol>` - Close position
- `POST /api/v1/trading/close-all` - Close all positions

### P&L Tracking
- `GET /api/v1/pnl/current` - Current P&L
- `GET /api/v1/pnl/history` - Historical P&L
- `GET /api/v1/pnl/chart-data` - Chart.js formatted data
- `GET /api/v1/pnl/statistics` - Performance statistics
- `GET /api/v1/pnl/export` - Export to CSV/JSON
- `GET /api/v1/pnl/trades` - Recent trades
- `GET /api/v1/pnl/performance` - Performance by symbol

### WebSocket Events
Connect to WebSocket for real-time updates:
- `connect` - Establish connection
- `subscribe` - Subscribe to updates
- `request_update` - Request data refresh

## Features

### Consolidated Dashboard
- Combines features from 6 different dashboard implementations
- Multiple view modes (simple/advanced)
- Real-time updates via WebSocket
- P&L tracking with historical data
- Technical indicators and signals
- Trade execution interface

### Service Layer Integration
- Integrates with existing `TradingBot` and `TradingExecutor`
- Uses unified configuration system
- Connects to service registry
- Maintains backward compatibility

### Security Features
- API key authentication
- Rate limiting
- Input validation
- Error sanitization
- CORS configuration

### Database Integration
- SQLite for P&L history
- Trade tracking
- Performance metrics
- Export functionality

## Configuration

The application uses the unified configuration system:
- **Config file**: `config/unified_config.yml`
- **Config class**: `config/unified_config.py`
- **Environment overrides**: Supported via environment variables

## Migration from Old Dashboard

### Old Files (Archived)
The following files have been consolidated and archived:
- `app.py` - Original crypto dashboard (still functional)
- `realtime_pnl_dashboard.py` - P&L tracking features
- `live_dashboard.py` - Live trading view
- `simple_pnl_dashboard.py` - Simplified view
- `realtime_dashboard.py` - WebSocket features

### Migration Path
1. Start using the new Flask app: `python backend/api/run.py`
2. Old app.py still works for compatibility
3. Gradually migrate frontend to use new API endpoints
4. Archive old dashboard files once migration complete

## Development

### Adding New Endpoints
1. Create or modify blueprint in `blueprints/`
2. Add business logic to `services/`
3. Register blueprint in `__init__.py`

### Testing
```bash
# Run in testing mode
python backend/api/run.py --env testing

# Test API endpoints
curl http://localhost:5001/api/v1/status
curl http://localhost:5001/api/v1/account
```

## Benefits of New Architecture

1. **Modular Design**: Easy to maintain and extend
2. **Best Practices**: Follows Flask conventions
3. **Scalable**: Can handle increased load
4. **Testable**: Proper separation of concerns
5. **Documented**: Clear API structure
6. **Unified**: Single dashboard instead of 6
7. **Modern**: Uses latest Flask patterns