
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
