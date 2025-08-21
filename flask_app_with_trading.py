#!/usr/bin/env python3
"""
Enhanced Flask app with Trading Execution Engine integration
"""

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
import asyncio
import threading
from typing import Dict, Optional

# Import our trading components
from services.trading_executor import TradingExecutor, TradingSignal
from services.signal_processor import SignalProcessor

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

# Trading configuration
TRADING_CONFIG = {
    'max_positions': 5,
    'max_position_size_pct': 0.10,  # 10% of account
    'max_account_exposure_pct': 0.50,  # 50% max exposure
    'min_signal_strength': 70,
    'stop_loss_pct': 0.02,  # 2% stop loss
    'take_profit_ratio': 2.0,  # 2:1 risk/reward
    'use_trailing_stop': True,
    'min_signal_gap_seconds': 300,  # 5 minutes between signals
    'require_confirmation': True
}

# Initialize trading components
trading_executor = TradingExecutor(api, TRADING_CONFIG)
signal_processor = SignalProcessor(trading_executor, TRADING_CONFIG)

# Global bot state
bot_state = {
    'is_running': False,
    'start_time': None,
    'trades_today': 0,
    'last_signal': None,
    'active_symbols': ['AAPL', 'SPY', 'TSLA'],
    'strategy': 'stoch_rsi'  # or 'ma_crossover'
}

