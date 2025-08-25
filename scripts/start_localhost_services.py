#!/usr/bin/env python3
"""
Localhost Microservices Launcher

Starts all microservices on localhost without Docker.
Each service runs on its designated port using uvicorn.
"""

import subprocess
import sys
import time
import os
import signal
import asyncio
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor

# Service configuration - All ports moved to 9000s
SERVICES = {
    "api-gateway": {"port": 9000, "path": "microservices/services/api-gateway/app/main.py"},
    "position-management": {"port": 9001, "path": "microservices/services/position-management/app/main.py"},
    "trading-execution": {"port": 9002, "path": "microservices/services/trading-execution/app/main.py"},
    "signal-processing": {"port": 9003, "path": "microservices/services/signal-processing/app/main.py"},
    "risk-management": {"port": 9004, "path": "microservices/services/risk-management/app/main.py"},
    "market-data": {"port": 9005, "path": "microservices/services/market-data/app/main.py"},
    "historical-data": {"port": 9006, "path": "microservices/services/historical-data/app/main.py"},
    "analytics": {"port": 9007, "path": "microservices/services/analytics/app/main.py"},
    "notification": {"port": 9008, "path": "microservices/services/notification/app/main.py"},
    "configuration": {"port": 9009, "path": "microservices/services/configuration/app/main.py"},
    "health-monitor": {"port": 9010, "path": "microservices/services/health-monitor/app/main.py"},
    "frontend": {"port": 9100, "path": "microservices/services/frontend/app/main.py"}
}

# Global process list for cleanup
processes = []

def install_dependencies():
    """Install required Python packages for all services."""
    print("📦 Installing dependencies...")
    
    # Common dependencies for all microservices
    common_deps = [
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0",
        "pydantic==2.5.0",
        "httpx==0.25.2",
        "structlog==23.2.0",
        "python-multipart==0.0.6",
        "jinja2==3.1.2",
        "aiofiles==23.2.1",
        "requests==2.31.0",
        "pandas==2.1.4",
        "numpy==1.25.2",
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "python-dotenv==1.0.0"
    ]
    
    # Optional dependencies (install if possible)
    optional_deps = [
        "redis==5.0.1",
        "asyncpg==0.29.0", 
        "sqlalchemy[asyncio]==2.0.23",
        "alpaca-py==0.13.1"
    ]
    
    for dep in common_deps:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                         check=True, capture_output=True)
            print(f"✅ Installed {dep}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to install {dep}: {e}")
    
    for dep in optional_deps:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                         check=True, capture_output=True)
            print(f"✅ Installed {dep}")
        except subprocess.CalledProcessError:
            print(f"⚠️  Optional dependency {dep} not installed (may need external services)")

