# Epic 1 Deployment Guide
## Alpaca StochRSI EMA Trading Bot

**Version:** Epic 1.0.0  
**Last Updated:** 2025-08-19  
**Deployment Type:** Production Ready

---

## Overview

This guide provides step-by-step instructions for deploying Epic 1 enhancements to the Alpaca StochRSI EMA Trading Bot. Epic 1 maintains full backward compatibility while adding powerful new features for enhanced trading performance.

### What's New in Epic 1

- 🎯 **Dynamic StochRSI** - Adaptive bands based on market volatility
- 📊 **Volume Confirmation** - Real-time volume analysis and validation
- ⏱️ **Multi-timeframe Validation** - Cross-timeframe signal verification
- 🎚️ **Signal Quality Metrics** - Comprehensive signal assessment
- 🚀 **Enhanced APIs** - New endpoints for Epic 1 features
- 🔄 **Real-time Integration** - WebSocket enhancements
- ⚙️ **Unified Configuration** - Enhanced configuration management

---

## Pre-Deployment Requirements

### System Requirements

- **Python:** 3.8+ (tested with 3.9, 3.10, 3.11)
- **Memory:** Minimum 2GB RAM (4GB recommended)
- **Storage:** Additional 500MB for Epic 1 components
- **Network:** Stable internet connection for real-time data

### Dependencies

```bash
# Core dependencies (already installed for Epic 0)
pandas>=1.5.0
numpy>=1.21.0
flask>=2.0.0
flask-socketio>=5.0.0
eventlet>=0.33.0

# Epic 1 specific dependencies (auto-installed)
scipy>=1.9.0
scikit-learn>=1.1.0  # Optional for advanced features
```

### Backup Requirements

**⚠️ CRITICAL: Always backup before deployment**

```bash
# Create timestamped backup
BACKUP_DIR="backup-$(date +%Y%m%d_%H%M%S)"
cp -r /path/to/trading-bot $BACKUP_DIR
echo "Backup created at: $BACKUP_DIR"
```

---

## Deployment Options

### Option 1: Automatic Deployment (Recommended)

**For most users - minimal configuration required**

```bash
# 1. Update the repository
git pull origin main

# 2. Run Epic 1 deployment script
python scripts/deploy_epic1.py --auto

# 3. Verify deployment
python tests/test_epic1_integration.py
```

### Option 2: Manual Deployment (Advanced)

**For users who want full control over the deployment process**

#### Step 1: Environment Preparation

```bash
# Navigate to project directory
cd /path/to/Alpaca-StochRSI-EMA-Trading-Bot

# Activate virtual environment (if using)
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Verify Python version
python --version  # Should be 3.8+
```

#### Step 2: Code Update

```bash
# Backup current configuration
cp config/unified_config.py config/unified_config.py.bak

# Pull latest code
git stash  # Save any local changes
git pull origin main
git stash pop  # Restore local changes if needed
```

#### Step 3: Dependency Installation

```bash
# Update pip
pip install --upgrade pip

# Install/update dependencies
pip install -r requirements.txt

# Verify Epic 1 dependencies
python -c "import scipy, sklearn; print('Epic 1 dependencies OK')"
```

#### Step 4: Configuration Update

```bash
# Copy Epic 1 configuration template
cp config/epic1_config.yml.example config/epic1_config.yml

# Edit configuration (see Configuration Section below)
nano config/epic1_config.yml
```

#### Step 5: Database Migration (if applicable)

```bash
# Run database migrations for Epic 1 features
python scripts/migrate_database.py --epic1

# Verify database schema
python scripts/verify_database.py
```

#### Step 6: Integration Testing

```bash
# Run Epic 1 integration tests
python tests/test_epic1_integration.py

# Run full test suite
python -m pytest tests/ -v
```

#### Step 7: Service Deployment

```bash
# Stop existing service
sudo systemctl stop trading-bot  # For systemd
# or
pkill -f flask_app.py           # For manual processes

# Start with Epic 1
python flask_app.py

# Or start as service
sudo systemctl start trading-bot
```

---

## Configuration

### Epic 1 Configuration File

Create or update `config/epic1_config.yml`:

