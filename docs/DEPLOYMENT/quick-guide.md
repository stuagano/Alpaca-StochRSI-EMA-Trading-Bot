# Deployment Quick Guide

Fast deployment guide for the Alpaca StochRSI-EMA Trading Bot.

## Prerequisites

- Python 3.8+
- Docker (optional)
- Alpaca API account
- 2GB RAM minimum
- 10GB disk space

## Quick Start (5 minutes)

### 1. Clone and Setup
```bash
git clone https://github.com/stuagano/Alpaca-StochRSI-EMA-Trading-Bot.git
cd Alpaca-StochRSI-EMA-Trading-Bot
pip install -r requirements.txt
```

### 2. Configure API
```bash
# Edit AUTH/authAlpaca.txt
echo "APCA-API-KEY-ID=your_key_here" > AUTH/authAlpaca.txt
echo "APCA-API-SECRET-KEY=your_secret_here" >> AUTH/authAlpaca.txt
echo "BASE-URL=https://paper-api.alpaca.markets" >> AUTH/authAlpaca.txt
```

### 3. Start Trading
```bash
python main.py                    # Start bot
python run_enhanced_dashboard.py # Launch dashboard (separate terminal)
```

## Docker Deployment (Recommended)

### Quick Deploy
```bash
docker-compose up -d
```

### Custom Configuration
```bash
# Create environment file
cp .env.example .env
# Edit .env with your settings
docker-compose --env-file .env up -d
```

## Cloud Deployment

### AWS EC2
```bash
# Launch t3.small instance
# Install Docker
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Deploy bot
git clone https://github.com/stuagano/Alpaca-StochRSI-EMA-Trading-Bot.git
cd Alpaca-StochRSI-EMA-Trading-Bot
docker-compose up -d
```

### Digital Ocean Droplet
```bash
# Create $20/month droplet
# Use Docker marketplace image
git clone https://github.com/stuagano/Alpaca-StochRSI-EMA-Trading-Bot.git
cd Alpaca-StochRSI-EMA-Trading-Bot
docker-compose up -d
```

## Production Configuration

### 1. Security
```bash
# Use environment variables for secrets
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"

# Setup SSL for dashboard
# Configure firewall
```

### 2. Monitoring
```bash
# Setup health checks
docker-compose -f docker-compose.prod.yml up -d

# Configure alerts
# Setup log aggregation
```

### 3. Backup
```bash
# Database backup
docker exec trading_db pg_dump trading > backup.sql

# Configuration backup
tar -czf config_backup.tar.gz AUTH/ config/
```

## Quick Validation

```bash
# Test API connection
python scripts/test_auth_system.py

# Validate configuration
python -m utils.config_validator

# Run quick test
python tests/test_quick_validation.py
```

## Common Deployment Issues

| Issue | Solution |
|-------|----------|
| API Authentication Failed | Verify keys in AUTH/authAlpaca.txt |
| Port 5000 in use | Change port in docker-compose.yml |
| Insufficient memory | Upgrade to minimum 2GB RAM |
| Database connection error | Check PostgreSQL service status |

## Next Steps

1. **Monitor Performance**: Check dashboard at http://localhost:5000
2. **Review Logs**: `docker logs trading_bot`
3. **Customize Settings**: Edit AUTH/ConfigFile.txt
4. **Scale Up**: Add more tickers or increase capital allocation

## Support

- 📖 [Complete Documentation](../README.md)
- 🔧 [Configuration Guide](../GUIDES/configuration.md)
- 🐛 [Troubleshooting](../COMMON_ISSUES_AND_FIXES.md)
- 💬 [GitHub Issues](https://github.com/stuagano/Alpaca-StochRSI-EMA-Trading-Bot/issues)

---

**⚡ Pro Tip**: Start with paper trading and small position sizes until you're comfortable with the bot's behavior.