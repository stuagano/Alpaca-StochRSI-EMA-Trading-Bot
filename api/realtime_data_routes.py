"""
Real-time data routes that bypass cache for fresh market data
"""

from flask import Blueprint, jsonify, request
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
import pandas as pd

# Load environment
load_dotenv()

# Create blueprint
realtime_bp = Blueprint('realtime', __name__)
logger = logging.getLogger(__name__)

# Initialize Alpaca API
api = tradeapi.REST(
    key_id=os.getenv('ALPACA_API_KEY'),
    secret_key=os.getenv('ALPACA_SECRET_KEY'),
    base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
)

@realtime_bp.route('/api/realtime/chart/<symbol>')
def get_realtime_chart(symbol):
    """Get real-time chart data directly from Alpaca, bypassing cache"""
    try:
        timeframe = request.args.get('timeframe', '1Min')
        limit = int(request.args.get('limit', 100))
        
        # Map timeframes
        tf_map = {
            '1Min': '1Min',
            '5Min': '5Min', 
            '15Min': '15Min',
            '1Hour': '1Hour',
            '1Day': '1Day'
        }
        alpaca_tf = tf_map.get(timeframe, '1Min')
        
        # Get fresh data from Alpaca
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        logger.info(f"Fetching fresh data for {symbol} from Alpaca...")
        
        bars = api.get_bars(
            symbol.upper(),
            alpaca_tf,
            start=start_time.isoformat(),
            end=end_time.isoformat(),
            limit=limit
        )
        
        # Convert to DataFrame
        bars_df = bars.df if hasattr(bars, 'df') else pd.DataFrame([{
            'open': b.o,
            'high': b.h,
            'low': b.l,
            'close': b.c,
            'volume': b.v,
            'timestamp': b.t
        } for b in bars])
        
        if bars_df.empty:
            # Try without time constraints for pre-market/after-hours
            bars = api.get_bars(symbol.upper(), alpaca_tf, limit=limit)
            bars_df = bars.df if hasattr(bars, 'df') else pd.DataFrame([{
                'open': b.o,
                'high': b.h,
                'low': b.l,
                'close': b.c,
                'volume': b.v,
                'timestamp': b.t
            } for b in bars])
        
        if not bars_df.empty:
            # Convert to LightweightCharts format
            candlesticks = []
            
            # Handle both index types (timestamp in index or column)
            if 'timestamp' in bars_df.columns:
                for _, row in bars_df.iterrows():
                    timestamp = row['timestamp']
                    if hasattr(timestamp, 'timestamp'):
                        time_unix = int(timestamp.timestamp())
                    else:
                        time_unix = int(pd.Timestamp(timestamp).timestamp())
                    
                    candlesticks.append({
                        'time': time_unix,
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row['volume'])
                    })
            else:
                # Timestamp is in index
                for timestamp, row in bars_df.iterrows():
                    time_unix = int(timestamp.timestamp())
                    candlesticks.append({
                        'time': time_unix,
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row['volume'])
                    })
            
            # Sort by time
            candlesticks.sort(key=lambda x: x['time'])
            
            # Get latest price info
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
                    'is_realtime': True,
                    'source': 'alpaca_direct'
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No data available from Alpaca',
                'symbol': symbol.upper()
            })
            
    except Exception as e:
        logger.error(f"Error fetching realtime chart data for {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'symbol': symbol.upper()
        })

@realtime_bp.route('/api/realtime/latest/<symbol>')
def get_realtime_latest(symbol):
    """Get the latest real-time price for a symbol"""
    try:
        # Get latest trade
        latest_trade = api.get_latest_trade(symbol.upper())
        
        # Get latest quote
        latest_quote = api.get_latest_quote(symbol.upper())
        
        # Get latest bar
        bars = api.get_bars(symbol.upper(), '1Min', limit=1)
        latest_bar = None
        
        if bars:
            bar = list(bars)[0] if bars else None
            if bar:
                latest_bar = {
                    'open': bar.o,
                    'high': bar.h,
                    'low': bar.l,
                    'close': bar.c,
                    'volume': bar.v,
                    'timestamp': bar.t.isoformat() if hasattr(bar.t, 'isoformat') else str(bar.t)
                }
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'latest_trade': {
                'price': float(latest_trade.price) if latest_trade else None,
                'size': int(latest_trade.size) if latest_trade else None,
                'timestamp': latest_trade.timestamp.isoformat() if latest_trade and hasattr(latest_trade.timestamp, 'isoformat') else None
            },
            'latest_quote': {
                'ask': float(latest_quote.ask_price) if latest_quote else None,
                'bid': float(latest_quote.bid_price) if latest_quote else None,
                'ask_size': int(latest_quote.ask_size) if latest_quote else None,
                'bid_size': int(latest_quote.bid_size) if latest_quote else None
            },
            'latest_bar': latest_bar,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching realtime latest for {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'symbol': symbol.upper()
        })

@realtime_bp.route('/api/realtime/market_status')
def get_market_status():
    """Get current market status"""
    try:
        clock = api.get_clock()
        
        return jsonify({
            'success': True,
            'is_open': clock.is_open,
            'next_open': clock.next_open.isoformat() if clock.next_open else None,
            'next_close': clock.next_close.isoformat() if clock.next_close else None,
            'timestamp': clock.timestamp.isoformat() if hasattr(clock.timestamp, 'isoformat') else None,
            'current_time': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching market status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })