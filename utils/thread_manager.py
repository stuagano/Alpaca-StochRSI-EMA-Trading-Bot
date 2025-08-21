"""
Thread Manager for Memory Leak Prevention
Manages threading resources and prevents memory leaks in long-running processes
"""

import threading
import time
import logging
import weakref
from typing import Dict, List, Optional, Callable, Any
from contextlib import contextmanager
from datetime import datetime, timedelta
import atexit

logger = logging.getLogger(__name__)

class ManagedThread:
    """Thread wrapper with proper lifecycle management"""
    
    def __init__(self, target: Callable, name: str, daemon: bool = True, 
                 cleanup_func: Optional[Callable] = None, **kwargs):
        self.target = target
        self.name = name
        self.cleanup_func = cleanup_func
        self.kwargs = kwargs
        self.thread = None
        self.shutdown_event = threading.Event()
        self.start_time = None
        self.last_heartbeat = None
        self._is_stopped = False
    
    def start(self):
        """Start the managed thread"""
        if self.thread and self.thread.is_alive():
            logger.warning(f"Thread {self.name} is already running")
            return
        
        self.shutdown_event.clear()
        self._is_stopped = False
        self.thread = threading.Thread(
            target=self._wrapped_target,
            name=self.name,
            daemon=True
        )
        self.start_time = datetime.now()
        self.thread.start()
        logger.info(f"Started managed thread: {self.name}")
    
    def _wrapped_target(self):
        """Wrapped target with proper cleanup"""
        try:
            self.last_heartbeat = datetime.now()
            self.target(shutdown_event=self.shutdown_event, **self.kwargs)
        except Exception as e:
            logger.error(f"Error in thread {self.name}: {e}", exc_info=True)
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Perform cleanup operations"""
        try:
            if self.cleanup_func:
                self.cleanup_func()
            logger.info(f"Thread {self.name} cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup for thread {self.name}: {e}")
        finally:
            self._is_stopped = True
    
    def stop(self, timeout: float = 5.0):
        """Stop the thread gracefully"""
        if not self.thread or not self.thread.is_alive():
            return
        
        logger.info(f"Stopping thread: {self.name}")
        self.shutdown_event.set()
        self.thread.join(timeout=timeout)
        
        if self.thread.is_alive():
            logger.warning(f"Thread {self.name} did not stop within {timeout}s")
        else:
            logger.info(f"Thread {self.name} stopped successfully")
    
    def is_alive(self) -> bool:
        """Check if thread is alive"""
        return self.thread is not None and self.thread.is_alive()
    
    def update_heartbeat(self):
        """Update thread heartbeat"""
        self.last_heartbeat = datetime.now()
    
    def get_runtime(self) -> Optional[timedelta]:
        """Get thread runtime"""
        if self.start_time:
            return datetime.now() - self.start_time
        return None

class ThreadManager:
    """Global thread manager for preventing memory leaks"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.threads: Dict[str, ManagedThread] = {}
        self.cleanup_funcs: List[Callable] = []
        self._monitor_thread = None
        self._shutdown_event = threading.Event()
        
        # Register cleanup on exit
        atexit.register(self.shutdown_all)
        
        # Start monitoring thread
        self._start_monitor()
    
    def _start_monitor(self):
        """Start the monitoring thread"""
        self._monitor_thread = threading.Thread(
            target=self._monitor_threads,
            name="ThreadManager-Monitor",
            daemon=True
        )
        self._monitor_thread.start()
    
    def _monitor_threads(self):
        """Monitor thread health and cleanup dead threads"""
        while not self._shutdown_event.is_set():
            try:
                current_time = datetime.now()
                dead_threads = []
                
                for name, managed_thread in self.threads.items():
                    # Check if thread is dead
                    if not managed_thread.is_alive():
                        dead_threads.append(name)
                        continue
                    
                    # Check for stale threads (no heartbeat for 5 minutes)
                    if (managed_thread.last_heartbeat and 
                        current_time - managed_thread.last_heartbeat > timedelta(minutes=5)):
                        logger.warning(f"Thread {name} appears stale, last heartbeat: {managed_thread.last_heartbeat}")
                
                # Clean up dead threads
                for name in dead_threads:
                    self._cleanup_dead_thread(name)
                
                # Log thread status
                if self.threads:
                    alive_count = sum(1 for t in self.threads.values() if t.is_alive())
                    logger.debug(f"Thread status: {alive_count}/{len(self.threads)} alive")
                
                self._shutdown_event.wait(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in thread monitor: {e}")
                self._shutdown_event.wait(30)
    
    def _cleanup_dead_thread(self, name: str):
        """Clean up a dead thread"""
        try:
            managed_thread = self.threads.pop(name, None)
            if managed_thread:
                logger.info(f"Cleaned up dead thread: {name}")
        except Exception as e:
            logger.error(f"Error cleaning up dead thread {name}: {e}")
    
    def create_thread(self, target: Callable, name: str, daemon: bool = True,
                     cleanup_func: Optional[Callable] = None, **kwargs) -> ManagedThread:
        """Create a new managed thread"""
        if name in self.threads:
            logger.warning(f"Thread {name} already exists, stopping existing thread")
            self.stop_thread(name)
        
        managed_thread = ManagedThread(
            target=target,
            name=name,
            daemon=daemon,
            cleanup_func=cleanup_func,
            **kwargs
        )
        
        self.threads[name] = managed_thread
        return managed_thread
    
    def start_thread(self, name: str):
        """Start a managed thread"""
        if name in self.threads:
            self.threads[name].start()
        else:
            logger.error(f"Thread {name} not found")
    
    def stop_thread(self, name: str, timeout: float = 5.0):
        """Stop a managed thread"""
        if name in self.threads:
            self.threads[name].stop(timeout)
            # Remove from tracking after stop
            self._cleanup_dead_thread(name)
        else:
            logger.warning(f"Thread {name} not found for stopping")
    
    def register_cleanup(self, cleanup_func: Callable):
        """Register a cleanup function"""
        self.cleanup_funcs.append(cleanup_func)
    
    def get_thread_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all managed threads"""
        status = {}
        for name, managed_thread in self.threads.items():
            status[name] = {
                'is_alive': managed_thread.is_alive(),
                'start_time': managed_thread.start_time,
                'runtime': managed_thread.get_runtime(),
                'last_heartbeat': managed_thread.last_heartbeat,
                'thread_id': managed_thread.thread.ident if managed_thread.thread else None
            }
        return status
    
    def shutdown_all(self, timeout: float = 10.0):
        """Shutdown all managed threads"""
        logger.info("Shutting down all managed threads...")
        
        # Stop monitoring first
        self._shutdown_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        
        # Stop all managed threads
        for name, managed_thread in list(self.threads.items()):
            managed_thread.stop(timeout=timeout / len(self.threads) if self.threads else 1.0)
        
        # Run cleanup functions
        for cleanup_func in self.cleanup_funcs:
            try:
                cleanup_func()
            except Exception as e:
                logger.error(f"Error in cleanup function: {e}")
        
        self.threads.clear()
        logger.info("All threads shutdown completed")

# Global thread manager instance
thread_manager = ThreadManager()

@contextmanager
def managed_thread_context(target: Callable, name: str, cleanup_func: Optional[Callable] = None, **kwargs):
    """Context manager for temporary managed threads"""
    managed_thread = thread_manager.create_thread(
        target=target,
        name=name,
        cleanup_func=cleanup_func,
        **kwargs
    )
    
    try:
        managed_thread.start()
        yield managed_thread
    finally:
        managed_thread.stop()

def heartbeat_wrapper(original_func: Callable) -> Callable:
    """Decorator to add heartbeat functionality to thread functions"""
    def wrapper(*args, **kwargs):
        # Extract shutdown_event if present
        shutdown_event = kwargs.get('shutdown_event')
        
        # Get current thread name for heartbeat updates
        current_thread_name = threading.current_thread().name
        
        def heartbeat_func():
            """Internal function with heartbeat"""
            try:
                while not (shutdown_event and shutdown_event.is_set()):
                    # Update heartbeat for current thread
                    if current_thread_name in thread_manager.threads:
                        thread_manager.threads[current_thread_name].update_heartbeat()
                    
                    # Run original function logic
                    result = original_func(*args, **kwargs)
                    
                    # If original function returns, break the loop
                    if result is not None:
                        return result
                    
                    # Small sleep to prevent busy waiting
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error in heartbeat wrapper for {current_thread_name}: {e}")
                raise
        
        return heartbeat_func()
    
    return wrapper

# Resource cleanup utilities
class ResourceCleaner:
    """Utility class for resource cleanup"""
    
    @staticmethod
    def cleanup_websocket_connections(websocket_server):
        """Clean up WebSocket connections"""
        try:
            if hasattr(websocket_server, 'disconnect_all'):
                websocket_server.disconnect_all()
            elif hasattr(websocket_server, 'close'):
                websocket_server.close()
            logger.info("WebSocket connections cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up WebSocket connections: {e}")
    
    @staticmethod
    def cleanup_database_connections(db_manager):
        """Clean up database connections"""
        try:
            if hasattr(db_manager, 'close'):
                db_manager.close()
            elif hasattr(db_manager, 'disconnect'):
                db_manager.disconnect()
            logger.info("Database connections cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up database connections: {e}")
    
    @staticmethod
    def cleanup_api_clients(api_client):
        """Clean up API clients"""
        try:
            if hasattr(api_client, 'close'):
                api_client.close()
            elif hasattr(api_client, 'disconnect'):
                api_client.disconnect()
            logger.info("API clients cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up API clients: {e}")

# Memory monitoring utilities
def get_memory_usage() -> Dict[str, float]:
    """Get current memory usage statistics"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024
        }
    except ImportError:
        logger.warning("psutil not available for memory monitoring")
        return {}
    except Exception as e:
        logger.error(f"Error getting memory usage: {e}")
        return {}

def log_memory_usage(interval: int = 60):
    """Log memory usage periodically"""
    def memory_logger():
        while True:
            try:
                memory_stats = get_memory_usage()
                if memory_stats:
                    logger.info(f"Memory usage: {memory_stats['rss_mb']:.1f}MB RSS, "
                              f"{memory_stats['percent']:.1f}% of system memory")
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in memory logger: {e}")
                time.sleep(interval)
    
    # Start memory logging thread
    memory_thread = thread_manager.create_thread(
        target=memory_logger,
        name="MemoryLogger",
        daemon=True
    )
    memory_thread.start()

# Convenient decorators for common threading patterns
def run_in_background_thread(name: str, cleanup_func: Optional[Callable] = None):
    """Decorator to run a function in a managed background thread"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            managed_thread = thread_manager.create_thread(
                target=func,
                name=name,
                cleanup_func=cleanup_func,
                *args,
                **kwargs
            )
            managed_thread.start()
            return managed_thread
        return wrapper
    return decorator