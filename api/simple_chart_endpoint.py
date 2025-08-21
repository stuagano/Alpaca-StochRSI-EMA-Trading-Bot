"""
Simple Chart Endpoint for Testing TradingView Integration
This provides a basic working chart data endpoint that always returns valid data
"""
from flask import Blueprint, jsonify, request
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Create blueprint for simple chart endpoints
simple_chart_bp = Blueprint('simple_chart', __name__)
logger = logging.getLogger(__name__)

def generate_sample_ohlc_data(symbol: str, timeframe: str = "15Min", limit: int = 100):
    """Generate realistic sample OHLC data for testing"""
    
    # Base prices for different symbols
    base_prices = {
        'AAPL': 150.0,
        'SPY': 420.0,
        'QQQ': 350.0,
        'TSLA': 200.0,
        'MSFT': 300.0,
        'GOOGL': 135.0,
        'AMZN': 140.0,
        'META': 280.0,
        'NVDA': 450.0
    }
    
    base_price = base_prices.get(symbol.upper(), 150.0)
    
    # Timeframe intervals in minutes
    intervals = {
        '1Min': 1,
        '5Min': 5,
        '15Min': 15,
        '30Min': 30,
        '1Hour': 60,
        '1Day': 1440
    }
    
    interval_minutes = intervals.get(timeframe, 15)
    
    # Generate timestamps going backwards from now
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=interval_minutes * limit)
    
    timestamps = []
    current_time = start_time
    while current_time <= end_time:
        timestamps.append(current_time)
        current_time += timedelta(minutes=interval_minutes)
    
    # Generate realistic price movements
    np.random.seed(42)  # For consistent test data
    data = []
    current_price = base_price
    
    for timestamp in timestamps:
        # Random walk with mean reversion
        price_change = np.random.normal(0, 0.02)  # 2% volatility
        trend = (base_price - current_price) * 0.001  # Mean reversion
        
        open_price = current_price
        price_move = base_price * (price_change + trend)
        
        # Generate realistic OHLC from the price movement
        high_addon = abs(np.random.normal(0, 0.005)) * base_price
        low_addon = abs(np.random.normal(0, 0.005)) * base_price
        
        close_price = open_price + price_move
        high_price = max(open_price, close_price) + high_addon
        low_price = min(open_price, close_price) - low_addon
        
        # Ensure high >= open,close and low <= open,close
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        # Generate volume
        volume = int(np.random.normal(1000000, 200000))
        volume = max(volume, 100000)  # Minimum volume
        
        data.append({
            'timestamp': timestamp,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
        
        current_price = close_price
    
    return data

@simple_chart_bp.route('/api/chart-test/<symbol>')
def get_test_chart_data(symbol):
    """Simple test endpoint that always returns valid chart data"""
    try:
        timeframe = request.args.get('timeframe', '15Min')
        limit = min(int(request.args.get('limit', 100)), 1000)  # Cap at 1000
        
        logger.info(f"🧪 Generating test chart data for {symbol.upper()} - {timeframe} - {limit} points")
        
        # Generate sample data
        ohlc_data = generate_sample_ohlc_data(symbol, timeframe, limit)
        
        # Convert to TradingView Lightweight Charts format
        chart_data = []
        for item in ohlc_data:
            chart_data.append({
                'time': int(item['timestamp'].timestamp()),
                'open': item['open'],
                'high': item['high'],
                'low': item['low'],
                'close': item['close'],
                'volume': item['volume']
            })
        
        response = {
            'success': True,
            'data': chart_data,
            'symbol': symbol.upper(),
            'timeframe': timeframe,
            'count': len(chart_data),
            'generated_at': datetime.now().isoformat(),
            'note': 'This is generated test data for chart integration testing'
        }
        
        logger.info(f"✅ Test chart data generated: {len(chart_data)} points for {symbol.upper()}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"❌ Error generating test chart data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'endpoint': 'chart-test'
        }), 500

@simple_chart_bp.route('/api/v2/chart-data/<symbol>')
def get_v2_chart_data(symbol):
    """V2 chart endpoint with enhanced error handling"""
    try:
        timeframe = request.args.get('timeframe', '15Min')
        limit = min(int(request.args.get('limit', 100)), 1000)
        
        logger.info(f"📊 V2 Chart data request: {symbol.upper()} - {timeframe} - {limit}")
        
        # Try to get real data first (this would connect to your data manager)
        # For now, we'll return test data
        
        ohlc_data = generate_sample_ohlc_data(symbol, timeframe, limit)
        
        # Format for the professional dashboard expected format
        candlestick_data = []
        for item in ohlc_data:
            candlestick_data.append({
                'timestamp': item['timestamp'].isoformat(),
                'open': item['open'],
                'high': item['high'], 
                'low': item['low'],
                'close': item['close'],
                'volume': item['volume']
            })
        
        response = {
            'success': True,
            'candlestick_data': candlestick_data,
            'symbol': symbol.upper(),
            'timeframe': timeframe,
            'data_points': len(candlestick_data),
            'timestamp': datetime.now().isoformat(),
            'endpoint': 'v2/chart-data'
        }
        
        logger.info(f"✅ V2 chart data generated: {len(candlestick_data)} points for {symbol.upper()}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"❌ Error in V2 chart endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'endpoint': 'v2/chart-data'
        }), 500

@simple_chart_bp.route('/api/chart-status')
def get_chart_status():
    """Get status of chart endpoints"""
    return jsonify({
        'success': True,
        'endpoints': {
            '/api/chart-test/<symbol>': 'Simple test endpoint with generated data',
            '/api/v2/chart-data/<symbol>': 'Enhanced endpoint matching dashboard expectations'
        },
        'parameters': {
            'timeframe': ['1Min', '5Min', '15Min', '30Min', '1Hour', '1Day'],
            'limit': 'Max 1000 data points'
        },
        'timestamp': datetime.now().isoformat()
    })

# Health check endpoint
@simple_chart_bp.route('/api/health')
def health_check():
    """Simple health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'chart-endpoints',
        'timestamp': datetime.now().isoformat()
    })