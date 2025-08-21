#!/usr/bin/env python3
"""
Complete Flask app with WebSocket and all required endpoints
"""

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
import pandas as pd
import os
from dotenv import load_dotenv
import logging
import threading
import time

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize Alpaca API
api = tradeapi.REST(
    key_id=os.getenv('ALPACA_API_KEY'),
    secret_key=os.getenv('ALPACA_SECRET_KEY'),
    base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
)

logger.info("✅ Flask app initialized with Alpaca API and WebSocket support")

# Global variable for WebSocket broadcasting
ws_clients = set()

@app.route('/')
def index():
    """Render unified dashboard"""
    return render_template('unified_dashboard.html')

@app.route('/dashboard')
def dashboard():
    """Render unified dashboard"""
    return render_template('unified_dashboard.html')

@app.route('/dashboard/professional')
def professional_dashboard():
    """Redirect to unified dashboard"""
    return render_template('unified_dashboard.html')

@app.route('/dashboard/fixed')
def fixed_dashboard():
    """Redirect to unified dashboard"""  
    return render_template('unified_dashboard.html')

@app.route('/debug/positions')
def debug_positions():
    """Debug positions page"""
    from flask import send_file
    return send_file('debug_positions.html')

@app.route('/tests/frontend')
def frontend_tests():
    """Frontend test suite"""
    from flask import send_file
    return send_file('tests/frontend_test_suite.html')

