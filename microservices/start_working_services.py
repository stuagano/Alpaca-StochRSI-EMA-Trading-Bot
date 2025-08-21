#!/usr/bin/env python3
"""
Working microservices startup script
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

def start_service(name, port, service_dir, module):
    """Start a single service"""
    print(f"🚀 Starting {name} on port {port}...")
    
    # Change to service directory and start uvicorn
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(service_dir).resolve())
    
    try:
        proc = subprocess.Popen([
            "venv/bin/python", "-m", "uvicorn", module,
            "--host", "0.0.0.0", "--port", str(port)
        ], 
        cwd=service_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
        )
        
        print(f"  ✅ {name} started (PID: {proc.pid})")
        return proc
        
    except Exception as e:
        print(f"  ❌ Failed to start {name}: {e}")
        return None

def main():
    """Start all services"""
    print("🚀 STARTING MICROSERVICES (NO DOCKER)")
    print("="*50)
    
    services = [
        ("Position Management", 6001, "services/position-management", "app.main:app"),
        ("Trading Execution", 6002, "services/trading-execution", "app.main:app"), 
        ("Signal Processing", 6003, "services/signal-processing", "app.main:app"),
        ("Risk Management", 6004, "services/risk-management", "app.main:app"),
        ("API Gateway", 6000, "services/api-gateway", "app.main:app")
    ]
    
    processes = []
    
    # Start each service
    for name, port, service_dir, module in services:
        proc = start_service(name, port, service_dir, module)
        if proc:
            processes.append((name, proc))
        time.sleep(2)  # Give each service time to start
    
    print(f"\n✅ Started {len(processes)}/{len(services)} services")
    
    print("\n🌐 SERVICE ENDPOINTS:")
    print("  API Gateway:        http://localhost:6000")
    print("  Position Management: http://localhost:6001") 
    print("  Trading Execution:   http://localhost:6002")
    print("  Signal Processing:   http://localhost:6003")
    print("  Risk Management:     http://localhost:6004")
    
    print("\n📖 API DOCUMENTATION:")
    for _, port, _, _ in services:
        print(f"  http://localhost:{port}/docs")
    
    print("\n🧪 QUICK TESTS:")
    print("  curl http://localhost:6000/health")
    print("  curl http://localhost:6000/api/dashboard/overview")
    print("  curl http://localhost:6001/positions")
    
    print("\n📱 CONNECT TO DASHBOARD:")
    print("  Your existing unified_dashboard.html should work")
    print("  Update API URLs to point to localhost:6000")
    
    print(f"\n🎯 All services running! Press Ctrl+C to stop.")
    
    # Signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\n🛑 Stopping all services...")
        for name, proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"  ✅ Stopped {name}")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"  🔄 Force killed {name}")
            except Exception as e:
                print(f"  ⚠️  Error stopping {name}: {e}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    # Change to microservices directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    main()