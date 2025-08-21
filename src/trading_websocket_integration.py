"""
Integration layer for WebSocket server with trading bot functionality.
Provides real-time data streaming for market data, positions, signals, and orders.
"""

import asyncio
import threading
from utils.thread_manager import thread_manager, ResourceCleaner
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

from src.websocket_server import WebSocketServer, WebSocketConfig, StreamType
from flask import Flask

logger = logging.getLogger(__name__)

@dataclass
class MarketDataUpdate:
    """Market data update structure"""
    symbol: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class PositionUpdate:
    """Position update structure"""
    symbol: str
    quantity: float
    market_value: float
    unrealized_pnl: float
    side: str  # 'long' or 'short'
    avg_entry_price: Optional[float] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class SignalUpdate:
    """Trading signal update structure"""
    symbol: str
    signal_type: str  # 'buy', 'sell', 'hold'
    strength: float  # 0-1 strength of signal
    indicators: Dict[str, Any]
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

@dataclass
class OrderUpdate:
    """Order update structure"""
    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    status: str  # 'pending', 'filled', 'cancelled', etc.
    filled_quantity: Optional[float] = None
    avg_fill_price: Optional[float] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class TradingWebSocketService:
    """Service to integrate trading bot functionality with WebSocket server"""
    
    def __init__(self, websocket_server: WebSocketServer, data_manager, bot_manager=None):
        self.websocket_server = websocket_server
        self.data_manager = data_manager
        self.bot_manager = bot_manager
        
        # Data streaming configuration
        self.streaming_active = False
        self.streaming_interval = 1.0  # seconds
        self.last_updates = {}
        
        # Background streaming thread
        self.streaming_thread = None
        self.shutdown_event = threading.Event()
        
        # Performance tracking
        self.update_counts = {
            'market_data': 0,
            'positions': 0,
            'signals': 0,
            'orders': 0,
            'account': 0
        }
        
        logger.info("Trading WebSocket service initialized")
    
    def start_streaming(self, interval: float = 1.0):
        """Start real-time data streaming"""
        if self.streaming_active:
            logger.warning("Streaming already active")
            return
        
        self.streaming_interval = interval
        self.streaming_active = True
        self.shutdown_event.clear()
        
        # Start background streaming thread with proper management
        self.streaming_thread = thread_manager.create_thread(
            target=self._streaming_loop,
            name="TradingWebSocketStreaming",
            cleanup_func=self._cleanup_streaming_resources
        )
        self.streaming_thread.start()
        
        logger.info(f"Started WebSocket streaming with {interval}s interval")
    
    def stop_streaming(self):
        """Stop real-time data streaming"""
        if not self.streaming_active:
            return
        
        self.streaming_active = False
        self.shutdown_event.set()
        
        if self.streaming_thread:
            self.streaming_thread.stop(timeout=5)
        
        # Clean up resources
        self._cleanup_resources()
        
        logger.info("Stopped WebSocket streaming")
    
    def _cleanup_streaming_resources(self):
        """Cleanup streaming-specific resources"""
        try:
            # Clean up WebSocket connections
            if self.websocket_server:
                ResourceCleaner.cleanup_websocket_connections(self.websocket_server)
            
            # Clean up any cached data
            self.update_counts = {
                'positions': 0,
                'account': 0,
                'orders': 0,
                'market_data': 0
            }
            
            logger.info("Streaming resources cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up streaming resources: {e}")
    
    def _cleanup_resources(self):
        """Cleanup all resources"""
        try:
            # Clean up streaming resources
            self._cleanup_streaming_resources()
            
            # Clean up data manager connections
            if hasattr(self.data_manager, 'close'):
                self.data_manager.close()
            
            logger.info("All trading WebSocket resources cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up resources: {e}")
    
    def _streaming_loop(self, shutdown_event=None):
        """Main streaming loop for real-time data"""
        logger.info("WebSocket streaming loop started")
        
        # Use the provided shutdown_event from ThreadManager
        event_to_check = shutdown_event or self.shutdown_event
        
        while self.streaming_active and not event_to_check.is_set():
            try:
                start_time = time.time()
                
                # Stream market data
                self._stream_market_data()
                
                # Stream position updates
                self._stream_position_updates()
                
                # Stream account information
                self._stream_account_updates()
                
                # Stream trading signals (if bot is running)
                if self.bot_manager and hasattr(self.bot_manager, 'is_bot_running'):
                    if self.bot_manager.is_bot_running():
                        self._stream_signal_updates()
                
                # Calculate processing time and adjust sleep
                processing_time = time.time() - start_time
                sleep_time = max(0, self.streaming_interval - processing_time)
                
                # Log performance occasionally
                if self.update_counts['market_data'] % 60 == 0:  # Every minute
                    logger.info(f"Streaming performance: {processing_time:.3f}s processing, "
                              f"{sleep_time:.3f}s sleep, {self.websocket_server.get_connected_clients()} clients")
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in streaming loop: {e}", exc_info=True)
                time.sleep(1)  # Prevent tight error loop
    
    def _stream_market_data(self):
        """Stream real-time market data"""
        try:
            if not self.bot_manager:
                return
            
            # Get configured tickers
            tickers = getattr(self.bot_manager, 'load_tickers', lambda: [])()
            if not tickers:
                return
            
            market_updates = []
            
            for symbol in tickers:
                try:
                    # Get latest price data
                    price = self.data_manager.get_latest_price(symbol)
                    if price is None:
                        continue
                    
                    # Get additional market data if available
                    market_data = {
                        'symbol': symbol,
                        'price': price,
                        'timestamp': time.time()
                    }
                    
                    # Try to get bid/ask if available
                    try:
                        quote = self.data_manager.get_latest_quote(symbol)
                        if quote:
                            market_data.update({
                                'bid': quote.get('bid_price'),
                                'ask': quote.get('ask_price'),
                                'bid_size': quote.get('bid_size'),
                                'ask_size': quote.get('ask_size')
                            })
                    except:
                        pass  # Quote data not available
                    
                    market_updates.append(market_data)
                    
                    # Broadcast individual symbol data
                    self.websocket_server.broadcast_market_data(symbol, market_data)
                    
                except Exception as e:
                    logger.debug(f"Error getting market data for {symbol}: {e}")
            
            # Broadcast consolidated market data
            if market_updates:
                self.websocket_server._broadcast_to_stream(
                    StreamType.MARKET_DATA,
                    {'updates': market_updates, 'timestamp': time.time()}
                )
                self.update_counts['market_data'] += len(market_updates)
                
        except Exception as e:
            logger.error(f"Error streaming market data: {e}")
    
    def _stream_position_updates(self):
        """Stream real-time position updates"""
        try:
            positions_data = self.data_manager.get_positions()
            if not positions_data:
                return
            
            # Format positions for streaming
            formatted_positions = []
            
            for position in positions_data:
                formatted_position = {
                    'symbol': position.get('symbol', ''),
                    'quantity': float(position.get('qty', 0)),
                    'market_value': float(position.get('market_value', 0)),
                    'unrealized_pnl': float(position.get('unrealized_pnl', 0)),
                    'side': position.get('side', 'long'),
                    'avg_entry_price': float(position.get('avg_entry_price', 0)),
                    'timestamp': time.time()
                }
                formatted_positions.append(formatted_position)
            
            # Broadcast position updates
            self.websocket_server.broadcast_position_update(formatted_positions)
            self.update_counts['positions'] += len(formatted_positions)
            
        except Exception as e:
            logger.error(f"Error streaming position updates: {e}")
    
    def _stream_account_updates(self):
        """Stream account information updates"""
        try:
            account_info = self.data_manager.get_account_info()
            if not account_info:
                return
            
            # Format account data
            formatted_account = {
                'buying_power': float(account_info.get('buying_power', 0)),
                'cash': float(account_info.get('cash', 0)),
                'portfolio_value': float(account_info.get('portfolio_value', 0)),
                'day_trade_count': int(account_info.get('daytrade_count', 0)),
                'equity': float(account_info.get('equity', 0)),
                'timestamp': time.time()
            }
            
            # Broadcast account updates
            self.websocket_server.broadcast_account_update(formatted_account)
            self.update_counts['account'] += 1
            
        except Exception as e:
            logger.error(f"Error streaming account updates: {e}")
    
    def _stream_signal_updates(self):
        """Stream trading signal updates"""
        try:
            if not self.bot_manager:
                return
            
            tickers = getattr(self.bot_manager, 'load_tickers', lambda: [])()
            config = getattr(self.bot_manager, 'load_config', lambda: None)()
            
            if not tickers or not config:
                return
            
            for symbol in tickers:
                try:
                    # Get historical data for signal calculation
                    data = self.data_manager.get_historical_data(
                        symbol, timeframe='1Min', limit=100
                    )
                    if data.empty:
                        continue
                    
                    # Convert config to legacy format for indicators
                    config_dict = self._convert_config_for_indicators(config)
                    
                    # Calculate indicators
                    indicators = self.data_manager.calculate_indicators(data, config_dict)
                    if not indicators:
                        continue
                    
                    # Generate signal data
                    signal_data = self._generate_signal_data(symbol, indicators, config)
                    
                    # Broadcast signal update
                    self.websocket_server.broadcast_signal(symbol, signal_data)
                    self.update_counts['signals'] += 1
                    
                except Exception as e:
                    logger.debug(f"Error generating signal for {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error streaming signal updates: {e}")
    
    def _convert_config_for_indicators(self, config) -> Dict:
        """Convert unified config to legacy format for indicators"""
        try:
            return {
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
                    },
                    'stoch': "True" if config.indicators.stoch.enabled else "False",
                    'stoch_params': {
                        'lower_band': config.indicators.stoch.lower_band,
                        'upper_band': config.indicators.stoch.upper_band,
                        'K_Length': config.indicators.stoch.K_Length,
                        'smooth_K': config.indicators.stoch.smooth_K,
                        'smooth_D': config.indicators.stoch.smooth_D
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error converting config: {e}")
            return {'indicators': {}}
    
    def _generate_signal_data(self, symbol: str, indicators: Dict, config) -> Dict:
        """Generate signal data from indicators"""
        try:
            signal_data = {
                'symbol': symbol,
                'timestamp': time.time(),
                'indicators': indicators,
                'signals': {}
            }
            
            # StochRSI signal
            if 'StochRSI_K' in indicators and 'StochRSI_D' in indicators:
                k = indicators['StochRSI_K']
                d = indicators['StochRSI_D']
                lower_band = config.indicators.stochRSI.lower_band
                
                signal_data['signals']['stochRSI'] = {
                    'signal': 1 if (k > d and k < lower_band) else 0,
                    'strength': min(abs(k - lower_band) / lower_band, 1.0) if lower_band > 0 else 0,
                    'status': 'OVERSOLD' if k < lower_band else 'NORMAL',
                    'k': k,
                    'd': d,
                    'lower_band': lower_band
                }
            
            # EMA signal
            if 'EMA' in indicators:
                current_price = self.data_manager.get_latest_price(symbol)
                if current_price:
                    ema = indicators['EMA']
                    signal_data['signals']['ema'] = {
                        'signal': 1 if current_price > ema else 0,
                        'strength': abs(current_price - ema) / ema if ema > 0 else 0,
                        'status': 'BULLISH' if current_price > ema else 'BEARISH',
                        'ema': ema,
                        'price': current_price
                    }
            
            # SuperTrend signal (if available)
            try:
                from indicators.supertrend import get_current_signal
                data = self.data_manager.get_historical_data(symbol, '1Min', limit=50)
                if not data.empty:
                    st_data = get_current_signal(data, period=10, multiplier=3.0)
                    signal_data['signals']['supertrend'] = {
                        'signal': st_data['signal'],
                        'trend': st_data['trend'],
                        'action': st_data['action'],
                        'value': st_data['supertrend_value'],
                        'price': st_data['current_price']
                    }
            except Exception as e:
                logger.debug(f"SuperTrend calculation error for {symbol}: {e}")
            
            return signal_data
            
        except Exception as e:
            logger.error(f"Error generating signal data for {symbol}: {e}")
            return {'symbol': symbol, 'timestamp': time.time(), 'error': str(e)}
    
    def broadcast_order_update(self, order_data: Dict[str, Any]):
        """Manually broadcast order update"""
        try:
            formatted_order = {
                'order_id': order_data.get('id', ''),
                'symbol': order_data.get('symbol', ''),
                'side': order_data.get('side', ''),
                'quantity': float(order_data.get('qty', 0)),
                'status': order_data.get('status', ''),
                'filled_quantity': float(order_data.get('filled_qty', 0)),
                'avg_fill_price': float(order_data.get('filled_avg_price', 0)) if order_data.get('filled_avg_price') else None,
                'timestamp': time.time()
            }
            
            self.websocket_server.broadcast_order_update(formatted_order)
            self.update_counts['orders'] += 1
            
        except Exception as e:
            logger.error(f"Error broadcasting order update: {e}")
    
    def get_streaming_stats(self) -> Dict[str, Any]:
        """Get streaming statistics"""
        return {
            'streaming_active': self.streaming_active,
            'streaming_interval': self.streaming_interval,
            'connected_clients': self.websocket_server.get_connected_clients(),
            'update_counts': self.update_counts.copy(),
            'websocket_stats': self.websocket_server.get_performance_stats()
        }
    
    def set_streaming_interval(self, interval: float):
        """Set streaming interval"""
        self.streaming_interval = max(0.1, min(60.0, interval))  # Clamp between 0.1s and 60s
        logger.info(f"Set streaming interval to {self.streaming_interval}s")

# Integration with Flask app
def integrate_websocket_with_flask_app(app: Flask, data_manager, bot_manager=None) -> TradingWebSocketService:
    """Integrate WebSocket server with existing Flask app"""
    
    # Create WebSocket configuration optimized for trading
    ws_config = WebSocketConfig(
        ping_timeout=60,
        ping_interval=25,
        compression=True,
        binary=True,
        max_http_buffer_size=65536,
        heartbeat_interval=10,
        reconnect_attempts=5,
        reconnect_delay=1,
        max_latency_ms=100
    )
    
    # Create WebSocket server
    websocket_server = WebSocketServer(app, ws_config)
    
    # Create trading service
    trading_service = TradingWebSocketService(websocket_server, data_manager, bot_manager)
    
    # Add Flask routes for WebSocket management
    @app.route('/api/websocket/start', methods=['POST'])
    def start_websocket_streaming():
        from flask import request, jsonify
        interval = request.json.get('interval', 1.0) if request.json else 1.0
        trading_service.start_streaming(interval)
        return jsonify({'success': True, 'message': 'WebSocket streaming started'})
    
    @app.route('/api/websocket/stop', methods=['POST'])
    def stop_websocket_streaming():
        from flask import jsonify
        trading_service.stop_streaming()
        return jsonify({'success': True, 'message': 'WebSocket streaming stopped'})
    
    @app.route('/api/websocket/stats')
    def get_websocket_stats():
        from flask import jsonify
        stats = trading_service.get_streaming_stats()
        return jsonify({'success': True, 'stats': stats})
    
    @app.route('/api/websocket/config', methods=['GET', 'POST'])
    def websocket_config():
        from flask import request, jsonify
        
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'config': {
                    'streaming_interval': trading_service.streaming_interval,
                    'streaming_active': trading_service.streaming_active,
                    'ping_timeout': ws_config.ping_timeout,
                    'ping_interval': ws_config.ping_interval,
                    'max_latency_ms': ws_config.max_latency_ms
                }
            })
        else:
            interval = request.json.get('interval')
            if interval:
                trading_service.set_streaming_interval(float(interval))
            return jsonify({'success': True, 'message': 'Configuration updated'})
    
    logger.info("WebSocket integration with Flask app completed")
    
    return trading_service

# Utility function for easy setup
def setup_trading_websockets(app: Flask, data_manager, bot_manager=None, auto_start: bool = True) -> TradingWebSocketService:
    """Easy setup function for trading WebSockets"""
    
    trading_service = integrate_websocket_with_flask_app(app, data_manager, bot_manager)
    
    if auto_start:
        trading_service.start_streaming(interval=1.0)
        logger.info("WebSocket streaming started automatically")
    
    return trading_service