```yaml
# Epic 1 Configuration
epic1:
  # Main Epic 1 toggle
  enabled: true
  
  # Fallback behavior
  fallback_to_epic0: true
  require_epic1_consensus: false
  
  # API and WebSocket enhancements
  enable_epic1_api_endpoints: true
  enable_enhanced_websocket: true
  
  # Dynamic StochRSI Configuration
  dynamic_stochrsi:
    enabled: true
    enable_adaptive_bands: true
    volatility_window: 20
    base_volatility_window: 100
    min_lower_band: 10
    max_lower_band: 30
    min_upper_band: 70
    max_upper_band: 90
    default_lower_band: 20
    default_upper_band: 80
    band_adjustment_sensitivity: 1.0
    enable_trend_filtering: true
  
  # Volume Confirmation Configuration
  volume_confirmation:
    enabled: true
    confirmation_threshold: 1.2
    volume_ma_period: 20
    enable_relative_volume: true
    relative_volume_threshold: 1.5
    volume_trend_periods: 5
    require_volume_confirmation: true
    volume_strength_levels:
      very_low: -2.0
      low: -1.0
      normal: 0.0
      high: 1.0
      very_high: 2.0
  
  # Multi-timeframe Configuration
  multi_timeframe:
    enabled: true
    timeframes: ['15m', '1h', '1d']
    enable_real_time_validation: true
    consensus_threshold: 0.75
    enable_performance_tracking: true
    max_concurrent_validations: 10
    auto_update_interval: 60000  # milliseconds
    timeframe_weights:
      '15m': 0.3
      '1h': 0.4
      '1d': 0.3
    trend_analysis_periods:
      '15m': 20
      '1h': 20
      '1d': 20
  
  # Signal Quality Configuration
  signal_quality:
    enabled: true
    enable_quality_filtering: true
    minimum_quality_score: 0.6
    quality_weights:
      volatility: 0.25
      volume_consistency: 0.20
      data_completeness: 0.25
      signal_reliability: 0.20
      data_freshness: 0.10
    volatility_penalty_multiplier: 5.0
    max_volatility_penalty: 0.3
    volume_consistency_bonus_threshold: 0.5
    volume_bonus_multiplier: 0.1
    enable_recommendations: true
  
  # Performance Tracking Configuration
  performance:
    enabled: true
    track_signal_outcomes: true
    enable_adaptive_learning: true
    performance_window_days: 30
    min_trades_for_analysis: 10
    enable_strategy_comparison: true
    auto_parameter_optimization: false
    optimization_frequency_hours: 24
```

### Environment Variables

Epic 1 supports environment-based configuration:

```bash
# Epic 1 toggles
export EPIC1_ENABLED=true
export EPIC1_FALLBACK_TO_EPIC0=true

# Component toggles
export EPIC1_DYNAMIC_STOCHRSI_ENABLED=true
export EPIC1_VOLUME_CONFIRMATION_ENABLED=true
export EPIC1_MULTI_TIMEFRAME_ENABLED=true
export EPIC1_SIGNAL_QUALITY_ENABLED=true

# Performance tuning
export EPIC1_VOLUME_CONFIRMATION_THRESHOLD=1.2
export EPIC1_MULTI_TIMEFRAME_CONSENSUS=0.75
export EPIC1_SIGNAL_QUALITY_MIN_SCORE=0.6

# API and WebSocket
export EPIC1_API_ENDPOINTS_ENABLED=true
export EPIC1_WEBSOCKET_ENHANCED=true
```

### Legacy Configuration Migration

Epic 1 automatically migrates existing Epic 0 configurations:

```python
# Automatic migration on startup
from config.unified_config import UnifiedConfigManager

config_manager = UnifiedConfigManager()
config = config_manager.load_config()  # Handles migration

# Manual migration (if needed)
python scripts/migrate_config.py --from-epic0 --to-epic1
```

---

## Service Integration

### Systemd Service (Linux)

Create `/etc/systemd/system/trading-bot-epic1.service`:

```ini
[Unit]
Description=Alpaca Trading Bot with Epic 1
After=network.target

[Service]
Type=simple
User=trading
WorkingDirectory=/home/trading/Alpaca-StochRSI-EMA-Trading-Bot
Environment=EPIC1_ENABLED=true
Environment=FLASK_ENV=production
ExecStart=/home/trading/venv/bin/python flask_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable trading-bot-epic1
sudo systemctl start trading-bot-epic1

# Check status
sudo systemctl status trading-bot-epic1
```

