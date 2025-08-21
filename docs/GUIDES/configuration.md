# Configuration Guide

This guide covers how to configure the Alpaca StochRSI-EMA Trading Bot for your specific needs.

## Authentication Setup

### 1. Alpaca API Credentials

Edit `AUTH/authAlpaca.txt`:
```text
APCA-API-KEY-ID=your_api_key_here
APCA-API-SECRET-KEY=your_secret_key_here
BASE-URL=https://paper-api.alpaca.markets  # For paper trading
# BASE-URL=https://api.alpaca.markets      # For live trading
```

**Security Note**: Never commit actual API keys to version control.

### 2. Trading Parameters

Edit `AUTH/ConfigFile.txt` to customize trading behavior:

```text
# Trade Parameters
use_percentage_of_capital=true
percentage_of_capital_to_use=10
stop_loss_percentage=2.5
trailing_stop_percentage=1.5
limit_price_percentage=5.0

# Data Parameters
timeframe=15Min
start_date=2024-01-01
end_date=2024-12-31

# Indicator Parameters
stochrsi_enabled=true
stochrsi_lower_band=20
stochrsi_upper_band=80
stochrsi_k=3
stochrsi_d=3
stochrsi_rsi_length=14

stoch_enabled=true
stoch_lower_band=20
stoch_upper_band=80
stoch_k_smoothing=3
stoch_d_smoothing=3

ema_enabled=true
ema_period=20
ema_smoothing=2
```

### 3. Ticker Selection

Edit `AUTH/Tickers.txt` to specify which assets to trade:
```text
AAPL GOOGL MSFT TSLA AMZN SPY QQQ IWM
```

## Advanced Configuration

### Risk Management

The bot includes advanced risk management features:

- **Position Sizing**: Configurable percentage of capital per trade
- **Stop Loss**: Automatic loss protection
- **Trailing Stops**: Lock in profits as prices move favorably
- **Maximum Positions**: Limit concurrent open positions

### Indicator Fine-tuning

#### StochRSI Parameters
- `stochrsi_lower_band`: Buy signal threshold (default: 20)
- `stochrsi_upper_band`: Sell signal threshold (default: 80)
- `stochrsi_k`: K period for smoothing (default: 3)
- `stochrsi_d`: D period for smoothing (default: 3)
- `stochrsi_rsi_length`: RSI calculation period (default: 14)

#### EMA Parameters
- `ema_period`: Number of periods for calculation (default: 20)
- `ema_smoothing`: Smoothing factor (default: 2)

### Database Configuration

The bot uses SQLite by default. For production, configure PostgreSQL:

Edit `config/database.json`:
```json
{
  "type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "trading_bot",
  "username": "your_username",
  "password": "your_password"
}
```

### Logging Configuration

Configure logging levels in `config/logging.json`:
```json
{
  "level": "INFO",
  "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  "file_rotation": true,
  "max_file_size": "10MB",
  "backup_count": 5
}
```

## Environment Variables

The bot supports environment variable configuration:

```bash
export ALPACA_API_KEY="your_api_key"
export ALPACA_SECRET_KEY="your_secret_key"
export ALPACA_BASE_URL="https://paper-api.alpaca.markets"
export TRADING_MODE="paper"  # or "live"
export LOG_LEVEL="INFO"
```

## Docker Configuration

For Docker deployment, use environment files:

Create `.env` file:
```text
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
TRADING_MODE=paper
LOG_LEVEL=INFO
```

Update `docker-compose.yml` to use the environment file:
```yaml
services:
  trading-bot:
    env_file:
      - .env
```

## Configuration Validation

The bot includes configuration validation:

```bash
# Validate configuration
python -m utils.config_validator

# Test API connection
python -m scripts.test_auth_system
```

## Production Checklist

Before deploying to production:

1. ✅ Update API credentials for live trading
2. ✅ Set appropriate position sizing
3. ✅ Configure stop losses and risk limits
4. ✅ Test with paper trading first
5. ✅ Set up monitoring and alerts
6. ✅ Configure database backups
7. ✅ Set up log rotation
8. ✅ Test failover procedures

## Troubleshooting

### Common Configuration Issues

**Authentication Errors**:
- Verify API keys are correct
- Check base URL matches trading mode
- Ensure account has sufficient permissions

**Trading Errors**:
- Verify sufficient buying power
- Check market hours
- Confirm tickers are valid and tradeable

**Performance Issues**:
- Adjust data polling frequency
- Optimize database queries
- Consider upgrading hardware resources

For more detailed troubleshooting, see [Common Issues and Fixes](../COMMON_ISSUES_AND_FIXES.md).