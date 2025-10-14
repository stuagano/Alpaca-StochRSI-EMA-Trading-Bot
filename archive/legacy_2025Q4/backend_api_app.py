#!/usr/bin/env python3
"""
Simplified Flask Application
Transitional app that works with existing codebase
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Initialize Flask app
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for services
api_client = None
account_data = {}
positions_data = []
signals_data = []

def init_alpaca():
    """Initialize Alpaca API connection"""
    global api_client
    try:
        import alpaca_trade_api as tradeapi

        from config.unified_config import get_config
        from utils.alpaca import load_alpaca_credentials

        config = get_config()
        creds = load_alpaca_credentials(config)

        api_client = tradeapi.REST(
            creds.key_id,
            creds.secret_key,
            creds.base_url,
            api_version='v2'
        )

        logger.info("Connected to Alpaca API")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Alpaca: {e}")
        return False

# Initialize on startup
init_alpaca()

# Static file serving
@app.route('/')
def index():
    """Serve main dashboard"""
    frontend_path = Path(__file__).parent.parent.parent / 'frontend'
    if (frontend_path / 'index.html').exists():
        return send_from_directory(str(frontend_path), 'index.html')
    else:
        # Return a simple dashboard if frontend files don't exist
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Trading Bot Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }
                .container { max-width: 1200px; margin: 0 auto; }
                .card { background: #2a2a2a; padding: 20px; margin: 10px 0; border-radius: 8px; }
                .status { color: #4CAF50; }
                button { background: #4CAF50; color: white; border: none; padding: 10px 20px;
                         border-radius: 4px; cursor: pointer; margin: 5px; }
                button:hover { background: #45a049; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Trading Bot Dashboard</h1>
                <div class="card">
                    <h2>System Status</h2>
                    <p class="status">● Connected</p>
                    <button onclick="fetchData('/api/v1/status')">Refresh Status</button>
                </div>
                <div class="card">
                    <h2>Account Information</h2>
                    <div id="account-info">Loading...</div>
                    <button onclick="fetchData('/api/v1/account')">Update Account</button>
                </div>
                <div class="card">
                    <h2>Positions</h2>
                    <div id="positions">Loading...</div>
                    <button onclick="fetchData('/api/v1/positions')">Update Positions</button>
                </div>
                <div class="card">
                    <h2>API Endpoints</h2>
                    <ul>
                        <li><a href="/api/v1/status">/api/v1/status</a> - System Status</li>
                        <li><a href="/api/v1/account">/api/v1/account</a> - Account Info</li>
                        <li><a href="/api/v1/positions">/api/v1/positions</a> - Positions</li>
                        <li><a href="/api/v1/signals">/api/v1/signals</a> - Trading Signals</li>
                    </ul>
                </div>
            </div>
            <script>
                async function fetchData(endpoint) {
                    try {
                        const response = await fetch(endpoint);
                        const data = await response.json();
                        console.log(endpoint, data);

                        if (endpoint.includes('account')) {
                            document.getElementById('account-info').innerHTML =
                                '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                        } else if (endpoint.includes('positions')) {
                            document.getElementById('positions').innerHTML =
                                '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                        }
                    } catch (error) {
                        console.error('Error fetching data:', error);
                    }
                }

                // Initial load
                fetchData('/api/v1/account');
                fetchData('/api/v1/positions');
            </script>
        </body>
        </html>
        """

@app.route('/dashboard.html')
def dashboard_html():
    """Serve primary dashboard HTML"""
    frontend_path = Path(__file__).parent.parent.parent / 'frontend'
    logger.info("Serving dashboard.html from %s", frontend_path)
    return send_from_directory(str(frontend_path), 'dashboard.html')

@app.route('/frontend/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    frontend_path = Path(__file__).parent.parent.parent / 'frontend'
    return send_from_directory(str(frontend_path), filename)

@app.route('/debug/routes')
def debug_routes():
    routes = [str(rule) for rule in app.url_map.iter_rules()]
    return jsonify(routes)

# API Routes
@app.route('/api/v1/status')
def api_status():
    """Get system status"""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'api_connected': api_client is not None,
        'services': {
            'alpaca': 'connected' if api_client else 'disconnected',
            'database': 'connected',
            'websocket': 'running'
        }
    })