### Docker Deployment

Create `Dockerfile.epic1`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Epic 1 environment variables
ENV EPIC1_ENABLED=true
ENV EPIC1_FALLBACK_TO_EPIC0=true
ENV FLASK_ENV=production

# Expose port
EXPOSE 9765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:9765/api/epic1/status || exit 1

# Start application
CMD ["python", "flask_app.py"]
```

```bash
# Build and run
docker build -f Dockerfile.epic1 -t trading-bot-epic1 .
docker run -d -p 9765:9765 --name trading-bot-epic1 trading-bot-epic1

# Check logs
docker logs trading-bot-epic1
```

### Docker Compose

Create `docker-compose.epic1.yml`:

```yaml
version: '3.8'

services:
  trading-bot:
    build:
      context: .
      dockerfile: Dockerfile.epic1
    ports:
      - "9765:9765"
    environment:
      - EPIC1_ENABLED=true
      - EPIC1_FALLBACK_TO_EPIC0=true
      - FLASK_ENV=production
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./database:/app/database
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9765/api/epic1/status"]
      interval: 30s
      timeout: 10s
      retries: 3
```

```bash
# Deploy with docker-compose
docker-compose -f docker-compose.epic1.yml up -d

# Check status
docker-compose -f docker-compose.epic1.yml ps
```

---

## Post-Deployment Verification

### Health Checks

#### 1. Epic 1 Status Check

```bash
# Check Epic 1 availability
curl http://localhost:9765/api/epic1/status

# Expected response:
{
  "success": true,
  "epic1_status": {
    "epic1_available": true,
    "components_initialized": true,
    "components": {
      "multi_timeframe_validator": true,
      "volume_confirmation_system": true,
      "enhanced_signal_integration": true
    }
  }
}
```

#### 2. Enhanced Signal Verification

```bash
# Test enhanced signal endpoint
curl "http://localhost:9765/api/epic1/enhanced-signal/AAPL?timeframe=1Min&limit=50"

# Expected: Enhanced signal data with Epic 1 features
```

#### 3. Volume Dashboard Data

```bash
# Test volume confirmation
curl "http://localhost:9765/api/epic1/volume-dashboard-data?symbol=AAPL"

# Expected: Volume analysis with confirmation status
```

#### 4. Multi-timeframe Analysis

```bash
# Test multi-timeframe endpoint
curl "http://localhost:9765/api/epic1/multi-timeframe/AAPL?timeframes=15m,1h,1d"

# Expected: Cross-timeframe analysis data
```

### WebSocket Testing

```javascript
// Connect to WebSocket
const socket = io('http://localhost:9765');

// Test Epic 1 subscription
socket.emit('epic1_subscribe', {
  symbols: ['AAPL', 'MSFT'],
  features: ['dynamic_stochrsi', 'volume_confirmation', 'multi_timeframe']
});

// Listen for confirmation
socket.on('epic1_subscription_confirmed', (data) => {
  console.log('Epic 1 subscription confirmed:', data);
});

// Test signal request
socket.emit('epic1_get_signal', {
  symbol: 'AAPL',
  timeframe: '1Min'
});

// Listen for signal updates
socket.on('epic1_signal_update', (data) => {
  console.log('Epic 1 signal received:', data);
});
```

### Performance Verification

```bash
# Run performance benchmarks
python scripts/benchmark_epic1.py

# Expected output:
# Epic 1 Performance Benchmark Results:
# - Enhanced signal calculation: 52ms avg
# - Volume confirmation: 8ms avg
# - Multi-timeframe analysis: 124ms avg
# - Signal quality assessment: 15ms avg
# - Overall performance improvement: 300% features, 15% time increase
```

### Integration Testing

```bash
# Run comprehensive integration tests
python tests/test_epic1_integration.py

