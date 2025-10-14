# Alpaca StochRSI-EMA Trading Bot

A sophisticated algorithmic trading bot built with Python and the Alpaca API, featuring StochRSI and EMA indicators for signal generation.

## Features

- **Multiple Technical Indicators**: StochRSI, Stochastic Oscillator, EMA
- **Risk Management**: Stop loss, trailing stops, position sizing
- **Real-time Trading**: Live market data and order execution
- **Backtesting Engine**: Strategy validation and optimization
- **Web Dashboard**: Real-time monitoring and visualization
- **Docker Support**: Containerized deployment

## Quick Start

1. **Setup Configuration**
   ```bash
   cp .env.example .env            # Provide runtime configuration overrides
   # Configure API credentials in AUTH/authAlpaca.txt or via environment variables
   # Set trading parameters in AUTH/ConfigFile.txt
   # Add tickers in AUTH/Tickers.txt
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   # Optional: install strategy runtime extras to exercise scanner-dependent tests
   pip install -r requirements/strategy-runtime.txt
   # Or install the equivalent extras directly from the project package definition
   pip install .[strategy]
   ```

3. **Run the Bot**
   ```bash
   python main.py                 # Start trading bot
   python backend/api/app.py      # Launch Flask dashboard + API
   ```

4. **Docker Deployment**
   ```bash
   docker-compose up --build
   ```

## Key Components

- **Trading Engine**: `main.py` - Core trading logic and execution
- **Indicators**: `indicator.py` - Technical analysis calculations
- **Dashboard**: `backend/api/app.py` - Unified Flask monitoring interface
- **Risk Management**: `risk_management/` - Position sizing and stop losses
- **Backtesting**: `backtesting/` - Strategy validation tools

## Configuration

Runtime configuration is centralized to avoid drift between environments:

- **.env**: Copy from `.env.example` to declare API credentials, scanner cadence, and runtime guardrails. Scanner symbols are derived from the strategy defaults and automatically sync with the values declared in `TRADING_SERVICE_CRYPTO_SYMBOLS`.
- **AUTH/authAlpaca.txt**: Optional fallback credentials file for local development.
- **AUTH/ConfigFile.txt**: Indicator parameters, risk settings, timeframes.
- **AUTH/Tickers.txt**: Assets to monitor and trade.

## Documentation

Comprehensive documentation is available in the `/docs` directory:

- [📚 Complete Documentation](docs/README.md)
- [🚀 Quick Start Guide](docs/BMAD/guides/quick-start.md)
- [⚙️ Configuration Guide](docs/GUIDES/configuration.md)
- [📊 Strategy Documentation](docs/IMPLEMENTATION/strategies.md)

## BMAD Methodology

This project implements the BMAD (Build, Measure, Analyze, Document) methodology for systematic development:

```bash
npx claude-flow bmad cycle "feature-name"  # Complete BMAD cycle
npx claude-flow bmad build "component"     # Build phase only
```

## Support

- 📖 [Documentation](docs/README.md)
- 🐛 [Common Issues](docs/COMMON_ISSUES_AND_FIXES.md)
- 💬 Create an issue for support

---

**⚠️ Disclaimer**: This software is for educational purposes. Trading involves risk of financial loss. Always test strategies thoroughly before live trading.