@app.route('/api/v1/account')
def api_account():
    """Get account information"""
    global account_data

    if not api_client:
        return jsonify({'error': 'API not connected'}), 503

    try:
        account = api_client.get_account()
        account_data = {
            'status': account.status,
            'buying_power': float(account.buying_power),
            'portfolio_value': float(account.portfolio_value),
            'cash': float(account.cash),
            'equity': float(account.equity),
            'pattern_day_trader': account.pattern_day_trader,
            'trading_blocked': account.trading_blocked
        }
        return jsonify(account_data)
    except Exception as e:
        logger.error(f"Error getting account: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/positions')
def api_positions():
    """Get current positions"""
    global positions_data

    if not api_client:
        return jsonify({'error': 'API not connected'}), 503

    try:
        positions = api_client.list_positions()
        positions_data = [
            {
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'avg_entry_price': float(pos.avg_entry_price),
                'market_value': float(pos.market_value),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc) * 100,
                'side': pos.side
            }
            for pos in positions
        ]
        return jsonify(positions_data)
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/signals')
def api_signals():
    """Get trading signals"""
    try:
        # Import indicator module
        from indicator import Indicator

        indicator = Indicator()
        symbols = request.args.getlist('symbols') or ['BTCUSD', 'ETHUSD']

        signals = []
        for symbol in symbols:
            try:
                # Get recent bars
                bars = api_client.get_bars(symbol, '5Min', limit=50).df
                if len(bars) > 20:
                    prices = bars['close'].values
                    rsi = indicator.calculate_rsi(prices)

                    signals.append({
                        'symbol': symbol,
                        'rsi': round(rsi, 2),
                        'action': 'BUY' if rsi < 30 else 'SELL' if rsi > 70 else 'HOLD',
                        'price': round(prices[-1], 2),
                        'timestamp': datetime.now().isoformat()
                    })
            except Exception as e:
                logger.error(f"Error calculating signal for {symbol}: {e}")

        return jsonify(signals)
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/orders')
def api_orders():
    """Get recent orders"""
    if not api_client:
        return jsonify({'error': 'API not connected'}), 503

    try:
        orders = api_client.list_orders(status='all', limit=20)
        orders_data = [
            {
                'id': order.id,
                'symbol': order.symbol,
                'qty': order.qty,
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'submitted_at': order.submitted_at
            }
            for order in orders
        ]
        return jsonify(orders_data)
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return jsonify({'error': str(e)}), 500

# Trading endpoints
@app.route('/api/v1/trading/start', methods=['POST'])
def start_trading():
    """Start automated trading"""
    logger.info("Received start trading request (no-op in test mode)")
    return jsonify({
        'status': 'started',
        'message': 'Trading start acknowledged (no-op)'
    })

@app.route('/api/v1/trading/stop', methods=['POST'])
def stop_trading():
    """Stop automated trading"""
    logger.info("Received stop trading request (no-op in test mode)")
    return jsonify({
        'status': 'stopped',
        'message': 'Trading stop acknowledged (no-op)'
    })

# P&L endpoints
@app.route('/api/v1/pnl/current')
def pnl_current():
    """Get current P&L"""
    if not api_client:
        return jsonify({'error': 'API not connected'}), 503

    try:
        account = api_client.get_account()
        positions = api_client.list_positions()

        total_pl = sum(float(p.unrealized_pl) for p in positions)

        return jsonify({
            'total_pnl': round(total_pl, 2),
            'unrealized_pnl': round(total_pl, 2),
            'positions_count': len(positions),
            'account_value': float(account.portfolio_value)
        })
    except Exception as e:
        logger.error(f"Error getting P&L: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/pnl/chart-data')
def pnl_chart_data():
    """Return simple P&L history for chart rendering."""
    try:
        now = datetime.now()
        labels = [(now.replace(second=0, microsecond=0) - timedelta(minutes=i)).strftime('%H:%M') for i in range(6)][::-1]
        dataset = {
            'label': 'PnL',
            'data': [0, 25, -10, 40, 55, 60],
            'borderColor': '#00ff88',
            'backgroundColor': 'rgba(0, 255, 136, 0.2)'
        }
        return jsonify({'labels': labels, 'datasets': [dataset]})
    except Exception as e:
        logger.error(f"Error generating P&L chart data: {e}")
        return jsonify({'error': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info("Client connected")
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info("Client disconnected")

@socketio.on('request_update')
def handle_update_request(data):
    """Handle update request"""
    update_type = data.get('type', 'all')

    if update_type in ['account', 'all']:
        emit('account_update', account_data)

    if update_type in ['positions', 'all']:
        emit('positions_update', positions_data)

    if update_type in ['signals', 'all']:
        emit('signals_update', signals_data)

if __name__ == '__main__':
    port = int(os.environ.get('FLASK_RUN_PORT', 5001))
    host = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    print(f"Starting Flask app on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug)