logger.info("✅ Flask app initialized with Trading Execution Engine")

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Render trading dashboard"""
    return render_template('trading_dashboard.html')

@app.route('/dashboard/classic')
def classic_dashboard():
    """Render classic unified dashboard"""
    return render_template('unified_dashboard.html')

@app.route('/dashboard/positions')
def position_management_dashboard():
    """Render position management dashboard"""
    return render_template('position_management_dashboard.html')

# ==================== COMPATIBILITY ENDPOINTS ====================
# These endpoints maintain compatibility with the original dashboard

@app.route('/api/account')
def get_account():
    """Get account information (compatibility endpoint)"""
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
    """Get current positions (compatibility endpoint)"""
    try:
        positions = api.list_positions()
        position_list = []
        
        for pos in positions:
            current_price = float(pos.current_price) if pos.current_price else float(pos.market_value) / float(pos.qty)
            position_list.append({
                'symbol': pos.symbol,
                'qty': int(pos.qty),
                'side': pos.side,
                'market_value': float(pos.market_value),
                'cost_basis': float(pos.cost_basis),
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

@app.route('/api/v2/chart-data/<symbol>')
def get_chart_data(symbol):
    """Get chart data (compatibility endpoint)"""
    try:
        timeframe = request.args.get('timeframe', '15Min')
        limit = int(request.args.get('limit', 100))
        
        bars = api.get_bars(
            symbol.upper(),
            timeframe,
            limit=limit,
            feed='iex'
        )
        
        bars_list = list(bars)
        
        if bars_list:
            candlestick_data = []
            for bar in bars_list:
                candlestick_data.append({
                    'timestamp': bar.t.isoformat() if hasattr(bar.t, 'isoformat') else str(bar.t),
                    'open': float(bar.o),
                    'high': float(bar.h),
                    'low': float(bar.l),
                    'close': float(bar.c),
                    'volume': int(bar.v)
                })
            
            return jsonify({
                'success': True,
                'candlestick_data': candlestick_data,
                'symbol': symbol.upper(),
                'timeframe': timeframe,
                'data_points': len(candlestick_data),
                'latest_price': candlestick_data[-1]['close'] if candlestick_data else None
            })
            
        return jsonify({
            'success': False,
            'error': 'No data available',
            'symbol': symbol.upper()
        })
        
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'symbol': symbol.upper()
        })

@app.route('/api/signals/current')
def get_signals():
    """Get current signals (compatibility endpoint)"""
    symbol = request.args.get('symbol', 'AAPL')
    
    try:
        # Generate a simple signal for compatibility
        signal_data = generate_signal_for_symbol(symbol, bot_state['strategy'])
        
        if signal_data:
            return jsonify({
                'success': True,
                'symbol': symbol.upper(),
                'current_signal': signal_data['signal'],
                'signal_strength': signal_data['strength'],
                'signals': [{
                    'timestamp': datetime.now().isoformat(),
                    'symbol': symbol.upper(),
                    'signal': signal_data['signal'],
                    'strength': signal_data['strength'],
                    'price': signal_data['price'],
                    'reason': signal_data['reason']
                }]
            })
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'current_signal': 'HOLD',
            'signal_strength': 0,
            'signals': []
        })
        
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/bot/start', methods=['POST'])
async def start_bot():
    """Start the trading bot with real execution"""
    try:
        if bot_state['is_running']:
            return jsonify({
                'success': False,
                'message': 'Bot is already running',
                'status': 'running'
            })
        
        # Get configuration from request
        data = request.json or {}
        symbols = data.get('symbols', bot_state['active_symbols'])
        strategy = data.get('strategy', bot_state['strategy'])
        
        # Update bot state
        bot_state['is_running'] = True
        bot_state['start_time'] = datetime.now()
        bot_state['active_symbols'] = symbols
        bot_state['strategy'] = strategy
        
        # Start signal monitoring
        await signal_processor.start_monitoring()
        
        # Start the trading loop in background
        threading.Thread(target=run_trading_loop, daemon=True).start()
        
        logger.info(f"Trading bot started with symbols: {symbols}, strategy: {strategy}")
        
        # Notify frontend via WebSocket
        socketio.emit('bot_status', {
            'status': 'running',
            'symbols': symbols,
            'strategy': strategy,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': 'Trading bot started successfully',
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'bot_id': 'trading-executor-v1',
            'symbols': symbols,
            'strategy': strategy,
            'features': {
                'real_execution': True,
                'stop_loss': True,
                'position_sizing': True,
                'risk_management': True
            }
        })
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        bot_state['is_running'] = False
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/bot/stop', methods=['POST'])
async def stop_bot():
    """Stop the trading bot"""
    try:
        if not bot_state['is_running']:
            return jsonify({
                'success': False,
                'message': 'Bot is not running',
                'status': 'stopped'
            })
        
        # Stop signal monitoring
        await signal_processor.stop_monitoring()
        
        # Cancel all open orders
        await trading_executor.cancel_all_orders()
        
        # Update bot state
        bot_state['is_running'] = False
        bot_state['start_time'] = None
        
        logger.info("Trading bot stopped")
        
        # Notify frontend via WebSocket
        socketio.emit('bot_status', {
            'status': 'stopped',
            'timestamp': datetime.now().isoformat()
        })
        
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
    """Get detailed bot status"""
    try:
        uptime = None
        if bot_state['is_running'] and bot_state['start_time']:
            uptime_delta = datetime.now() - bot_state['start_time']
            uptime = f"{uptime_delta.total_seconds() / 60:.1f}m"
        
        # Get position summary
        position_summary = asyncio.run(trading_executor.get_position_summary())
        
        # Get signal statistics
        signal_stats = signal_processor.get_signal_statistics()
        
        return jsonify({
            'success': True,
            'status': 'running' if bot_state['is_running'] else 'stopped',
            'bot_id': 'trading-executor-v1',
            'uptime': uptime,
            'last_signal': bot_state['last_signal'],
            'trades_today': bot_state['trades_today'],
            'active_symbols': bot_state['active_symbols'],
            'strategy': bot_state['strategy'],
            'positions': position_summary,
            'signal_stats': signal_stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bot/execute_signal', methods=['POST'])
async def execute_signal():
    """Manually execute a trading signal (for testing)"""
    try:
        data = request.json
        
        # Create trading signal from request
        signal = TradingSignal(
            symbol=data['symbol'],
            action=data['action'],  # BUY or SELL
            strength=data.get('strength', 75),
            price=data.get('price', 0),
            timestamp=datetime.now(),
            reason=data.get('reason', 'Manual signal'),
            indicators=data.get('indicators', {})
        )
        
        # Process the signal
        result = await signal_processor.process_signal(signal.symbol, {
            'signal': signal.action,
            'strength': signal.strength,
            'price': signal.price,
            'reason': signal.reason,
            'indicators': signal.indicators
        })
        
        if result:
            bot_state['trades_today'] += 1
            bot_state['last_signal'] = {
                'symbol': signal.symbol,
                'action': signal.action,
                'timestamp': signal.timestamp.isoformat()
            }
            
            # Notify frontend
            socketio.emit('trade_executed', {
                'symbol': signal.symbol,
                'action': signal.action,
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'success': True,
                'message': f'Signal executed for {signal.symbol}',
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Signal not executed (validation failed or conditions not met)'
            })
            
    except Exception as e:
        logger.error(f"Error executing signal: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/positions/summary')
async def get_positions_summary():
    """Get detailed position summary with enhanced P&L and risk metrics"""
    try:
        summary = await trading_executor.get_position_summary()
        return jsonify({
            'success': True,
            **summary
        })
    except Exception as e:
        logger.error(f"Error getting position summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/positions/risk')
async def get_risk_status():
    """Get comprehensive risk management status"""
    try:
        risk_data = await trading_executor.check_risk_management()
        return jsonify({
            'success': True,
            **risk_data
        })
    except Exception as e:
        logger.error(f"Error getting risk status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/positions/<symbol>/levels', methods=['PUT'])
async def update_position_levels(symbol):
    """Update stop loss and take profit levels for a position"""
    try:
        data = request.json
        stop_loss = data.get('stop_loss')
        take_profit = data.get('take_profit')
        
        success = await trading_executor.update_position_levels(
            symbol.upper(), stop_loss, take_profit
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Updated levels for {symbol}',
                'stop_loss': stop_loss,
                'take_profit': take_profit
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update position levels'
            }), 400
            
    except Exception as e:
        logger.error(f"Error updating position levels: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/positions/<symbol>/close', methods=['POST'])
async def close_position(symbol):
    """Close a specific position"""
    try:
        data = request.json or {}
        reason = data.get('reason', 'manual_close')
        
        success = await trading_executor.close_position_by_symbol(
            symbol.upper(), reason
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Position closed for {symbol}',
                'reason': reason
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to close position'
            }), 400
            
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/positions/metrics')
async def get_portfolio_metrics():
    """Get comprehensive portfolio performance metrics"""
    try:
        metrics = await trading_executor.position_manager.get_portfolio_metrics()
        risk_report = await trading_executor.position_manager.get_risk_report()
        
        return jsonify({
            'success': True,
            'portfolio_metrics': {
                'total_positions': metrics.total_positions,
                'long_positions': metrics.long_positions,
                'short_positions': metrics.short_positions,
                'total_market_value': metrics.total_market_value,
                'total_unrealized_pnl': metrics.total_unrealized_pnl,
                'total_unrealized_pnl_pct': metrics.total_unrealized_pnl_pct,
                'largest_position': metrics.largest_position,
                'portfolio_concentration': metrics.portfolio_concentration,
                'win_rate': metrics.win_rate,
                'avg_hold_time_hours': metrics.avg_hold_time.total_seconds() / 3600
            },
            'risk_metrics': risk_report,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting portfolio metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders/active')
def get_active_orders():
    """Get all active orders"""
    try:
        orders = api.list_orders(status='open')
        order_list = []
        
        for order in orders:
            order_list.append({
                'id': order.id,
                'symbol': order.symbol,
                'side': order.side,
                'qty': order.qty,
                'type': order.order_type,
                'status': order.status,
                'submitted_at': order.submitted_at.isoformat() if order.submitted_at else None,
                'limit_price': order.limit_price,
                'stop_price': order.stop_price
            })
        
        return jsonify({
            'success': True,
            'orders': order_list,
            'count': len(order_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting active orders: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders/cancel/<order_id>', methods=['POST'])
def cancel_order(order_id):
    """Cancel a specific order"""
    try:
        api.cancel_order(order_id)
        
        return jsonify({
            'success': True,
            'message': f'Order {order_id} cancelled'
        })
        
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders/cancel_all', methods=['POST'])
async def cancel_all_orders():
    """Cancel all open orders"""
    try:
        await trading_executor.cancel_all_orders()
        
        return jsonify({
            'success': True,
            'message': 'All orders cancelled'
        })
        
    except Exception as e:
        logger.error(f"Error cancelling all orders: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== TRADING LOOP ====================

def run_trading_loop():
    """Main trading loop that monitors signals and executes trades"""
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    
    while bot_state['is_running']:
        try:
            # Check each symbol for signals
            for symbol in bot_state['active_symbols']:
                # Get latest market data and generate signal
                signal_data = generate_signal_for_symbol(symbol, bot_state['strategy'])
                
                if signal_data and signal_data['signal'] != 'HOLD':
                    # Process the signal
                    loop.run_until_complete(
                        signal_processor.process_signal(symbol, signal_data)
                    )
                    
                    # Update bot state
                    bot_state['last_signal'] = {
                        'symbol': symbol,
                        'action': signal_data['signal'],
                        'timestamp': datetime.now().isoformat()
                    }
            
            # Sleep before next iteration
            loop.run_until_complete(asyncio.sleep(60))  # Check every minute
            
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            loop.run_until_complete(asyncio.sleep(10))

def generate_signal_for_symbol(symbol: str, strategy: str) -> Optional[Dict]:
    """
    Generate trading signal for a symbol using specified strategy
    
    This is a placeholder - you would integrate your actual strategy here
    """
    try:
        # Get latest bars
        bars = api.get_bars(symbol, '15Min', limit=100, feed='iex')
        bars_list = list(bars)
        
        if not bars_list:
            return None
        
        # Simple example signal generation (replace with actual strategy)
        latest_bar = bars_list[-1]
        prev_bar = bars_list[-2] if len(bars_list) > 1 else latest_bar
        
        # Calculate simple momentum
        momentum = (float(latest_bar.c) - float(prev_bar.c)) / float(prev_bar.c)
        
        # Generate signal based on momentum
        if momentum > 0.002:  # 0.2% positive momentum
            return {
                'signal': 'BUY',
                'strength': min(100, abs(momentum) * 10000),
                'price': float(latest_bar.c),
                'reason': f'Positive momentum: {momentum:.4f}',
                'indicators': {
                    'momentum': momentum,
                    'volume_confirmed': latest_bar.v > prev_bar.v
                }
            }
        elif momentum < -0.002:  # 0.2% negative momentum
            return {
                'signal': 'SELL',
                'strength': min(100, abs(momentum) * 10000),
                'price': float(latest_bar.c),
                'reason': f'Negative momentum: {momentum:.4f}',
                'indicators': {
                    'momentum': momentum,
                    'volume_confirmed': latest_bar.v > prev_bar.v
                }
            }
        
        return {
            'signal': 'HOLD',
            'strength': 0,
            'price': float(latest_bar.c),
            'reason': 'No clear signal'
        }
        
    except Exception as e:
        logger.error(f"Error generating signal for {symbol}: {e}")
        return None

# ==================== WebSocket Event Handlers ====================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {
        'message': 'Connected to trading server',
        'bot_status': 'running' if bot_state['is_running'] else 'stopped'
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('request_bot_status')
def handle_status_request():
    """Handle bot status request"""
    emit('bot_status', {
        'status': 'running' if bot_state['is_running'] else 'stopped',
        'trades_today': bot_state['trades_today'],
        'last_signal': bot_state['last_signal'],
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    logger.info("🚀 Starting Flask app with Trading Execution Engine on port 9765")
    socketio.run(app, host='0.0.0.0', port=9765, debug=False, allow_unsafe_werkzeug=True)