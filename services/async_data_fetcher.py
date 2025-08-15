"""
Async Data Fetcher for high-performance concurrent operations.

This module provides:
- Concurrent API requests with connection pooling
- Streaming data handling with backpressure management
- WebSocket optimization with reconnection logic
- Rate limiting and throttling mechanisms
- Async queue management for real-time data
- Circuit breaker patterns for resilience
"""

import asyncio
import aiohttp
import websockets
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Callable, Union, AsyncGenerator, Set
from dataclasses import dataclass, field
from collections import deque, defaultdict
from datetime import datetime, timedelta
import weakref
import ssl
from urllib.parse import urljoin, urlparse

# Rate limiting imports
from asyncio import Semaphore, Event, Queue
import heapq

logger = logging.getLogger(__name__)


@dataclass
class RequestConfig:
    """Configuration for HTTP requests."""
    timeout: float = 30.0
    retries: int = 3
    backoff_factor: float = 1.0
    headers: Dict[str, str] = field(default_factory=dict)
    ssl_verify: bool = True
    
    
@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_second: float = 10.0
    burst_size: int = 20
    window_size: float = 60.0  # seconds
    

@dataclass
class WebSocketConfig:
    """WebSocket configuration."""
    reconnect_interval: float = 5.0
    max_reconnect_attempts: int = 10
    ping_interval: float = 30.0
    ping_timeout: float = 10.0
    message_queue_size: int = 10000
    compression: bool = True


