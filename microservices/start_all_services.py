#!/usr/bin/env python3
"""
Start all microservices locally without Docker
"""

import os
import sys
import time
import subprocess
import signal
import asyncio
import httpx
from typing import List, Dict
from pathlib import Path

class ServiceManager:
    def __init__(self):
        self.services = []
        self.processes = {}
        
    def add_service(self, name: str, port: int, module_path: str):
        """Add a service to be managed"""
        self.services.append({
            "name": name,
            "port": port,
            "module_path": module_path,
            "url": f"http://localhost:{port}"
        })
    
    def start_service(self, service: Dict) -> subprocess.Popen:
        """Start a single service"""
        print(f"🚀 Starting {service['name']} on port {service['port']}...")
        
        # Set environment variables
        env = os.environ.copy()
        env.update({
            "PORT": str(service['port']),
            "PYTHONPATH": os.getcwd(),
            "POSITION_SERVICE_URL": "http://localhost:8001",
            "TRADING_SERVICE_URL": "http://localhost:8002",
            "SIGNAL_SERVICE_URL": "http://localhost:8003",
            "RISK_SERVICE_URL": "http://localhost:8004",
            "MARKET_DATA_SERVICE_URL": "http://localhost:8005"
        })
        
        # Start the service
        cmd = [
            sys.executable, "-m", "uvicorn",
            service['module_path'],
            "--host", "0.0.0.0",
            "--port", str(service['port']),
            "--reload"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[service['name']] = process
            print(f"✅ {service['name']} started (PID: {process.pid})")
            return process
            
        except Exception as e:
            print(f"❌ Failed to start {service['name']}: {e}")
            return None
    
    def start_all(self):
        """Start all services"""
        print("🎯 Starting all microservices...")
        print("="*60)
        
        for service in self.services:
            process = self.start_service(service)
            if process:
                # Give service time to start
                time.sleep(3)
        
        print("\n" + "="*60)
        print("✨ All services starting up...")
        
        # Wait a bit for services to fully initialize
        print("⏳ Waiting for services to initialize...")
        time.sleep(10)
        
        # Check service health
        asyncio.run(self.check_all_health())
    
    async def check_service_health(self, service: Dict) -> Dict:
        """Check health of a single service"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{service['url']}/health")
                
                if response.status_code == 200:
                    return {
                        "name": service['name'],
                        "status": "healthy",
                        "port": service['port'],
                        "response_time": response.elapsed.total_seconds()
                    }
                else:
                    return {
                        "name": service['name'],
                        "status": "unhealthy",
                        "port": service['port'],
                        "status_code": response.status_code
                    }
                    
        except Exception as e:
            return {
                "name": service['name'],
                "status": "error",
                "port": service['port'],
                "error": str(e)
            }
    
    async def check_all_health(self):
        """Check health of all services"""
        print("\n🔍 Checking service health...")
        print("-" * 60)
        
        health_tasks = [self.check_service_health(service) for service in self.services]
        health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
        
        healthy_count = 0
        for result in health_results:
            if isinstance(result, dict):
                name = result['name']
                status = result['status']
                port = result['port']
                
                if status == "healthy":
                    response_time = result.get('response_time', 0)
                    print(f"  ✅ {name:20} | Port {port} | {response_time:.3f}s")
                    healthy_count += 1
                elif status == "unhealthy":
                    print(f"  ❌ {name:20} | Port {port} | Status {result.get('status_code')}")
                else:
                    print(f"  ⚠️  {name:20} | Port {port} | {result.get('error', 'Unknown error')}")
            else:
                print(f"  ❌ Health check failed: {result}")
        
        print(f"\n📊 Health Summary: {healthy_count}/{len(self.services)} services healthy")
        
        if healthy_count == len(self.services):
            print("🎉 All services are running successfully!")
            self.show_endpoints()
        else:
            print("⚠️  Some services may need more time to start up")
    
    def show_endpoints(self):
        """Show available endpoints"""
        print("\n" + "="*60)
        print("🌐 AVAILABLE ENDPOINTS")
        print("="*60)
        
        print("\n🏠 Service Health Checks:")
        for service in self.services:
            print(f"  {service['url']}/health")
        
        print("\n🚪 API Gateway (Main Entry Point):")
        print("  http://localhost:8000/health")
        print("  http://localhost:8000/api/dashboard/overview")
        print("  http://localhost:8000/api/positions")
        print("  http://localhost:8000/api/orders")
        print("  http://localhost:8000/api/signals")
        print("  http://localhost:8000/api/risk")
        
        print("\n📖 API Documentation:")
        for service in self.services:
            print(f"  {service['url']}/docs")
        
        print("\n🎯 Quick Test:")
        print("  curl http://localhost:8000/health")
        print("  curl http://localhost:8000/api/dashboard/overview")
    
    def stop_all(self):
        """Stop all services"""
        print("\n🛑 Stopping all services...")
        
        for name, process in self.processes.items():
            try:
                print(f"  Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
                print(f"  ✅ {name} stopped")
            except subprocess.TimeoutExpired:
                print(f"  🔄 Force killing {name}...")
                process.kill()
                process.wait()
                print(f"  ✅ {name} killed")
            except Exception as e:
                print(f"  ❌ Error stopping {name}: {e}")
        
        self.processes.clear()
        print("✨ All services stopped")

def setup_signal_handlers(service_manager):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        print(f"\n📡 Received signal {signum}")
        service_manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        "fastapi", "uvicorn", "sqlalchemy", "aiosqlite", 
        "pydantic", "httpx", "numpy"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package}")
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("📦 Run: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies available")
    return True

def main():
    """Main function"""
    print("🚀 MICROSERVICES LOCAL STARTUP")
    print("="*60)
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    # Create service manager
    manager = ServiceManager()
    
    # Add all services
    manager.add_service(
        "position-management", 
        8001, 
        "services.position-management.app.main:app"
    )
    manager.add_service(
        "trading-execution", 
        8002, 
        "services.trading-execution.app.main:app"
    )
    manager.add_service(
        "signal-processing", 
        8003, 
        "services.signal-processing.app.main:app"
    )
    manager.add_service(
        "risk-management", 
        8004, 
        "services.risk-management.app.main:app"
    )
    manager.add_service(
        "api-gateway", 
        8000, 
        "services.api-gateway.app.main:app"
    )
    
    # Setup signal handlers
    setup_signal_handlers(manager)
    
    try:
        # Start all services
        manager.start_all()
        
        print("\n🎯 Services are running! Press Ctrl+C to stop all services.")
        print("📱 You can now use the unified dashboard or API endpoints.")
        
        # Keep the script running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        manager.stop_all()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        manager.stop_all()
        sys.exit(1)

if __name__ == "__main__":
    main()