"""
WebSocket Connection Manager with automatic reconnection and health monitoring
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import websockets
from websockets.exceptions import WebSocketException
import time

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class WebSocketManager:
    """
    Manages WebSocket connections with automatic reconnection,
    heartbeat monitoring, and message queuing.
    """
    
    def __init__(
        self,
        url: str,
        on_message: Optional[Callable] = None,
        on_connect: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        heartbeat_interval: int = 30,
        max_reconnect_attempts: int = 10,
        reconnect_base_delay: float = 1.0,
        reconnect_max_delay: float = 60.0,
        message_queue_size: int = 1000
    ):
        self.url = url
        self.ws = None
        self.state = ConnectionState.DISCONNECTED
        
        # Callbacks
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_error = on_error
        
        # Configuration
        self.heartbeat_interval = heartbeat_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_base_delay = reconnect_base_delay
        self.reconnect_max_delay = reconnect_max_delay
        
        # State management
        self.reconnect_count = 0
        self.last_heartbeat = None
        self.last_message_time = None
        self.connection_start_time = None
        
        # Message queue for offline handling
        self.message_queue: List[Dict[str, Any]] = []
        self.message_queue_size = message_queue_size
        
        # Tasks
        self.receive_task = None
        self.heartbeat_task = None
        self.reconnect_task = None
        
        # Statistics
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "reconnections": 0,
            "errors": 0,
            "uptime": 0,
            "last_error": None
        }

    async def connect(self) -> bool:
        """Establish WebSocket connection"""
        if self.state == ConnectionState.CONNECTED:
            logger.info("Already connected")
            return True
            
        self.state = ConnectionState.CONNECTING
        
        try:
            logger.info(f"Connecting to {self.url}")
            self.ws = await websockets.connect(
                self.url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.state = ConnectionState.CONNECTED
            self.connection_start_time = datetime.now()
            self.reconnect_count = 0
            
            # Start background tasks
            self.receive_task = asyncio.create_task(self._receive_messages())
            self.heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
            
            # Process queued messages
            await self._process_message_queue()
            
            # Trigger callback
            if self.on_connect:
                await self._safe_callback(self.on_connect)
            
            logger.info("WebSocket connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.state = ConnectionState.ERROR
            self.stats["errors"] += 1
            self.stats["last_error"] = str(e)
            
            if self.on_error:
                await self._safe_callback(self.on_error, e)
            
            # Start reconnection
            await self._start_reconnection()
            return False

    async def disconnect(self):
        """Gracefully disconnect WebSocket"""
        logger.info("Disconnecting WebSocket")
        
        # Cancel tasks
        if self.receive_task:
            self.receive_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.reconnect_task:
            self.reconnect_task.cancel()
        
        # Close connection
        if self.ws:
            await self.ws.close()
            self.ws = None
        
        self.state = ConnectionState.DISCONNECTED
        
        if self.on_disconnect:
            await self._safe_callback(self.on_disconnect)

    async def send(self, message: Dict[str, Any]) -> bool:
        """Send message through WebSocket"""
        if self.state != ConnectionState.CONNECTED:
            logger.warning("Not connected, queuing message")
            self._queue_message(message)
            return False
        
        try:
            await self.ws.send(json.dumps(message))
            self.stats["messages_sent"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Send failed: {e}")
            self._queue_message(message)
            await self._handle_connection_error(e)
            return False

    async def _receive_messages(self):
        """Receive and process messages"""
        try:
            async for message in self.ws:
                self.last_message_time = datetime.now()
                self.stats["messages_received"] += 1
                
                try:
                    data = json.loads(message)
                    
                    # Handle different message types
                    if data.get("type") == "ping":
                        await self.send({"type": "pong"})
                    elif self.on_message:
                        await self._safe_callback(self.on_message, data)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Connection closed: {e}")
            await self._handle_connection_error(e)
            
        except Exception as e:
            logger.error(f"Receive error: {e}")
            await self._handle_connection_error(e)

    async def _heartbeat_monitor(self):
        """Monitor connection health"""
        while self.state == ConnectionState.CONNECTED:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Check last message time
                if self.last_message_time:
                    time_since_last = (datetime.now() - self.last_message_time).seconds
                    if time_since_last > self.heartbeat_interval * 2:
                        logger.warning("No messages received, sending ping")
                        await self.send({"type": "ping"})
                
                # Update uptime
                if self.connection_start_time:
                    self.stats["uptime"] = (datetime.now() - self.connection_start_time).seconds
                    
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _start_reconnection(self):
        """Start reconnection process"""
        if self.reconnect_task and not self.reconnect_task.done():
            return
            
        self.reconnect_task = asyncio.create_task(self._reconnect())

    async def _reconnect(self):
        """Reconnection with exponential backoff"""
        self.state = ConnectionState.RECONNECTING
        
        while self.reconnect_count < self.max_reconnect_attempts:
            # Calculate delay with exponential backoff
            delay = min(
                self.reconnect_base_delay * (2 ** self.reconnect_count),
                self.reconnect_max_delay
            )
            
            logger.info(f"Reconnecting in {delay}s (attempt {self.reconnect_count + 1})")
            await asyncio.sleep(delay)
            
            self.reconnect_count += 1
            self.stats["reconnections"] += 1
            
            if await self.connect():
                logger.info("Reconnection successful")
                return
        
        logger.error("Max reconnection attempts reached")
        self.state = ConnectionState.ERROR
        
        if self.on_error:
            await self._safe_callback(
                self.on_error,
                Exception("Max reconnection attempts reached")
            )

    async def _handle_connection_error(self, error: Exception):
        """Handle connection errors"""
        logger.error(f"Connection error: {error}")
        
        self.state = ConnectionState.ERROR
        self.stats["errors"] += 1
        self.stats["last_error"] = str(error)
        
        if self.ws:
            await self.ws.close()
            self.ws = None
        
        await self._start_reconnection()

    def _queue_message(self, message: Dict[str, Any]):
        """Queue messages for later delivery"""
        if len(self.message_queue) >= self.message_queue_size:
            self.message_queue.pop(0)  # Remove oldest
            
        self.message_queue.append({
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.debug(f"Message queued (queue size: {len(self.message_queue)})")

    async def _process_message_queue(self):
        """Process queued messages after reconnection"""
        if not self.message_queue:
            return
            
        logger.info(f"Processing {len(self.message_queue)} queued messages")
        
        messages_to_send = self.message_queue.copy()
        self.message_queue.clear()
        
        for item in messages_to_send:
            await self.send(item["message"])
            await asyncio.sleep(0.1)  # Rate limit

    async def _safe_callback(self, callback: Callable, *args, **kwargs):
        """Safely execute callbacks"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Callback error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get connection status and statistics"""
        return {
            "state": self.state.value,
            "url": self.url,
            "reconnect_count": self.reconnect_count,
            "last_message_time": self.last_message_time.isoformat() if self.last_message_time else None,
            "queue_size": len(self.message_queue),
            "stats": self.stats
        }

    def is_connected(self) -> bool:
        """Check if connected"""
        return self.state == ConnectionState.CONNECTED