class TokenBucket:
    """Token bucket for rate limiting."""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity  # maximum tokens
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from bucket."""
        async with self._lock:
            now = time.time()
            # Add tokens based on elapsed time
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def wait_for_tokens(self, tokens: int = 1) -> None:
        """Wait until tokens are available."""
        while not await self.acquire(tokens):
            # Calculate wait time
            async with self._lock:
                needed_tokens = tokens - self.tokens
                wait_time = needed_tokens / self.rate
                await asyncio.sleep(min(wait_time, 1.0))  # Maximum 1 second wait


class RateLimiter:
    """Advanced rate limiter with multiple strategies."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.token_bucket = TokenBucket(config.requests_per_second, config.burst_size)
        self.request_times = deque()
        self.per_endpoint_limits = defaultdict(lambda: TokenBucket(config.requests_per_second / 2, config.burst_size // 2))
        self._lock = asyncio.Lock()
    
    async def acquire(self, endpoint: Optional[str] = None) -> None:
        """Acquire permission to make a request."""
        # Global rate limiting
        await self.token_bucket.wait_for_tokens()
        
        # Per-endpoint rate limiting
        if endpoint:
            endpoint_limiter = self.per_endpoint_limits[endpoint]
            await endpoint_limiter.wait_for_tokens()
        
        # Sliding window check
        async with self._lock:
            now = time.time()
            # Remove old requests
            while self.request_times and self.request_times[0] < now - self.config.window_size:
                self.request_times.popleft()
            
            # Check if we're within rate limit
            if len(self.request_times) >= self.config.requests_per_second * self.config.window_size:
                oldest_request = self.request_times[0]
                wait_time = oldest_request + self.config.window_size - now
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            self.request_times.append(now)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            'requests_per_second': self.config.requests_per_second,
            'current_tokens': self.token_bucket.tokens,
            'recent_requests': len(self.request_times),
            'per_endpoint_limits': len(self.per_endpoint_limits)
        }


class ConnectionPool:
    """Async HTTP connection pool with optimization."""
    
    def __init__(self, max_connections: int = 100, max_per_host: int = 20):
        self.max_connections = max_connections
        self.max_per_host = max_per_host
        self._connector = None
        self._session = None
        self._lock = asyncio.Lock()
        
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    # Create optimized connector
                    self._connector = aiohttp.TCPConnector(
                        limit=self.max_connections,
                        limit_per_host=self.max_per_host,
                        ttl_dns_cache=300,
                        use_dns_cache=True,
                        keepalive_timeout=30,
                        enable_cleanup_closed=True
                    )
                    
                    # Create session with optimized settings
                    timeout = aiohttp.ClientTimeout(total=30, connect=10)
                    self._session = aiohttp.ClientSession(
                        connector=self._connector,
                        timeout=timeout,
                        headers={'User-Agent': 'TradingBot/1.0'}
                    )
        
        return self._session
    
    async def close(self) -> None:
        """Close session and connector."""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._connector:
            await self._connector.close()


class AsyncDataFetcher:
    """High-performance async data fetcher."""
    
    def __init__(
        self,
        rate_limit_config: Optional[RateLimitConfig] = None,
        request_config: Optional[RequestConfig] = None,
        max_concurrent: int = 50
    ):
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())
        self.request_config = request_config or RequestConfig()
        self.connection_pool = ConnectionPool()
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)
        
        # Statistics
        self.stats = defaultdict(int)
        self._stats_lock = asyncio.Lock()
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker()
        
    async def fetch_single(
        self,
        url: str,
        method: str = 'GET',
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        endpoint_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch single URL with rate limiting and error handling."""
        async with self.semaphore:
            await self.rate_limiter.acquire(endpoint_name)
            
            # Prepare request
            merged_headers = {**self.request_config.headers}
            if headers:
                merged_headers.update(headers)
            
            session = await self.connection_pool.get_session()
            
            for attempt in range(self.request_config.retries + 1):
                try:
                    async with self.circuit_breaker:
                        async with session.request(
                            method,
                            url,
                            json=data,
                            headers=merged_headers,
                            ssl=self.request_config.ssl_verify,
                            timeout=aiohttp.ClientTimeout(total=self.request_config.timeout)
                        ) as response:
                            
                            await self._update_stats('requests_total')
                            
                            if response.status == 200:
                                content_type = response.headers.get('content-type', '')
                                if 'application/json' in content_type:
                                    result = await response.json()
                                else:
                                    result = {'text': await response.text()}
                                
                                await self._update_stats('requests_success')
                                return {
                                    'success': True,
                                    'data': result,
                                    'status': response.status,
                                    'url': url
                                }
                            else:
                                await self._update_stats('requests_error')
                                if response.status >= 500 and attempt < self.request_config.retries:
                                    # Retry on server errors
                                    wait_time = self.request_config.backoff_factor * (2 ** attempt)
                                    await asyncio.sleep(wait_time)
                                    continue
                                
                                return {
                                    'success': False,
                                    'error': f"HTTP {response.status}",
                                    'status': response.status,
                                    'url': url
                                }
                
                except asyncio.TimeoutError:
                    await self._update_stats('requests_timeout')
                    if attempt < self.request_config.retries:
                        wait_time = self.request_config.backoff_factor * (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        continue
                    
                    return {
                        'success': False,
                        'error': 'Request timeout',
                        'url': url
                    }
                
                except Exception as e:
                    await self._update_stats('requests_exception')
                    if attempt < self.request_config.retries:
                        wait_time = self.request_config.backoff_factor * (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        continue
                    
                    return {
                        'success': False,
                        'error': str(e),
                        'url': url
                    }
            
            return {
                'success': False,
                'error': 'Max retries exceeded',
                'url': url
            }
    
    async def fetch_batch(
        self,
        urls: List[str],
        method: str = 'GET',
        data_list: Optional[List[Dict]] = None,
        headers: Optional[Dict] = None,
        max_concurrent: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch multiple URLs concurrently."""
        if max_concurrent is None:
            max_concurrent = min(len(urls), self.max_concurrent)
        
        semaphore = Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(i: int, url: str) -> Dict[str, Any]:
            async with semaphore:
                data = data_list[i] if data_list and i < len(data_list) else None
                return await self.fetch_single(url, method, data, headers)
        
        tasks = [fetch_with_semaphore(i, url) for i, url in enumerate(urls)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error responses
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'success': False,
                    'error': str(result),
                    'url': urls[i] if i < len(urls) else 'unknown'
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def stream_data(
        self,
        url_generator: AsyncGenerator[str, None],
        processor: Callable[[Dict], Any],
        buffer_size: int = 1000
    ) -> AsyncGenerator[Any, None]:
        """Stream data processing with backpressure management."""
        buffer = Queue(buffer_size)
        
        async def producer():
            """Produce data from URLs."""
            async for url in url_generator:
                try:
                    result = await self.fetch_single(url)
                    if result['success']:
                        await buffer.put(result['data'])
                except Exception as e:
                    logger.error(f"Producer error: {e}")
                    await buffer.put(None)  # Sentinel value
        
        async def consumer():
            """Consume and process data."""
            while True:
                try:
                    data = await buffer.get()
                    if data is None:  # Sentinel value
                        break
                    
                    processed = processor(data)
                    yield processed
                    buffer.task_done()
                except Exception as e:
                    logger.error(f"Consumer error: {e}")
                    break
        
        # Start producer
        producer_task = asyncio.create_task(producer())
        
        try:
            async for result in consumer():
                yield result
        finally:
            producer_task.cancel()
            try:
                await producer_task
            except asyncio.CancelledError:
                pass
    
    async def _update_stats(self, key: str) -> None:
        """Update statistics atomically."""
        async with self._stats_lock:
            self.stats[key] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fetcher statistics."""
        return {
            'requests': dict(self.stats),
            'rate_limiter': self.rate_limiter.get_stats(),
            'circuit_breaker': self.circuit_breaker.get_stats(),
            'max_concurrent': self.max_concurrent
        }
    
    async def close(self) -> None:
        """Close connections and clean up."""
        await self.connection_pool.close()


class CircuitBreaker:
    """Circuit breaker for fault tolerance."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        async with self._lock:
            if self.state == 'OPEN':
                if self.last_failure_time and time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = 'HALF_OPEN'
                    logger.info("Circuit breaker moving to HALF_OPEN")
                else:
                    raise CircuitBreakerError("Circuit breaker is OPEN")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._lock:
            if exc_type and issubclass(exc_type, self.expected_exception):
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = 'OPEN'
                    logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")
            else:
                # Success
                if self.state == 'HALF_OPEN':
                    self.state = 'CLOSED'
                    self.failure_count = 0
                    logger.info("Circuit breaker CLOSED")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time
        }


class CircuitBreakerError(Exception):
    """Circuit breaker exception."""
    pass


class WebSocketManager:
    """High-performance WebSocket manager with reconnection."""
    
    def __init__(self, config: Optional[WebSocketConfig] = None):
        self.config = config or WebSocketConfig()
        self.connections = {}
        self.message_handlers = defaultdict(list)
        self.stats = defaultdict(int)
        self._running = False
        self._tasks = set()
        
    async def connect(
        self,
        url: str,
        name: Optional[str] = None,
        headers: Optional[Dict] = None,
        subprotocols: Optional[List[str]] = None
    ) -> str:
        """Connect to WebSocket with auto-reconnection."""
        connection_name = name or f"ws_{len(self.connections)}"
        
        if connection_name in self.connections:
            await self.disconnect(connection_name)
        
        connection_info = {
            'url': url,
            'headers': headers,
            'subprotocols': subprotocols,
            'websocket': None,
            'reconnect_count': 0,
            'last_ping': time.time(),
            'message_queue': Queue(self.config.message_queue_size)
        }
        
        self.connections[connection_name] = connection_info
        
        # Start connection task
        task = asyncio.create_task(self._manage_connection(connection_name))
        self._tasks.add(task)
        
        return connection_name
    
    async def _manage_connection(self, connection_name: str) -> None:
        """Manage WebSocket connection with reconnection logic."""
        connection_info = self.connections[connection_name]
        
        while self._running and connection_name in self.connections:
            try:
                # Connect to WebSocket
                extra_headers = connection_info.get('headers', {})
                subprotocols = connection_info.get('subprotocols', [])
                
                async with websockets.connect(
                    connection_info['url'],
                    extra_headers=extra_headers,
                    subprotocols=subprotocols,
                    ping_interval=self.config.ping_interval,
                    ping_timeout=self.config.ping_timeout,
                    compression='deflate' if self.config.compression else None
                ) as websocket:
                    
                    connection_info['websocket'] = websocket
                    connection_info['reconnect_count'] = 0
                    self.stats[f'{connection_name}_connected'] += 1
                    
                    logger.info(f"WebSocket {connection_name} connected")
                    
                    # Start message handling tasks
                    receive_task = asyncio.create_task(
                        self._receive_messages(connection_name, websocket)
                    )
                    send_task = asyncio.create_task(
                        self._send_messages(connection_name, websocket)
                    )
                    
                    try:
                        # Wait for any task to complete/fail
                        await asyncio.wait(
                            [receive_task, send_task],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                    finally:
                        receive_task.cancel()
                        send_task.cancel()
                        
                        try:
                            await receive_task
                        except asyncio.CancelledError:
                            pass
                        
                        try:
                            await send_task
                        except asyncio.CancelledError:
                            pass
            
            except Exception as e:
                connection_info['reconnect_count'] += 1
                self.stats[f'{connection_name}_errors'] += 1
                
                logger.error(f"WebSocket {connection_name} error: {e}")
                
                if connection_info['reconnect_count'] > self.config.max_reconnect_attempts:
                    logger.error(f"Max reconnection attempts reached for {connection_name}")
                    break
                
                # Wait before reconnecting
                wait_time = min(
                    self.config.reconnect_interval * connection_info['reconnect_count'],
                    60.0  # Max 60 seconds
                )
                await asyncio.sleep(wait_time)
        
        # Cleanup
        if connection_name in self.connections:
            del self.connections[connection_name]
    
    async def _receive_messages(self, connection_name: str, websocket) -> None:
        """Receive messages from WebSocket."""
        async for message in websocket:
            try:
                if isinstance(message, str):
                    data = json.loads(message)
                else:
                    data = message  # Binary data
                
                # Call message handlers
                for handler in self.message_handlers[connection_name]:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(data)
                        else:
                            handler(data)
                    except Exception as e:
                        logger.error(f"Message handler error: {e}")
                
                self.stats[f'{connection_name}_messages_received'] += 1
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                self.stats[f'{connection_name}_decode_errors'] += 1
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                self.stats[f'{connection_name}_processing_errors'] += 1
    
    async def _send_messages(self, connection_name: str, websocket) -> None:
        """Send queued messages to WebSocket."""
        connection_info = self.connections[connection_name]
        message_queue = connection_info['message_queue']
        
        while True:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(message_queue.get(), timeout=1.0)
                
                if isinstance(message, dict):
                    await websocket.send(json.dumps(message))
                else:
                    await websocket.send(message)
                
                self.stats[f'{connection_name}_messages_sent'] += 1
                
            except asyncio.TimeoutError:
                # Timeout is normal, continue
                continue
            except Exception as e:
                logger.error(f"Send message error: {e}")
                break
    
    async def send_message(self, connection_name: str, message: Union[str, Dict]) -> bool:
        """Send message to WebSocket."""
        if connection_name not in self.connections:
            return False
        
        connection_info = self.connections[connection_name]
        message_queue = connection_info['message_queue']
        
        try:
            message_queue.put_nowait(message)
            return True
        except asyncio.QueueFull:
            logger.warning(f"Message queue full for {connection_name}")
            return False
    
    def add_message_handler(self, connection_name: str, handler: Callable) -> None:
        """Add message handler for connection."""
        self.message_handlers[connection_name].append(handler)
    
    def remove_message_handler(self, connection_name: str, handler: Callable) -> None:
        """Remove message handler for connection."""
        if handler in self.message_handlers[connection_name]:
            self.message_handlers[connection_name].remove(handler)
    
    async def disconnect(self, connection_name: str) -> None:
        """Disconnect WebSocket."""
        if connection_name in self.connections:
            connection_info = self.connections[connection_name]
            websocket = connection_info.get('websocket')
            
            if websocket:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.error(f"Error closing WebSocket {connection_name}: {e}")
            
            del self.connections[connection_name]
    
    async def start(self) -> None:
        """Start WebSocket manager."""
        self._running = True
        logger.info("WebSocket manager started")
    
    async def stop(self) -> None:
        """Stop WebSocket manager and close all connections."""
        self._running = False
        
        # Disconnect all connections
        for connection_name in list(self.connections.keys()):
            await self.disconnect(connection_name)
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()
        logger.info("WebSocket manager stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket statistics."""
        return {
            'connections': len(self.connections),
            'stats': dict(self.stats),
            'connection_info': {
                name: {
                    'url': info['url'],
                    'reconnect_count': info['reconnect_count'],
                    'queue_size': info['message_queue'].qsize()
                }
                for name, info in self.connections.items()
            }
        }


# Factory functions for easy access
def create_data_fetcher(
    rate_limit: Optional[RateLimitConfig] = None,
    request_config: Optional[RequestConfig] = None,
    max_concurrent: int = 50
) -> AsyncDataFetcher:
    """Create optimized data fetcher."""
    return AsyncDataFetcher(rate_limit, request_config, max_concurrent)


def create_websocket_manager(config: Optional[WebSocketConfig] = None) -> WebSocketManager:
    """Create optimized WebSocket manager."""
    return WebSocketManager(config)


# Global instances
_global_fetcher: Optional[AsyncDataFetcher] = None
_global_ws_manager: Optional[WebSocketManager] = None


async def get_global_fetcher() -> AsyncDataFetcher:
    """Get global data fetcher instance."""
    global _global_fetcher
    if _global_fetcher is None:
        _global_fetcher = create_data_fetcher()
    return _global_fetcher


async def get_global_ws_manager() -> WebSocketManager:
    """Get global WebSocket manager instance."""
    global _global_ws_manager
    if _global_ws_manager is None:
        _global_ws_manager = create_websocket_manager()
        await _global_ws_manager.start()
    return _global_ws_manager


async def cleanup_global_instances() -> None:
    """Cleanup global instances."""
    global _global_fetcher, _global_ws_manager
    
    if _global_fetcher:
        await _global_fetcher.close()
        _global_fetcher = None
    
    if _global_ws_manager:
        await _global_ws_manager.stop()
        _global_ws_manager = None