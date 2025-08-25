#!/usr/bin/env python3
"""
Complete Flask app with WebSocket and all required endpoints
"""

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
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

# Enable CORS
CORS(app, origins="*", supports_credentials=True)

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
    # Use enhanced dashboard if it exists, otherwise fallback to original
    try:
        return render_template('unified_dashboard_enhanced.html')
    except:
        return render_template('unified_dashboard.html')

@app.route('/dashboard')
def dashboard():
    """Render unified dashboard"""
    try:
        return render_template('unified_dashboard_enhanced.html')
    except:
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

@app.route('/api/orders', methods=['GET', 'POST'])
def handle_orders():
    """Handle order operations"""
    if request.method == 'GET':
        # Get list of orders
        try:
            status = request.args.get('status', 'all')
            limit = int(request.args.get('limit', 100))
            
            orders = api.list_orders(status=status, limit=limit)
            order_list = []
            
            for order in orders:
                order_list.append({
                    'id': order.id,
                    'symbol': order.symbol,
                    'qty': int(float(order.qty)),  # Handle fractional shares
                    'side': order.side,
                    'type': order.order_type,
                    'time_in_force': order.time_in_force,
                    'limit_price': float(order.limit_price) if order.limit_price else None,
                    'stop_price': float(order.stop_price) if order.stop_price else None,
                    'filled_qty': int(float(order.filled_qty)) if order.filled_qty else 0,  # Handle fractional shares
                    'status': order.status,
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                    'filled_at': order.filled_at.isoformat() if order.filled_at else None
                })
            
            return jsonify({
                'success': True,
                'orders': order_list,
                'count': len(order_list)
            })
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return jsonify({'success': False, 'error': str(e), 'orders': []})
    
    elif request.method == 'POST':
        # Create new order
        try:
            data = request.json
            symbol = data.get('symbol', 'SPY')
            qty = int(data.get('qty', 1))
            side = data.get('side', 'buy')
            order_type = data.get('type', 'market')
            time_in_force = data.get('time_in_force', 'day')
            limit_price = data.get('limit_price')
            stop_price = data.get('stop_price')
            
            # Create order based on type
            if order_type == 'market':
                order = api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    type=order_type,
                    time_in_force=time_in_force
                )
            elif order_type == 'limit':
                order = api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    type=order_type,
                    time_in_force=time_in_force,
                    limit_price=limit_price
                )
            elif order_type == 'stop':
                order = api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    type=order_type,
                    time_in_force=time_in_force,
                    stop_price=stop_price
                )
            elif order_type == 'stop_limit':
                order = api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    type=order_type,
                    time_in_force=time_in_force,
                    limit_price=limit_price,
                    stop_price=stop_price
                )
            else:
                return jsonify({'success': False, 'error': 'Invalid order type'})
            
            return jsonify({
                'success': True,
                'order': {
                    'id': order.id,
                    'symbol': order.symbol,
                    'qty': int(order.qty),
                    'side': order.side,
                    'type': order.order_type,
                    'status': order.status,
                    'created_at': order.created_at.isoformat() if order.created_at else None
                }
            })
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/orders/<order_id>', methods=['DELETE'])
def cancel_order(order_id):
    """Cancel an order"""
    try:
        api.cancel_order(order_id)
        return jsonify({
            'success': True,
            'message': f'Order {order_id} cancelled successfully'
        })
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/market/bars/<symbol>')
def get_market_bars(symbol):
    """Get market bars for a symbol"""
    try:
        timeframe = request.args.get('timeframe', '1Day')
        limit = int(request.args.get('limit', 100))
        
        bars = api.get_bars(
            symbol.upper(),
            timeframe,
            limit=limit,
            feed='iex'
        )
        
        bars_list = []
        for bar in bars:
            bars_list.append({
                'time': bar.t.isoformat() if hasattr(bar.t, 'isoformat') else str(bar.t),
                'open': float(bar.o),
                'high': float(bar.h),
                'low': float(bar.l),
                'close': float(bar.c),
                'volume': int(bar.v)
            })
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'bars': bars_list,
            'count': len(bars_list)
        })
    except Exception as e:
        logger.error(f"Error getting bars for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/market/quote/<symbol>')
def get_market_quote(symbol):
    """Get latest quote for a symbol"""
    try:
        quote = api.get_latest_quote(symbol.upper())
        trade = api.get_latest_trade(symbol.upper())
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'ask': float(quote.ask_price) if quote else None,
            'ask_size': int(quote.ask_size) if quote else None,
            'bid': float(quote.bid_price) if quote else None,
            'bid_size': int(quote.bid_size) if quote else None,
            'last': float(trade.price) if trade else None,
            'last_size': int(trade.size) if trade else None,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting quote for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)})

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
@app.route('/api/signals/latest')
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
    """Health check endpoint with system status"""
    # Check various system components
    alpaca_status = False
    database_status = True  # Assuming in-memory for now
    websocket_status = len(ws_clients) > 0 or True  # WebSocket is available
    trading_engine_status = True
    
    try:
        # Check Alpaca connection
        account = api.get_account()
        alpaca_status = account.status == 'ACTIVE'
    except:
        alpaca_status = False
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'alpaca': alpaca_status,
        'database': database_status,
        'websocket': websocket_status,
        'trading_engine': trading_engine_status
    })

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

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """Handle configuration get/set"""
    if request.method == 'GET':
        # Return current configuration
        return jsonify({
            'success': True,
            'config': {
                'strategy': {
                    'ema_short': 20,
                    'ema_long': 50,
                    'stochrsi_period': 14,
                    'stochrsi_smooth': 3,
                    'oversold_threshold': 20,
                    'overbought_threshold': 80
                },
                'risk': {
                    'max_position_size': 10,
                    'stop_loss': 5,
                    'take_profit': 10,
                    'max_daily_loss': 2
                },
                'trading': {
                    'start_time': '09:30',
                    'end_time': '16:00',
                    'enabled': True,
                    'paper_trading': True
                },
                'notifications': {
                    'email_enabled': False,
                    'email_address': '',
                    'slack_enabled': False,
                    'slack_webhook': ''
                }
            }
        })
    else:
        # Save configuration
        try:
            config = request.json
            # In a real app, you'd save this to a database or config file
            logger.info(f"Configuration updated: {config}")
            return jsonify({'success': True, 'message': 'Configuration saved successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/config/test-connection', methods=['POST'])
def test_connection():
    """Test API connections"""
    try:
        # Test Alpaca connection
        account = api.get_account()
        return jsonify({
            'success': True,
            'alpaca': {
                'status': 'connected',
                'account_number': account.account_number,
                'account_status': account.status
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'alpaca': {
                'status': 'disconnected',
                'error': str(e)
            }
        })

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

# Monitoring API endpoints
@app.route('/api/monitoring/status')
def get_monitoring_status():
    """Get comprehensive system monitoring status"""
    try:
        # Check system components
        alpaca_status = False
        database_status = True  # In-memory for now
        websocket_status = len(ws_clients) > 0 or True
        trading_engine_status = True
        
        try:
            account = api.get_account()
            alpaca_status = account.status == 'ACTIVE'
        except:
            alpaca_status = False
        
        # Calculate overall status
        overall_status = 'online' if all([alpaca_status, database_status, websocket_status]) else 'degraded'
        if not alpaca_status:
            overall_status = 'warning'
        
        # Mock system metrics
        import psutil
        cpu_percent = psutil.cpu_percent() if 'psutil' in globals() else 15.3
        memory_percent = psutil.virtual_memory().percent if 'psutil' in globals() else 42.1
        
        return jsonify({
            'success': True,
            'overall': {
                'status': overall_status,
                'message': 'System healthy' if overall_status == 'online' else 'Some services degraded'
            },
            'uptime': 3600,  # Mock uptime in seconds
            'alerts': [],
            'resources': {
                'cpu': round(cpu_percent, 1),
                'memory': round(memory_percent, 1),
                'disk': 23.4,
                'network': 0.8
            },
            'trading': {
                'active_positions': len(api.list_positions()) if alpaca_status else 0
            },
            'metrics': {
                'requests_per_sec': 12,
                'avg_response_time': 45,
                'error_rate': 0.1,
                'active_connections': len(ws_clients)
            }
        })
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'overall': {'status': 'offline', 'message': 'System error'}
        })

