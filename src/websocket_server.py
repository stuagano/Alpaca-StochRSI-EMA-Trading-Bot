import asyncio
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, asdict
import logging
from collections import defaultdict, deque
import gzip
import hashlib
from enum import Enum

from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import eventlet

# Performance and monitoring
import psutil
import functools

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class StreamType(Enum):
    """Types of data streams available"""
    MARKET_DATA = "market_data"
    POSITIONS = "positions"
    SIGNALS = "signals"
    ORDERS = "orders"
    ACCOUNT = "account"
    SYSTEM_HEALTH = "system_health"
    PERFORMANCE_METRICS = "performance_metrics"

@dataclass
class WebSocketConfig:
    """Configuration for WebSocket server"""
    ping_timeout: int = 60
    ping_interval: int = 25
    compression: bool = True
    binary: bool = True
    max_http_buffer_size: int = 65536  # 64KB
    heartbeat_interval: int = 10  # seconds
    reconnect_attempts: int = 5
    reconnect_delay: int = 1  # seconds
    max_latency_ms: int = 100
    
@dataclass
class ClientSubscription:
    """Client subscription information"""
    client_id: str
    stream_types: Set[StreamType]
    symbols: Set[str]
    last_ping: float
    connected_at: float
    latency_samples: deque
    
    def __post_init__(self):
        if not hasattr(self, 'latency_samples') or self.latency_samples is None:
            self.latency_samples = deque(maxlen=10)

@dataclass
class StreamData:
    """Data structure for streaming"""
    stream_type: StreamType
    data: Any
    timestamp: float
    symbols: Optional[List[str]] = None
    compression_ratio: Optional[float] = None
    
class PerformanceMonitor:
    """Monitor WebSocket performance metrics"""
    
    def __init__(self):
        self.metrics = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'compression_savings': 0,
            'average_latency': 0,
            'peak_latency': 0,
            'active_connections': 0,
            'total_connections': 0,
            'reconnections': 0,
            'errors': 0,
            'stream_rates': defaultdict(int)
        }
        self.start_time = time.time()
        self.latency_samples = deque(maxlen=1000)
        
    def record_message_sent(self, size: int, stream_type: StreamType, compressed: bool = False):
        self.metrics['messages_sent'] += 1
        self.metrics['bytes_sent'] += size
        self.metrics['stream_rates'][stream_type.value] += 1
        if compressed:
            self.metrics['compression_savings'] += 1
            
    def record_message_received(self, size: int):
        self.metrics['messages_received'] += 1
        self.metrics['bytes_received'] += size
        
    def record_latency(self, latency_ms: float):
        self.latency_samples.append(latency_ms)
        self.metrics['average_latency'] = sum(self.latency_samples) / len(self.latency_samples)
        self.metrics['peak_latency'] = max(self.latency_samples)
        
    def record_connection(self):
        self.metrics['active_connections'] += 1
        self.metrics['total_connections'] += 1
        
    def record_disconnection(self):
        self.metrics['active_connections'] = max(0, self.metrics['active_connections'] - 1)
        
    def record_reconnection(self):
        self.metrics['reconnections'] += 1
        
    def record_error(self):
        self.metrics['errors'] += 1
        
    def get_stats(self) -> Dict:
        uptime = time.time() - self.start_time
        return {
            **self.metrics,
            'uptime_seconds': uptime,
            'messages_per_second': self.metrics['messages_sent'] / max(uptime, 1),
            'bytes_per_second': self.metrics['bytes_sent'] / max(uptime, 1),
            'error_rate': self.metrics['errors'] / max(self.metrics['total_connections'], 1)
        }

class DataCompressor:
    """Handles data compression for WebSocket messages"""
    
    @staticmethod
    def compress_data(data: Any, min_size: int = 1024) -> tuple[bytes, bool]:
        """Compress data if beneficial"""
        if isinstance(data, (dict, list)):
            json_data = json.dumps(data, separators=(',', ':'))
            json_bytes = json_data.encode('utf-8')
            
            if len(json_bytes) > min_size:
                compressed = gzip.compress(json_bytes)
                if len(compressed) < len(json_bytes) * 0.9:  # 10% compression threshold
                    return compressed, True
            return json_bytes, False
        return str(data).encode('utf-8'), False
    
    @staticmethod
    def decompress_data(data: bytes, compressed: bool) -> Any:
        """Decompress data if needed"""
        if compressed:
            decompressed = gzip.decompress(data)
            return json.loads(decompressed.decode('utf-8'))
        return json.loads(data.decode('utf-8'))

