
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
