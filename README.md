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
   # Configure API credentials in AUTH/authAlpaca.txt
   # Set trading parameters in AUTH/ConfigFile.txt
   # Add tickers in AUTH/Tickers.txt
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Bot**
   ```bash
   python main.py                    # Start trading bot
   python run_enhanced_dashboard.py # Launch web dashboard
   ```

4. **Docker Deployment**
   ```bash
   docker-compose up --build
   ```

## Key Components

- **Trading Engine**: `main.py` - Core trading logic and execution
- **Indicators**: `indicator.py` - Technical analysis calculations
- **Dashboard**: `flask_app.py` - Web-based monitoring interface
- **Risk Management**: `risk_management/` - Position sizing and stop losses
- **Backtesting**: `backtesting/` - Strategy validation tools

## Configuration

All trading parameters are configurable through files in the `AUTH/` directory:

- **ConfigFile.txt**: Indicator parameters, risk settings, timeframes
- **authAlpaca.txt**: API credentials (paper/live trading)
- **Tickers.txt**: Assets to monitor and trade

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