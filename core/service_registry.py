import logging

logger = logging.getLogger(__name__)

class ServiceRegistry:
    def __init__(self):
        self._services = {}

    def register(self, name, service_instance):
        self._services[name] = service_instance
        logger.info(f"Service '{name}' registered.")

    def get(self, name):
        service = self._services.get(name)
        if not service:
            raise ValueError(f"Service '{name}' not found in registry.")
        return service

    def start_health_monitoring(self, check_interval):
        logger.info(f"Health monitoring started with interval {check_interval}s.")

    def get_health_report(self):
        return {"ready_services": len(self._services), "total_services": len(self._services)}

_registry = None

def get_service_registry():
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry

from core.stubs import TradingDataServiceStub
from core.alpaca_data_service import AlpacaDataService

def setup_core_services(api_key: str = None, secret_key: str = None):
    """Initialize and register core services."""
    logger.info("Setting up core services.")
    registry = get_service_registry()
    
    if api_key and secret_key:
        logger.info("Registering production AlpacaDataService")
        # We'll use paper URL as default for safety
        base_url = "https://paper-api.alpaca.markets"
        registry.register('data_manager', AlpacaDataService(api_key, secret_key, base_url))
    else:
        logger.warning("No credentials provided, registering TradingDataServiceStub")
        registry.register('data_manager', TradingDataServiceStub())

def cleanup_service_registry():
    logger.info("Cleaning up service registry (placeholder).")