class WebSocketServer:
    """Robust WebSocket server for trading bot real-time data"""
    
    def __init__(self, app: Flask, config: WebSocketConfig = None):
        self.app = app
        self.config = config or WebSocketConfig()
        self.performance_monitor = PerformanceMonitor()
        self.compressor = DataCompressor()
        
        # Client management
        self.clients: Dict[str, ClientSubscription] = {}
        self.client_lock = threading.RLock()
        
        # Data streams
        self.data_streams: Dict[StreamType, Any] = {}
        self.stream_lock = threading.RLock()
        
        # Background tasks
        self.background_tasks: List[threading.Thread] = []
        self.shutdown_event = threading.Event()
        
        # Initialize SocketIO with optimized settings
        self.socketio = SocketIO(
            app,
            cors_allowed_origins="*",  # Configure appropriately for production
            logger=False,
            engineio_logger=False,
            async_mode='eventlet',
            ping_timeout=self.config.ping_timeout,
            ping_interval=self.config.ping_interval,
            compression=self.config.compression,
            binary=self.config.binary,
            max_http_buffer_size=self.config.max_http_buffer_size,
            json=json
        )
        
        self._setup_event_handlers()
        self._start_background_tasks()
        
        logger.info(f"WebSocket server initialized with config: {asdict(self.config)}")
    
    def _setup_event_handlers(self):
        """Setup SocketIO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            client_id = self._generate_client_id()
            with self.client_lock:
                self.clients[client_id] = ClientSubscription(
                    client_id=client_id,
                    stream_types=set(),
                    symbols=set(),
                    last_ping=time.time(),
                    connected_at=time.time(),
                    latency_samples=deque(maxlen=10)
                )
            
            self.performance_monitor.record_connection()
            
            logger.info(f"Client {client_id} connected")
            emit('connected', {
                'client_id': client_id,
                'server_time': time.time(),
                'config': {
                    'ping_interval': self.config.ping_interval,
                    'heartbeat_interval': self.config.heartbeat_interval,
                    'compression_enabled': self.config.compression
                }
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = self._get_client_id()
            if client_id:
                with self.client_lock:
                    if client_id in self.clients:
                        del self.clients[client_id]
                
                self.performance_monitor.record_disconnection()
                logger.info(f"Client {client_id} disconnected")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            client_id = self._get_client_id()
            if not client_id:
                emit('error', {'message': 'Client not identified'})
                return
            
            try:
                stream_types = {StreamType(st) for st in data.get('stream_types', [])}
                symbols = set(data.get('symbols', []))
                
                with self.client_lock:
                    if client_id in self.clients:
                        self.clients[client_id].stream_types.update(stream_types)
                        self.clients[client_id].symbols.update(symbols)
                
                # Join rooms for efficient broadcasting
                for stream_type in stream_types:
                    join_room(f"stream_{stream_type.value}")
                
                for symbol in symbols:
                    join_room(f"symbol_{symbol}")
                
                logger.info(f"Client {client_id} subscribed to {stream_types} for symbols {symbols}")
                emit('subscription_confirmed', {
                    'stream_types': [st.value for st in stream_types],
                    'symbols': list(symbols)
                })
                
            except Exception as e:
                logger.error(f"Subscription error for client {client_id}: {e}")
                emit('error', {'message': f'Subscription failed: {str(e)}'})
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            client_id = self._get_client_id()
            if not client_id:
                return
            
            try:
                stream_types = {StreamType(st) for st in data.get('stream_types', [])}
                symbols = set(data.get('symbols', []))
                
                with self.client_lock:
                    if client_id in self.clients:
                        self.clients[client_id].stream_types -= stream_types
                        self.clients[client_id].symbols -= symbols
                
                # Leave rooms
                for stream_type in stream_types:
                    leave_room(f"stream_{stream_type.value}")
                
                for symbol in symbols:
                    leave_room(f"symbol_{symbol}")
                
                logger.info(f"Client {client_id} unsubscribed from {stream_types} for symbols {symbols}")
                emit('unsubscription_confirmed', {
                    'stream_types': [st.value for st in stream_types],
                    'symbols': list(symbols)
                })
                
            except Exception as e:
                logger.error(f"Unsubscription error for client {client_id}: {e}")
                emit('error', {'message': f'Unsubscription failed: {str(e)}'})
        
        @self.socketio.on('ping')
        def handle_ping(data):
            client_id = self._get_client_id()
            if client_id:
                ping_time = data.get('timestamp', time.time())
                latency = (time.time() - ping_time) * 1000  # Convert to ms
                
                with self.client_lock:
                    if client_id in self.clients:
                        self.clients[client_id].last_ping = time.time()
                        self.clients[client_id].latency_samples.append(latency)
                
                self.performance_monitor.record_latency(latency)
                
                emit('pong', {
                    'timestamp': time.time(),
                    'latency_ms': latency,
                    'client_ping_time': ping_time
                })
        
        @self.socketio.on('get_performance_stats')
        def handle_get_performance_stats():
            emit('performance_stats', self.performance_monitor.get_stats())
    
    def _generate_client_id(self) -> str:
        """Generate unique client ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _get_client_id(self) -> Optional[str]:
        """Get client ID from session - simplified for this implementation"""
        from flask import request
        # In a real implementation, you'd store this in the session
        # For now, we'll use a simplified approach
        return getattr(request, 'sid', None)
    
    def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        
        def heartbeat_task():
            """Send heartbeat to detect disconnected clients"""
            while not self.shutdown_event.is_set():
                try:
                    current_time = time.time()
                    disconnected_clients = []
                    
                    with self.client_lock:
                        for client_id, client in self.clients.items():
                            if current_time - client.last_ping > self.config.ping_timeout:
                                disconnected_clients.append(client_id)
                    
                    # Clean up disconnected clients
                    for client_id in disconnected_clients:
                        with self.client_lock:
                            if client_id in self.clients:
                                del self.clients[client_id]
                        logger.warning(f"Client {client_id} disconnected due to timeout")
                        self.performance_monitor.record_disconnection()
                    
                    # Send heartbeat to all connected clients
                    self.socketio.emit('heartbeat', {
                        'timestamp': current_time,
                        'server_status': 'healthy',
                        'active_clients': len(self.clients)
                    })
                    
                except Exception as e:
                    logger.error(f"Heartbeat task error: {e}")
                    self.performance_monitor.record_error()
                
                eventlet.sleep(self.config.heartbeat_interval)
        
        def performance_monitoring_task():
            """Monitor and log performance metrics"""
            while not self.shutdown_event.is_set():
                try:
                    stats = self.performance_monitor.get_stats()
                    
                    # Log performance warnings
                    if stats['average_latency'] > self.config.max_latency_ms:
                        logger.warning(f"High latency detected: {stats['average_latency']:.2f}ms")
                    
                    if stats['error_rate'] > 0.05:  # 5% error rate threshold
                        logger.warning(f"High error rate detected: {stats['error_rate']:.2%}")
                    
                    # Emit performance stats to subscribed clients
                    self.socketio.emit('performance_update', stats, 
                                     room='stream_performance_metrics')
                    
                except Exception as e:
                    logger.error(f"Performance monitoring task error: {e}")
                
                eventlet.sleep(30)  # Every 30 seconds
        
        def system_health_task():
            """Monitor system health and resources"""
            while not self.shutdown_event.is_set():
                try:
                    process = psutil.Process()
                    system_stats = {
                        'cpu_percent': process.cpu_percent(),
                        'memory_mb': process.memory_info().rss / 1024 / 1024,
                        'memory_percent': process.memory_percent(),
                        'threads': process.num_threads(),
                        'timestamp': time.time()
                    }
                    
                    # Store system health data
                    with self.stream_lock:
                        self.data_streams[StreamType.SYSTEM_HEALTH] = system_stats
                    
                    # Emit to subscribed clients
                    self._broadcast_to_stream(StreamType.SYSTEM_HEALTH, system_stats)
                    
                except Exception as e:
                    logger.error(f"System health task error: {e}")
                
                eventlet.sleep(10)  # Every 10 seconds
        
        # Start background tasks
        tasks = [
            threading.Thread(target=heartbeat_task, daemon=True, name="WebSocket-Heartbeat"),
            threading.Thread(target=performance_monitoring_task, daemon=True, name="WebSocket-Performance"),
            threading.Thread(target=system_health_task, daemon=True, name="WebSocket-SystemHealth")
        ]
        
        for task in tasks:
            task.start()
            self.background_tasks.append(task)
        
        logger.info(f"Started {len(tasks)} background tasks")
    
    def _broadcast_to_stream(self, stream_type: StreamType, data: Any, symbols: List[str] = None):
        """Broadcast data to all clients subscribed to a stream"""
        try:
            # Create stream data object
            stream_data = StreamData(
                stream_type=stream_type,
                data=data,
                timestamp=time.time(),
                symbols=symbols
            )
            
            # Compress data if beneficial
            compressed_data, was_compressed = self.compressor.compress_data(asdict(stream_data))
            
            # Determine target room(s)
            rooms = [f"stream_{stream_type.value}"]
            if symbols:
                rooms.extend([f"symbol_{symbol}" for symbol in symbols])
            
            # Broadcast to all relevant rooms
            for room in rooms:
                if was_compressed:
                    self.socketio.emit('compressed_data', {
                        'compressed': True,
                        'data': compressed_data
                    }, room=room)
                else:
                    self.socketio.emit('stream_data', asdict(stream_data), room=room)
            
            # Update performance metrics
            self.performance_monitor.record_message_sent(
                len(compressed_data), stream_type, was_compressed
            )
            
        except Exception as e:
            logger.error(f"Broadcast error for {stream_type}: {e}")
            self.performance_monitor.record_error()
    
    # Public API methods for data streaming
    
    def broadcast_market_data(self, symbol: str, market_data: Dict[str, Any]):
        """Broadcast real-time market data"""
        self._broadcast_to_stream(StreamType.MARKET_DATA, market_data, [symbol])
    
    def broadcast_position_update(self, positions: List[Dict[str, Any]]):
        """Broadcast position updates"""
        self._broadcast_to_stream(StreamType.POSITIONS, positions)
    
    def broadcast_signal(self, symbol: str, signal_data: Dict[str, Any]):
        """Broadcast trading signals"""
        self._broadcast_to_stream(StreamType.SIGNALS, signal_data, [symbol])
    
    def broadcast_order_update(self, order_data: Dict[str, Any]):
        """Broadcast order updates"""
        self._broadcast_to_stream(StreamType.ORDERS, order_data)
    
    def broadcast_account_update(self, account_data: Dict[str, Any]):
        """Broadcast account information updates"""
        self._broadcast_to_stream(StreamType.ACCOUNT, account_data)
    
    def get_connected_clients(self) -> int:
        """Get number of connected clients"""
        with self.client_lock:
            return len(self.clients)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        return self.performance_monitor.get_stats()
    
    def shutdown(self):
        """Gracefully shutdown the WebSocket server"""
        logger.info("Shutting down WebSocket server...")
        self.shutdown_event.set()
        
        # Wait for background tasks to complete
        for task in self.background_tasks:
            if task.is_alive():
                task.join(timeout=5)
        
        logger.info("WebSocket server shutdown complete")
    
    def run(self, host: str = '0.0.0.0', port: int = 8765, debug: bool = False):
        """Run the WebSocket server"""
        logger.info(f"Starting WebSocket server on {host}:{port}")
        try:
            self.socketio.run(self.app, host=host, port=port, debug=debug)
        except KeyboardInterrupt:
            logger.info("WebSocket server interrupted")
        finally:
            self.shutdown()