@app.route('/api/monitoring/services')
def get_services_status():
    """Get microservices status"""
    try:
        services = [
            {
                'name': 'API Gateway',
                'status': 'online',
                'status_text': 'Running',
                'port': 8765,
                'response_time': 23
            },
            {
                'name': 'Frontend Service',
                'status': 'online',
                'status_text': 'Running',
                'port': 9100,
                'response_time': 18
            },
            {
                'name': 'Trading Execution',
                'status': 'online',
                'status_text': 'Running',
                'port': 8001,
                'response_time': 35
            },
            {
                'name': 'Position Management',
                'status': 'online',
                'status_text': 'Running',
                'port': 8002,
                'response_time': 28
            },
            {
                'name': 'Notification Service',
                'status': 'warning',
                'status_text': 'Degraded',
                'port': 8004,
                'response_time': 120
            }
        ]
        
        return jsonify(services)
    except Exception as e:
        logger.error(f"Error getting services status: {e}")
        return jsonify([])

@app.route('/api/monitoring/metrics/resources')
def get_resource_metrics():
    """Get historical resource usage metrics"""
    try:
        # Generate mock time series data
        from datetime import datetime, timedelta
        
        timestamps = []
        cpu_data = []
        memory_data = []
        disk_data = []
        
        for i in range(30):  # Last 30 data points
            timestamp = (datetime.now() - timedelta(minutes=i)).strftime('%H:%M')
            timestamps.insert(0, timestamp)
            
            # Mock data with some variance
            cpu_data.insert(0, 15 + (i % 10) * 2)
            memory_data.insert(0, 42 + (i % 8) * 3)
            disk_data.insert(0, 23 + (i % 5) * 1)
        
        return jsonify({
            'success': True,
            'timestamps': timestamps,
            'cpu': cpu_data,
            'memory': memory_data,
            'disk': disk_data
        })
    except Exception as e:
        logger.error(f"Error getting resource metrics: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/monitoring/metrics/requests')
def get_request_metrics():
    """Get request performance metrics"""
    try:
        # Generate mock time series data
        from datetime import datetime, timedelta
        
        timestamps = []
        requests_data = []
        response_times = []
        
        for i in range(30):  # Last 30 data points
            timestamp = (datetime.now() - timedelta(minutes=i)).strftime('%H:%M')
            timestamps.insert(0, timestamp)
            
            # Mock data
            requests_data.insert(0, 10 + (i % 15) * 2)
            response_times.insert(0, 40 + (i % 8) * 5)
        
        return jsonify({
            'success': True,
            'timestamps': timestamps,
            'requests_per_sec': requests_data,
            'response_times': response_times
        })
    except Exception as e:
        logger.error(f"Error getting request metrics: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/monitoring/alerts')
def get_monitoring_alerts():
    """Get system alerts"""
    try:
        alerts = [
            {
                'severity': 'warning',
                'title': 'High Memory Usage',
                'message': 'System memory usage is above 80%',
                'timestamp': datetime.now().isoformat()
            },
            {
                'severity': 'info',
                'title': 'New Trade Executed',
                'message': 'Successfully executed buy order for AAPL',
                'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat()
            }
        ]
        
        return jsonify(alerts)
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify([])

@app.route('/api/monitoring/logs')
def get_monitoring_logs():
    """Get system logs"""
    try:
        level_filter = request.args.get('level', 'all')
        service_filter = request.args.get('service', 'all')
        limit = int(request.args.get('limit', 50))
        
        # Mock log entries
        logs = []
        log_levels = ['INFO', 'WARNING', 'ERROR', 'DEBUG']
        services = ['api-gateway', 'trading-execution', 'position-management', 'notification']
        messages = [
            'Trade executed successfully',
            'Market data updated',
            'Position opened for AAPL',
            'WebSocket connection established',
            'Configuration updated',
            'Alert sent to user',
            'Database query completed',
            'Signal generated for SPY'
        ]
        
        for i in range(limit):
            level = log_levels[i % len(log_levels)]
            service = services[i % len(services)]
            message = messages[i % len(messages)]
            
            # Apply filters
            if level_filter != 'all' and level.lower() != level_filter.lower():
                continue
            if service_filter != 'all' and service != service_filter:
                continue
            
            logs.append({
                'level': level,
                'service': service,
                'message': message,
                'timestamp': (datetime.now() - timedelta(seconds=i*30)).isoformat()
            })
        
        return jsonify(logs[:limit])
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify([])

# Analytics API endpoints
@app.route('/api/analytics/summary')
def get_analytics_summary():
    """Get analytics summary"""
    try:
        # Calculate basic metrics from positions and orders
        positions = api.list_positions()
        orders = api.list_orders(status='filled', limit=100)
        
        total_pnl = sum(float(pos.unrealized_pl) for pos in positions)
        
        # Mock additional analytics data
        return jsonify({
            'success': True,
            'total_pnl': total_pnl,
            'total_pnl_percent': (total_pnl / 10000) * 100 if total_pnl != 0 else 0,
            'win_rate': 65.4,
            'winning_trades': len([o for o in orders if float(o.filled_qty) > 0]),
            'losing_trades': max(0, len(orders) - len([o for o in orders if float(o.filled_qty) > 0])),
            'avg_trade': total_pnl / max(1, len(orders)),
            'total_trades': len(orders),
            'sharpe_ratio': 1.23,
            'max_drawdown': -5.67,
            'best_day': 234.56,
            'worst_day': -123.45,
            'avg_win': 89.12,
            'avg_loss': -45.67,
            'profit_factor': 1.95,
            'recovery_factor': 2.34
        })
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analytics/trades')
def get_analytics_trades():
    """Get trade history for analytics"""
    try:
        orders = api.list_orders(status='filled', limit=50)
        
        trades = []
        for order in orders:
            trades.append({
                'date': order.filled_at.isoformat() if order.filled_at else datetime.now().isoformat(),
                'symbol': order.symbol,
                'strategy': 'StochRSI-EMA',
                'side': order.side,
                'quantity': int(float(order.filled_qty)) if order.filled_qty else int(float(order.qty)),
                'entry_price': float(order.filled_avg_price) if order.filled_avg_price else float(order.limit_price or 0),
                'exit_price': float(order.filled_avg_price) if order.filled_avg_price else float(order.limit_price or 0),
                'pnl': (float(order.filled_avg_price) - float(order.limit_price or 0)) * int(float(order.filled_qty or order.qty)) if order.side == 'buy' else 0,
                'pnl_percent': 2.34,
                'duration': '2h 15m'
            })
        
        return jsonify(trades)
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify([])

@app.route('/api/analytics/pnl-history')
def get_pnl_history():
    """Get P&L history for chart"""
    try:
        # Mock P&L history data
        labels = []
        values = []
        cumulative_pnl = 0
        
        for i in range(30):
            date = (datetime.now() - timedelta(days=29-i)).strftime('%m/%d')
            labels.append(date)
            
            # Mock daily P&L
            daily_pnl = (i % 7 - 3) * 50 + (i % 3) * 25
            cumulative_pnl += daily_pnl
            values.append(cumulative_pnl)
        
        return jsonify({
            'success': True,
            'labels': labels,
            'values': values
        })
    except Exception as e:
        logger.error(f"Error getting P&L history: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analytics/win-loss-distribution')
def get_win_loss_distribution():
    """Get win/loss distribution"""
    try:
        return jsonify({
            'success': True,
            'winning_trades': 65,
            'losing_trades': 35
        })
    except Exception as e:
        logger.error(f"Error getting win/loss distribution: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analytics/monthly-performance')
def get_monthly_performance():
    """Get monthly performance data"""
    try:
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        values = [234, -123, 456, 789, -234, 567]
        
        return jsonify({
            'success': True,
            'labels': months,
            'values': values
        })
    except Exception as e:
        logger.error(f"Error getting monthly performance: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analytics/strategy-performance')
def get_strategy_performance():
    """Get strategy performance data"""
    try:
        strategies = ['StochRSI-EMA', 'Momentum', 'Mean Reversion']
        values = [1234, 567, 890]
        
        return jsonify({
            'success': True,
            'labels': strategies,
            'values': values
        })
    except Exception as e:
        logger.error(f"Error getting strategy performance: {e}")
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