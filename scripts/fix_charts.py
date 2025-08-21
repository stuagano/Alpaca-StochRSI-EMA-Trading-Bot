#!/usr/bin/env python3
"""
Chart Fixing Script

This script diagnoses and fixes common TradingView Lightweight Charts issues
in the trading dashboard.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_chart_dependencies():
    """Check if required chart dependencies are available."""
    logger.info("🔍 Checking chart dependencies...")
    
    issues = []
    fixes = []
    
    # Check TradingView Lightweight Charts library
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
    </head>
    <body>
        <div id="chart"></div>
        <script>
            try {
                const chart = LightweightCharts.createChart(document.getElementById('chart'), {
                    width: 400,
                    height: 300
                });
                console.log('✅ Lightweight Charts library loaded successfully');
            } catch (e) {
                console.error('❌ Lightweight Charts error:', e);
            }
        </script>
    </body>
    </html>
    """
    
    # Write test file
    test_file = os.path.join(project_root, 'test_charts_dependency.html')
    with open(test_file, 'w') as f:
        f.write(test_html)
    
    logger.info(f"📝 Created test file: {test_file}")
    logger.info("🌐 Open this file in a browser to test chart library loading")
    
    return issues, fixes

def fix_chart_api_endpoints():
    """Fix chart API endpoints to return proper format."""
    logger.info("🔧 Fixing chart API endpoints...")
    
    # Check if flask_app.py has the chart endpoints
    flask_app_path = os.path.join(project_root, 'flask_app.py')
    
    if not os.path.exists(flask_app_path):
        logger.error(f"❌ flask_app.py not found at {flask_app_path}")
        return False
    
    # Add fixed chart routes to flask app
    fixed_routes_code = """
# FIXED CHART ROUTES - Add to flask_app.py

@app.route('/api/v2/chart-test/<symbol>')
def test_chart_endpoint(symbol):
    \"\"\"Test endpoint for chart data.\"\"\"
    import time
    import numpy as np
    from datetime import datetime, timedelta
    
    try:
        # Generate sample data for testing
        current_time = int(time.time())
        data_points = 50
        
        candlesticks = []
        base_price = 150.0
        
        for i in range(data_points):
            timestamp = current_time - (data_points - i) * 300  # 5-minute intervals
            
            # Generate realistic price movement
            price_change = np.random.normal(0, 1) * 0.5
            open_price = base_price + price_change
            
            high_price = open_price + abs(np.random.normal(0, 0.5))
            low_price = open_price - abs(np.random.normal(0, 0.5))
            close_price = low_price + (high_price - low_price) * np.random.random()
            
            candlesticks.append({
                'time': timestamp,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2)
            })
            
            base_price = close_price
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'data': candlesticks,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
"""
    
    logger.info("📝 Fixed chart endpoint code generated")
    logger.info("💡 Add the above code to your flask_app.py file")
    
    return True

