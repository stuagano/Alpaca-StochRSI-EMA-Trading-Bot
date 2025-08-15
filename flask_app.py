import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify, request, g, send_from_directory, Response
from flask_socketio import SocketIO, emit
from flask_compress import Compress
from werkzeug.middleware.proxy_fix import ProxyFix
import json
import pandas as pd
import numpy as np
import os
import subprocess
import threading
import time
import gzip
import functools
from datetime import datetime, timedelta
from core.service_registry import get_service_registry, setup_core_services
from config.unified_config import get_config, get_legacy_config
from services.performance_optimizer import get_performance_optimizer
from services.async_data_fetcher import get_global_fetcher, get_global_ws_manager
import logging
from utils.auth_manager import get_environment_manager, require_auth, create_demo_token
from utils.secure_config_loader import get_secure_config_loader, validate_security
from flask_cors import CORS
import hashlib
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Configure logging (ERROR level for production debugging)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Initialize performance optimizer
performance_optimizer = get_performance_optimizer()
thread_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="FlaskWorker")

# Initialize environment manager
env_manager = get_environment_manager()

# Validate environment on startup
if not env_manager.validate_environment():
    logger.critical("Environment validation failed. Please check your .env file.")
    logger.critical("Copy .env.example to .env and configure your credentials.")
    # Continue with legacy mode but log warnings

# Flask app configuration
app = Flask(__name__)

# Add performance middleware
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Initialize compression
compress = Compress()
compress.init_app(app)

# Cache configuration
CACHE_TIMEOUT = 300  # 5 minutes
REALTIME_CACHE_TIMEOUT = 10  # 10 seconds
STATIC_CACHE_TIMEOUT = 3600  # 1 hour

# Load Flask configuration from environment
try:
    flask_config = env_manager.get_flask_config()
    app.config.update(flask_config)
    logger.info("Loaded Flask configuration from environment")
except Exception as e:
    logger.warning(f"Failed to load environment config: {e}")
    logger.warning("Using fallback configuration - SECURITY WARNING!")
    app.config['SECRET_KEY'] = 'trading_bot_secret_key_2024_INSECURE_FALLBACK'
    app.config['JWT_SECRET_KEY'] = 'jwt_secret_key_INSECURE_FALLBACK'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600

# Configure CORS with specific origins
try:
    allowed_origins = env_manager.get_cors_origins()
    CORS(app, origins=allowed_origins, supports_credentials=True)
    logger.info(f"CORS configured with origins: {allowed_origins}")
except Exception as e:
    logger.warning(f"CORS configuration failed: {e}")
    # Fallback to localhost only
    CORS(app, origins=["http://localhost:8765", "http://127.0.0.1:8765"], supports_credentials=True)

# WebSocket configuration
websocket_compression = True
websocket_buffer_size = 64 * 1024  # 64KB buffer

# Initialize SocketIO with secure CORS and performance optimizations
try:
    allowed_origins = env_manager.get_cors_origins()
    socketio = SocketIO(
        app, 
        cors_allowed_origins=allowed_origins, 
        logger=False, 
        engineio_logger=False,
        # Performance optimizations
        async_mode='eventlet',
        ping_timeout=60,
        ping_interval=25,
        compression=websocket_compression,
        binary=True,
        # Buffer and queue settings
        max_http_buffer_size=websocket_buffer_size,
        # JSON serialization optimization
        json=json
    )
except Exception as e:
    logger.warning(f"SocketIO CORS configuration failed: {e}")
    socketio = SocketIO(
        app, 
        cors_allowed_origins=["http://localhost:8765", "http://127.0.0.1:8765"], 
        logger=False, 
        engineio_logger=False,
        async_mode='eventlet',
        ping_timeout=60,
        ping_interval=25,
        compression=websocket_compression,
        binary=True,
        max_http_buffer_size=websocket_buffer_size,
        json=json
    )

from trading_bot import TradingBot
from main import get_strategy


# Performance optimization decorators and utilities
def cache_response(timeout=CACHE_TIMEOUT, key_func=None):
    """Decorator for caching API responses."""
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{f.__name__}_{hash(str(args) + str(kwargs))}"
            
            # Check cache
            with cache_lock:
                if cache_key in response_cache:
                    cached_data, timestamp = response_cache[cache_key]
                    if time.time() - timestamp < timeout:
                        return cached_data
            
            # Execute function
            result = f(*args, **kwargs)
            
            # Cache result
            with cache_lock:
                response_cache[cache_key] = (result, time.time())
                
                # Clean old entries periodically
                if len(response_cache) % 100 == 0:
                    current_time = time.time()
                    expired_keys = [
                        k for k, (_, ts) in response_cache.items()
                        if current_time - ts > timeout * 2
                    ]
                    for k in expired_keys:
                        del response_cache[k]
            
            return result
        return wrapper
    return decorator


def compress_response(response_data):
    """Compress response data if beneficial."""
    if isinstance(response_data, (dict, list)):
        json_data = json.dumps(response_data, separators=(',', ':'))
        if len(json_data) > 1024:  # Only compress if > 1KB
            compressed = gzip.compress(json_data.encode('utf-8'))
            if len(compressed) < len(json_data) * 0.9:  # Only if 10%+ compression
                return compressed, True
    return response_data, False