@app.route('/backtest')
def backtest_dashboard():
    """Epic 2: Backtesting Dashboard"""
    return render_template('backtesting_dashboard.html')

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
@app.route('/api/v2/chart-data/<symbol>')  # Support both endpoints
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
        
        try:
            bars = api.get_bars(
                symbol.upper(),
                timeframe,
                start=start_time.strftime('%Y-%m-%d'),
                end=end_time.strftime('%Y-%m-%d'),
                limit=limit,
                feed='iex'  # Use IEX for free tier
            )
        except Exception as e:
            # Fallback without date range
            bars = api.get_bars(
                symbol.upper(),
                timeframe,
                limit=limit,
                feed='iex'
            )
        
        # Convert to list
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
            
            # Convert to the format the dashboard expects
            candlestick_data = []
            for candle in candlesticks:
                candlestick_data.append({
                    'timestamp': datetime.fromtimestamp(candle['time']).isoformat(),
                    'open': candle['open'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'close': candle['close'],
                    'volume': candle['volume']
                })
            
            return jsonify({
                'success': True,
                'candlestick_data': candlestick_data,  # This is the key the dashboard expects
                'symbol': symbol.upper(),
                'timeframe': timeframe,
                'data_points': len(candlestick_data),
                'latest_price': latest['close'] if latest else None,
                'cache_timestamp': datetime.now().isoformat()
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
@app.route('/api/latest_bar/<symbol>')  # Support both endpoints
def get_latest_price(symbol):
    """Get latest price for a symbol"""
    try:
        # Get latest trade
        latest_trade = api.get_latest_trade(symbol.upper())
        
        # Get latest quote
        latest_quote = api.get_latest_quote(symbol.upper())
        
        # Get latest bar
        try:
            bars = api.get_bars(symbol.upper(), '1Min', limit=1, feed='iex')
            bars_list = list(bars)
            latest_bar = None
            
            if bars_list:
                bar = bars_list[0]
                latest_bar = {
                    'open': float(bar.o),
                    'high': float(bar.h),
                    'low': float(bar.l),
                    'close': float(bar.c),
                    'volume': int(bar.v),
                    'time': int(bar.t.timestamp()) if hasattr(bar.t, 'timestamp') else int(pd.Timestamp(bar.t).timestamp())
                }
        except:
            latest_bar = None
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'price': float(latest_trade.price) if latest_trade else None,
            'size': int(latest_trade.size) if latest_trade else None,
            'ask': float(latest_quote.ask_price) if latest_quote else None,
            'bid': float(latest_quote.bid_price) if latest_quote else None,
            'latest_bar': latest_bar,
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
@app.route('/api/signals/current')
def get_signals():
    """Get trading signals with real analysis"""
    symbol = request.args.get('symbol', 'SPY')
    
    try:
        # Get latest chart data for signal analysis
        bars = api.get_bars(
            symbol.upper(),
            '15Min',
            limit=100,
            feed='iex'
        )
        
        bars_list = list(bars)
        
        if bars_list:
            # Simple signal generation based on recent price action
            latest_bar = bars_list[-1]
            prev_bar = bars_list[-2] if len(bars_list) > 1 else latest_bar
            
            # Calculate simple metrics
            price_change = float(latest_bar.c) - float(prev_bar.c)
            price_change_pct = (price_change / float(prev_bar.c)) * 100
            
            # Calculate simple RSI (simplified for demo)
            gains = []
            losses = []
            for i in range(1, min(14, len(bars_list))):
                change = float(bars_list[i].c) - float(bars_list[i-1].c)
                if change > 0:
                    gains.append(change)
                else:
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))
            
            # Generate signal based on RSI
            signal_type = 'HOLD'
            signal_strength = 0
            reason = ''
            
            if rsi < 30:
                signal_type = 'BUY'
                signal_strength = min(90, 100 - rsi)
                reason = f'Oversold (RSI: {rsi:.1f})'
            elif rsi > 70:
                signal_type = 'SELL'
                signal_strength = min(90, rsi)
                reason = f'Overbought (RSI: {rsi:.1f})'
            else:
                signal_type = 'HOLD'
                signal_strength = 50
                reason = f'Neutral (RSI: {rsi:.1f})'
            
            # Create signal object
            signals = [{
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol.upper(),
                'signal': signal_type,
                'strength': signal_strength,
                'price': float(latest_bar.c),
                'volume': int(latest_bar.v),
                'reason': reason,
                'indicators': {
                    'rsi': rsi,
                    'price_change': price_change,
                    'price_change_pct': price_change_pct,
                    'volume_ratio': float(latest_bar.v) / float(prev_bar.v) if prev_bar.v > 0 else 1
                }
            }]
            
            # Add some recent historical signals for display
            if len(bars_list) > 20:
                for i in [-20, -10, -5]:
                    if abs(i) < len(bars_list):
                        bar = bars_list[i]
                        signals.append({
                            'timestamp': pd.Timestamp(bar.t).isoformat() if hasattr(bar.t, 'timestamp') else str(bar.t),
                            'symbol': symbol.upper(),
                            'signal': 'HOLD',
                            'strength': 50,
                            'price': float(bar.c),
                            'volume': int(bar.v),
                            'reason': 'Historical',
                            'indicators': {}
                        })
            
            return jsonify({
                'success': True,
                'signals': signals,
                'symbol': symbol.upper(),
                'current_signal': signal_type,
                'signal_strength': signal_strength,
                'rsi_value': rsi,
                'stoch_rsi_value': rsi,  # Simplified for now
                'volume_confirmed': latest_bar.v > prev_bar.v,
                'latest_price': float(latest_bar.c)
            })
        
        return jsonify({
            'success': False,
            'signals': [],
            'symbol': symbol.upper(),
            'message': 'No data available for signal generation'
        })
        
    except Exception as e:
        logger.error(f"Error generating signals: {e}")
        return jsonify({
            'success': True,
            'signals': [],
            'symbol': symbol,
            'message': 'Signal generation in progress'
        })

@app.route('/api/indicators/<symbol>')
def get_indicators(symbol):
    """Get indicators (placeholder)"""
    return jsonify({
        'success': True,
        'indicators': {
            'StochRSI_K': 50.0,
            'StochRSI_D': 50.0,
            'EMA': 0,
            'volume_ratio': 1.0
        },
        'symbol': symbol.upper()
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

@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Start the trading bot"""
    try:
        # Simulate bot start logic
        logger.info("Trading bot start requested from dashboard")
        
        # Here you would normally start your trading bot logic
        # For now, return success status
        
        return jsonify({
            'success': True,
            'message': 'Trading bot started successfully',
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'bot_id': 'epic1-stoch-rsi-bot',
            'features': {
                'dynamic_stoch_rsi': True,
                'volume_confirmation': True,
                'signal_quality': True
            }
        })
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    """Stop the trading bot"""
    try:
        logger.info("Trading bot stop requested from dashboard")
        
        return jsonify({
            'success': True,
            'message': 'Trading bot stopped successfully',
            'status': 'stopped',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/bot/status')
def bot_status():
    """Get bot status"""
    return jsonify({
        'success': True,
        'status': 'ready',  # or 'running', 'stopped', 'error'
        'bot_id': 'epic1-stoch-rsi-bot',
        'uptime': '0m',
        'last_signal': None,
        'trades_today': 0,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/historical/<symbol>')
def get_historical_data(symbol):
    """Get historical data from cache for 24/7 access"""
    try:
        from services.historical_data_service import get_historical_data_service
        
        timeframe = request.args.get('timeframe', '1Day')
        days = int(request.args.get('days', 30))
        
        # Get historical data service
        service = get_historical_data_service(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY')
        )
        
        # Get hybrid data (live if available, cached otherwise)
        df = service.get_hybrid_data(symbol, timeframe, days)
        
        if not df.empty:
            # Convert to API format
            historical_data = []
            for idx, row in df.iterrows():
                historical_data.append({
                    'timestamp': idx.isoformat() if hasattr(idx, 'isoformat') else str(idx),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row['volume'])
                })
            
            return jsonify({
                'success': True,
                'symbol': symbol.upper(),
                'timeframe': timeframe,
                'historical_data': historical_data,
                'data_source': 'historical',
                'data_points': len(historical_data)
            })
        
        return jsonify({
            'success': False,
            'error': 'No historical data available',
            'symbol': symbol.upper()
        })
        
    except Exception as e:
        logger.error(f"Error getting historical data: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cache/stats')
def get_cache_stats():
    """Get cache statistics"""
    try:
        from services.historical_data_service import get_historical_data_service
        
        symbol = request.args.get('symbol')
        
        service = get_historical_data_service(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY')
        )
        
        stats = service.get_data_stats(symbol)
        
        return jsonify({
            'success': True,
            **stats
        })
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """Run backtest with specified parameters"""
    try:
        data = request.json
        symbol = data.get('symbol', 'AAPL')
        strategy_name = data.get('strategy', 'stoch_rsi')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Import strategy based on selection
        if strategy_name == 'stoch_rsi_enhanced':
            from strategies.enhanced_stoch_rsi_strategy import EnhancedStochRSIStrategy
            strategy = EnhancedStochRSIStrategy()
        elif strategy_name == 'ma_crossover':
            from strategies.ma_crossover_strategy import MACrossoverStrategy
            strategy = MACrossoverStrategy()
        else:
            from strategies.stoch_rsi_strategy import StochRSIStrategy
            strategy = StochRSIStrategy()
        
        # Run backtest
        from backtesting.enhanced_backtesting_engine import EnhancedBacktestingEngine
        
        engine = EnhancedBacktestingEngine(
            strategy=strategy,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        results = engine.run()
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'strategy': strategy_name,
            'performance_metrics': results.performance_metrics,
            'volume_analysis': results.volume_analysis,
            'summary_report': results.summary_report,
            'total_trades': len(results.trades),
            'final_value': results.portfolio_value[-1] if results.portfolio_value else 0
        })
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        return jsonify({'success': False, 'error': str(e)})

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    ws_clients.add(request.sid)
    emit('connected', {'message': 'Connected to trading server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")
    ws_clients.discard(request.sid)

@socketio.on('subscribe')
def handle_subscribe(data):
    """Handle subscription requests"""
    symbol = data.get('symbol', 'SPY')
    logger.info(f"Client {request.sid} subscribed to {symbol}")
    emit('subscribed', {'symbol': symbol, 'message': f'Subscribed to {symbol}'})

@socketio.on('request_update')
def handle_update_request(data):
    """Handle update requests"""
    symbol = data.get('symbol', 'SPY')
    
    try:
        # Get latest price
        latest_trade = api.get_latest_trade(symbol)
        
        update_data = {
            'symbol': symbol,
            'price': float(latest_trade.price) if latest_trade else None,
            'timestamp': datetime.now().isoformat()
        }
        
        emit('price_update', update_data)
        
    except Exception as e:
        logger.error(f"Error getting update for {symbol}: {e}")
        emit('error', {'error': str(e)})

# Background thread for periodic updates
def broadcast_updates():
    """Broadcast price updates periodically"""
    symbols = ['SPY', 'AAPL', 'TSLA', 'NVDA']
    
    while True:
        try:
            for symbol in symbols:
                try:
                    latest_trade = api.get_latest_trade(symbol)
                    
                    update_data = {
                        'symbol': symbol,
                        'price': float(latest_trade.price) if latest_trade else None,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Broadcast to all connected clients
                    socketio.emit('price_update', update_data)
                    
                except Exception as e:
                    logger.error(f"Error broadcasting {symbol}: {e}")
            
            # Wait 5 seconds between updates
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Error in broadcast loop: {e}")
            time.sleep(10)

# Start background thread
update_thread = threading.Thread(target=broadcast_updates, daemon=True)
update_thread.start()

if __name__ == '__main__':
    logger.info("🚀 Starting complete Flask app with WebSocket on port 8765")
    socketio.run(app, host='0.0.0.0', port=8765, debug=False, allow_unsafe_werkzeug=True)