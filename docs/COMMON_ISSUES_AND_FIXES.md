# Common Issues and Fixes - Trading Dashboard

## 🐛 TradingView Lightweight Charts Error

### **Issue:**
```javascript
Uncaught TypeError: chart.addCandlestickSeries is not a function
```

### **Root Cause:**
Different versions of TradingView Lightweight Charts use different method names:
- Some versions: `addCandlestickSeries()`
- Other versions: `addCandleSeries()`

### **Solution:**
Always implement a fallback mechanism that checks for both method names:

```javascript
// Check for method availability and use the correct one
if (typeof chart.addCandlestickSeries === 'function') {
    candlestickSeries = chart.addCandlestickSeries(options);
} else if (typeof chart.addCandleSeries === 'function') {
    candlestickSeries = chart.addCandleSeries(options);
} else {
    // Fallback to line chart if neither works
    candlestickSeries = chart.addLineSeries(options);
}
```

---

## 🐛 Chrome Extension Connection Error

### **Issue:**
```
Unchecked runtime.lastError: Could not establish connection. Receiving end does not exist.
```

### **Root Cause:**
Chrome extensions trying to communicate with the page but finding no receiver. This is NOT related to our application.

### **Solution:**
Suppress these errors in the console:

```javascript
// Add this at the top of your JavaScript
(function() {
    const originalError = console.error;
    console.error = function(...args) {
        if (args[0] && typeof args[0] === 'string') {
            if (args[0].includes('chrome-extension://') || 
                args[0].includes('Could not establish connection') ||
                args[0].includes('Receiving end does not exist')) {
                return; // Suppress these errors
            }
        }
        originalError.apply(console, args);
    };
})();
```

---

## 🐛 WebSocket Connection Issues

### **Issue:**
WebSocket fails to connect or disconnects frequently

### **Solution:**
```javascript
// Implement reconnection logic
socket.on('disconnect', function() {
    console.log('WebSocket disconnected, attempting reconnect...');
    setTimeout(() => {
        socket.connect();
    }, 1000);
});

// Add connection timeout
socket.on('connect_timeout', function() {
    console.log('Connection timeout, retrying...');
});
```

---

## 🐛 Flask App Port Already in Use

### **Issue:**
```
Address already in use
Port 9765 is in use by another program
```

### **Solution:**
```bash
# Kill all Python Flask processes
pkill -f "python.*flask"

# Or find and kill specific process
lsof -ti:9765 | xargs kill -9

# Then restart
python flask_app.py
```

---

## 🐛 Epic 1 Endpoints Not Loading

### **Issue:**
Epic 1 endpoints returning 404 or not available

### **Solution:**
Epic 1 runs on a separate port (8767). Start it separately:

```bash
# Start Epic 1 service
python epic1_endpoints.py

# Access at:
# http://localhost:8767/epic1/dashboard
# http://localhost:8767/api/epic1/status
```

---

## 🐛 Missing Dependencies

### **Issue:**
```
ModuleNotFoundError: No module named 'flask_compress'
```

### **Solution:**
```bash
# Activate virtual environment first
source venv/bin/activate

# Install missing dependencies
pip install flask-compress pyjwt pandas-ta scipy scikit-learn

# Or install all requirements
pip install -r requirements.txt
```

---

## 🐛 Chart Data Not Loading

### **Issue:**
Charts show but no candlestick data appears

### **Solution:**
1. Check API endpoint is working:
```javascript
fetch('/api/v2/chart-data/AAPL')
    .then(res => res.json())
    .then(data => console.log(data));
```

2. Verify data format:
```javascript
// Data must be in this format
const chartData = data.map(item => ({
    time: Math.floor(new Date(item.timestamp).getTime() / 1000),
    open: item.open,
    high: item.high,
    low: item.low,
    close: item.close
}));
```

---

## 🐛 Logging Not Working

### **Issue:**
No logs appearing in console or files

### **Solution:**
```python
# Import enhanced logging at the top of your file
from utils.enhanced_logging_config import get_logger

# Get logger for your module
logger = get_logger(__name__)

# Use appropriate log levels
logger.info("✅ Info message")
logger.warning("⚠️ Warning message")
logger.error("❌ Error message")
```

---

## 🔧 Quick Health Check

Run this to verify everything is working:

```bash
# Check Flask app
curl http://localhost:9765/api/bot/status

# Check Epic 1
curl http://localhost:8767/api/epic1/status

# Check WebSocket (in browser console)
const socket = io('/');
socket.on('connect', () => console.log('WebSocket connected'));

# Check logs
tail -f logs/trading_bot.log
```

---

## 📝 Notes for Future Reference

1. **Always use try-catch blocks** around chart initialization
2. **Implement fallback mechanisms** for library method variations
3. **Suppress unrelated browser extension errors** to keep console clean
4. **Use the enhanced logging system** for better debugging
5. **Keep Epic 1 and main Flask app on separate ports** to avoid conflicts
6. **Check virtual environment is activated** before installing packages

---

**Last Updated:** 2025-08-18
**Committed to Memory:** Yes (stored in claude-flow memory)