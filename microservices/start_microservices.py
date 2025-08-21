#!/usr/bin/env python3
"""
Simple microservices startup
"""

import subprocess
import time
import signal
import sys
from pathlib import Path

services = [
    ("Position Management", 6001, "services.position-management.app.main:app"),
    ("Trading Execution", 6002, "services.trading-execution.app.main:app"),
    ("Signal Processing", 6003, "services.signal-processing.app.main:app"),
    ("Risk Management", 6004, "services.risk-management.app.main:app"),
    ("API Gateway", 6000, "services.api-gateway.app.main:app")
]

processes = []

def signal_handler(signum, frame):
    print("\n🛑 Stopping all services...")
    for proc in processes:
        proc.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

print("🚀 Starting microservices...")

for name, port, module in services:
    print(f"  Starting {name} on port {port}...")
    
    proc = subprocess.Popen([
        "venv/bin/python", "-m", "uvicorn", module,
        "--host", "0.0.0.0", "--port", str(port)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    processes.append(proc)
    time.sleep(2)

print("\n✅ All services started!")
print("🌐 API Gateway: http://localhost:6000")
print("📖 API Docs: http://localhost:6000/docs")
print("❤️  Health: http://localhost:6000/health")
print("\n🧪 Test: curl http://localhost:6000/health")
print("\nPress Ctrl+C to stop all services...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    signal_handler(signal.SIGINT, None)
