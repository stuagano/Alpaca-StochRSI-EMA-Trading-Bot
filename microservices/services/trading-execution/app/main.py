
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
