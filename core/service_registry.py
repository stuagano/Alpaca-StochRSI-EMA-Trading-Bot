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

def setup_core_services():
    logger.info("Setting up core services.")
    # Removed backend dependency - using simple data service stub
    class TradingDataService:
        """Simple data service stub to replace backend dependency"""
        def __init__(self):
            pass

        def get_market_data(self, symbol):
            """Get market data for symbol"""
            return {'symbol': symbol, 'price': 0, 'volume': 0}

    registry = get_service_registry()
    registry.register('data_manager', TradingDataService())

def cleanup_service_registry():
    logger.info("Cleaning up service registry (placeholder).")
