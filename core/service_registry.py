"""
Unified Service Registry for Trading Bot

This module provides centralized service management with:
- Dependency injection for all major services
- Resource lifecycle management  
- Service health monitoring
- Proper error handling and logging
"""

import logging
import threading
import time
import weakref
from typing import Any, Dict, Optional, Type, TypeVar, Callable, List
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceState(Enum):
    """Service lifecycle states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class ServiceInfo:
    """Information about a registered service."""
    service_type: Type
    instance: Optional[Any] = None
    factory: Optional[Callable] = None
    singleton: bool = True
    dependencies: List[str] = field(default_factory=list)
    state: ServiceState = ServiceState.UNINITIALIZED
    created_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    health_status: bool = True
    error_count: int = 0
    max_errors: int = 5


class ServiceRegistry:
    """
    Central service container with dependency injection and lifecycle management.
    
    Features:
    - Singleton and factory service patterns
    - Dependency injection with circular dependency detection
    - Service health monitoring
    - Resource cleanup management
    - Thread-safe operations
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        self._instances: Dict[str, Any] = {}
        self._cleanup_callbacks: List[Callable] = []
        self._lock = threading.RLock()
        self._health_monitor_active = False
        self._health_monitor_thread: Optional[threading.Thread] = None
        self._shutdown_requested = False
        
        # Track weak references to prevent memory leaks
        self._weak_instances: Dict[str, weakref.ref] = {}
        
        logger.info("Service registry initialized")
    
    def register(
        self,
        service_name: str,
        service_type: Type[T],
        factory: Optional[Callable[[], T]] = None,
        singleton: bool = True,
        dependencies: Optional[List[str]] = None
    ) -> None:
        """Register a service with the registry."""
        with self._lock:
            if service_name in self._services:
                logger.warning(f"Service {service_name} already registered, overwriting")
            
            self._services[service_name] = ServiceInfo(
                service_type=service_type,
                factory=factory,
                singleton=singleton,
                dependencies=dependencies or []
            )
            
            logger.debug(f"Registered service: {service_name}")
    
    def get(self, service_name: str, **kwargs) -> Any:
        """Get a service instance with dependency injection."""
        with self._lock:
            return self._get_service(service_name, set(), **kwargs)
    
    def _get_service(self, service_name: str, resolving: set, **kwargs) -> Any:
        """Internal service resolution with circular dependency detection."""
        if service_name in resolving:
            raise ValueError(f"Circular dependency detected for service: {service_name}")
        
        if service_name not in self._services:
            raise ValueError(f"Service not registered: {service_name}")
        
        service_info = self._services[service_name]
        
        # Return existing singleton instance
        if service_info.singleton and service_name in self._instances:
            instance = self._instances[service_name]
            if instance is not None:
                return instance
        
        # Check if we have a weak reference that's still alive
        if service_name in self._weak_instances:
            weak_ref = self._weak_instances[service_name]
            instance = weak_ref()
            if instance is not None:
                return instance
            else:
                # Clean up dead weak reference
                del self._weak_instances[service_name]
        
        resolving.add(service_name)
        
        try:
            service_info.state = ServiceState.INITIALIZING
            
            # Resolve dependencies first
            dependency_instances = {}
            for dep_name in service_info.dependencies:
                dependency_instances[dep_name] = self._get_service(dep_name, resolving, **kwargs)
            
            # Create the service instance
            if service_info.factory:
                instance = service_info.factory(**dependency_instances, **kwargs)
            else:
                # Try to instantiate with dependencies
                try:
                    if dependency_instances:
                        instance = service_info.service_type(**dependency_instances, **kwargs)
                    else:
                        instance = service_info.service_type(**kwargs)
                except TypeError:
                    # Fallback to no-args constructor
                    instance = service_info.service_type()
            
            # Store instance
            if service_info.singleton:
                self._instances[service_name] = instance
            else:
                # Store weak reference for non-singletons
                self._weak_instances[service_name] = weakref.ref(instance)
            
            service_info.instance = instance
            service_info.state = ServiceState.READY
            service_info.created_at = datetime.now()
            service_info.error_count = 0
            
            logger.debug(f"Created service instance: {service_name}")
            
            # Register cleanup if the instance has a cleanup method
            if hasattr(instance, 'cleanup') and callable(getattr(instance, 'cleanup')):
                self._cleanup_callbacks.append(instance.cleanup)
            
            return instance
            
        except Exception as e:
            service_info.state = ServiceState.ERROR
            service_info.error_count += 1
            logger.error(f"Failed to create service {service_name}: {e}", exc_info=True)
            
            if service_info.error_count >= service_info.max_errors:
                logger.critical(f"Service {service_name} exceeded max errors ({service_info.max_errors})")
            
            raise
        finally:
            resolving.discard(service_name)
    
    def has(self, service_name: str) -> bool:
        """Check if a service is registered."""
        with self._lock:
            return service_name in self._services
    
    def is_ready(self, service_name: str) -> bool:
        """Check if a service is ready for use."""
        with self._lock:
            if service_name not in self._services:
                return False
            return self._services[service_name].state == ServiceState.READY
    
    def get_service_info(self, service_name: str) -> Optional[ServiceInfo]:
        """Get information about a registered service."""
        with self._lock:
            return self._services.get(service_name)
    
    def list_services(self) -> Dict[str, ServiceInfo]:
        """List all registered services."""
        with self._lock:
            return self._services.copy()
    
    def unregister(self, service_name: str) -> bool:
        """Unregister a service and clean up its instance."""
        with self._lock:
            if service_name not in self._services:
                return False
            
            # Clean up instance if it exists
            if service_name in self._instances:
                instance = self._instances[service_name]
                if hasattr(instance, 'cleanup') and callable(getattr(instance, 'cleanup')):
                    try:
                        instance.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up service {service_name}: {e}")
                
                del self._instances[service_name]
            
            # Clean up weak reference
            if service_name in self._weak_instances:
                del self._weak_instances[service_name]
            
            # Remove from registry
            del self._services[service_name]
            
            logger.info(f"Unregistered service: {service_name}")
            return True
    
    def start_health_monitoring(self, check_interval: float = 60.0) -> None:
        """Start background health monitoring for services."""
        if self._health_monitor_active:
            return
        
        self._health_monitor_active = True
        
        def health_monitor():
            while self._health_monitor_active and not self._shutdown_requested:
                try:
                    self._perform_health_checks()
                    time.sleep(check_interval)
                except Exception as e:
                    logger.error(f"Health monitor error: {e}")
                    time.sleep(check_interval)
        
        self._health_monitor_thread = threading.Thread(
            target=health_monitor,
            daemon=True,
            name="ServiceHealthMonitor"
        )
        self._health_monitor_thread.start()
        
        logger.info("Service health monitoring started")
    
    def stop_health_monitoring(self) -> None:
        """Stop health monitoring."""
        if not self._health_monitor_active:
            return
        
        self._health_monitor_active = False
        
        if self._health_monitor_thread and self._health_monitor_thread.is_alive():
            self._health_monitor_thread.join(timeout=5)
        
        logger.info("Service health monitoring stopped")
    
    def _perform_health_checks(self) -> None:
        """Perform health checks on all ready services."""
        with self._lock:
            for service_name, service_info in self._services.items():
                if service_info.state != ServiceState.READY:
                    continue
                
                if service_name not in self._instances:
                    continue
                
                instance = self._instances[service_name]
                
                try:
                    # Check if service has a health check method
                    if hasattr(instance, 'health_check') and callable(getattr(instance, 'health_check')):
                        healthy = instance.health_check()
                        service_info.health_status = bool(healthy)
                    else:
                        # Basic health check - just verify instance exists
                        service_info.health_status = instance is not None
                    
                    service_info.last_health_check = datetime.now()
                    
                    if not service_info.health_status:
                        logger.warning(f"Service {service_name} failed health check")
                    
                except Exception as e:
                    service_info.health_status = False
                    service_info.error_count += 1
                    logger.error(f"Health check failed for {service_name}: {e}")
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate a comprehensive health report."""
        with self._lock:
            report = {
                'registry_status': 'healthy' if not self._shutdown_requested else 'shutdown',
                'total_services': len(self._services),
                'ready_services': sum(1 for s in self._services.values() if s.state == ServiceState.READY),
                'error_services': sum(1 for s in self._services.values() if s.state == ServiceState.ERROR),
                'health_monitoring': self._health_monitor_active,
                'services': {}
            }
            
            for name, info in self._services.items():
                report['services'][name] = {
                    'state': info.state.value,
                    'health_status': info.health_status,
                    'error_count': info.error_count,
                    'created_at': info.created_at.isoformat() if info.created_at else None,
                    'last_health_check': info.last_health_check.isoformat() if info.last_health_check else None,
                    'dependencies': info.dependencies
                }
            
            return report
    
    @contextmanager
    def service_context(self, service_name: str, **kwargs):
        """Context manager for temporary service usage."""
        instance = None
        try:
            instance = self.get(service_name, **kwargs)
            yield instance
        finally:
            # For non-singleton services, we might want to clean up
            service_info = self._services.get(service_name)
            if service_info and not service_info.singleton and instance:
                if hasattr(instance, 'cleanup') and callable(getattr(instance, 'cleanup')):
                    try:
                        instance.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up temporary service {service_name}: {e}")
    
    def reload_service(self, service_name: str) -> Any:
        """Reload a service by recreating its instance."""
        with self._lock:
            if service_name not in self._services:
                raise ValueError(f"Service not registered: {service_name}")
            
            # Clean up existing instance
            if service_name in self._instances:
                instance = self._instances[service_name]
                if hasattr(instance, 'cleanup') and callable(getattr(instance, 'cleanup')):
                    try:
                        instance.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up service {service_name} during reload: {e}")
                
                del self._instances[service_name]
            
            # Reset service state
            service_info = self._services[service_name]
            service_info.state = ServiceState.UNINITIALIZED
            service_info.error_count = 0
            
            # Recreate the service
            return self.get(service_name)
    
    def shutdown(self) -> None:
        """Shutdown the service registry and clean up all resources."""
        logger.info("Starting service registry shutdown...")
        
        self._shutdown_requested = True
        
        # Stop health monitoring
        self.stop_health_monitoring()
        
        with self._lock:
            # Run cleanup callbacks in reverse order
            for cleanup_fn in reversed(self._cleanup_callbacks):
                try:
                    cleanup_fn()
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")
            
            # Clean up all service instances
            for service_name, instance in self._instances.items():
                if hasattr(instance, 'cleanup') and callable(getattr(instance, 'cleanup')):
                    try:
                        instance.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up service {service_name}: {e}")
            
            # Update service states
            for service_info in self._services.values():
                service_info.state = ServiceState.SHUTDOWN
            
            # Clear collections
            self._instances.clear()
            self._weak_instances.clear()
            self._cleanup_callbacks.clear()
        
        logger.info("Service registry shutdown complete")


# Global service registry instance
_service_registry: Optional[ServiceRegistry] = None
_registry_lock = threading.RLock()


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry instance."""
    global _service_registry
    
    with _registry_lock:
        if _service_registry is None:
            _service_registry = ServiceRegistry()
        return _service_registry


def setup_core_services():
    """Setup core services in the registry."""
    registry = get_service_registry()
    
    # Register core services
    from services.unified_data_manager import UnifiedDataManager
    from services.data_service import TradingDataService as DataService  
    from database.database_manager import DatabaseManager
    from risk_management.enhanced_risk_manager import EnhancedRiskManager
    from ml_models.price_predictor import PricePredictor
    
    try:
        # Data services
        registry.register(
            'data_manager',
            UnifiedDataManager,
            singleton=True
        )
        
        registry.register(
            'database_manager', 
            DatabaseManager,
            singleton=True
        )
        
        # Risk management
        registry.register(
            'risk_manager',
            EnhancedRiskManager,
            singleton=True
        )
        
        # ML services  
        registry.register(
            'price_predictor',
            PricePredictor,
            singleton=True
        )
        
        logger.info("Core services registered successfully")
        
    except ImportError as e:
        logger.warning(f"Some core services could not be registered: {e}")
    except Exception as e:
        logger.error(f"Error setting up core services: {e}")


def cleanup_service_registry():
    """Clean up the global service registry."""
    global _service_registry
    
    with _registry_lock:
        if _service_registry is not None:
            _service_registry.shutdown()
            _service_registry = None