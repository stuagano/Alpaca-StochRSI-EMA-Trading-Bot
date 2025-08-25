#!/usr/bin/env python3
"""
Ultra-Simple Position Management Service
Just serves basic endpoints for the dashboard
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn

app = FastAPI(title="Position Management Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
MOCK_POSITIONS = [
    {
        "symbol": "AAPL",
        "qty": 100,
        "avg_entry_price": 175.50,
        "current_price": 178.25,
        "market_value": 17825.00,
        "unrealized_pl": 275.00,
        "unrealized_plpc": 0.0157,
        "side": "long"
    },
    {
        "symbol": "MSFT", 
        "qty": 50,
        "avg_entry_price": 420.00,
        "current_price": 416.75,
        "market_value": 20837.50,
        "unrealized_pl": -162.50,
        "unrealized_plpc": -0.0077,
        "side": "long"
    },
    {
        "symbol": "GOOGL",
        "qty": 25,
        "avg_entry_price": 140.00,
        "current_price": 142.80,
        "market_value": 3570.00,
        "unrealized_pl": 70.00,
        "unrealized_plpc": 0.02,
        "side": "long"
    }
]

@app.get("/health")
async def health_check():
    return {
        "service": "position-management",
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/positions")
async def get_positions():
    return {
        "positions": MOCK_POSITIONS,
        "count": len(MOCK_POSITIONS),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/positions/{symbol}")
async def get_position(symbol: str):
    position = next((p for p in MOCK_POSITIONS if p["symbol"] == symbol.upper()), None)
    if not position:
        return {"error": f"Position not found for {symbol}"}
    return position

@app.get("/portfolio/summary")
async def get_portfolio_summary():
    total_market_value = sum(p["market_value"] for p in MOCK_POSITIONS)
    total_pl = sum(p["unrealized_pl"] for p in MOCK_POSITIONS)
    
    return {
        "total_value": total_market_value + 75000,  # Add cash
        "cash_balance": 75000.00,
        "positions_value": total_market_value,
        "positions_count": len(MOCK_POSITIONS),
        "today_pnl": total_pl * 0.3,  # Mock daily P&L
        "total_pnl": total_pl,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run("simple_service:app", host="127.0.0.1", port=9001, reload=True)