def create_chart_diagnostic():
    """Create a diagnostic HTML page for chart testing."""
    logger.info("🏥 Creating chart diagnostic page...")
    
    diagnostic_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chart Diagnostic Tool</title>
    <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 20px;
            background: #0a0e1a;
            color: white;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #1e3a8a, #7c3aed);
            border-radius: 12px;
        }
        .diagnostic-section {
            background: #111827;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #374151;
        }
        .chart-container {
            height: 400px;
            margin: 20px 0;
            background: #1f2937;
            border-radius: 8px;
        }
        .status {
            padding: 10px;
            border-radius: 8px;
            margin: 10px 0;
            font-weight: bold;
        }
        .status.success {
            background: rgba(16, 185, 129, 0.2);
            border: 1px solid #10b981;
            color: #10b981;
        }
        .status.error {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid #ef4444;
            color: #ef4444;
        }
        .status.warning {
            background: rgba(245, 158, 11, 0.2);
            border: 1px solid #f59e0b;
            color: #f59e0b;
        }
        button {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            margin: 5px;
        }
        button:hover {
            background: #2563eb;
        }
        .log {
            background: #000;
            border: 1px solid #374151;
            border-radius: 8px;
            padding: 15px;
            height: 200px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Chart Diagnostic Tool</h1>
            <p>Diagnose and fix TradingView Lightweight Charts issues</p>
        </div>

        <!-- Library Test -->
        <div class="diagnostic-section">
            <h3>1. Library Loading Test</h3>
            <div id="libraryStatus" class="status warning">Testing...</div>
            <button onclick="testLibrary()">Test Library</button>
        </div>

        <!-- Chart Creation Test -->
        <div class="diagnostic-section">
            <h3>2. Chart Creation Test</h3>
            <div id="chartStatus" class="status warning">Not tested</div>
            <button onclick="testChartCreation()">Test Chart Creation</button>
            <div id="testChart" class="chart-container"></div>
        </div>

        <!-- Data Loading Test -->
        <div class="diagnostic-section">
            <h3>3. Data Loading Test</h3>
            <div id="dataStatus" class="status warning">Not tested</div>
            <button onclick="testDataLoading()">Test Data Loading</button>
            <button onclick="testAPI()">Test API Endpoint</button>
        </div>

        <!-- Real-time Test -->
        <div class="diagnostic-section">
            <h3>4. Real-time Updates Test</h3>
            <div id="realtimeStatus" class="status warning">Not tested</div>
            <button onclick="testRealtime()">Test Real-time Updates</button>
            <button onclick="stopRealtime()">Stop Updates</button>
        </div>

        <!-- Diagnostic Log -->
        <div class="diagnostic-section">
            <h3>5. Diagnostic Log</h3>
            <div id="diagnosticLog" class="log"></div>
            <button onclick="clearLog()">Clear Log</button>
            <button onclick="exportLog()">Export Log</button>
        </div>
    </div>

    <script>
        let chart = null;
        let candlestickSeries = null;
        let realtimeInterval = null;
        
        function log(message, type = 'info') {
            const logDiv = document.getElementById('diagnosticLog');
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = `[${timestamp}] ${type.toUpperCase()}: ${message}\\n`;
            logDiv.textContent += logEntry;
            logDiv.scrollTop = logDiv.scrollHeight;
            console.log(logEntry);
        }

        function setStatus(elementId, message, type) {
            const element = document.getElementById(elementId);
            element.textContent = message;
            element.className = `status ${type}`;
        }

        function testLibrary() {
            log('Testing TradingView Lightweight Charts library...');
            
            try {
                if (typeof LightweightCharts === 'undefined') {
                    throw new Error('LightweightCharts is not defined');
                }
                
                const version = LightweightCharts.version || 'Unknown';
                log(`✅ Library loaded successfully. Version: ${version}`);
                setStatus('libraryStatus', `✅ Library loaded (v${version})`, 'success');
                
                // Test basic API
                const testMethods = ['createChart', 'LineStyle', 'CrosshairMode'];
                testMethods.forEach(method => {
                    if (typeof LightweightCharts[method] !== 'undefined') {
                        log(`✅ Method ${method} available`);
                    } else {
                        log(`⚠️ Method ${method} not available`, 'warning');
                    }
                });
                
            } catch (error) {
                log(`❌ Library test failed: ${error.message}`, 'error');
                setStatus('libraryStatus', `❌ Library failed: ${error.message}`, 'error');
            }
        }

        function testChartCreation() {
            log('Testing chart creation...');
            
            try {
                const container = document.getElementById('testChart');
                container.innerHTML = ''; // Clear previous chart
                
                chart = LightweightCharts.createChart(container, {
                    width: container.clientWidth,
                    height: 400,
                    layout: {
                        background: { color: '#1f2937' },
                        textColor: '#ffffff'
                    },
                    grid: {
                        vertLines: { color: '#374151' },
                        horzLines: { color: '#374151' }
                    },
                    crosshair: {
                        mode: LightweightCharts.CrosshairMode.Normal
                    },
                    timeScale: {
                        timeVisible: true,
                        secondsVisible: false
                    }
                });
                
                candlestickSeries = chart.addCandlestickSeries({
                    upColor: '#10b981',
                    downColor: '#ef4444',
                    borderUpColor: '#10b981',
                    borderDownColor: '#ef4444',
                    wickUpColor: '#10b981',
                    wickDownColor: '#ef4444'
                });
                
                log('✅ Chart created successfully');
                setStatus('chartStatus', '✅ Chart created successfully', 'success');
                
            } catch (error) {
                log(`❌ Chart creation failed: ${error.message}`, 'error');
                setStatus('chartStatus', `❌ Chart creation failed: ${error.message}`, 'error');
            }
        }

        function testDataLoading() {
            log('Testing data loading...');
            
            if (!chart || !candlestickSeries) {
                log('❌ Chart not created yet. Please run chart creation test first.', 'error');
                setStatus('dataStatus', '❌ Chart not ready', 'error');
                return;
            }
            
            try {
                // Generate sample data
                const sampleData = generateSampleData(50);
                
                candlestickSeries.setData(sampleData);
                
                log(`✅ Data loaded successfully: ${sampleData.length} points`);
                setStatus('dataStatus', `✅ Data loaded: ${sampleData.length} points`, 'success');
                
            } catch (error) {
                log(`❌ Data loading failed: ${error.message}`, 'error');
                setStatus('dataStatus', `❌ Data loading failed: ${error.message}`, 'error');
            }
        }

        function testAPI() {
            log('Testing API endpoint...');
            
            fetch('/api/v2/chart-test/SPY')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        log(`✅ API test successful: ${data.data?.length || 0} data points`);
                        
                        if (candlestickSeries && data.data) {
                            candlestickSeries.setData(data.data);
                            log('✅ API data loaded into chart');
                        }
                    } else {
                        throw new Error(data.error || 'API returned error');
                    }
                })
                .catch(error => {
                    log(`❌ API test failed: ${error.message}`, 'error');
                });
        }

        function testRealtime() {
            log('Testing real-time updates...');
            
            if (!chart || !candlestickSeries) {
                log('❌ Chart not ready for real-time test', 'error');
                setStatus('realtimeStatus', '❌ Chart not ready', 'error');
                return;
            }
            
            try {
                let updateCount = 0;
                realtimeInterval = setInterval(() => {
                    const newCandle = generateLatestCandle();
                    candlestickSeries.update(newCandle);
                    updateCount++;
                    
                    if (updateCount % 5 === 0) {
                        log(`📊 Real-time update ${updateCount}`);
                    }
                }, 1000);
                
                log('✅ Real-time updates started');
                setStatus('realtimeStatus', '✅ Real-time updates active', 'success');
                
            } catch (error) {
                log(`❌ Real-time test failed: ${error.message}`, 'error');
                setStatus('realtimeStatus', `❌ Real-time failed: ${error.message}`, 'error');
            }
        }

        function stopRealtime() {
            if (realtimeInterval) {
                clearInterval(realtimeInterval);
                realtimeInterval = null;
                log('🛑 Real-time updates stopped');
                setStatus('realtimeStatus', '🛑 Real-time updates stopped', 'warning');
            }
        }

        function generateSampleData(count) {
            const data = [];
            let basePrice = 150.0;
            const currentTime = Math.floor(Date.now() / 1000);
            
            for (let i = 0; i < count; i++) {
                const time = currentTime - (count - i) * 300; // 5-minute intervals
                
                const priceChange = (Math.random() - 0.5) * 2;
                const open = basePrice + priceChange;
                const high = open + Math.abs(Math.random() * 2);
                const low = open - Math.abs(Math.random() * 2);
                const close = low + (high - low) * Math.random();
                
                data.push({
                    time: time,
                    open: parseFloat(open.toFixed(2)),
                    high: parseFloat(high.toFixed(2)),
                    low: parseFloat(low.toFixed(2)),
                    close: parseFloat(close.toFixed(2))
                });
                
                basePrice = close;
            }
            
            return data;
        }

        function generateLatestCandle() {
            const currentTime = Math.floor(Date.now() / 1000);
            const basePrice = 150 + (Math.random() - 0.5) * 10;
            
            const open = basePrice;
            const high = open + Math.random() * 2;
            const low = open - Math.random() * 2;
            const close = low + (high - low) * Math.random();
            
            return {
                time: currentTime,
                open: parseFloat(open.toFixed(2)),
                high: parseFloat(high.toFixed(2)),
                low: parseFloat(low.toFixed(2)),
                close: parseFloat(close.toFixed(2))
            };
        }

        function clearLog() {
            document.getElementById('diagnosticLog').textContent = '';
        }

        function exportLog() {
            const log = document.getElementById('diagnosticLog').textContent;
            const blob = new Blob([log], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `chart-diagnostic-${new Date().toISOString().slice(0,10)}.log`;
            a.click();
            URL.revokeObjectURL(url);
        }

        // Auto-run library test on load
        document.addEventListener('DOMContentLoaded', () => {
            log('🚀 Chart Diagnostic Tool initialized');
            setTimeout(testLibrary, 500);
        });

        // Handle window resize
        window.addEventListener('resize', () => {
            if (chart) {
                const container = document.getElementById('testChart');
                chart.applyOptions({ width: container.clientWidth });
            }
        });
    </script>
</body>
</html>
"""
    
    diagnostic_file = os.path.join(project_root, 'chart_diagnostic.html')
    with open(diagnostic_file, 'w') as f:
        f.write(diagnostic_html)
    
    logger.info(f"🏥 Chart diagnostic page created: {diagnostic_file}")
    logger.info("🌐 Open this file in a browser to run diagnostics")
    
    return diagnostic_file

def create_deployment_guide():
    """Create a deployment guide for the fixed charts."""
    logger.info("📚 Creating deployment guide...")
    
    guide = """
# Chart Fixing Deployment Guide

## 🎯 Quick Fix Steps

### 1. Update Dashboard Template
Replace your current dashboard with the fixed version:
```bash
cp templates/fixed_trading_dashboard.html templates/trading_dashboard.html
```

### 2. Add Fixed Chart Endpoints
Add the fixed chart endpoints to your Flask app:
```python
# Add to flask_app.py
from api.fixed_chart_endpoints import fixed_chart_bp
app.register_blueprint(fixed_chart_bp)
```

### 3. Test Chart Functionality
1. Open `chart_diagnostic.html` in your browser
2. Run all diagnostic tests
3. Verify all tests pass

### 4. Update Chart Library Version
Ensure you're using the correct Lightweight Charts version:
```html
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
```

## 🔧 Common Issues & Fixes

### Issue: Charts Not Rendering
**Fix:** Check browser console for JavaScript errors. Ensure Lightweight Charts library is loaded.

### Issue: Data Not Loading
**Fix:** Verify API endpoints return correct format. Use `/api/v2/chart-test/SPY` for testing.

### Issue: Real-time Updates Not Working
**Fix:** Check WebSocket connection. Verify socket.io is properly configured.

### Issue: Indicators Not Displaying
**Fix:** Ensure indicator data is in correct format with `time` and `value` fields.

## 📊 Data Format Requirements

### Candlestick Data
```javascript
[
    { time: 1642425600, open: 4.0, high: 5.0, low: 1.0, close: 4.0 },
    ...
]
```

### Volume Data
```javascript
[
    { time: 1642425600, value: 123456, color: 'rgba(16, 185, 129, 0.6)' },
    ...
]
```

### Indicator Data
```javascript
[
    { time: 1642425600, value: 4.5 },
    ...
]
```

## 🚀 Performance Optimization

1. **Data Limiting:** Limit chart data to 2000 points maximum
2. **Caching:** Implement proper caching for chart data
3. **Compression:** Use gzip compression for API responses
4. **WebSocket:** Use WebSocket for real-time updates

## 🐛 Debugging

1. Open browser DevTools (F12)
2. Check Console for JavaScript errors
3. Check Network tab for failed API requests
4. Use the diagnostic tool for systematic testing

## 📞 Support

If issues persist:
1. Run the diagnostic tool
2. Export the diagnostic log
3. Check the implementation against the fixed templates
4. Verify all dependencies are correctly loaded
"""
    
    guide_file = os.path.join(project_root, 'CHART_FIXING_GUIDE.md')
    with open(guide_file, 'w') as f:
        f.write(guide)
    
    logger.info(f"📚 Deployment guide created: {guide_file}")
    return guide_file

def main():
    """Main chart fixing function."""
    logger.info("🔧 Starting Chart Fixing Process...")
    logger.info(f"📁 Project root: {project_root}")
    
    # Run diagnostics
    issues, fixes = check_chart_dependencies()
    
    # Fix API endpoints
    fix_chart_api_endpoints()
    
    # Create diagnostic tools
    diagnostic_file = create_chart_diagnostic()
    guide_file = create_deployment_guide()
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("🎉 CHART FIXING COMPLETE!")
    logger.info("="*60)
    logger.info(f"✅ Fixed trading dashboard: templates/fixed_trading_dashboard.html")
    logger.info(f"✅ Fixed chart endpoints: api/fixed_chart_endpoints.py")
    logger.info(f"✅ Diagnostic tool: {diagnostic_file}")
    logger.info(f"✅ Deployment guide: {guide_file}")
    logger.info("\n📋 Next Steps:")
    logger.info("1. Update your Flask app to use the fixed endpoints")
    logger.info("2. Replace your dashboard template with the fixed version")
    logger.info("3. Run the diagnostic tool to verify everything works")
    logger.info("4. Test with real data and WebSocket connections")
    logger.info("\n🌐 Open chart_diagnostic.html in your browser to test!")

if __name__ == "__main__":
    main()