# Expected output:
# EPIC 1 INTEGRATION VALIDATION SUMMARY
# ============================================================
# Total Tests: 24
# Passed: 22
# Failed: 0
# Errors: 0
# Skipped: 2
# ============================================================
# ✅ All Epic 1 integration tests passed!
```

---

## Troubleshooting

### Common Issues

#### 1. Epic 1 Components Not Available

**Symptom:** API returns "Epic 1 components not available"

**Solution:**
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Verify Epic 1 modules
python -c "from src.utils.epic1_integration_helpers import get_epic1_status; print('OK')"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 2. Configuration Errors

**Symptom:** Config validation failures

**Solution:**
```bash
# Validate configuration
python scripts/validate_config.py --epic1

# Reset to defaults
cp config/epic1_config.yml.example config/epic1_config.yml

# Check environment variables
env | grep EPIC1
```

#### 3. Performance Issues

**Symptom:** Slow response times

**Solution:**
```bash
# Check system resources
top | grep python

# Reduce Epic 1 features temporarily
export EPIC1_MULTI_TIMEFRAME_ENABLED=false
export EPIC1_SIGNAL_QUALITY_ENABLED=false

# Restart service
sudo systemctl restart trading-bot-epic1
```

#### 4. WebSocket Connection Issues

**Symptom:** Epic 1 WebSocket events not working

**Solution:**
```bash
# Check WebSocket configuration
curl http://localhost:9765/socket.io/

# Verify Epic 1 WebSocket enablement
grep "enable_enhanced_websocket" config/epic1_config.yml

# Test with simple WebSocket client
python scripts/test_websocket.py
```

### Debugging Tools

#### 1. Epic 1 Debug Mode

```bash
# Enable debug logging
export EPIC1_DEBUG=true
export FLASK_ENV=development

# Restart application
python flask_app.py
```

#### 2. Component Status Check

```python
# Check individual component status
from src.utils.epic1_integration_helpers import get_epic1_status

status = get_epic1_status()
print(json.dumps(status, indent=2))
```

#### 3. Performance Profiling

```bash
# Profile Epic 1 performance
python scripts/profile_epic1.py --symbol AAPL --duration 60

# Generate performance report
python scripts/generate_performance_report.py
```

### Log Analysis

Epic 1 logs are integrated with the main application logs:

```bash
# View Epic 1 specific logs
grep "epic1" logs/trading_bot.log

# Real-time log monitoring
tail -f logs/trading_bot.log | grep -E "(epic1|Epic 1)"

# Check for errors
grep -E "(ERROR|CRITICAL)" logs/trading_bot.log | grep epic1
```

---

## Rollback Procedures

### Emergency Rollback

If Epic 1 deployment causes issues:

#### 1. Quick Disable

```bash
# Disable Epic 1 without code changes
export EPIC1_ENABLED=false
sudo systemctl restart trading-bot-epic1
```

#### 2. Configuration Rollback

```bash
# Restore previous configuration
cp config/unified_config.py.bak config/unified_config.py
sudo systemctl restart trading-bot-epic1
```

#### 3. Full Code Rollback

```bash
# Stop service
sudo systemctl stop trading-bot-epic1

# Restore from backup
rm -rf /path/to/trading-bot
cp -r /path/to/backup-YYYYMMDD_HHMMSS /path/to/trading-bot

# Restart service
sudo systemctl start trading-bot
```

### Verification After Rollback

```bash
# Verify Epic 0 functionality
curl http://localhost:9765/api/indicators/AAPL
curl http://localhost:9765/api/tickers

# Check system status
curl http://localhost:9765/api/performance/system
```

---

## Performance Optimization

### Epic 1 Tuning

#### 1. Component-Specific Tuning

```yaml
# Optimize for performance over features
epic1:
  multi_timeframe:
    max_concurrent_validations: 5  # Reduce from 10
    auto_update_interval: 120000   # Increase from 60000
  
  signal_quality:
    enable_quality_filtering: false  # Disable if not needed
  
  performance:
    enable_adaptive_learning: false  # Disable for production
```

#### 2. Caching Configuration

```yaml
# Enhanced caching for Epic 1
caching:
  epic1_signal_cache_ttl: 30      # Cache signals for 30 seconds
  volume_analysis_cache_ttl: 60   # Cache volume data for 1 minute
  timeframe_data_cache_ttl: 300   # Cache timeframe data for 5 minutes
