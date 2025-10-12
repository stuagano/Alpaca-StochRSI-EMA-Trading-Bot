# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Alpaca StochRSI EMA Trading Bot - a cryptocurrency and stock trading bot that uses technical analysis indicators (StochRSI, EMA, Stochastic) to generate trading signals. The bot features a service-oriented architecture with unified configuration management and supports both paper and live trading through the Alpaca API.

## Common Commands

### Running the Application
- **Start the main trading bot**: `python main.py`
- **Start the NEW Flask interface**: `python backend/api/run.py` (starts on http://localhost:5001)
- **Start legacy web interface**: `python app.py` (deprecated - use new Flask app)
- **Start P&L Dashboard**: `cd frontend && npm start` (React dashboard on http://localhost:3000)
- **Install dependencies**: `pip install -r requirements.txt`

### Development Commands
- **Run POC version**: `python main_poc.py`
- **Liquidate positions**: `python liquidate_positions.py` 
- **Check positions**: `python position_manager.py`
- **Demo dashboard**: `python scripts/demo_dashboard.py`
- **Test risk alerts**: `python scripts/test_risk_alerts.py`

## Architecture Overview

### Core Components

1. **Flask Application Factory** (`backend/api/__init__.py`)
   - Modern Flask application factory pattern
   - Blueprint-based modular architecture
   - Integrated with existing trading services
   - WebSocket support via SocketIO

2. **Service Registry Pattern** (`core/service_registry.py`)
   - Centralized service management with health monitoring
   - Dependency injection for trading services
   - All services registered through `setup_core_services()`

3. **Unified Configuration System** (`config/unified_config.py`)
   - Single source of truth for all configuration
   - Environment variable overrides supported
   - Migrates from legacy JSON format to YAML
   - Nested dataclass structure with validation
   - Integrated with Flask configuration

4. **Trading Architecture**
   - `TradingBot` - Main orchestrator that coordinates data, strategy, and execution
   - `TradingExecutor` - Handles order placement and position management
   - `SignalProcessor` - Processes trading signals with volume confirmation
   - Strategies in `strategies/` directory implementing base strategy interface

5. **Flask Blueprint Structure**
   - `dashboard` - Main web interface routes
   - `api` - Core API endpoints (account, positions, signals)
   - `trading` - Trading operations (start/stop, buy/sell)
   - `pnl` - P&L tracking and analytics
   - `websocket` - Real-time WebSocket events

6. **Data Flow**
   - `DataService/DataManager` - Fetches market data
   - `Indicator` - Calculates technical indicators (StochRSI, EMA, Stochastic)
   - Strategy generates signals → SignalProcessor validates → TradingExecutor executes
   - Flask services wrap existing components for web access

### Configuration Structure

The configuration is hierarchical with these main sections:
- `trading` - Core trading parameters (stop loss, position sizing, etc.)
- `indicators` - StochRSI, Stochastic, and EMA settings
- `risk_management` - ATR-based position sizing and stop losses
- `api` - Alpaca API configuration 
- `epic1` - Advanced features (volume confirmation, multi-timeframe analysis, signal quality)
- `database` - SQLite database configuration
- `logging` - Log file and level configuration

### Strategy System

Strategies implement a common interface and are selected via configuration:
- `StochRSI Strategy` - Primary strategy using StochRSI crossovers
- `MA Crossover Strategy` - Moving average crossover strategy 
- `Crypto Scalping Strategy` - High-frequency crypto trading
- All strategies extend base classes in `strategies/base_strategy.py`

### Epic 1 Advanced Features

The codebase includes "Epic 1" enhanced features:
- **Dynamic StochRSI Bands** - Adaptive thresholds based on volatility
- **Volume Confirmation** - Validates signals with volume analysis
- **Multi-Timeframe Analysis** - Cross-timeframe signal validation
- **Signal Quality Assessment** - Scores signal reliability
- **Performance Tracking** - Monitors strategy effectiveness

## Authentication Setup

The bot requires Alpaca API credentials in `AUTH/authAlpaca.txt` as JSON:
```json
{
  "APCA-API-KEY-ID": "your_key",
  "APCA-API-SECRET-KEY": "your_secret", 
  "BASE-URL": "https://paper-api.alpaca.markets"
}
```

## Key File Locations

- **Main entry point**: `main.py`
- **Configuration**: `config/unified_config.yml` and `config/unified_config.py`
- **Strategies**: `strategies/` directory
- **Core services**: `core/service_registry.py`
- **Web interface**: `app.py` with templates in `frontend/`
- **Trading logic**: `trading_bot.py`, `trading_executor.py`, `signal_processor.py`
- **P&L Dashboard**: `frontend/src/` (React components)
- **API endpoints**: `backend/api/` (Flask/WebSocket)
- **Risk management**: `lib/risk-analyzer/`, `lib/pnl-calculator/`

## Development Notes

- The codebase has been through significant cleanup, removing microservices complexity
- Uses asyncio for concurrent operations
- Supports both paper trading (default) and live trading
- Extensive configuration validation and migration support
- Service health monitoring and graceful shutdown handling
- Epic 1 features are modular and can be enabled/disabled via configuration

## Recent Changes (Feature 001-real-time-profit)

- **Real-time P&L Dashboard**: React-based dashboard with WebSocket updates
- **Risk Management API**: RESTful endpoints for risk metrics and alerts
- **WebSocket Integration**: Socket.IO for real-time position and portfolio updates
- **Redis Caching**: Added for performance optimization of real-time data
- **New Database Tables**: position_history, risk_metrics, alerts for tracking
- **Chart Integration**: Chart.js for interactive price and P&L visualization