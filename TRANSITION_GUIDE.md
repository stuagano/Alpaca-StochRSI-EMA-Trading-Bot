# Complete Flask Architecture Transition Guide

## 🎯 Transition Complete!

Your Flask application has been fully transitioned to a modern, scalable architecture. This guide will help you use and maintain the new system.

## 📁 New Structure Overview

```
Alpaca-StochRSI-EMA-Trading-Bot/
├── backend/api/                  # NEW Flask Application
│   ├── __init__.py               # Application factory
│   ├── app.py                    # Simplified transitional app (USE THIS)
│   ├── run.py                    # Full application with blueprints
│   ├── config.py                 # Flask configuration
│   ├── blueprints/               # Modular routes
│   │   ├── dashboard.py          # Dashboard routes
│   │   ├── api.py                # Core API endpoints
│   │   ├── trading.py            # Trading operations
│   │   ├── pnl.py                # P&L tracking
│   │   └── websocket_events.py  # Real-time updates
│   ├── services/                 # Business logic
│   │   ├── trading_service.py    # Trading operations
│   │   ├── pnl_service.py        # P&L calculations
│   │   └── alpaca_client.py      # Alpaca wrapper
│   └── utils/                    # Utilities
│       ├── decorators.py         # Route decorators
│       ├── validators.py         # Input validation
│       └── error_handlers.py     # Error handling
├── dashboard_archive/             # Old dashboards (archived)
├── frontend/                      # Frontend files
│   ├── dashboard.html            # NEW responsive dashboard
│   ├── config.js                 # API configuration
│   └── index.html                # Original frontend
└── migration_report.txt          # Migration details

```

## 🚀 Quick Start

### Option 1: Use the Simplified App (Recommended for Transition)
```bash
# This version works standalone with minimal dependencies
python backend/api/run.py
```
Open: http://localhost:5001/

### Option 2: Legacy Startup Scripts (Archived)

The helper scripts `start_flask.sh` and `start_flask.bat` have been moved to `archive/legacy_2025Q4/`. Use Option 1 (direct launch) or Option 3 (application factory) going forward.

### Option 3: Use Full Application Factory
```bash
# Full blueprint architecture
python backend/api/run.py --env development
```

## 🔌 API Endpoints

### Core Endpoints
- `GET /api/v1/status` - System status
- `GET /api/v1/account` - Account information
- `GET /api/v1/positions` - Current positions
- `GET /api/v1/signals` - Trading signals
- `GET /api/v1/orders` - Order history

### Trading Operations
- `POST /api/v1/trading/start` - Start bot
- `POST /api/v1/trading/stop` - Stop bot
- `POST /api/v1/trading/buy` - Place buy order
- `POST /api/v1/trading/sell` - Place sell order

### P&L Tracking
- `GET /api/v1/pnl/current` - Current P&L
- `GET /api/v1/pnl/history` - Historical data
- `GET /api/v1/pnl/chart-data` - Chart data
- `GET /api/v1/pnl/export` - Export CSV

## 🧪 Testing

### Test API Endpoints
```bash
python test_flask_api.py

# Full test suite
python test_flask_api.py --full

# Test specific URL
python test_flask_api.py --url http://localhost:8080
```

### Manual Testing
```bash
# Test status
curl http://localhost:5001/api/v1/status

# Test account
curl http://localhost:5001/api/v1/account

# Test positions
curl http://localhost:5001/api/v1/positions
```

## 🎨 Frontend Access

### New Dashboard
Open http://localhost:5001/frontend/dashboard.html

Features:
- Real-time WebSocket updates
- Interactive P&L charts
- Position monitoring
- Signal tracking
- One-click trading controls

### Legacy Dashboard
The original `app.py` still works:
```bash
python backend/api/run.py
```

## 🔄 Migration Steps Completed

✅ **Phase 1: Architecture Setup**
- Created Flask application factory
- Implemented blueprint architecture
- Set up service layer
- Integrated configuration system

✅ **Phase 2: Dashboard Consolidation**
- Merged 6 dashboard files into unified structure
- Archived old dashboards in `dashboard_archive/`
- Preserved best features from each

✅ **Phase 3: API Implementation**
- RESTful API with versioning
- WebSocket support
- Error handling
- Input validation

✅ **Phase 4: Frontend Update**
- Created responsive dashboard
- Added Chart.js visualization
- Implemented real-time updates
- Created API configuration

✅ **Phase 5: Testing & Documentation**
- Created test suite
- Added migration script
- Updated documentation
- Created startup scripts

## 📝 Configuration

### Environment Variables (.env)
```env
FLASK_APP=backend.api.app
FLASK_ENV=development
SECRET_KEY=your-secret-key
API_HOST=localhost
API_PORT=5001
```

### Alpaca Credentials
Still uses: `AUTH/authAlpaca.txt`

## 🚢 Production Deployment

### Using systemd (Linux)
```bash
# Copy service file
sudo cp trading-bot.service /etc/systemd/system/

# Edit paths in service file
sudo nano /etc/systemd/system/trading-bot.service

# Start service
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

### Using Docker (Optional)
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "backend/api/run.py", "--host", "0.0.0.0"]
```

## 🔍 Troubleshooting

### Port Already in Use
```bash
# Find process using port 5001
lsof -i :5001  # Mac/Linux
netstat -ano | findstr :5001  # Windows

# Kill process or use different port
python backend/api/run.py --port 5002
```

### Import Errors
```bash
# Ensure all dependencies installed
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

### API Connection Issues
1. Check Alpaca credentials in `AUTH/authAlpaca.txt`
2. Verify network connectivity
3. Check firewall settings
4. Review logs for errors

## 📊 Benefits of New Architecture

1. **Modular Design** - Easy to maintain and extend
2. **Scalability** - Handles increased load better
3. **Best Practices** - Follows Flask conventions
4. **Single Dashboard** - No more confusion with multiple files
5. **Real-time Updates** - WebSocket integration
6. **API Versioning** - Backward compatibility
7. **Error Handling** - Graceful error management
8. **Testing** - Comprehensive test suite

## 🔄 Rollback Plan

If you need to revert:
1. Backups are in `backup/[timestamp]/`
2. Old dashboards in `dashboard_archive/`
3. Run original app: `python backend/api/run.py`

## 📞 Next Steps

1. **Test the new system**: Run `python backend/api/run.py`
2. **Explore the dashboard**: http://localhost:5001/frontend/dashboard.html
3. **Run API tests**: `python test_flask_api.py`
4. **Monitor performance**: Check logs and metrics
5. **Customize as needed**: Modify blueprints and services

## 🎉 Congratulations!

Your Flask application is now:
- ✅ Properly structured
- ✅ Following best practices
- ✅ Scalable and maintainable
- ✅ Fully documented
- ✅ Ready for production

The transition is complete! Your trading bot now has a professional, modern web interface.
