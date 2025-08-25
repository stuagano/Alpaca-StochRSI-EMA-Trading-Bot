#!/usr/bin/env python3
"""
Ultra-Simple Trading Execution Service
Just serves basic endpoints for the dashboard
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uvicorn
import random

app = FastAPI(title="Trading Execution Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock order data
MOCK_ORDERS = [
    {
        "id": "order-001",
        "symbol": "AAPL", 
        "side": "buy",
        "qty": 100,
        "order_type": "market",
        "status": "filled",
        "filled_price": 178.25,
        "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "filled_at": (datetime.utcnow() - timedelta(hours=1, minutes=58)).isoformat()
    },
    {
        "id": "order-002", 
        "symbol": "MSFT",
        "side": "buy",
        "qty": 50,
        "order_type": "limit",
        "limit_price": 420.00,
        "status": "filled", 
        "filled_price": 419.75,
        "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
        "filled_at": (datetime.utcnow() - timedelta(days=1, minutes=-10)).isoformat()
    },
    {
        "id": "order-003",
        "symbol": "GOOGL",
        "side": "buy", 
        "qty": 25,
        "order_type": "market",
        "status": "pending",
        "created_at": (datetime.utcnow() - timedelta(minutes=15)).isoformat()
    }
]

MOCK_ACCOUNT = {
    "id": "account-123",
    "account_number": "12345678",
    "status": "ACTIVE",
    "currency": "USD",
    "buying_power": 95267.50,
    "cash": 75000.00,
    "portfolio_value": 117232.50,
    "equity": 117232.50,
    "last_equity": 116800.00,
    "day_trade_count": 0,
    "pattern_day_trader": False,
    "long_market_value": 42232.50,
    "short_market_value": 0.0
}

@app.get("/health")
async def health_check():
    return {
        "service": "trading-execution",
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/orders")
async def get_orders():
    return {
        "orders": MOCK_ORDERS,
        "count": len(MOCK_ORDERS),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = next((o for o in MOCK_ORDERS if o["id"] == order_id), None)
    if not order:
        return {"error": f"Order not found: {order_id}"}
    return order

@app.get("/account")
async def get_account():
    # Add some random variation to make it feel alive
    account = MOCK_ACCOUNT.copy()
    account["portfolio_value"] += random.uniform(-100, 100)
    account["timestamp"] = datetime.utcnow().isoformat()
    return account

@app.post("/orders")
async def create_order(order_data: dict):
    # Mock order creation
    new_order = {
        "id": f"order-{random.randint(1000, 9999)}",
        "symbol": order_data.get("symbol", "AAPL"),
        "side": order_data.get("side", "buy"),
        "qty": order_data.get("qty", 1),
        "order_type": order_data.get("order_type", "market"),
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Add to mock orders
    MOCK_ORDERS.append(new_order)
    
    return {
        "message": "Order submitted successfully",
        "order": new_order,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/positions/summary")
async def get_positions_summary():
    return {
        "open_positions": 3,
        "total_value": 42232.50,
        "unrealized_pnl": 182.50,
        "realized_pnl": 450.75,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run("simple_service:app", host="127.0.0.1", port=9002, reload=True)