#!/usr/bin/env python3
"""
Minimal Flask app with real-time data for dashboard
"""

from flask import Flask, jsonify, render_template, request
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
import pandas as pd
import os
from dotenv import load_dotenv
import logging

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Initialize Alpaca API
api = tradeapi.REST(
    key_id=os.getenv('ALPACA_API_KEY'),
    secret_key=os.getenv('ALPACA_SECRET_KEY'),
    base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
)

logger.info("✅ Flask app initialized with Alpaca API")

@app.route('/')
def index():
    """Render main dashboard"""
    return render_template('professional_trading_dashboard.html')

@app.route('/dashboard/professional')
def professional_dashboard():
    """Render professional dashboard"""
    return render_template('professional_trading_dashboard.html')

@app.route('/api/account')
def get_account():
    """Get account information"""
    try:
        account = api.get_account()
        return jsonify({
            'success': True,
            'balance': float(account.equity),
            'buying_power': float(account.buying_power),
            'cash': float(account.cash),
            'pattern_day_trader': account.pattern_day_trader,
            'account_number': account.account_number,
            'status': account.status
        })
    except Exception as e:
        logger.error(f"Error getting account: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/positions')
def get_positions():
    """Get current positions"""
    try:
        positions = api.list_positions()
        position_list = []
        
        for pos in positions:
            current_price = float(pos.current_price) if pos.current_price else float(pos.market_value) / float(pos.qty)
            cost_basis = float(pos.cost_basis)
            market_value = float(pos.market_value)
            
            position_list.append({
                'symbol': pos.symbol,
                'qty': int(pos.qty),
                'side': pos.side,
                'market_value': market_value,
                'cost_basis': cost_basis,
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc) * 100,
                'current_price': current_price,
                'avg_entry_price': float(pos.avg_entry_price)
            })
        
        return jsonify({
            'success': True,
            'positions': position_list,
            'count': len(position_list)
        })
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return jsonify({'success': False, 'error': str(e), 'positions': []})

@app.route('/api/chart/<symbol>')
def get_chart_data(symbol):
    """Get real-time chart data"""
    try:
        timeframe = request.args.get('timeframe', '1Min')
        limit = int(request.args.get('limit', 100))
        
        # Get fresh data from Alpaca
        logger.info(f"Fetching chart data for {symbol}...")
        
        # Use current time as end
        end_time = datetime.now()
        
        # For intraday, get last 4 hours; for daily, get last 30 days
        if timeframe in ['1Min', '5Min', '15Min']:
            start_time = end_time - timedelta(hours=4)
        else:
            start_time = end_time - timedelta(days=30)
        
        bars = api.get_bars(
            symbol.upper(),
            timeframe,
            start=start_time.strftime('%Y-%m-%d'),
            end=end_time.strftime('%Y-%m-%d'),
            limit=limit,
            feed='iex'  # Use IEX for free tier
        )
        
        # Convert to DataFrame
        bars_list = list(bars)
        
        if bars_list:
            candlesticks = []
            for bar in bars_list:
                # Convert timestamp properly
                if hasattr(bar.t, 'timestamp'):
                    time_unix = int(bar.t.timestamp())
                else:
                    # bar.t is already a datetime
                    time_unix = int(pd.Timestamp(bar.t).timestamp())
                
                candlesticks.append({
                    'time': time_unix,
                    'open': float(bar.o),
                    'high': float(bar.h),
                    'low': float(bar.l),
                    'close': float(bar.c),
                    'volume': int(bar.v)
                })
            
            # Sort by time
            candlesticks.sort(key=lambda x: x['time'])
            
            # Get latest info
            latest = candlesticks[-1] if candlesticks else None
            
            return jsonify({
                'success': True,
                'data': {
                    'symbol': symbol.upper(),
                    'timeframe': timeframe,
                    'data': candlesticks,
                    'data_points': len(candlesticks),
                    'latest_price': latest['close'] if latest else None,
                    'latest_time': datetime.fromtimestamp(latest['time']).isoformat() if latest else None,
                    'cache_timestamp': datetime.now().isoformat()
                }
            })
        else:
            # If no bars, try getting without time constraints
            bars = api.get_bars(symbol.upper(), timeframe, limit=limit, feed='iex')
            bars_list = list(bars)
            
            if bars_list:
                candlesticks = []
                for bar in bars_list:
                    if hasattr(bar.t, 'timestamp'):
                        time_unix = int(bar.t.timestamp())
                    else:
                        time_unix = int(pd.Timestamp(bar.t).timestamp())
                    
                    candlesticks.append({
                        'time': time_unix,
                        'open': float(bar.o),
                        'high': float(bar.h),
                        'low': float(bar.l),
                        'close': float(bar.c),
                        'volume': int(bar.v)
                    })
                
                candlesticks.sort(key=lambda x: x['time'])
                latest = candlesticks[-1] if candlesticks else None
                
                return jsonify({
                    'success': True,
                    'data': {
                        'symbol': symbol.upper(),
                        'timeframe': timeframe,
                        'data': candlesticks,
                        'data_points': len(candlesticks),
                        'latest_price': latest['close'] if latest else None,
                        'latest_time': datetime.fromtimestamp(latest['time']).isoformat() if latest else None,
                        'cache_timestamp': datetime.now().isoformat()
                    }
                })
            
        return jsonify({
            'success': False,
            'error': 'No data available',
            'symbol': symbol.upper()
        })
        
    except Exception as e:
        logger.error(f"Error getting chart data for {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'symbol': symbol.upper()
        })

@app.route('/api/latest/<symbol>')
def get_latest_price(symbol):
    """Get latest price for a symbol"""
    try:
        # Get latest trade
        latest_trade = api.get_latest_trade(symbol.upper())
        
        # Get latest quote
        latest_quote = api.get_latest_quote(symbol.upper())
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'price': float(latest_trade.price) if latest_trade else None,
            'size': int(latest_trade.size) if latest_trade else None,
            'ask': float(latest_quote.ask_price) if latest_quote else None,
            'bid': float(latest_quote.bid_price) if latest_quote else None,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting latest price for {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'symbol': symbol.upper()
        })

@app.route('/api/market_status')
def get_market_status():
    """Get market status"""
    try:
        clock = api.get_clock()
        
        return jsonify({
            'success': True,
            'is_open': clock.is_open,
            'next_open': clock.next_open.isoformat() if clock.next_open else None,
            'next_close': clock.next_close.isoformat() if clock.next_close else None,
            'timestamp': clock.timestamp.isoformat() if hasattr(clock.timestamp, 'isoformat') else None
        })
        
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/signals')
def get_signals():
    """Get trading signals (placeholder)"""
    return jsonify({
        'success': True,
        'signals': [],
        'message': 'Signal generation pending - bot needs to be running'
    })

@app.route('/api/epic1/status')
def get_epic1_status():
    """Get Epic 1 status"""
    return jsonify({
        'success': True,
        'epic1_enabled': True,
        'features': {
            'dynamic_bands': True,
            'volume_confirmation': True,
            'signal_quality': True
        },
        'status': 'operational'
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    logger.info("🚀 Starting minimal Flask app on port 9765")
    app.run(host='0.0.0.0', port=9765, debug=False)