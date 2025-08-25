#!/usr/bin/env python3
"""
Market Data Service
Real-time and historical market data provider
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uvicorn
import asyncio
import json
import random
from typing import Dict, List

app = FastAPI(title="Market Data Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock market data
MARKET_DATA = {
    "AAPL": {"price": 178.25, "change": 2.75, "change_pct": 1.57, "volume": 45234567},
    "MSFT": {"price": 416.75, "change": -3.25, "change_pct": -0.77, "volume": 28934521},
    "GOOGL": {"price": 142.80, "change": 2.80, "change_pct": 2.00, "volume": 19876543},
    "TSLA": {"price": 245.67, "change": 12.45, "change_pct": 5.34, "volume": 87654321},
    "NVDA": {"price": 875.32, "change": -15.68, "change_pct": -1.76, "volume": 34567890},
    "AMD": {"price": 145.23, "change": 4.12, "change_pct": 2.92, "volume": 23456789},
    "NFLX": {"price": 485.67, "change": -8.34, "change_pct": -1.69, "volume": 12345678},
    "META": {"price": 325.89, "change": 7.23, "change_pct": 2.27, "volume": 19876543}
}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

def simulate_price_movement():
    """Simulate realistic price movements"""
    for symbol in MARKET_DATA:
        # Random price movement within reasonable bounds
        current_price = MARKET_DATA[symbol]["price"]
        movement_pct = random.uniform(-0.02, 0.02)  # ±2% max movement
        new_price = current_price * (1 + movement_pct)
        
        change = new_price - current_price
        change_pct = (change / current_price) * 100
        
        MARKET_DATA[symbol].update({
            "price": round(new_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": MARKET_DATA[symbol]["volume"] + random.randint(-100000, 500000)
        })

@app.get("/health")
async def health_check():
    return {
        "service": "market-data",
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "symbols_tracked": len(MARKET_DATA)
    }

@app.get("/market/quote/{symbol}")
async def get_quote(symbol: str):
    """Get current quote for a symbol"""
    symbol = symbol.upper()
    if symbol not in MARKET_DATA:
        return {"error": f"Symbol {symbol} not found"}
    
    data = MARKET_DATA[symbol].copy()
    data.update({
        "symbol": symbol,
        "timestamp": datetime.utcnow().isoformat(),
        "market_status": "OPEN"
    })
    return data

@app.get("/market/quotes")
async def get_all_quotes():
    """Get quotes for all tracked symbols"""
    quotes = {}
    for symbol, data in MARKET_DATA.items():
        quotes[symbol] = {
            **data,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return {
        "quotes": quotes,
        "count": len(quotes),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/market/movers")
async def get_market_movers():
    """Get top gainers and losers"""
    symbols_with_change = [(symbol, data["change_pct"]) for symbol, data in MARKET_DATA.items()]
    
    # Sort by percentage change
    sorted_symbols = sorted(symbols_with_change, key=lambda x: x[1], reverse=True)
    
    gainers = []
    losers = []
    
    for symbol, change_pct in sorted_symbols:
        data = MARKET_DATA[symbol]
        symbol_data = {
            "symbol": symbol,
            "price": data["price"],
            "change": data["change"],
            "change_pct": change_pct,
            "volume": data["volume"]
        }
        
        if change_pct > 0:
            gainers.append(symbol_data)
        else:
            losers.append(symbol_data)
    
    return {
        "gainers": gainers[:5],  # Top 5 gainers
        "losers": losers[-5:],   # Top 5 losers
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/market/status")
async def get_market_status():
    """Get overall market status"""
    total_symbols = len(MARKET_DATA)
    gainers = sum(1 for data in MARKET_DATA.values() if data["change_pct"] > 0)
    losers = total_symbols - gainers
    
    return {
        "status": "OPEN",
        "session": "REGULAR",
        "total_symbols": total_symbols,
        "gainers": gainers,
        "losers": losers,
        "timestamp": datetime.utcnow().isoformat(),
        "next_close": (datetime.utcnow() + timedelta(hours=2)).isoformat()
    }

@app.websocket("/ws/market")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time market data"""
    await manager.connect(websocket)
    try:
        # Send initial market data
        await websocket.send_json({
            "type": "initial_data",
            "data": MARKET_DATA,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            # Wait for client message (keep-alive)
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

# Background task to simulate market data updates
async def market_data_updater():
    """Background task to update market data and broadcast to WebSocket clients"""
    while True:
        try:
            # Simulate price movements
            simulate_price_movement()
            
            # Broadcast updates to WebSocket clients
            await manager.broadcast({
                "type": "price_update",
                "data": MARKET_DATA,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Update every 5 seconds
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"Error in market data updater: {e}")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    asyncio.create_task(market_data_updater())

if __name__ == "__main__":
    uvicorn.run("simple_service:app", host="127.0.0.1", port=9005, reload=True)