def async_route(f):
    """Decorator to run route handlers in thread pool."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if asyncio.iscoroutinefunction(f):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(f(*args, **kwargs))
            finally:
                loop.close()
        else:
            # For now, just run synchronously to avoid context issues
            return f(*args, **kwargs)
    return wrapper


def optimize_json_response(data, cache_timeout=None):
    """Optimize JSON response with caching headers."""
    response = jsonify(data)
    
    # Add performance headers
    if cache_timeout:
        response.cache_control.max_age = cache_timeout
        response.cache_control.public = True
    
    # Add ETag for client-side caching
    if isinstance(data, dict) and data.get('success'):
        etag = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
        response.set_etag(etag)
        
        # Check if client has cached version
        if request.if_none_match and etag in request.if_none_match:
            return '', 304
    
    # Compression hint
    response.headers['Vary'] = 'Accept-Encoding'
    
    return response


# CDN and static file optimization
@app.route('/static/<path:filename>')
def optimized_static(filename):
    """Serve static files with optimization."""
    response = send_from_directory(app.static_folder, filename)
    
    # Set aggressive caching for static files
    response.cache_control.max_age = STATIC_CACHE_TIMEOUT
    response.cache_control.public = True
    
    # Add immutable hint for versioned files
    if '.' in filename and any(filename.endswith(ext) for ext in ['.css', '.js', '.png', '.jpg', '.gif']):
        response.cache_control.immutable = True
    
    return response

# Global variables
bot_thread = None
bot_running = False
streaming_active = False
refresh_interval = 5
bot_manager = None  # Will be initialized after class definition

# Initialize service registry
setup_core_services()
registry = get_service_registry()
data_manager = registry.get('data_manager')

# Response cache
response_cache = {}
cache_lock = threading.RLock()

# WebSocket optimization - moved to top of file

class BotManager:
    def __init__(self):
        self.bot_thread = None
        self.bot_running = False
        self.secure_loader = get_secure_config_loader()
    
    def load_tickers(self):
        """Load tickers from file"""
        try:
            with open('AUTH/Tickers.txt', 'r') as f:
                return f.read().strip().split()
        except Exception as e:
            logger.error(f"Error loading tickers: {e}")
            return []
    
    def save_tickers(self, tickers):
        """Save tickers to file"""
        try:
            with open('AUTH/Tickers.txt', 'w') as f:
                f.write(' '.join(tickers))
            return True
        except Exception as e:
            logger.error(f"Error saving tickers: {e}")
            return False
    
    def load_config(self):
        """Load configuration with security enhancements"""
        try:
            # Use the unified config system
            config = get_config()
            
            # Log security warnings
            security_status = validate_security()
            if not security_status['secure']:
                logger.warning("Security validation failed. Check your environment configuration.")
                for error in security_status['errors']:
                    logger.error(f"Security error: {error}")
                for warning in security_status['warnings']:
                    logger.warning(f"Security warning: {warning}")
            
            return config
        except Exception as e:
            logger.error(f"Error during secure config loading: {e}")
            # Fallback to legacy config for backward compatibility
            return get_legacy_config()
    
    def save_config(self, config_data):
        """Save configuration"""
        # For now, return True as config is loaded from YAML
        return True
    
    def load_orders(self):
        """Load orders from file"""
        try:
            import csv
            orders = []
            if os.path.exists('ORDERS/Orders.csv'):
                with open('ORDERS/Orders.csv', 'r') as f:
                    reader = csv.DictReader(f)
                    orders = list(reader)
            return orders
        except Exception as e:
            logger.error(f"Error loading orders: {e}")
            return []
    
    def is_bot_running(self):
        """Check if bot is running"""
        return self.bot_running

class BotService:
    def __init__(self):
        self.bot_thread = None
        self.bot_running = False

    def start_bot(self):
        if not self.bot_running:
            config = get_config()
            strategy_name = config.strategy
            strategy = get_strategy(strategy_name, config)
            bot = TradingBot(data_manager, strategy)
            
            self.bot_thread = threading.Thread(target=bot.run)
            self.bot_thread.daemon = True
            self.bot_thread.start()
            self.bot_running = True
            logger.info("Trading bot started")
        return True

    def stop_bot(self):
        if self.bot_running:
            # This is a simplified stop mechanism. A more robust solution would involve
            # a more graceful shutdown of the bot's loop.
            self.bot_running = False
            if self.bot_thread.is_alive():
                # This is not ideal, but for now it's the only way to stop the thread.
                # A better approach would be to have a flag in the bot's run loop.
                pass
            logger.info("Trading bot stopped")
        return True

    def is_bot_running(self):
        return self.bot_running

bot_service = BotService()

# Real-time data streaming thread with performance optimizations
def real_time_data_thread():
    global streaming_active, refresh_interval
    logger.info("Real-time data thread started.")
    
    # Initialize performance tracking
    last_performance_log = time.time()
    performance_interval = 60  # Log performance every minute
    
    # Data compression for WebSocket
    last_full_update = 0
    incremental_update_interval = 5  # Send incremental updates every 5 seconds
    full_update_interval = 30  # Send full updates every 30 seconds
    
    while True:
        if streaming_active:
            try:
                current_time = time.time()
                tickers = bot_manager.load_tickers()
                
                # Use performance monitoring
                context = performance_optimizer.monitor.start_operation('real_time_streaming')
                
                logger.info(f"Streaming active: fetching data for tickers: {tickers}")

                if not tickers:
                    logger.warning("No tickers configured. Pausing for refresh interval.")
                    socketio.sleep(refresh_interval)
                    continue

                account_info = data_manager.get_account_info()
                positions = data_manager.get_positions()
                config = bot_manager.load_config()

                ticker_prices = {}
                ticker_signals = {}
                ticker_candlesticks = {}

                if not config:
                    logger.error("Config not found. Cannot calculate signals.")
                else:
                    # Convert unified config to legacy format for indicators
                    config_dict = {
                        'indicators': {
                            'stochRSI': "True" if config.indicators.stochRSI.enabled else "False",
                            'stochRSI_params': {
                                'rsi_length': config.indicators.stochRSI.rsi_length,
                                'stoch_length': config.indicators.stochRSI.stoch_length,
                                'K': config.indicators.stochRSI.K,
                                'D': config.indicators.stochRSI.D,
                                'lower_band': config.indicators.stochRSI.lower_band,
                                'upper_band': config.indicators.stochRSI.upper_band
                            },
                            'EMA': "True" if config.indicators.EMA.enabled else "False",
                            'EMA_params': {
                                'ema_period': config.indicators.EMA.ema_period
                            }
                        }
                    }
                    
                    for ticker in tickers:
                        price = data_manager.get_latest_price(ticker)
                        if price:
                            ticker_prices[ticker] = price
                            data = data_manager.get_historical_data(ticker, timeframe='1Min', start_hours_ago=2, limit=50)
                            
                            # Add candlestick data for live charts
                            if not data.empty:
                                # Get last 20 bars for candlestick chart
                                recent_data = data.tail(20)
                                # Convert to LightweightCharts format
                                candlesticks = []
                                for i, (timestamp, row) in enumerate(recent_data.iterrows()):
                                    time_unix = int(timestamp.timestamp())
                                    candle = {
                                        'time': time_unix,
                                        'open': float(row['open']),
                                        'high': float(row['high']),
                                        'low': float(row['low']),
                                        'close': float(row['close'])
                                    }
                                    candlesticks.append(candle)
                                    
                                    # Debug: Log the first candlestick to verify format
                                    if i == 0:
                                        logger.info(f"🕯️ First candlestick for {ticker}: time={time_unix} (type: {type(time_unix)}), OHLC=[{candle['open']},{candle['high']},{candle['low']},{candle['close']}]")
                                
                                ticker_candlesticks[ticker] = {
                                    'data': sorted(candlesticks, key=lambda x: x['time']),  # Ensure chronological order
                                    'last_update': int(datetime.now().timestamp())
                                }
                                
                                logger.info(f"📊 Prepared {len(candlesticks)} candlesticks for {ticker} WebSocket stream")
                                
                            data = data_manager.get_historical_data(ticker, timeframe='1Min', start_hours_ago=24, limit=200)
                            if not data.empty:
                                indicators = data_manager.calculate_indicators(data, config_dict)
                                if indicators and 'StochRSI_K' in indicators and 'StochRSI_D' in indicators:
                                    k = indicators['StochRSI_K']
                                    d = indicators['StochRSI_D']
                                    lower_band = config.indicators.stochRSI.lower_band
                                    
                                    # Calculate signal strength for better visualization
                                    strength = min(abs(k - lower_band) / lower_band, 1.0) if lower_band > 0 else 0
                                    
                                    # Calculate SuperTrend signal
                                    supertrend_signal = 0
                                    supertrend_trend = 'neutral'
                                    supertrend_action = 'NEUTRAL'
                                    try:
                                        from indicators.supertrend import get_current_signal
                                        st_data = get_current_signal(data, period=10, multiplier=3.0)
                                        supertrend_signal = st_data['signal']
                                        supertrend_trend = st_data['trend']
                                        supertrend_action = st_data['action']
                                    except Exception as e:
                                        logger.debug(f"SuperTrend calculation error for {ticker}: {e}")
                                    
                                    ticker_signals[ticker] = {
                                        'stochRSI': {
                                            'signal': 1 if (k > d and k < lower_band) else 0,
                                            'k': k, 'd': d, 
                                            'status': 'OVERSOLD' if k < lower_band else 'NORMAL',
                                            'lower_band': lower_band,
                                            'strength': strength,
                                            'timestamp': datetime.now().isoformat()
                                        },
                                        'supertrend_signal': supertrend_signal,
                                        'supertrend_trend': supertrend_trend,
                                        'supertrend_action': supertrend_action,
                                        'rsi': indicators.get('RSI', 50)
                                    }

                data_payload = {
                    'timestamp': datetime.now().isoformat(), 
                    'account_info': account_info,
                    'positions': positions, 
                    'ticker_prices': ticker_prices,
                    'ticker_signals': ticker_signals, 
                    'ticker_candlesticks': ticker_candlesticks,
                    'bot_running': bot_manager.is_bot_running()
                }
                
                # Optimize payload based on update type
                is_full_update = (current_time - last_full_update) >= full_update_interval
                if is_full_update:
                    data_payload['update_type'] = 'full'
                    last_full_update = current_time
                else:
                    data_payload['update_type'] = 'incremental'
                    # For incremental updates, only send changed data
                    # (This could be enhanced with delta compression)
                
                # Add performance metadata
                data_payload['performance'] = {
                    'processing_time': time.time() - current_time,
                    'data_size': len(str(data_payload)),
                    'tickers_count': len(tickers)
                }
                
                # Compress large payloads
                compressed_data, was_compressed = compress_response(data_payload)
                if was_compressed:
                    socketio.emit('real_time_update_compressed', {
                        'compressed': True,
                        'data': compressed_data
                    })
                else:
                    socketio.emit('real_time_update', data_payload)
                
                # End performance monitoring
                performance_optimizer.monitor.end_operation(context, cache_hits=len(ticker_prices))
                
                # Log performance statistics periodically
                if current_time - last_performance_log >= performance_interval:
                    stats = performance_optimizer.get_comprehensive_stats()
                    logger.info(f"Performance stats: {stats['monitor']}")
                    last_performance_log = current_time
                
                logger.info(f"Emitting payload with keys: {list(data_payload.keys())}")

            except Exception as e:
                logger.error(f"Error in real-time thread: {e}", exc_info=True)
                # End performance monitoring on error
                if 'context' in locals():
                    performance_optimizer.monitor.end_operation(context, cache_misses=1)
            
            # Dynamic sleep based on load
            if len(tickers) > 10:
                socketio.sleep(max(refresh_interval * 1.5, 3))  # Slower for many tickers
            else:
                socketio.sleep(refresh_interval)
        else:
            socketio.sleep(1)

# Start the real-time thread as a background task
socketio.start_background_task(target=real_time_data_thread)

# Security and Authentication Routes
@app.route('/api/auth/login', methods=['POST'])
def login():
    """Basic authentication endpoint for demo purposes"""
    try:
        data = request.json or {}
        username = data.get('username', '')
        password = data.get('password', '')
        
        # Basic demo authentication (replace with real authentication)
        if username == 'demo' and password == 'demo123':
            token = create_demo_token(env_manager)
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'username': 'demo',
                    'role': 'trader'
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Authentication failed'}), 500

@app.route('/api/auth/validate', methods=['GET'])
@require_auth
def validate_token():
    """Validate JWT token endpoint"""
    return jsonify({
        'success': True,
        'valid': True,
        'user': request.current_user
    })

@app.route('/api/auth/demo-token', methods=['GET'])
def get_demo_token():
    """Get demo token for development (remove in production)"""
    try:
        if app.config.get('ENV') == 'development':
            token = create_demo_token(env_manager)
            return jsonify({
                'success': True,
                'token': token,
                'warning': 'This is a demo token for development only'
            })
        else:
            return jsonify({'success': False, 'error': 'Demo tokens not available in production'}), 403
    except Exception as e:
        logger.error(f"Demo token error: {e}")
        return jsonify({'success': False, 'error': 'Failed to create demo token'}), 500

@app.route('/api/security/status')
@require_auth
def security_status():
    """Get security status and recommendations"""
    try:
        security_results = validate_security()
        return jsonify({
            'success': True,
            'security_status': security_results
        })
    except Exception as e:
        logger.error(f"Security status error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get security status'}), 500

@app.route('/api/security/config-template')
@require_auth
def get_config_template():
    """Get secure configuration template"""
    try:
        secure_loader = get_secure_config_loader()
        template = secure_loader.create_secure_config_template()
        return jsonify({
            'success': True,
            'template': template
        })
    except Exception as e:
        logger.error(f"Config template error: {e}")
        return jsonify({'success': False, 'error': 'Failed to create config template'}), 500

# Routes
@app.route('/')
def index():
    return render_template('trading_dashboard.html')

@app.route('/dashboard')
@require_auth
def dashboard():
    return render_template('trading_dashboard.html')

@app.route('/dashboard_v2')
def dashboard_v2():
    return render_template('dashboard_v2.html')

@app.route('/v1')
def index_v1():
    return render_template('index.html')

@app.route('/test')
def test_simple():
    with open('test_simple.html', 'r') as f:
        return f.read()

@app.route('/test_charts')
def test_charts():
    with open('test_real_time_charts.html', 'r') as f:
        return f.read()

@app.route('/api/config', methods=['GET', 'POST'])
@require_auth
@cache_response(timeout=60)  # Cache config for 1 minute
def config_api():
    if request.method == 'GET':
        config = bot_manager.load_config()
        return optimize_json_response({'success': True, 'config': config}, cache_timeout=60)
    
    elif request.method == 'POST':
        try:
            config = request.json
            success = bot_manager.save_config(config)
            # Clear config cache on update
            with cache_lock:
                cache_keys_to_remove = [k for k in response_cache.keys() if 'config_api' in k]
                for k in cache_keys_to_remove:
                    del response_cache[k]
            return optimize_json_response({'success': success})
        except Exception as e:
            return optimize_json_response({'success': False, 'error': str(e)})

@app.route('/api/tickers', methods=['GET', 'POST', 'DELETE'])
@require_auth
def tickers_api():
    if request.method == 'GET':
        tickers = bot_manager.load_tickers()
        return jsonify({'success': True, 'tickers': tickers})
    
    elif request.method == 'POST':
        try:
            ticker = request.json.get('ticker', '').upper()
            if ticker:
                tickers = bot_manager.load_tickers()
                if ticker not in tickers:
                    tickers.append(ticker)
                    success = bot_manager.save_tickers(tickers)
                    return jsonify({'success': success, 'tickers': tickers})
                return jsonify({'success': True, 'tickers': tickers})
            return jsonify({'success': False, 'error': 'Invalid ticker'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    elif request.method == 'DELETE':
        try:
            ticker = request.json.get('ticker', '').upper()
            if ticker:
                tickers = bot_manager.load_tickers()
                if ticker in tickers:
                    tickers.remove(ticker)
                    success = bot_manager.save_tickers(tickers)
                    return jsonify({'success': success, 'tickers': tickers})
                return jsonify({'success': True, 'tickers': tickers})
            return jsonify({'success': False, 'error': 'Invalid ticker'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/bot/start', methods=['POST'])
@require_auth
def start_bot():
    success = bot_service.start_bot()
    return jsonify({'success': success, 'running': bot_service.is_bot_running()})

@app.route('/api/bot/stop', methods=['POST'])
@require_auth
def stop_bot():
    success = bot_service.stop_bot()
    return jsonify({'success': success, 'running': bot_service.is_bot_running()})

@app.route('/api/bot/status')
def bot_status():
    return jsonify({
        'success': True,
        'running': bot_service.is_bot_running(),
        'streaming': streaming_active
    })

@app.route('/api/account')
@require_auth
@cache_response(timeout=REALTIME_CACHE_TIMEOUT)  # Cache for 10 seconds
@async_route
def account_info():
    try:
        info = data_manager.get_account_info()
        return optimize_json_response({'success': True, 'account': info}, cache_timeout=REALTIME_CACHE_TIMEOUT)
    except Exception as e:
        return optimize_json_response({'success': False, 'error': str(e)})

@app.route('/api/positions')
@require_auth
@cache_response(timeout=REALTIME_CACHE_TIMEOUT)  # Cache for 10 seconds
@async_route
def positions_info():
    try:
        positions = data_manager.get_positions()
        return optimize_json_response({'success': True, 'positions': positions}, cache_timeout=REALTIME_CACHE_TIMEOUT)
    except Exception as e:
        return optimize_json_response({'success': False, 'error': str(e)})

@app.route('/api/orders')
@require_auth
def orders_history():
    try:
        orders = bot_manager.load_orders()
        if not orders.empty:
            return jsonify({'success': True, 'orders': orders.to_dict('records')})
        return jsonify({'success': True, 'orders': []})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/price/<symbol>')
@cache_response(timeout=5, key_func=lambda symbol: f"price_{symbol.upper()}")
@async_route
def get_price(symbol):
    try:
        price = data_manager.get_latest_price(symbol.upper())
        return optimize_json_response(
            {'success': True, 'symbol': symbol.upper(), 'price': price}, 
            cache_timeout=5
        )
    except Exception as e:
        return optimize_json_response({'success': False, 'error': str(e)})

@app.route('/api/chart/<symbol>')
@cache_response(
    timeout=60,  # Cache chart data for 1 minute
    key_func=lambda symbol: f"chart_{symbol.upper()}_{request.args.get('timeframe', '1Min')}_{request.args.get('limit', 100)}"
)
@async_route
def get_chart_data(symbol):
    try:
        timeframe = request.args.get('timeframe', '1Min')
        limit = int(request.args.get('limit', 100))
        
        logger.info(f"Fetching chart data for {symbol.upper()} with timeframe {timeframe}, limit {limit}")
        data = data_manager.get_historical_data(symbol.upper(), timeframe, limit=limit)
        
        if not data.empty:
            # Convert to LightweightCharts format with optimization
            candlesticks = []
            for timestamp, row in data.iterrows():
                time_unix = int(timestamp.timestamp())
                candlesticks.append({
                    'time': time_unix,
                    'open': round(float(row['open']), 4),  # Round to reduce payload size
                    'high': round(float(row['high']), 4),
                    'low': round(float(row['low']), 4),
                    'close': round(float(row['close']), 4),
                    'volume': int(row['volume']) if 'volume' in row else 0
                })
            
            chart_data = {
                'data': sorted(candlesticks, key=lambda x: x['time']),
                'symbol': symbol.upper(),
                'timeframe': timeframe,
                'data_points': len(candlesticks),
                'cache_timestamp': datetime.now().isoformat()
            }
            logger.info(f"Chart data for {symbol.upper()}: {len(chart_data['data'])} data points")
            return optimize_json_response({'success': True, 'data': chart_data}, cache_timeout=60)
        
        logger.warning(f"No chart data available for {symbol.upper()}")
        return optimize_json_response({'success': False, 'error': 'No data available'})
    except Exception as e:
        logger.error(f"Error getting chart data for {symbol.upper()}: {e}")
        return optimize_json_response({'success': False, 'error': str(e)})

@app.route('/api/latest_bar/<symbol>')
def get_latest_bar(symbol):
    try:
        # Fetch the most recent 10 1-minute bars to ensure we have enough data for new candle detection
        data = data_manager.get_historical_data(symbol.upper(), timeframe='1Min', limit=10)
        if not data.empty:
            # Get the most recent bar
            bar = data.iloc[-1]
            
            # Also return the previous bar for comparison
            prev_bar = data.iloc[-2] if len(data) > 1 else None
            
            # Ensure timestamps are proper integers
            bar_timestamp = int(bar.name.timestamp())
            
            # Determine if this is a new candle or an update to existing candle
            # A new candle is created every minute (60 seconds)
            current_time = datetime.now()
            current_minute = current_time.replace(second=0, microsecond=0)
            bar_minute = bar.name.replace(second=0, microsecond=0, tzinfo=None)
            
            # Check if this bar represents the current minute
            is_current_minute = bar_minute == current_minute
            
            # Determine if this is a new candle by comparing with previous bar timestamp
            is_new_candle = False
            if prev_bar is not None:
                prev_timestamp = int(prev_bar.name.timestamp())
                # If the bar timestamp is more than 60 seconds from previous, it's a new candle
                is_new_candle = (bar_timestamp - prev_timestamp) >= 60
            else:
                # If no previous bar, treat as new candle
                is_new_candle = True
            
            logger.info(f"Bar analysis for {symbol}: time={bar.name}, current_minute={current_minute}, is_current_minute={is_current_minute}, is_new_candle={is_new_candle}")
            
            response_data = {
                'success': True,
                'bar': {
                    'time': bar_timestamp,
                    'open': float(bar['open']),
                    'high': float(bar['high']),
                    'low': float(bar['low']),
                    'close': float(bar['close'])
                },
                'is_new_candle': is_new_candle,
                'is_current_minute': is_current_minute,
                'bar_age_seconds': (current_time - bar.name.replace(tzinfo=None)).total_seconds()
            }
            
            # Add previous bar data if available
            if prev_bar is not None:
                prev_timestamp = int(prev_bar.name.timestamp())
                response_data['prev_bar'] = {
                    'time': prev_timestamp,
                    'close': float(prev_bar['close'])
                }
            
            # Log the update for debugging
            logger.info(f"Latest bar for {symbol}: time={bar.name}, close={bar['close']}, new_candle={is_new_candle}")
            
            return jsonify(response_data)
        return jsonify({'success': False, 'error': 'No data available'})
    except Exception as e:
        logger.error(f"Error getting latest bar for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/realtime_bars/<symbol>')
def get_realtime_bars(symbol):
    """Get the most recent bars with real-time detection for chart updates"""
    try:
        # Fetch more recent data to ensure we capture new candle formation
        data = data_manager.get_historical_data(symbol.upper(), timeframe='1Min', limit=50)
        if not data.empty:
            # Convert to the format expected by LightweightCharts
            bars = []
            for index, row in data.iterrows():
                bar_timestamp = int(index.timestamp())
                bars.append({
                    'time': bar_timestamp,
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close'])
                })
            
            # Get the most recent bar for analysis
            latest_bar = bars[-1] if bars else None
            
            # Analyze candle timing
            current_time = datetime.now()
            current_minute_timestamp = int(current_time.replace(second=0, microsecond=0).timestamp())
            
            response_data = {
                'success': True,
                'bars': bars,
                'latest_bar': latest_bar,
                'current_minute_timestamp': current_minute_timestamp,
                'bars_count': len(bars)
            }
            
            if latest_bar:
                is_current_minute = latest_bar['time'] == current_minute_timestamp
                bar_age_seconds = (current_time.timestamp() - latest_bar['time'])
                response_data.update({
                    'is_current_minute': is_current_minute,
                    'bar_age_seconds': bar_age_seconds
                })
            
            logger.info(f"Realtime bars for {symbol}: {len(bars)} bars, latest at {latest_bar['time'] if latest_bar else 'N/A'}")
            return jsonify(response_data)
        
        return jsonify({'success': False, 'error': 'No data available'})
    except Exception as e:
        logger.error(f"Error getting realtime bars for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/indicators/<symbol>')
def get_indicators(symbol):
    try:
        config = bot_manager.load_config()
        if not config:
            return jsonify({'success': False, 'error': 'Config not found'})
        
        data = data_manager.get_historical_data(symbol.upper(), limit=50)
        if not data.empty:
            # Convert config to legacy format for indicators
            config_dict = {
                'indicators': {
                    'stochRSI': "True" if config.indicators.stochRSI.enabled else "False",
                    'stochRSI_params': {
                        'rsi_length': config.indicators.stochRSI.rsi_length,
                        'stoch_length': config.indicators.stochRSI.stoch_length,
                        'K': config.indicators.stochRSI.K,
                        'D': config.indicators.stochRSI.D,
                        'lower_band': config.indicators.stochRSI.lower_band,
                        'upper_band': config.indicators.stochRSI.upper_band
                    },
                    'stoch': "True" if config.indicators.stoch.enabled else "False",
                    'stoch_params': {
                        'lower_band': config.indicators.stoch.lower_band,
                        'upper_band': config.indicators.stoch.upper_band,
                        'K_Length': config.indicators.stoch.K_Length,
                        'smooth_K': config.indicators.stoch.smooth_K,
                        'smooth_D': config.indicators.stoch.smooth_D
                    },
                    'EMA': "True" if config.indicators.EMA.enabled else "False",
                    'EMA_params': {
                        'ema_period': config.indicators.EMA.ema_period
                    }
                }
            }
            indicators = data_manager.calculate_indicators(data, config_dict)
            return jsonify({'success': True, 'indicators': indicators})
        return jsonify({'success': False, 'error': 'No data available'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/chart_indicators/<symbol>')
def get_chart_indicators(symbol):
    """Get historical indicator data for charting"""
    try:
        config = bot_manager.load_config()
        if not config:
            return jsonify({'success': False, 'error': 'Config not found'})
        
        timeframe = request.args.get('timeframe', '1Min')
        limit = int(request.args.get('limit', 200))
        # Ensure minimum data for indicator calculation
        limit = max(limit, 50)
        
        logger.info(f"Fetching indicator data for {symbol.upper()} with timeframe {timeframe}, limit {limit}")
        data = data_manager.get_historical_data(symbol.upper(), timeframe, limit=limit)
        
        if not data.empty:
            # Convert unified config to legacy format for indicators
            config_dict = {
                'indicators': {
                    'stochRSI': "True" if config.indicators.stochRSI.enabled else "False",
                    'stochRSI_params': {
                        'rsi_length': config.indicators.stochRSI.rsi_length,
                        'stoch_length': config.indicators.stochRSI.stoch_length,
                        'K': config.indicators.stochRSI.K,
                        'D': config.indicators.stochRSI.D
                    },
                    'EMA': "True" if config.indicators.EMA.enabled else "False",
                    'EMA_params': {
                        'ema_period': config.indicators.EMA.ema_period
                    },
                    'stoch': "True" if config.indicators.stoch.enabled else "False",
                    'stoch_params': {
                        'K_Length': config.indicators.stoch.K_Length,
                        'smooth_K': config.indicators.stoch.smooth_K,
                        'smooth_D': config.indicators.stoch.smooth_D
                    }
                }
            }
            
            # Calculate indicators for all historical data points
            chart_indicators = data_manager.calculate_indicators_series(data, config_dict)
            
            if chart_indicators:
                # Convert timestamps to UNIX timestamps for charting - ensure integers
                timestamps = (data.index.astype(np.int64) // 10**9).astype(int).tolist()
                
                response_data = {
                    'success': True,
                    'timestamps': timestamps,
                    'indicators': {}
                }
                
                # Add RSI series if available
                if 'RSI' in chart_indicators:
                    response_data['indicators']['rsi'] = [
                        {'time': ts, 'value': val} for ts, val in zip(timestamps, chart_indicators['RSI'])
                        if not pd.isna(val)
                    ]
                
                # Add StochRSI series if available
                if 'StochRSI_K' in chart_indicators and 'StochRSI_D' in chart_indicators:
                    response_data['indicators']['stochRSI_K'] = [
                        {'time': ts, 'value': val} for ts, val in zip(timestamps, chart_indicators['StochRSI_K'])
                        if not pd.isna(val)
                    ]
                    response_data['indicators']['stochRSI_D'] = [
                        {'time': ts, 'value': val} for ts, val in zip(timestamps, chart_indicators['StochRSI_D'])
                        if not pd.isna(val)
                    ]
                
                # Add EMA series if available
                if 'EMA' in chart_indicators:
                    response_data['indicators']['ema'] = [
                        {'time': ts, 'value': val} for ts, val in zip(timestamps, chart_indicators['EMA'])
                        if not pd.isna(val)
                    ]
                
                logger.info(f"Indicator data for {symbol.upper()}: {len(response_data['indicators'])} indicator series")
                return jsonify(response_data)
            
        logger.warning(f"No indicator data available for {symbol.upper()}")
        return jsonify({'success': False, 'error': 'No indicator data available'})
    except Exception as e:
        logger.error(f"Error getting indicator data for {symbol.upper()}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/signals/<symbol>')
def get_signals(symbol):
    try:
        config = bot_manager.load_config()
        if not config:
            return jsonify({'success': False, 'error': 'Config not found'})
        
        # Get recent data for signal calculation
        data = data_manager.get_historical_data(symbol.upper(), limit=100)
        if not data.empty:
            # Convert config to legacy format for indicators
            config_dict = {
                'indicators': {
                    'stochRSI': "True" if config.indicators.stochRSI.enabled else "False",
                    'stochRSI_params': {
                        'rsi_length': config.indicators.stochRSI.rsi_length,
                        'stoch_length': config.indicators.stochRSI.stoch_length,
                        'K': config.indicators.stochRSI.K,
                        'D': config.indicators.stochRSI.D,
                        'lower_band': config.indicators.stochRSI.lower_band,
                        'upper_band': config.indicators.stochRSI.upper_band
                    },
                    'stoch': "True" if config.indicators.stoch.enabled else "False",
                    'stoch_params': {
                        'lower_band': config.indicators.stoch.lower_band,
                        'upper_band': config.indicators.stoch.upper_band,
                        'K_Length': config.indicators.stoch.K_Length,
                        'smooth_K': config.indicators.stoch.smooth_K,
                        'smooth_D': config.indicators.stoch.smooth_D
                    },
                    'EMA': "True" if config.indicators.EMA.enabled else "False",
                    'EMA_params': {
                        'ema_period': config.indicators.EMA.ema_period
                    }
                }
            }
            
            indicators = data_manager.calculate_indicators(data, config_dict)
            
            # Calculate signal status based on strategy analysis
            signals = {}
            
            # StochRSI Signal Logic (currently active strategy)
            if 'StochRSI_K' in indicators and 'StochRSI_D' in indicators:
                k = indicators['StochRSI_K']
                d = indicators['StochRSI_D']
                lower_band = config.indicators.stochRSI.lower_band
                
                # Buy signal: K > D and K < lower_band (oversold reversal)
                signals['stochRSI_signal'] = 1 if (k > d and k < lower_band) else 0
                signals['stochRSI_strength'] = abs(k - lower_band) / lower_band
                signals['stochRSI_status'] = 'OVERSOLD' if k < lower_band else 'NORMAL'
                
            # Stochastic Signal Logic  
            if 'Stoch_K' in indicators and 'Stoch_D' in indicators:
                k = indicators['Stoch_K']
                d = indicators['Stoch_D']
                lower_band = config.indicators.stoch.lower_band
                
                signals['stoch_signal'] = 1 if (k > d and k > lower_band) else 0
                signals['stoch_strength'] = k / 100.0
                signals['stoch_status'] = 'OVERSOLD' if k < lower_band else 'NORMAL'
            
            # EMA Signal Logic
            if 'EMA' in indicators:
                current_price = data_manager.get_latest_price(symbol.upper())
                if current_price:
                    ema = indicators['EMA']
                    signals['ema_signal'] = 1 if current_price > ema else 0
                    signals['ema_strength'] = abs(current_price - ema) / ema
                    signals['ema_status'] = 'BULLISH' if current_price > ema else 'BEARISH'
            
            return jsonify({
                'success': True, 
                'indicators': indicators,
                'signals': signals,
                'config': {
                    'stochRSI_lower': config.indicators.stochRSI.lower_band,
                    'stochRSI_upper': config.indicators.stochRSI.upper_band,
                    'stoch_lower': config.indicators.stoch.lower_band,
                    'stoch_upper': config.indicators.stoch.upper_band
                }
            })
        return jsonify({'success': False, 'error': 'No data available'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/supertrend/<symbol>')
def get_supertrend(symbol):
    """Get SuperTrend indicator signals for a symbol"""
    try:
        from indicators.supertrend import get_current_signal, calculate_multi_timeframe_supertrend
        
        # Get historical data
        data = data_manager.get_historical_data(symbol.upper(), '1Min', limit=200)
        
        if not data.empty:
            # Calculate SuperTrend signal
            signal_data = get_current_signal(data, period=10, multiplier=3.0)
            
            # Get multi-timeframe analysis for stronger signals
            mtf_analysis = calculate_multi_timeframe_supertrend(
                symbol.upper(), 
                data_manager,
                timeframes=['1Min', '5Min', '15Min']
            )
            
            return jsonify({
                'success': True,
                'symbol': symbol.upper(),
                'signal': signal_data['signal'],
                'trend': signal_data['trend'],
                'action': signal_data['action'],
                'supertrend_value': signal_data['supertrend_value'],
                'current_price': signal_data['current_price'],
                'recent_signal_change': signal_data['recent_signal_change'],
                'multi_timeframe': mtf_analysis,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No data available',
                'symbol': symbol.upper()
            })
    except Exception as e:
        logger.error(f"Error calculating SuperTrend for {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'symbol': symbol.upper()
        })

from backtesting.backtesting_engine import BacktestingEngine
from main import get_strategy

@app.route('/api/backtest', methods=['POST'])
def backtest():
    try:
        data = request.json
        strategy_name = data.get('strategy')
        symbol = data.get('symbol')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        strategy = get_strategy(strategy_name, bot_manager.load_config())
        engine = BacktestingEngine(strategy, symbol, start_date, end_date)
        results = engine.run()

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Enhanced SocketIO events with performance optimization
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    # Send optimized connection response
    emit('connected', {
        'data': 'Connected to real-time stream',
        'server_time': datetime.now().isoformat(),
        'compression_enabled': websocket_compression,
        'buffer_size': websocket_buffer_size
    })

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')
    # Clean up any client-specific caches
    # This could be enhanced with per-client caching

# Replace time.sleep with socketio.sleep for cooperative yielding
@socketio.on('start_streaming')
def handle_start_streaming(data):
    global streaming_active, refresh_interval
    streaming_active = True
    refresh_interval = data.get('interval', 5)
    logger.info(f'Started streaming with {refresh_interval}s interval')
    emit('streaming_status', {'active': True, 'interval': refresh_interval})

@socketio.on('stop_streaming')
def handle_stop_streaming():
    global streaming_active
    streaming_active = False
    logger.info('Stopped streaming')
    emit('streaming_status', {'active': False})

@socketio.on('update_interval')
def handle_update_interval(data):
    global refresh_interval
    refresh_interval = data.get('interval', 5)
    logger.info(f'Updated refresh interval to {refresh_interval}s')
    emit('interval_updated', {'interval': refresh_interval})

# Performance monitoring routes
@app.route('/api/performance/stats')
@require_auth
def get_performance_stats():
    """Get comprehensive performance statistics."""
    try:
        stats = performance_optimizer.get_comprehensive_stats()
        return optimize_json_response({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }, cache_timeout=10)
    except Exception as e:
        return optimize_json_response({'success': False, 'error': str(e)})

@app.route('/api/performance/cache')
@require_auth
def get_cache_stats():
    """Get cache performance statistics."""
    try:
        cache_stats = data_manager.get_cache_stats()
        response_cache_stats = {
            'size': len(response_cache),
            'memory_usage': sum(len(str(data)) for data, _ in response_cache.values())
        }
        
        return optimize_json_response({
            'success': True,
            'data_manager_cache': cache_stats,
            'response_cache': response_cache_stats,
            'performance_cache': performance_optimizer.cache.get_stats()
        }, cache_timeout=30)
    except Exception as e:
        return optimize_json_response({'success': False, 'error': str(e)})

@app.route('/api/performance/system')
@require_auth
def get_system_performance():
    """Get system performance metrics."""
    try:
        import psutil
        process = psutil.Process()
        
        system_stats = {
            'cpu_percent': process.cpu_percent(),
            'memory_info': {
                'rss': process.memory_info().rss / 1024 / 1024,  # MB
                'vms': process.memory_info().vms / 1024 / 1024,  # MB
                'percent': process.memory_percent()
            },
            'threads': process.num_threads(),
            'open_files': len(process.open_files()) if hasattr(process, 'open_files') else 0,
            'connections': len(process.connections()) if hasattr(process, 'connections') else 0
        }
        
        return optimize_json_response({
            'success': True,
            'system': system_stats,
            'data_manager': data_manager.get_system_health()
        }, cache_timeout=5)
    except Exception as e:
        return optimize_json_response({'success': False, 'error': str(e)})

@app.route('/api/performance/clear-cache', methods=['POST'])
@require_auth
def clear_performance_cache():
    """Clear performance caches."""
    try:
        # Clear response cache
        with cache_lock:
            cleared_count = len(response_cache)
            response_cache.clear()
        
        # Trigger data manager cache cleanup
        data_manager.get_cache_stats()  # This triggers cleanup
        
        return optimize_json_response({
            'success': True,
            'cleared_responses': cleared_count,
            'message': 'Performance caches cleared'
        })
    except Exception as e:
        return optimize_json_response({'success': False, 'error': str(e)})

# Initialize bot manager
bot_manager = BotManager()

# Perform security check on startup
try:
    security_status = validate_security()
    if security_status['secure']:
        logger.info("✅ Security validation passed")
    else:
        logger.warning("⚠️  Security validation failed:")
        for error in security_status['errors']:
            logger.error(f"  ❌ {error}")
        for warning in security_status['warnings']:
            logger.warning(f"  ⚠️  {warning}")
        logger.info("📝 Recommendations:")
        for rec in security_status.get('recommendations', []):
            logger.info(f"  💡 {rec}")
except Exception as e:
    logger.error(f"Failed to perform security validation: {e}")

if __name__ == '__main__':
    port = 8765
    logger.info(f'Starting Flask Trading Bot Dashboard on port {port}')
    logger.info('Real-time streaming enabled via WebSockets')
    
    # Final security reminder
    try:
        if not env_manager.validate_environment():
            logger.warning("\n" + "="*60)
            logger.warning("🔒 SECURITY NOTICE:")
            logger.warning("Environment validation failed. For production use:")
            logger.warning("1. Copy .env.example to .env")
            logger.warning("2. Set all required environment variables")
            logger.warning("3. Use strong, unique secret keys")
            logger.warning("4. Restrict CORS origins")
            logger.warning("="*60 + "\n")
    except Exception as e:
        logger.error(f"Environment validation error: {e}")
    
    # Performance optimizations for production
    if os.environ.get('FLASK_ENV') == 'production':
        # Production optimizations
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = STATIC_CACHE_TIMEOUT
        
        # Additional performance headers
        @app.after_request
        def add_performance_headers(response):
            # Security headers that also help performance
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Performance hints
            if request.endpoint and 'api' in request.endpoint:
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            
            return response
    
    # Log startup performance info
    logger.info(f"Flask app starting with performance optimizations:")
    logger.info(f"- Compression: Enabled")
    logger.info(f"- WebSocket compression: {websocket_compression}")
    logger.info(f"- WebSocket buffer size: {websocket_buffer_size}")
    logger.info(f"- Thread pool workers: {thread_executor._max_workers}")
    logger.info(f"- Cache timeouts: Realtime={REALTIME_CACHE_TIMEOUT}s, General={CACHE_TIMEOUT}s, Static={STATIC_CACHE_TIMEOUT}s")
    
    socketio.run(app, host='0.0.0.0', port=port)