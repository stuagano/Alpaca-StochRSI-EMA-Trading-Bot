#!/usr/bin/env python3
"""
Quick start script for microservices without complex dependencies
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

def install_basic_packages():
    """Install basic packages one by one"""
    print("📦 Installing basic packages...")
    
    packages = [
        "fastapi",
        "uvicorn[standard]", 
        "pydantic",
        "httpx"
    ]
    
    venv_pip = "venv/bin/pip" if os.name != 'nt' else "venv\\Scripts\\pip"
    
    for package in packages:
        print(f"  Installing {package}...")
        try:
            result = subprocess.run([
                venv_pip, "install", package
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"    ✅ {package} installed")
            else:
                print(f"    ⚠️  {package} failed: {result.stderr[:100]}...")
        except subprocess.TimeoutExpired:
            print(f"    ⏰ {package} timed out")
        except Exception as e:
            print(f"    ❌ {package} error: {e}")

def create_minimal_services():
    """Create minimal working services"""
    print("\n🛠️  Creating minimal services...")
    
    # Minimal Position Management Service
    pos_service = '''
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Position Management Service")

@app.get("/health")
async def health():
    return {
        "service": "position-management",
        "status": "healthy", 
        "timestamp": datetime.now().isoformat()
    }

@app.get("/positions")
async def get_positions():
    return [
        {"id": "1", "symbol": "AAPL", "quantity": 100, "market_value": 15000},
        {"id": "2", "symbol": "TSLA", "quantity": 50, "market_value": 12500}
    ]

@app.get("/portfolio/metrics")
async def get_portfolio_metrics():
    return {
        "total_positions": 2,
        "total_value": 27500,
        "total_unrealized_pnl": 1500,
        "calculated_at": datetime.now().isoformat()
    }

@app.get("/portfolio/pnl")
async def get_portfolio_pnl():
    return {
        "total_unrealized_pnl": 1500,
        "total_realized_pnl": 500,
        "total_pnl": 2000,
        "timestamp": datetime.now().isoformat()
    }
'''
    
    # Create position service directory and file
    pos_dir = Path("services/position-management/app")
    pos_dir.mkdir(parents=True, exist_ok=True)
    with open(pos_dir / "main.py", "w") as f:
        f.write(pos_service)
    print("  ✅ Position Management service created")
    
    # Minimal Trading Execution Service
    trading_service = '''
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Trading Execution Service")

@app.get("/health")
async def health():
    return {
        "service": "trading-execution",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/orders")
async def get_orders():
    return [
        {"id": "ord_1", "symbol": "AAPL", "side": "buy", "quantity": 100, "status": "filled"},
        {"id": "ord_2", "symbol": "TSLA", "side": "buy", "quantity": 50, "status": "pending"}
    ]

@app.post("/execute/signal")
async def execute_signal(signal: dict):
    return {
        "success": True,
        "message": f"Signal executed for {signal.get('symbol', 'UNKNOWN')}",
        "order_id": "ord_" + str(int(time.time()))
    }
'''
    
    trading_dir = Path("services/trading-execution/app")
    trading_dir.mkdir(parents=True, exist_ok=True)
    with open(trading_dir / "main.py", "w") as f:
        f.write(trading_service)
    print("  ✅ Trading Execution service created")
    
    # Minimal Signal Processing Service
    signal_service = '''
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Signal Processing Service")

@app.get("/health")
async def health():
    return {
        "service": "signal-processing",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/signals/summary")
async def get_signal_summary():
    return {
        "total_signals_today": 15,
        "buy_signals": 8,
        "sell_signals": 5,
        "hold_signals": 2,
        "avg_strength": 75.2,
        "generated_at": datetime.now().isoformat()
    }

@app.post("/signals/generate")
async def generate_signal(request: dict):
    symbol = request.get("symbol", "UNKNOWN")
    return {
        "id": f"sig_{int(time.time())}",
        "symbol": symbol,
        "signal_type": "buy",
        "strength": 78.5,
        "confidence": 82.0,
        "generated_at": datetime.now().isoformat()
    }
'''
    
    signal_dir = Path("services/signal-processing/app")
    signal_dir.mkdir(parents=True, exist_ok=True)
    with open(signal_dir / "main.py", "w") as f:
        f.write(signal_service)
    print("  ✅ Signal Processing service created")
    
    # Minimal Risk Management Service
    risk_service = '''
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Risk Management Service")

@app.get("/health")
async def health():
    return {
        "service": "risk-management",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/risk/summary")
async def get_risk_summary():
    return {
        "total_active_events": 2,
        "critical_events": 0,
        "portfolio_risk_level": "medium",
        "compliance_score": 85.0,
        "last_assessment": datetime.now().isoformat()
    }

@app.post("/risk/assess/portfolio")
async def assess_portfolio_risk(request: dict):
    return {
        "overall_risk_score": 45.0,
        "risk_level": "medium",
        "total_exposure_pct": 85.0,
        "largest_position_pct": 8.5,
        "calculated_at": datetime.now().isoformat()
    }
'''
    
    risk_dir = Path("services/risk-management/app")
    risk_dir.mkdir(parents=True, exist_ok=True)
    with open(risk_dir / "main.py", "w") as f:
        f.write(risk_service)
    print("  ✅ Risk Management service created")
    
    # Minimal API Gateway
    gateway_service = '''
import httpx
from fastapi import FastAPI, Request
from datetime import datetime

app = FastAPI(title="API Gateway")

SERVICES = {
    "position-management": "http://localhost:8001",
    "trading-execution": "http://localhost:8002", 
    "signal-processing": "http://localhost:8003",
    "risk-management": "http://localhost:8004"
}

@app.get("/health")
async def health():
    return {
        "service": "api-gateway",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/dashboard/overview")
async def dashboard_overview():
    data = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service, url in SERVICES.items():
            try:
                response = await client.get(f"{url}/health")
                data[service] = {"status": "healthy" if response.status_code == 200 else "unhealthy"}
            except:
                data[service] = {"status": "error"}
    
    return {
        "timestamp": datetime.now().isoformat(),
        "services": data,
        "status": "success"
    }

@app.api_route("/api/positions/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_positions(request: Request, path: str):
    async with httpx.AsyncClient() as client:
        response = await client.request(
            request.method,
            f"http://localhost:8001/positions/{path}",
            params=request.query_params
        )
        return response.json()

@app.api_route("/api/orders/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_orders(request: Request, path: str):
    async with httpx.AsyncClient() as client:
        response = await client.request(
            request.method,
            f"http://localhost:8002/orders/{path}",
            params=request.query_params
        )
        return response.json()
'''
    
    gateway_dir = Path("services/api-gateway/app")
    gateway_dir.mkdir(parents=True, exist_ok=True)
    with open(gateway_dir / "main.py", "w") as f:
        f.write(gateway_service)
    print("  ✅ API Gateway service created")

def create_simple_startup_script():
    """Create a simple startup script"""
    print("\n📝 Creating startup script...")
    
    python_cmd = "venv/bin/python" if os.name != 'nt' else "venv\\Scripts\\python"
    
    startup_script = f'''#!/usr/bin/env python3
"""
Simple microservices startup
"""

import subprocess
import time
import signal
import sys
from pathlib import Path

services = [
    ("Position Management", 8001, "services.position-management.app.main:app"),
    ("Trading Execution", 8002, "services.trading-execution.app.main:app"),
    ("Signal Processing", 8003, "services.signal-processing.app.main:app"),
    ("Risk Management", 8004, "services.risk-management.app.main:app"),
    ("API Gateway", 8000, "services.api-gateway.app.main:app")
]

processes = []

def signal_handler(signum, frame):
    print("\\n🛑 Stopping all services...")
    for proc in processes:
        proc.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

print("🚀 Starting microservices...")

for name, port, module in services:
    print(f"  Starting {{name}} on port {{port}}...")
    
    proc = subprocess.Popen([
        "{python_cmd}", "-m", "uvicorn", module,
        "--host", "0.0.0.0", "--port", str(port)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    processes.append(proc)
    time.sleep(2)

print("\\n✅ All services started!")
print("🌐 API Gateway: http://localhost:8000")
print("📖 API Docs: http://localhost:8000/docs")
print("❤️  Health: http://localhost:8000/health")
print("\\n🧪 Test: curl http://localhost:8000/health")
print("\\nPress Ctrl+C to stop all services...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    signal_handler(signal.SIGINT, None)
'''
    
    with open("start_microservices.py", "w") as f:
        f.write(startup_script)
    print("  ✅ Startup script created")

def main():
    """Main function"""
    print("🚀 QUICK MICROSERVICES SETUP")
    print("="*50)
    
    # Create virtual environment if it doesn't exist
    if not Path("venv").exists():
        print("🔧 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"])
        print("  ✅ Virtual environment created")
    
    # Install basic packages
    install_basic_packages()
    
    # Create minimal services
    create_minimal_services()
    
    # Create startup script
    create_simple_startup_script()
    
    print("\n" + "="*50)
    print("🎉 QUICK SETUP COMPLETE!")
    print("="*50)
    
    python_cmd = "venv/bin/python" if os.name != 'nt' else "venv\\Scripts\\python"
    
    print(f"\n🚀 START ALL SERVICES:")
    print(f"  {python_cmd} start_microservices.py")
    
    print(f"\n🌐 ACCESS POINTS:")
    print(f"  API Gateway: http://localhost:8000")
    print(f"  Health Check: http://localhost:8000/health")
    print(f"  Dashboard API: http://localhost:8000/api/dashboard/overview")
    
    print(f"\n🧪 QUICK TEST:")
    print(f"  {python_cmd} start_microservices.py")
    print(f"  curl http://localhost:8000/health")

if __name__ == "__main__":
    main()