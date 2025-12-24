"""
Thread-safe Service Registry with lifecycle management.
"""

import logging
import threading
from typing import Any, Dict, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from core.resilience import ServiceNotFoundError, TradingBotException

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service lifecycle states."""
    REGISTERED = "registered"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ServiceEntry:
    """Wrapper for registered service with metadata."""
    name: str
    instance: Any
    state: ServiceState = ServiceState.REGISTERED
    registered_at: datetime = field(default_factory=datetime.now)
    last_health_check: Optional[datetime] = None
    error_count: int = 0
    health_check_fn: Optional[Callable[[], bool]] = None


class ServiceRegistry:
    """
    Thread-safe service registry with lifecycle management.

    Features:
    - Thread-safe registration and retrieval
    - Service state tracking
    - Health monitoring
    - Graceful degradation
    """

    def __init__(self):
        self._services: Dict[str, ServiceEntry] = {}
        self._lock = threading.RLock()
        self._initialized = False

    def register(
        self,
        name: str,
        service_instance: Any,
        health_check_fn: Optional[Callable[[], bool]] = None,
    ) -> None:
        """
        Register a service with the registry.

        Args:
            name: Unique service identifier
            service_instance: The service object
            health_check_fn: Optional function that returns True if healthy
        """
        with self._lock:
            if name in self._services:
                logger.warning(f"Service '{name}' already registered, replacing...")

            entry = ServiceEntry(
                name=name,
                instance=service_instance,
                state=ServiceState.READY,
                health_check_fn=health_check_fn,
            )
            self._services[name] = entry
            logger.info(f"Service '{name}' registered.")

    def get(self, name: str, required: bool = True) -> Optional[Any]:
        """
        Get a service by name.

        Args:
            name: Service identifier
            required: If True, raises exception when not found

        Returns:
            Service instance or None if not found and not required

        Raises:
            ServiceNotFoundError: If required and service not found
        """
        with self._lock:
            entry = self._services.get(name)

            if not entry:
                if required:
                    available = list(self._services.keys())
                    raise ServiceNotFoundError(
                        f"Service '{name}' not found. Available: {available}"
                    )
                return None

            # Check if service is in a usable state
            if entry.state in (ServiceState.FAILED, ServiceState.STOPPED):
                if required:
                    raise ServiceNotFoundError(
                        f"Service '{name}' is in {entry.state.value} state"
                    )
                return None

            return entry.instance

    def get_optional(self, name: str) -> Optional[Any]:
        """Get a service, returning None if not found."""
        return self.get(name, required=False)

    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        with self._lock:
            return name in self._services

    def unregister(self, name: str) -> bool:
        """
        Unregister a service.

        Returns:
            True if service was removed, False if not found
        """
        with self._lock:
            if name in self._services:
                del self._services[name]
                logger.info(f"Service '{name}' unregistered.")
                return True
            return False

    def set_state(self, name: str, state: ServiceState) -> None:
        """Update service state."""
        with self._lock:
            if name in self._services:
                self._services[name].state = state
                logger.info(f"Service '{name}' state changed to {state.value}")

    def record_error(self, name: str) -> None:
        """Record an error for a service."""
        with self._lock:
            if name in self._services:
                entry = self._services[name]
                entry.error_count += 1

                # Auto-degrade after threshold
                if entry.error_count >= 5 and entry.state == ServiceState.READY:
                    entry.state = ServiceState.DEGRADED
                    logger.warning(f"Service '{name}' degraded due to errors")

    def reset_errors(self, name: str) -> None:
        """Reset error count for a service."""
        with self._lock:
            if name in self._services:
                entry = self._services[name]
                entry.error_count = 0
                if entry.state == ServiceState.DEGRADED:
                    entry.state = ServiceState.READY

    def list_services(self) -> List[str]:
        """List all registered service names."""
        with self._lock:
            return list(self._services.keys())

    def start_health_monitoring(self, check_interval: int = 30) -> None:
        """Start background health monitoring."""
        logger.info(f"Health monitoring started with interval {check_interval}s.")
        # Could implement periodic health checks here

    def check_health(self, name: str) -> bool:
        """
        Check health of a specific service.

        Returns:
            True if healthy, False otherwise
        """
        with self._lock:
            entry = self._services.get(name)
            if not entry:
                return False

            entry.last_health_check = datetime.now()

            if entry.health_check_fn:
                try:
                    is_healthy = entry.health_check_fn()
                    if is_healthy:
                        self.reset_errors(name)
                    else:
                        self.record_error(name)
                    return is_healthy
                except Exception as e:
                    logger.warning(f"Health check failed for '{name}': {e}")
                    self.record_error(name)
                    return False

            # No health check defined, assume healthy if READY
            return entry.state == ServiceState.READY

    def get_health_report(self) -> Dict[str, Any]:
        """Get health status of all services."""
        with self._lock:
            services = {}
            ready_count = 0
            degraded_count = 0
            failed_count = 0

            for name, entry in self._services.items():
                services[name] = {
                    'state': entry.state.value,
                    'error_count': entry.error_count,
                    'registered_at': entry.registered_at.isoformat(),
                    'last_health_check': (
                        entry.last_health_check.isoformat()
                        if entry.last_health_check else None
                    ),
                }

                if entry.state == ServiceState.READY:
                    ready_count += 1
                elif entry.state == ServiceState.DEGRADED:
                    degraded_count += 1
                elif entry.state == ServiceState.FAILED:
                    failed_count += 1

            return {
                'total_services': len(self._services),
                'ready_services': ready_count,
                'degraded_services': degraded_count,
                'failed_services': failed_count,
                'services': services,
            }

    def shutdown(self) -> None:
        """Gracefully shutdown all services."""
        with self._lock:
            for name, entry in self._services.items():
                try:
                    # Try to call shutdown/close if available
                    if hasattr(entry.instance, 'shutdown'):
                        entry.instance.shutdown()
                    elif hasattr(entry.instance, 'close'):
                        entry.instance.close()

                    entry.state = ServiceState.STOPPED
                    logger.info(f"Service '{name}' stopped.")
                except Exception as e:
                    logger.error(f"Error stopping service '{name}': {e}")
                    entry.state = ServiceState.FAILED


# Global singleton with thread-safe initialization
_registry: Optional[ServiceRegistry] = None
_registry_lock = threading.Lock()


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry instance (thread-safe singleton)."""
    global _registry

    if _registry is None:
        with _registry_lock:
            # Double-checked locking
            if _registry is None:
                _registry = ServiceRegistry()

    return _registry


def reset_service_registry() -> None:
    """Reset the global registry (mainly for testing)."""
    global _registry
    with _registry_lock:
        if _registry:
            _registry.shutdown()
        _registry = None


# Legacy imports for backward compatibility
from core.stubs import TradingDataServiceStub
from core.alpaca_data_service import AlpacaDataService


def setup_core_services(api_key: str = None, secret_key: str = None) -> None:
    """Initialize and register core services."""
    logger.info("Setting up core services.")
    registry = get_service_registry()

    if api_key and secret_key:
        logger.info("Registering production AlpacaDataService")
        base_url = "https://paper-api.alpaca.markets"
        registry.register('data_manager', AlpacaDataService(api_key, secret_key, base_url))
    else:
        logger.warning("No credentials provided, registering TradingDataServiceStub")
        registry.register('data_manager', TradingDataServiceStub())


def cleanup_service_registry() -> None:
    """Clean up and shutdown the service registry."""
    logger.info("Cleaning up service registry.")
    registry = get_service_registry()
    registry.shutdown()
