#!/usr/bin/env python3
"""
Centralized Port Configuration for Trading Bot System
===================================================

This module defines all port configurations to avoid conflicts and
provide a single source of truth for port management.

Port Allocation Strategy:
- Main Application: 9765 (moved from 8765)
- Epic 1 System: 9766 (moved from 8766/8767)
- Microservices: 6000-6005 range
- Infrastructure: Standard ports (3000, 6379, 9090, etc.)
- Development: 5678 (debug), 8888 (jupyter)
"""

import os
from typing import Dict, Any

class PortConfig:
    """Centralized port configuration management"""
    
    # Main Application Ports
    MAIN_FLASK_PORT = int(os.getenv('FLASK_PORT', 9765))
    EPIC1_PORT = int(os.getenv('EPIC1_PORT', 9766))
    
    # Microservices Ports
    API_GATEWAY_PORT = int(os.getenv('API_GATEWAY_PORT', 6000))
    POSITION_MANAGEMENT_PORT = int(os.getenv('POSITION_MANAGEMENT_PORT', 6001))
    TRADING_EXECUTION_PORT = int(os.getenv('TRADING_EXECUTION_PORT', 6002))
    SIGNAL_PROCESSING_PORT = int(os.getenv('SIGNAL_PROCESSING_PORT', 6003))
    RISK_MANAGEMENT_PORT = int(os.getenv('RISK_MANAGEMENT_PORT', 6004))
    MARKET_DATA_PORT = int(os.getenv('MARKET_DATA_PORT', 6005))
    
    # Infrastructure Ports (Standard)
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
    PROMETHEUS_PORT = int(os.getenv('PROMETHEUS_PORT', 9090))
    GRAFANA_PORT = int(os.getenv('GRAFANA_PORT', 3000))
    
    # Development Ports
    DEBUG_PORT = int(os.getenv('DEBUG_PORT', 5678))
    JUPYTER_PORT = int(os.getenv('JUPYTER_PORT', 8888))
    
    @classmethod
    def get_all_ports(cls) -> Dict[str, Any]:
        """Get all configured ports as a dictionary"""
        return {
            'main_application': {
                'flask': cls.MAIN_FLASK_PORT,
                'epic1': cls.EPIC1_PORT,
            },
            'microservices': {
                'api_gateway': cls.API_GATEWAY_PORT,
                'position_management': cls.POSITION_MANAGEMENT_PORT,
                'trading_execution': cls.TRADING_EXECUTION_PORT,
                'signal_processing': cls.SIGNAL_PROCESSING_PORT,
                'risk_management': cls.RISK_MANAGEMENT_PORT,
                'market_data': cls.MARKET_DATA_PORT,
            },
            'infrastructure': {
                'redis': cls.REDIS_PORT,
                'postgres': cls.POSTGRES_PORT,
                'prometheus': cls.PROMETHEUS_PORT,
                'grafana': cls.GRAFANA_PORT,
            },
            'development': {
                'debug': cls.DEBUG_PORT,
                'jupyter': cls.JUPYTER_PORT,
            }
        }
    
    @classmethod
    def get_cors_origins(cls) -> str:
        """Get CORS origins for the main application"""
        return f"http://localhost:{cls.MAIN_FLASK_PORT},http://127.0.0.1:{cls.MAIN_FLASK_PORT},http://localhost:{cls.GRAFANA_PORT},http://localhost:{cls.JUPYTER_PORT}"
    
    @classmethod
    def get_main_dashboard_url(cls) -> str:
        """Get the main dashboard URL"""
        return f"http://localhost:{cls.MAIN_FLASK_PORT}"
    
    @classmethod
    def get_epic1_dashboard_url(cls) -> str:
        """Get the Epic 1 dashboard URL"""
        return f"http://localhost:{cls.EPIC1_PORT}"
    
    @classmethod
    def check_port_conflicts(cls) -> Dict[str, Any]:
        """Check for potential port conflicts"""
        all_ports = []
        port_mapping = {}
        
        for category, ports in cls.get_all_ports().items():
            for service, port in ports.items():
                if port in all_ports:
                    return {
                        'conflict': True,
                        'port': port,
                        'services': [port_mapping[port], f"{category}.{service}"]
                    }
                all_ports.append(port)
                port_mapping[port] = f"{category}.{service}"
        
        return {'conflict': False, 'total_ports': len(all_ports)}
    
    @classmethod
    def validate_environment(cls) -> Dict[str, Any]:
        """Validate the current port environment"""
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'ports': cls.get_all_ports()
        }
        
        # Check for conflicts
        conflict_check = cls.check_port_conflicts()
        if conflict_check['conflict']:
            results['valid'] = False
            results['errors'].append(f"Port conflict detected on {conflict_check['port']}: {conflict_check['services']}")
        
        # Check for reserved ports
        reserved_ports = [22, 23, 25, 53, 80, 110, 143, 443, 993, 995]
        for category, ports in cls.get_all_ports().items():
            for service, port in ports.items():
                if port in reserved_ports:
                    results['warnings'].append(f"Port {port} ({category}.{service}) is a reserved system port")
                if port < 1024:
                    results['warnings'].append(f"Port {port} ({category}.{service}) requires root privileges")
        
        return results

# Export the main configuration instance
ports = PortConfig()

# Backwards compatibility
FLASK_PORT = ports.MAIN_FLASK_PORT
EPIC1_PORT = ports.EPIC1_PORT

if __name__ == '__main__':
    # CLI for port configuration management
    import json
    import sys
    
    def print_help():
        print("Port Configuration Management")
        print("Commands:")
        print("  list    - List all configured ports")
        print("  check   - Check for port conflicts")
        print("  validate - Validate current environment")
        print("  cors    - Get CORS origins")
        print("  urls    - Get dashboard URLs")
    
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        print(json.dumps(ports.get_all_ports(), indent=2))
    elif command == 'check':
        result = ports.check_port_conflicts()
        if result['conflict']:
            print(f"❌ Port conflict detected: {result}")
            sys.exit(1)
        else:
            print(f"✅ No port conflicts found. Total ports: {result['total_ports']}")
    elif command == 'validate':
        result = ports.validate_environment()
        print(json.dumps(result, indent=2))
        if not result['valid']:
            sys.exit(1)
    elif command == 'cors':
        print(ports.get_cors_origins())
    elif command == 'urls':
        print(f"Main Dashboard: {ports.get_main_dashboard_url()}")
        print(f"Epic 1 Dashboard: {ports.get_epic1_dashboard_url()}")
    else:
        print(f"Unknown command: {command}")
        print_help()
        sys.exit(1)