```

#### 3. Resource Limits

```bash
# Set resource limits
export EPIC1_MAX_MEMORY_MB=512
export EPIC1_MAX_CPU_PERCENT=50
export EPIC1_MAX_CONCURRENT_REQUESTS=20
```

### Monitoring Performance

```bash
# Monitor Epic 1 performance
python scripts/monitor_epic1_performance.py --duration 3600

# Generate optimization recommendations
python scripts/optimize_epic1_config.py --auto-tune
```

---

## Security Considerations

### Epic 1 Security Configuration

```yaml
# Security settings for Epic 1
security:
  epic1:
    enable_input_validation: true
    rate_limit_enhanced_endpoints: true
    max_requests_per_minute: 60
    enable_api_key_validation: true
    log_security_events: true
```

### Network Security

```bash
# Configure firewall for Epic 1 endpoints
sudo ufw allow 9765/tcp  # Main application port

# If using additional ports for Epic 1 features
sudo ufw allow 8766/tcp  # WebSocket enhancements (if separate)
```

### Data Protection

```yaml
# Data protection for Epic 1
data_protection:
  encrypt_epic1_cache: true
  anonymize_signal_logs: true
  secure_volume_data: true
  protect_timeframe_analysis: true
```

---

## Maintenance

### Regular Maintenance Tasks

#### Daily

```bash
# Check Epic 1 health
curl http://localhost:9765/api/epic1/status

# Review performance logs
python scripts/daily_epic1_report.py
```

#### Weekly

```bash
# Update Epic 1 performance baselines
python scripts/update_performance_baselines.py

# Cleanup Epic 1 caches
python scripts/cleanup_epic1_caches.py
```

#### Monthly

```bash
# Epic 1 performance optimization
python scripts/optimize_epic1_monthly.py

# Update Epic 1 configuration based on performance
python scripts/auto_tune_epic1_config.py
```

### Updates and Upgrades

```bash
# Check for Epic 1 updates
git fetch origin
git log HEAD..origin/main --oneline | grep -i epic1

# Apply Epic 1 updates
git pull origin main
pip install -r requirements.txt --upgrade
python tests/test_epic1_integration.py
sudo systemctl restart trading-bot-epic1
```

---

## Support and Documentation

### Getting Help

1. **Documentation:** Check `/docs/` directory for detailed documentation
2. **Log Analysis:** Review logs in `/logs/trading_bot.log`
3. **Health Checks:** Use `/api/epic1/status` endpoint
4. **Integration Tests:** Run `python tests/test_epic1_integration.py`

### Reporting Issues

When reporting Epic 1 issues, include:

```bash
# Collect diagnostic information
python scripts/collect_epic1_diagnostics.py > epic1_diagnostics.txt

# Include in issue report:
# - epic1_diagnostics.txt
# - Relevant log excerpts
# - Configuration files (sanitized)
# - Steps to reproduce
```

### Additional Resources

- **API Documentation:** `/docs/api/epic1/`
- **Configuration Reference:** `/docs/configuration/epic1.md`
- **Performance Tuning:** `/docs/performance/epic1_optimization.md`
- **Troubleshooting Guide:** `/docs/troubleshooting/epic1.md`

---

## Conclusion

Epic 1 deployment is now complete! The system provides:

- ✅ **Enhanced Trading Capabilities** with dynamic adaptations
- ✅ **Full Backward Compatibility** with existing Epic 0 features
- ✅ **Real-time Analytics** through WebSocket integration
- ✅ **Comprehensive APIs** for external integrations
- ✅ **Performance Optimization** with intelligent caching
- ✅ **Production-Ready Deployment** with monitoring and security

### Next Steps

1. **Monitor Performance:** Use built-in monitoring tools
2. **Optimize Configuration:** Tune parameters based on your trading needs
3. **Explore Features:** Experiment with Epic 1 enhancements
4. **Scale as Needed:** Add more symbols and timeframes
5. **Plan for Epic 2:** Prepare for future enhancements

---

**🚀 Epic 1 Deployment Complete - Happy Trading!**

*For additional support, refer to the comprehensive documentation in the `/docs` directory or check the integration status at `/api/epic1/status`.*