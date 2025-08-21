# Enhanced TradingView Lightweight Charts Implementation

## 🎯 Overview

This implementation provides a fully functional TradingView Lightweight Charts integration for the Alpaca StochRSI-EMA trading bot with real-time data updates, advanced indicators, and signal visualization.

## ✨ Features

### 📊 Chart Components
- **Main Price Chart**: Real-time candlestick chart with EMA overlay
- **StochRSI Oscillator**: Dedicated indicator chart with %K and %D lines
- **Volume Chart**: Volume bars with color-coded price movement
- **Signal Markers**: Buy/sell signals displayed directly on price chart

### 🎨 Visual Enhancements
- **Dark Theme**: GitHub-inspired dark theme optimized for trading
- **Real-time Updates**: Live WebSocket data streaming
- **Interactive Controls**: Symbol selection and timeframe switching
- **Loading States**: Visual feedback during data loading
- **Responsive Design**: Auto-resizing charts

### 🔧 Technical Features
- **Proper Data Formatting**: Correct timestamp handling for TradingView
- **StochRSI Implementation**: Enhanced StochRSI calculation with proper signals
- **Performance Optimization**: Efficient real-time updates without freezing
- **Error Handling**: Robust error handling and recovery
- **WebSocket Integration**: Seamless real-time data flow

## 🚀 Quick Start

### 1. Run the Enhanced Dashboard
```bash
python run_enhanced_dashboard.py
```

### 2. Access the Dashboards
- **Main Dashboard**: http://localhost:9765/
- **Enhanced Dashboard**: http://localhost:9765/enhanced
- **Test Charts**: http://localhost:9765/test_enhanced

### 3. Test the Charts
1. Open the enhanced dashboard
2. Select different symbols (SPY, AAPL, TSLA, etc.)
3. Switch timeframes (1m, 5m, 15m, 1h, 1D)
4. Watch for real-time signal markers

## 📁 File Structure

```
enhanced_charts/
├── templates/
│   └── enhanced_trading_dashboard.html    # Main enhanced dashboard
├── indicators/
│   └── stoch_rsi_enhanced.py             # Enhanced StochRSI implementation
├── api/
│   ├── __init__.py
│   └── enhanced_chart_routes.py          # Enhanced API endpoints
├── test_enhanced_charts.html             # Test page for chart functionality
├── run_enhanced_dashboard.py             # Launcher script
└── docs/
    └── ENHANCED_CHARTS_README.md         # This file
```

## 🔌 API Endpoints

### Enhanced Chart Data
- `GET /api/v2/chart/<symbol>` - Complete chart data with indicators
- `GET /api/v2/indicators/<symbol>` - Real-time indicator updates
- `GET /api/v2/realtime/<symbol>` - Real-time price updates
- `GET /api/v2/signals/<symbol>` - Trading signal analysis

### Original Endpoints (Still Available)
- `GET /api/chart/<symbol>` - Basic chart data
- `GET /api/chart_indicators/<symbol>` - Indicator series data
- `GET /api/latest_bar/<symbol>` - Latest price bar

## 🎯 StochRSI Implementation

### Parameters
- **RSI Length**: 14 (configurable)
- **Stoch Length**: 14 (configurable)
- **%K Smoothing**: 3 (configurable)
- **%D Smoothing**: 3 (configurable)

### Signal Logic
- **Buy Signal**: %K crosses above %D in oversold region (< 20)
- **Sell Signal**: %K crosses below %D in overbought region (> 80)
- **Signal Strength**: Based on distance from thresholds

### Visual Indicators
- **Green Arrow Up**: Buy signal marker
- **Red Arrow Down**: Sell signal marker
- **Orange Line**: %K values
- **Purple Line**: %D values
- **Reference Lines**: Overbought (80) and Oversold (20) levels

## 🔧 Configuration

### Chart Settings
```javascript
// Chart dimensions and styling
const chartConfig = {
    width: 'auto',
    height: 450,
    theme: 'dark',
    colors: {
        up: '#26a641',
        down: '#f85149',
        ema: '#1f6feb',
        stochK: '#f59e0b',
        stochD: '#8b5cf6'
    }
};
```

### Indicator Parameters
```python
# StochRSI configuration
stoch_rsi_config = {
    'rsi_length': 14,
    'stoch_length': 14,
    'K': 3,
    'D': 3,
    'oversold_threshold': 20,
    'overbought_threshold': 80
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Charts Not Loading**
   - Check browser console for JavaScript errors
   - Verify WebSocket connection is established
   - Ensure data manager is properly initialized

2. **No Real-time Updates**
   - Check WebSocket connection status
   - Verify streaming is started (green dot in header)
   - Check browser network tab for failed requests

3. **StochRSI Not Displaying**
   - Ensure minimum data points available (needs 14+ candles)
   - Check indicator calculation logs
   - Verify data format in browser console

4. **Signal Markers Missing**
   - Check if StochRSI data is available
   - Verify signal generation logic
   - Look for JavaScript errors in console

### Debug Mode
Enable debug logging:
```python
import logging
logging.getLogger('enhanced_charts').setLevel(logging.DEBUG)
```

### Browser Console
Check browser console for detailed error messages and data flow:
```javascript
// Enable debug logging in browser
localStorage.setItem('debug', 'enhanced_charts:*');
```

## 🔄 Real-time Data Flow

1. **WebSocket Connection**: Client connects to Flask-SocketIO
2. **Data Request**: Client requests streaming for specific symbols
3. **Server Processing**: 
   - Fetches latest price data
   - Calculates indicators (StochRSI, EMA)
   - Formats data for TradingView charts
4. **Data Transmission**: Server sends formatted data via WebSocket
5. **Chart Updates**: Client updates charts with new data
6. **Signal Detection**: New signals generate markers on chart

## 📈 Performance Optimizations

- **Efficient Data Structures**: Optimized pandas operations
- **Caching**: Response caching for frequently requested data
- **WebSocket Compression**: Compressed data transmission
- **Incremental Updates**: Only send changed data
- **Memory Management**: Proper cleanup of old data

## 🛠 Development

### Adding New Indicators
1. Create indicator class in `indicators/` directory
2. Implement calculation methods
3. Add formatting for TradingView charts
4. Update API endpoints
5. Add to dashboard JavaScript

### Customizing Charts
- Modify chart configuration in dashboard HTML
- Update color schemes in CSS variables
- Add new chart types or overlays
- Implement custom drawing tools

## 📊 Testing

### Manual Testing
1. Run test charts: http://localhost:9765/test_enhanced
2. Try different symbols and timeframes
3. Check real-time updates
4. Verify signal generation

### Automated Testing
```bash
# Test indicator calculations
python -m pytest tests/test_stoch_rsi_enhanced.py

# Test API endpoints
python -m pytest tests/test_enhanced_chart_routes.py
```

## 🤝 Contributing

1. Follow existing code style and patterns
2. Add proper error handling and logging
3. Include unit tests for new features
4. Update documentation for changes
5. Test thoroughly with real market data

## 📝 License

This implementation is part of the Alpaca StochRSI-EMA Trading Bot project.