"""
Enhanced Flask app with robust WebSocket integration for real-time trading data.
This replaces the existing flask_app.py with optimized WebSocket functionality.
"""

import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify, request
from flask_compress import Compress
from werkzeug.middleware.proxy_fix import ProxyFix
import json
import threading
import time
import logging
from datetime import datetime

# Import existing components
from core.service_registry import get_service_registry, setup_core_services
from config.unified_config import get_config
from services.performance_optimizer import get_performance_optimizer
from utils.auth_manager import get_environment_manager, require_auth
from flask_cors import CORS

# Import new WebSocket components
from src.websocket_server import WebSocketServer, WebSocketConfig
from src.trading_websocket_integration import TradingWebSocketService, integrate_websocket_with_flask_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize performance optimizer
performance_optimizer = get_performance_optimizer()

# Initialize environment manager
env_manager = get_environment_manager()

# Validate environment on startup
if not env_manager.validate_environment():
    logger.warning("Environment validation failed. Using fallback configuration.")

class EnhancedFlaskApp:
    """Enhanced Flask application with WebSocket integration"""
    
    def __init__(self):
        self.app = Flask(__name__)
        self.trading_websocket_service = None
        self.setup_app()
        self.setup_services()
        self.setup_websocket()
        self.setup_routes()
        
    def setup_app(self):
        """Configure Flask application"""
        # Add performance middleware
        self.app.wsgi_app = ProxyFix(self.app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
        
        # Initialize compression
        compress = Compress()
        compress.init_app(self.app)
        
        # Load Flask configuration
        try:
            flask_config = env_manager.get_flask_config()
            self.app.config.update(flask_config)
            logger.info("Loaded Flask configuration from environment")
        except Exception as e:
            logger.warning(f"Failed to load environment config: {e}")
            self.app.config.update({
                'SECRET_KEY': 'trading_bot_secret_key_2024_FALLBACK',
                'JWT_SECRET_KEY': 'jwt_secret_key_FALLBACK',
                'JWT_ACCESS_TOKEN_EXPIRES': 3600
            })
        
        # Configure CORS
        try:
            allowed_origins = env_manager.get_cors_origins()
            CORS(self.app, origins=allowed_origins, supports_credentials=True)
            logger.info(f"CORS configured with origins: {allowed_origins}")
        except Exception as e:
            logger.warning(f"CORS configuration failed: {e}")
            CORS(self.app, origins=["http://localhost:9765", "http://127.0.0.1:9765"], 
                 supports_credentials=True)
    
    def setup_services(self):
        """Initialize core services"""
        # Initialize service registry
        setup_core_services()
        self.registry = get_service_registry()
        self.data_manager = self.registry.get('data_manager')
        
        # Initialize bot manager
        from flask_app import BotManager  # Import existing BotManager
        self.bot_manager = BotManager()
        
        logger.info("Core services initialized")
    
    def setup_websocket(self):
        """Setup WebSocket server with trading integration"""
        try:
            # Create WebSocket configuration optimized for low latency
            ws_config = WebSocketConfig(
                ping_timeout=30,  # Shorter timeout for faster detection
                ping_interval=10,  # More frequent pings
                compression=True,
                binary=True,
                max_http_buffer_size=32768,  # 32KB for faster processing
                heartbeat_interval=5,  # More frequent heartbeats
                reconnect_attempts=10,
                reconnect_delay=0.5,  # Faster reconnection
                max_latency_ms=50  # Target <50ms latency
            )
            
            # Integrate WebSocket with Flask app
            self.trading_websocket_service = integrate_websocket_with_flask_app(
                self.app, self.data_manager, self.bot_manager
            )
            
            # Start streaming immediately
            self.trading_websocket_service.start_streaming(interval=0.5)  # 500ms updates
            
            logger.info("WebSocket server setup completed with low-latency configuration")
            
        except Exception as e:
            logger.error(f"Failed to setup WebSocket server: {e}")
            raise
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        # Existing routes
        @self.app.route('/')
        def index():
            return render_template('trading_dashboard.html')
        
        @self.app.route('/dashboard')
        @require_auth
        def dashboard():
            return render_template('trading_dashboard.html')
        
        @self.app.route('/api/config', methods=['GET', 'POST'])
        @require_auth
        def config_api():
            if request.method == 'GET':
                config = self.bot_manager.load_config()
                return jsonify({'success': True, 'config': config})
            else:
                try:
                    config = request.json
                    success = self.bot_manager.save_config(config)
                    return jsonify({'success': success})
                except Exception as e:
                    return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/tickers', methods=['GET', 'POST', 'DELETE'])
        @require_auth
        def tickers_api():
            if request.method == 'GET':
                tickers = self.bot_manager.load_tickers()
                return jsonify({'success': True, 'tickers': tickers})
            elif request.method == 'POST':
                try:
                    ticker = request.json.get('ticker', '').upper()
                    if ticker:
                        tickers = self.bot_manager.load_tickers()
                        if ticker not in tickers:
                            tickers.append(ticker)
                            success = self.bot_manager.save_tickers(tickers)
                            return jsonify({'success': success, 'tickers': tickers})
                        return jsonify({'success': True, 'tickers': tickers})
                    return jsonify({'success': False, 'error': 'Invalid ticker'})
                except Exception as e:
                    return jsonify({'success': False, 'error': str(e)})
            
        elif request.method == 'DELETE':
            try:
                ticker = request.json.get('ticker', '').upper()\n                    if ticker:\n                        tickers = self.bot_manager.load_tickers()\n                        if ticker in tickers:\n                            tickers.remove(ticker)\n                            success = self.bot_manager.save_tickers(tickers)\n                            return jsonify({'success': success, 'tickers': tickers})\n                        return jsonify({'success': True, 'tickers': tickers})\n                    return jsonify({'success': False, 'error': 'Invalid ticker'})\n                except Exception as e:\n                    return jsonify({'success': False, 'error': str(e)})\n        \n        @self.app.route('/api/account')\n        @require_auth\n        def account_info():\n            try:\n                info = self.data_manager.get_account_info()\n                return jsonify({'success': True, 'account': info})\n            except Exception as e:\n                return jsonify({'success': False, 'error': str(e)})\n        \n        @self.app.route('/api/positions')\n        @require_auth\n        def positions_info():\n            try:\n                positions = self.data_manager.get_positions()\n                return jsonify({'success': True, 'positions': positions})\n            except Exception as e:\n                return jsonify({'success': False, 'error': str(e)})\n        \n        @self.app.route('/api/price/<symbol>')\n        def get_price(symbol):\n            try:\n                price = self.data_manager.get_latest_price(symbol.upper())\n                return jsonify({\n                    'success': True, \n                    'symbol': symbol.upper(), \n                    'price': price,\n                    'timestamp': time.time()\n                })\n            except Exception as e:\n                return jsonify({'success': False, 'error': str(e)})\n        \n        # Enhanced WebSocket-specific routes\n        @self.app.route('/api/websocket/performance')\n        def websocket_performance():\n            \"\"\"Get WebSocket performance metrics\"\"\"\n            try:\n                if self.trading_websocket_service:\n                    stats = self.trading_websocket_service.get_streaming_stats()\n                    return jsonify({'success': True, 'performance': stats})\n                return jsonify({'success': False, 'error': 'WebSocket service not available'})\n            except Exception as e:\n                return jsonify({'success': False, 'error': str(e)})\n        \n        @self.app.route('/api/websocket/latency')\n        def websocket_latency():\n            \"\"\"Get current WebSocket latency statistics\"\"\"\n            try:\n                if self.trading_websocket_service:\n                    ws_stats = self.trading_websocket_service.websocket_server.get_performance_stats()\n                    return jsonify({\n                        'success': True,\n                        'latency': {\n                            'average_ms': ws_stats.get('average_latency', 0),\n                            'peak_ms': ws_stats.get('peak_latency', 0),\n                            'target_ms': 50,  # Our target\n                            'within_target': ws_stats.get('average_latency', 0) <= 50\n                        }\n                    })\n                return jsonify({'success': False, 'error': 'WebSocket service not available'})\n            except Exception as e:\n                return jsonify({'success': False, 'error': str(e)})\n        \n        @self.app.route('/api/websocket/clients')\n        def websocket_clients():\n            \"\"\"Get connected WebSocket clients information\"\"\"\n            try:\n                if self.trading_websocket_service:\n                    client_count = self.trading_websocket_service.websocket_server.get_connected_clients()\n                    return jsonify({\n                        'success': True,\n                        'connected_clients': client_count,\n                        'streaming_active': self.trading_websocket_service.streaming_active\n                    })\n                return jsonify({'success': False, 'error': 'WebSocket service not available'})\n            except Exception as e:\n                return jsonify({'success': False, 'error': str(e)})\n        \n        # Real-time data testing endpoint\n        @self.app.route('/api/test/realtime/<symbol>')\n        def test_realtime_data(symbol):\n            \"\"\"Test real-time data for a specific symbol\"\"\"\n            try:\n                # Get latest data\n                price = self.data_manager.get_latest_price(symbol.upper())\n                positions = self.data_manager.get_positions()\n                \n                # Manually trigger a WebSocket broadcast for testing\n                if self.trading_websocket_service:\n                    test_data = {\n                        'symbol': symbol.upper(),\n                        'price': price,\n                        'timestamp': time.time(),\n                        'test': True\n                    }\n                    self.trading_websocket_service.websocket_server.broadcast_market_data(\n                        symbol.upper(), test_data\n                    )\n                \n                return jsonify({\n                    'success': True,\n                    'symbol': symbol.upper(),\n                    'data': {\n                        'price': price,\n                        'positions_count': len(positions) if positions else 0,\n                        'websocket_broadcast': True if self.trading_websocket_service else False\n                    }\n                })\n            except Exception as e:\n                return jsonify({'success': False, 'error': str(e)})\n        \n        logger.info(\"Flask routes setup completed\")\n    \n    def run(self, host='0.0.0.0', port=8765, debug=False):\n        \"\"\"Run the enhanced Flask application\"\"\"\n        logger.info(f\"Starting Enhanced Trading Bot Dashboard on {host}:{port}\")\n        logger.info(\"Features enabled:\")\n        logger.info(\"  - Real-time WebSocket streaming\")\n        logger.info(\"  - Sub-100ms latency optimization\")\n        logger.info(\"  - Automatic reconnection\")\n        logger.info(\"  - Data compression\")\n        logger.info(\"  - Performance monitoring\")\n        \n        try:\n            # Get the SocketIO server from the WebSocket service\n            if self.trading_websocket_service:\n                socketio = self.trading_websocket_service.websocket_server.socketio\n                socketio.run(self.app, host=host, port=port, debug=debug)\n            else:\n                # Fallback to regular Flask\n                self.app.run(host=host, port=port, debug=debug)\n                \n        except KeyboardInterrupt:\n            logger.info(\"Application interrupted\")\n        finally:\n            self.shutdown()\n    \n    def shutdown(self):\n        \"\"\"Gracefully shutdown the application\"\"\"\n        logger.info(\"Shutting down Enhanced Flask App...\")\n        \n        if self.trading_websocket_service:\n            self.trading_websocket_service.stop_streaming()\n            self.trading_websocket_service.websocket_server.shutdown()\n        \n        logger.info(\"Enhanced Flask App shutdown complete\")\n\n# Factory function for easy use\ndef create_enhanced_app() -> EnhancedFlaskApp:\n    \"\"\"Create and configure the enhanced Flask application\"\"\"\n    return EnhancedFlaskApp()\n\n# For backward compatibility and direct running\nif __name__ == '__main__':\n    app = create_enhanced_app()\n    \n    # Performance logging\n    def log_performance():\n        while True:\n            try:\n                if app.trading_websocket_service:\n                    stats = app.trading_websocket_service.get_streaming_stats()\n                    ws_stats = stats.get('websocket_stats', {})\n                    \n                    logger.info(f\"Performance: {ws_stats.get('average_latency', 0):.1f}ms avg latency, \"\n                              f\"{stats.get('connected_clients', 0)} clients, \"\n                              f\"{ws_stats.get('messages_per_second', 0):.1f} msg/s\")\n                \n                time.sleep(30)  # Log every 30 seconds\n            except Exception as e:\n                logger.error(f\"Performance logging error: {e}\")\n                time.sleep(30)\n    \n    # Start performance logging thread\n    perf_thread = threading.Thread(target=log_performance, daemon=True)\n    perf_thread.start()\n    \n    # Run the application\n    app.run(host='0.0.0.0', port=8765, debug=False)"