# Factory function for easy integration
def create_websocket_server(app: Flask, config: WebSocketConfig = None) -> WebSocketServer:
    """Factory function to create a WebSocket server instance"""
    return WebSocketServer(app, config)

# Enhanced client-side auto-reconnection JavaScript code
WEBSOCKET_CLIENT_JS = """
<script>
class TradingBotWebSocketClient {
    constructor(url, options = {}) {
        this.url = url;
        this.options = {
            reconnectAttempts: 5,
            reconnectDelay: 1000,
            maxReconnectDelay: 30000,
            heartbeatInterval: 10000,
            pingInterval: 25000,
            ...options
        };
        
        this.socket = null;
        this.reconnectCount = 0;
        this.isConnected = false;
        this.subscriptions = new Set();
        this.eventHandlers = new Map();
        this.latencyHistory = [];
        this.lastPingTime = 0;
        
        this.connect();
        this.startHeartbeat();
    }
    
    connect() {
        try {
            this.socket = io(this.url, {
                transports: ['websocket', 'polling'],
                timeout: 5000,
                forceNew: true
            });
            
            this.setupEventHandlers();
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.handleReconnect();
        }
    }
    
    setupEventHandlers() {
        this.socket.on('connect', () => {
            console.log('Connected to trading bot WebSocket server');
            this.isConnected = true;
            this.reconnectCount = 0;
            this.resubscribeAll();
            this.emit('connected');
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('Disconnected from server:', reason);
            this.isConnected = false;
            this.emit('disconnected', reason);
            
            if (reason === 'io server disconnect') {
                // Server initiated disconnect, try to reconnect
                this.handleReconnect();
            }
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.handleReconnect();
        });
        
        this.socket.on('heartbeat', (data) => {
            this.emit('heartbeat', data);
        });
        
        this.socket.on('pong', (data) => {
            const latency = Date.now() - this.lastPingTime;
            this.latencyHistory.push(latency);
            if (this.latencyHistory.length > 10) {
                this.latencyHistory.shift();
            }
            this.emit('latency_update', {
                current: latency,
                average: this.latencyHistory.reduce((a, b) => a + b, 0) / this.latencyHistory.length
            });
        });
        
        this.socket.on('stream_data', (data) => {
            this.emit('stream_data', data);
        });
        
        this.socket.on('compressed_data', (data) => {
            if (data.compressed) {
                // Handle compressed data (would need decompression logic)
                this.emit('compressed_data', data);
            }
        });
        
        this.socket.on('performance_stats', (stats) => {
            this.emit('performance_stats', stats);
        });
        
        this.socket.on('error', (error) => {
            console.error('Server error:', error);
            this.emit('error', error);
        });
    }
    
    handleReconnect() {
        if (this.reconnectCount < this.options.reconnectAttempts) {
            const delay = Math.min(
                this.options.reconnectDelay * Math.pow(2, this.reconnectCount),
                this.options.maxReconnectDelay
            );
            
            console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectCount + 1})`);
            
            setTimeout(() => {
                this.reconnectCount++;
                this.connect();
            }, delay);
        } else {
            console.error('Max reconnection attempts reached');
            this.emit('max_reconnects_reached');
        }
    }
    
    subscribe(streamTypes, symbols = []) {
        if (this.isConnected) {
            const subscription = { stream_types: streamTypes, symbols: symbols };
            this.socket.emit('subscribe', subscription);
            this.subscriptions.add(JSON.stringify(subscription));
        }
    }
    
    unsubscribe(streamTypes, symbols = []) {
        if (this.isConnected) {
            const subscription = { stream_types: streamTypes, symbols: symbols };
            this.socket.emit('unsubscribe', subscription);
            this.subscriptions.delete(JSON.stringify(subscription));
        }
    }
    
    resubscribeAll() {
        this.subscriptions.forEach(sub => {
            const subscription = JSON.parse(sub);
            this.socket.emit('subscribe', subscription);
        });
    }
    
    startHeartbeat() {
        setInterval(() => {
            if (this.isConnected) {
                this.lastPingTime = Date.now();
                this.socket.emit('ping', { timestamp: this.lastPingTime / 1000 });
            }
        }, this.options.pingInterval);
    }
    
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, new Set());
        }
        this.eventHandlers.get(event).add(handler);
    }
    
    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).delete(handler);
        }
    }
    
    emit(event, data = null) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Event handler error for ${event}:`, error);
                }
            });
        }
    }
    
    getLatencyStats() {
        if (this.latencyHistory.length === 0) return null;
        return {
            current: this.latencyHistory[this.latencyHistory.length - 1],
            average: this.latencyHistory.reduce((a, b) => a + b, 0) / this.latencyHistory.length,
            min: Math.min(...this.latencyHistory),
            max: Math.max(...this.latencyHistory)
        };
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
    }
}

// Usage example:
// const wsClient = new TradingBotWebSocketClient('ws://localhost:8765');
// wsClient.subscribe(['market_data', 'signals'], ['AAPL', 'MSFT']);
// wsClient.on('stream_data', (data) => console.log('Received:', data));
</script>
"""