#!/usr/bin/env python3
"""
Core Services Launcher (Simplified)

Starts essential microservices without heavy dependencies.
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path
import requests

# Core services only (no pandas/numpy dependencies)
CORE_SERVICES = {
    "api-gateway": {"port": 8000, "path": "microservices/services/api-gateway/app/main.py"},
    "configuration": {"port": 8009, "path": "microservices/services/configuration/app/main.py"},
    "health-monitor": {"port": 8010, "path": "microservices/services/health-monitor/app/main.py"},
    "frontend": {"port": 3000, "path": "microservices/services/frontend/app/main.py"}
}

processes = []

def setup_environment():
    """Setup environment variables for localhost operation."""
    env_vars = {
        "DATABASE_URL": "sqlite:///./trading.db",
        "REDIS_URL": "memory://",
        "API_GATEWAY_URL": "http://localhost:8000",
        "JWT_SECRET": "localhost-development-secret"
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value

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

def start_service(service_name, config):
    """Start a single service."""
    port = config["port"]
    path = config["path"]
    
    if not check_port_available(port):
        print(f"⚠️  Port {port} is already in use for {service_name}")
        return None
    
    try:
        service_path = Path(path).resolve()
        service_dir = service_path.parent
        
        if not service_path.exists():
            print(f"❌ Service file not found: {service_path}")
            return None
        
        print(f"🚀 Starting {service_name} on port {port}...")
        
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

def check_service_health(service_name, port, max_retries=15):
    """Check if a service is responding."""
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
        except:
            try:
                process.kill()
            except:
                pass
    processes.clear()

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    cleanup_processes()
    sys.exit(0)

def main():
    """Start core services."""
    print("🚀 Starting Core Microservices (Localhost)")
    print("=" * 50)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        setup_environment()
        
        # Start services in order
        for service_name, config in CORE_SERVICES.items():
            start_service(service_name, config)
            time.sleep(3)
        
        print("\n⏳ Waiting for services to initialize...")
        time.sleep(8)
        
        # Check health
        print("\n🔍 Checking service health...")
        healthy_count = 0
        for service_name, config in CORE_SERVICES.items():
            if check_service_health(service_name, config["port"]):
                healthy_count += 1
        
        print(f"\n📈 Health Summary: {healthy_count}/{len(CORE_SERVICES)} services healthy")
        
        if healthy_count > 0:
            print("\n🌐 Access Points:")
            if healthy_count >= 2:
                print("  • Frontend Dashboard: http://localhost:3000")
                print("  • API Gateway: http://localhost:8000")
                print("  • Configuration Service: http://localhost:8009")
                print("  • Health Monitor: http://localhost:8010")
            
            print("\nPress Ctrl+C to stop all services")
            
            # Keep running
            while True:
                time.sleep(1)
        else:
            print("❌ No services started successfully")
            
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        cleanup_processes()

if __name__ == "__main__":
    main()