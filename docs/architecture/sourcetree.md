# Project Source Tree

## Overview
This document provides a comprehensive map of the Alpaca StochRSI-EMA Trading Bot project structure. Keep this updated whenever significant structural changes occur.

## Root Directory Structure

```
Alpaca-StochRSI-EMA-Trading-Bot/
├── api/                        # API endpoints and services
├── AUTH/                       # Authentication configuration
├── backtesting/               # Backtesting engines and utilities
├── config/                    # Configuration files and settings
├── core/                      # Core trading logic and components
├── database/                  # Database files and schemas
├── docker/                    # Docker configuration and scripts
├── docs/                      # Documentation
├── education/                 # Educational resources and tutorials
├── indicators/                # Technical indicators implementation
├── logs/                      # Application logs
├── memory/                    # Memory management and caching
├── ml_models/                 # Machine learning models
├── node_modules/              # Node.js dependencies
├── scripts/                   # Utility scripts
├── services/                  # Business logic services
├── src/                       # Source code
├── strategies/                # Trading strategies
├── templates/                 # HTML templates for dashboards
├── tests/                     # Test suites
├── utils/                     # Utility functions
└── worktrees/                 # Git worktrees

## Configuration Files (Root)
- `.env` - Environment variables
- `.env.development` - Development environment settings
- `.dockerignore` - Docker ignore patterns
- `.gitignore` - Git ignore patterns
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `CLAUDE.md` - Claude AI configuration and rules
- `docker-compose.yml` - Docker compose configuration
- `docker-compose.prod.yml` - Production Docker configuration
- `Dockerfile` - Docker image definition
- `Makefile` - Build automation
- `package.json` - Node.js dependencies
- `pyproject.toml` - Python project configuration
- `pytest.ini` - Pytest configuration

## Main Application Files
- `flask_app.py` - Flask web application
- `main.py` - Main trading bot entry point
- `indicator.py` - Indicator calculations
- `config_params.py` - Configuration parameters

## Key Directories

### `/api`
- REST API endpoints
- WebSocket connections
- API documentation

### `/config`
- `config.yml` - Main configuration
- `unified_config.yml` - Unified system configuration
- `timeframe.json` - Timeframe settings

### `/strategies`
- `stoch_rsi_strategy.py` - StochRSI trading strategy
- `ma_crossover_strategy.py` - Moving average crossover
- `enhanced_stoch_rsi_strategy.py` - Enhanced StochRSI

### `/indicators`
- `stoch_rsi_enhanced.py` - Enhanced StochRSI indicator
- `volume_analysis.py` - Volume analysis tools

### `/tests`
```
tests/
├── unit/                      # Unit tests
├── integration/               # Integration tests
├── performance/               # Performance tests
├── fixtures/                  # Test fixtures
├── mocks/                     # Mock objects
└── epic1_signal_quality/      # Signal quality tests
```

### `/docs`
```
docs/
├── API/                       # API documentation
├── ARCHITECTURE/              # System design
├── DEPLOYMENT/                # Deployment guides
├── EPICS/                     # Epic documentation
├── GUIDES/                    # User guides
├── IMPLEMENTATION/            # Implementation details
├── TESTING/                   # Testing documentation
└── sourcetree.md             # This file
```

### `/templates`
- Dashboard HTML templates
- Trading interface templates
- Report templates

### `/backtesting`
- `enhanced_backtesting_engine.py` - Advanced backtesting
- Historical data processing
- Performance metrics calculation

### `/services`
- `historical_data_service.py` - Historical data fetching
- Trading services
- Data processing services

## Hidden Directories

### `/.claude-flow`
```
.claude-flow/
├── metrics/                   # Performance metrics
│   ├── performance.json
│   ├── system-metrics.json
│   └── task-metrics.json
└── cache/                     # Cache data
```

### `/.roo`
Contains various rule configurations for different modes

### `/.git`
Git version control system files

## Database
- `database/trading_data.db` - SQLite trading database
- Schema includes: trades, positions, signals, performance metrics

## Docker Setup
- `docker/init-scripts/` - Database initialization scripts
- Container configurations for development and production

## Entry Points
- `start_trading_system.py` - Start main trading system
- `start_epic1_system.py` - Start Epic1 system
- `run_enhanced_dashboard.py` - Launch dashboard
- `epic1_endpoints.py` - Epic1 API endpoints

## Maintenance
This file should be updated when:
- New directories are added
- Major files are created or moved
- Project structure changes significantly
- New modules or components are introduced

Last Updated: 2025-08-19