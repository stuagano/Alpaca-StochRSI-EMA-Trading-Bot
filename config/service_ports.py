#!/usr/bin/env python3
"""
Centralized Service Port Configuration
=======================================

All microservices should use ports in the 9000 range for consistency.
This configuration file ensures all services use the same port mapping.
"""

import os
from typing import Dict

# Port Configuration (all in 9000 range)
SERVICE_PORTS = {
    "api-gateway": 9000,
    "position-management": 9001,
    "trading-execution": 9002,
    "signal-processing": 9003,
    "risk-management": 9004,
    "market-data": 9005,
    "historical-data": 9006,
    "analytics": 9007,
    "notification": 9008,
    "configuration": 9009,
    "health-monitor": 9010,
    "frontend": 9100,  # Frontend service
    "flask-dashboard": 8765,  # Keep Flask dashboard on original port
}

# Service URLs for localhost development
def get_service_urls(host: str = "localhost") -> Dict[str, str]:
    """Get service URLs for all microservices."""
    return {
        service: f"http://{host}:{port}"
        for service, port in SERVICE_PORTS.items()
    }

# Environment variable names for service URLs
SERVICE_URL_ENV_VARS = {
    "api-gateway": "API_GATEWAY_URL",
    "position-management": "POSITION_SERVICE_URL",
    "trading-execution": "TRADING_SERVICE_URL",
    "signal-processing": "SIGNAL_SERVICE_URL",
    "risk-management": "RISK_SERVICE_URL",
    "market-data": "MARKET_DATA_SERVICE_URL",
    "historical-data": "HISTORICAL_DATA_SERVICE_URL",
    "analytics": "ANALYTICS_SERVICE_URL",
    "notification": "NOTIFICATION_SERVICE_URL",
    "configuration": "CONFIG_SERVICE_URL",
    "health-monitor": "HEALTH_MONITOR_URL",
    "frontend": "FRONTEND_URL",
}

def export_service_urls():
    """Export service URLs as environment variables."""
    urls = get_service_urls()
    for service, url in urls.items():
        env_var = SERVICE_URL_ENV_VARS.get(service)
        if env_var:
            os.environ[env_var] = url

def get_service_port(service_name: str) -> int:
    """Get port for a specific service."""
    return SERVICE_PORTS.get(service_name, 9000)

def get_service_url(service_name: str, host: str = "localhost") -> str:
    """Get URL for a specific service."""
    port = get_service_port(service_name)
    return f"http://{host}:{port}"

# Docker compose service names (for container networking)
DOCKER_SERVICE_NAMES = {
    "api-gateway": "api-gateway",
    "position-management": "position-management",
    "trading-execution": "trading-execution",
    "signal-processing": "signal-processing",
    "risk-management": "risk-management",
    "market-data": "market-data",
    "historical-data": "historical-data",
    "analytics": "analytics",
    "notification": "notification",
    "configuration": "configuration",
    "health-monitor": "health-monitor",
    "frontend": "frontend",
}

def get_docker_service_urls() -> Dict[str, str]:
    """Get service URLs for Docker Compose networking."""
    return {
        service: f"http://{docker_name}:{SERVICE_PORTS[service]}"
        for service, docker_name in DOCKER_SERVICE_NAMES.items()
    }

if __name__ == "__main__":
    # Print configuration for verification
    print("Service Port Configuration")
    print("=" * 50)
    print("\nLocal Development URLs:")
    for service, url in get_service_urls().items():
        print(f"  {service:20s}: {url}")
    
    print("\nDocker Compose URLs:")
    for service, url in get_docker_service_urls().items():
        print(f"  {service:20s}: {url}")
    
    print("\nEnvironment Variables:")
    for service, env_var in SERVICE_URL_ENV_VARS.items():
        port = SERVICE_PORTS[service]
        print(f"  export {env_var}=http://localhost:{port}")