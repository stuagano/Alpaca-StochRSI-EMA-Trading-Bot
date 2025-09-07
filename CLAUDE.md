# Alpaca Trading Bot - Development Guidelines

## 🎯 What This Is
A **monolithic** Python trading bot for stocks and crypto via Alpaca API.
- Single service architecture (no microservices)
- One entry point: `unified_trading_service_with_frontend.py`
- React frontend + FastAPI backend in one process

## 🚀 Running the Bot
```bash
# Start everything
python unified_trading_service_with_frontend.py

# Access the UI
http://localhost:9100        # Stock trading
http://localhost:9100/crypto  # Crypto trading
```

## 📁 Project Structure
```
/
├── frontend-shadcn/        # React UI
├── strategies/             # Trading algorithms
├── services/              # Core modules
├── tests/                 # All tests go here
├── logs/                  # All logs go here
├── docs/                  # Documentation
├── AUTH/                  # API credentials
└── unified_trading_service_with_frontend.py  # Main entry point
```

## ⚙️ Configuration
Required files in `/AUTH/`:
- `authAlpaca.txt` - Your Alpaca API keys
- `ConfigFile.txt` - Trading parameters
- `Tickers.txt` - Symbols to trade

## 📝 Development Rules

### CRITICAL: File Management
**🚨 ALWAYS UPDATE EXISTING FILES - NEVER CREATE NEW ONES**
1. **SEARCH FIRST**: Always search for existing files before creating
2. **UPDATE OVER CREATE**: If a file exists with similar purpose, UPDATE it
3. **NO DUPLICATES**: Never create `file_v2.py`, `file_new.py`, `file_updated.py`
4. **CHECK DOCS**: Before creating docs, grep existing docs for the topic
5. **SINGLE SOURCE OF TRUTH**: One file per concept/feature

### File Organization
- **Tests**: Always in `/tests/`, never in root
- **Logs**: Always in `/logs/`, never in root  
- **Docs**: Update existing docs, don't create new ones
- **Scripts**: Check `/scripts/` before creating utilities

### Code Standards
- Real data only - no mocks or fake data
- Log errors to `logs/errors.log`
- Test changes before committing
- Update existing functions rather than creating duplicates

## 🔧 Common Commands

```bash
# Check if running
lsof -i :9000 | grep LISTEN

# View logs
tail -f logs/trading.log

# Run tests
cd tests && pytest              # Backend
cd frontend-shadcn && npm test  # Frontend

# Restart service
pkill -f "unified_trading"
python unified_trading_service_with_frontend.py
```

## 🚨 Troubleshooting

**Port Already in Use**
- Check: `lsof -i :9000` or `lsof -i :9100`
- Kill: `kill -9 [PID]`

**API Authentication Failed**
- Check `AUTH/authAlpaca.txt`
- Verify paper vs live mode

**WebSocket Disconnected**
- Check `logs/errors.log`
- Restart the service

---

**Remember**: This is a monolith. One service, one process. Keep it simple.