class MultiWebSocketManager:
    """Manages multiple WebSocket connections"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketManager] = {}
        
    async def add_connection(
        self,
        name: str,
        url: str,
        **kwargs
    ) -> WebSocketManager:
        """Add a new WebSocket connection"""
        if name in self.connections:
            logger.warning(f"Connection {name} already exists")
            return self.connections[name]
        
        manager = WebSocketManager(url, **kwargs)
        self.connections[name] = manager
        await manager.connect()
        
        return manager
    
    async def remove_connection(self, name: str):
        """Remove a WebSocket connection"""
        if name in self.connections:
            await self.connections[name].disconnect()
            del self.connections[name]
    
    def get_connection(self, name: str) -> Optional[WebSocketManager]:
        """Get a specific connection"""
        return self.connections.get(name)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Send message to all connections"""
        tasks = []
        for manager in self.connections.values():
            if manager.is_connected():
                tasks.append(manager.send(message))
        
        if tasks:
            await asyncio.gather(*tasks)
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all connections"""
        return {
            name: manager.get_status()
            for name, manager in self.connections.items()
        }
    
    async def disconnect_all(self):
        """Disconnect all connections"""
        tasks = []
        for manager in self.connections.values():
            tasks.append(manager.disconnect())
        
        if tasks:
            await asyncio.gather(*tasks)
        
        self.connections.clear()


# Example usage
async def main():
    """Example of using WebSocketManager"""
    
    async def on_message(data):
        print(f"Received: {data}")
    
    async def on_connect():
        print("Connected!")
    
    async def on_disconnect():
        print("Disconnected!")
    
    async def on_error(error):
        print(f"Error: {error}")
    
    # Create manager
    manager = WebSocketManager(
        url="ws://localhost:9000/ws/trading",
        on_message=on_message,
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        on_error=on_error
    )
    
    # Connect
    await manager.connect()
    
    # Send message
    await manager.send({"type": "subscribe", "symbols": ["AAPL", "GOOGL"]})
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
            status = manager.get_status()
            print(f"Status: {status['state']}, Queue: {status['queue_size']}")
            
    except KeyboardInterrupt:
        await manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())