def check_port_available(port):
    """Check if a port is available."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result != 0
    except:
        return True

def setup_environment():
    """Setup environment variables for localhost operation."""
    # Set localhost URLs for all services
    env_vars = {
        "DATABASE_URL": "sqlite:///./trading.db",  # Use SQLite for localhost
        "REDIS_URL": "memory://",  # Use in-memory cache
        "ALPACA_API_KEY": os.getenv("ALPACA_API_KEY", ""),
        "ALPACA_SECRET_KEY": os.getenv("ALPACA_SECRET_KEY", ""),
        "ALPACA_BASE_URL": "https://paper-api.alpaca.markets",
        
        # Service URLs (localhost) - Updated to 9000s
        "POSITION_SERVICE_URL": "http://localhost:9001",
        "TRADING_SERVICE_URL": "http://localhost:9002",
        "SIGNAL_SERVICE_URL": "http://localhost:9003",
        "RISK_SERVICE_URL": "http://localhost:9004",
        "MARKET_DATA_SERVICE_URL": "http://localhost:9005",
        "HISTORICAL_DATA_SERVICE_URL": "http://localhost:9006",
        "ANALYTICS_SERVICE_URL": "http://localhost:9007",
        "NOTIFICATION_SERVICE_URL": "http://localhost:9008",
        "CONFIGURATION_SERVICE_URL": "http://localhost:9009",
        "HEALTH_MONITOR_SERVICE_URL": "http://localhost:9010",
        
        # Frontend configuration
        "API_GATEWAY_URL": "http://localhost:9000",
        "WEBSOCKET_URL": "ws://localhost:9000/ws",
        
        # Email configuration (optional)
        "SMTP_HOST": "localhost",
        "SMTP_PORT": "587",
        "SMTP_USER": "",
        "SMTP_PASSWORD": "",
        "SMTP_FROM": "trading-bot@localhost",
        
        # Security
        "JWT_SECRET": "localhost-development-secret-key-change-in-production"
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("✅ Environment configured for localhost operation")

def start_service(service_name, config):
    """Start a single service."""
    port = config["port"]
    path = config["path"]
    
    if not check_port_available(port):
        print(f"⚠️  Port {port} is already in use for {service_name}")
        return None
    
    try:
        # Get the absolute path to the service
        service_path = Path(path).resolve()
        service_dir = service_path.parent
        
        if not service_path.exists():
            print(f"❌ Service file not found: {service_path}")
            return None
        
        print(f"🚀 Starting {service_name} on port {port}...")
        
        # Start the service using uvicorn
        cmd = [
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--reload"
        ]
        
        process = subprocess.Popen(
            cmd,
            cwd=service_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy()
        )
        
        processes.append(process)
        return process
        
    except Exception as e:
        print(f"❌ Failed to start {service_name}: {e}")
        return None

def check_service_health(service_name, port, max_retries=30):
    """Check if a service is responding to health checks."""
    url = f"http://localhost:{port}/health"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(f"✅ {service_name} (port {port}) - Healthy")
                return True
        except requests.RequestException:
            pass
        
        if attempt < max_retries - 1:
            time.sleep(2)
    
    print(f"❌ {service_name} (port {port}) - Not responding")
    return False

def cleanup_processes():
    """Clean up all started processes."""
    print("\n🧹 Stopping all services...")
    
    for process in processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except:
            pass
    
    processes.clear()
    print("✅ All services stopped")

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    cleanup_processes()
    sys.exit(0)

def main():
    """Main function to start all microservices."""
    print("🚀 Starting Microservices Trading System (Localhost)")
    print("=" * 60)
    
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Install dependencies
        install_dependencies()
        
        # Setup environment
        setup_environment()
        
        # Check available ports
        print("\n🔍 Checking port availability...")
        unavailable_ports = []
        for service_name, config in SERVICES.items():
            if not check_port_available(config["port"]):
                unavailable_ports.append((service_name, config["port"]))
        
        if unavailable_ports:
            print("\n⚠️  The following ports are in use:")
            for service_name, port in unavailable_ports:
                print(f"   {service_name}: {port}")
            print("\nPlease stop the services using these ports or modify the configuration.")
            return
        
        print("✅ All ports are available")
        
        # Start core infrastructure services first
        core_services = ["configuration", "health-monitor"]
        print(f"\n🏗️  Starting core services: {', '.join(core_services)}")
        
        for service_name in core_services:
            if service_name in SERVICES:
                start_service(service_name, SERVICES[service_name])
                time.sleep(3)  # Wait between starts
        
        # Start data and analytics services
        data_services = ["market-data", "historical-data", "analytics", "notification"]
        print(f"\n📊 Starting data services: {', '.join(data_services)}")
        
        for service_name in data_services:
            if service_name in SERVICES:
                start_service(service_name, SERVICES[service_name])
                time.sleep(2)
        
        # Start trading services
        trading_services = ["position-management", "trading-execution", "signal-processing", "risk-management"]
        print(f"\n💹 Starting trading services: {', '.join(trading_services)}")
        
        for service_name in trading_services:
            if service_name in SERVICES:
                start_service(service_name, SERVICES[service_name])
                time.sleep(2)
        
        # Start API Gateway
        print(f"\n🌐 Starting API Gateway...")
        start_service("api-gateway", SERVICES["api-gateway"])
        time.sleep(3)
        
        # Start Frontend
        print(f"\n🎨 Starting Frontend Dashboard...")
        start_service("frontend", SERVICES["frontend"])
        
        # Wait for all services to start
        print("\n⏳ Waiting for services to initialize...")
        time.sleep(10)
        
        # Check service health
        print("\n🔍 Checking service health...")
        healthy_services = 0
        total_services = len(SERVICES)
        
        for service_name, config in SERVICES.items():
            if check_service_health(service_name, config["port"]):
                healthy_services += 1
        
        print(f"\n📈 Health Summary: {healthy_services}/{total_services} services healthy")
        
        if healthy_services == total_services:
            print("\n🎉 All services started successfully!")
            print("\n🌐 Access Points:")
            print("  • Frontend Dashboard: http://localhost:9100")
            print("  • API Gateway: http://localhost:9000")
            print("  • API Documentation: http://localhost:9000/docs")
            print("  • Health Monitor: http://localhost:9010/system/health")
            print("\n🔧 Service Endpoints:")
            for service_name, config in SERVICES.items():
                print(f"  • {service_name}: http://localhost:{config['port']}")
            
            print("\n✨ System is ready for trading operations!")
            print("Press Ctrl+C to stop all services")
            
        elif healthy_services > total_services // 2:
            print(f"\n⚠️  Most services started ({healthy_services}/{total_services})")
            print("Some services may need more time or have dependency issues.")
            print("Check individual service logs if needed.")
            
        else:
            print(f"\n❌ Many services failed to start ({healthy_services}/{total_services})")
            print("Check that all dependencies are installed and ports are available.")
            cleanup_processes()
            return
        
        # Keep the script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
    except Exception as e:
        print(f"❌ Error starting services: {e}")
    finally:
        cleanup_processes()

if __name__ == "__main__":
    main()