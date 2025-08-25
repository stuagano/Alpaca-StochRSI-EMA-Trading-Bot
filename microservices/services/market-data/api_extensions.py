#!/usr/bin/env python3
"""
API Extensions for Market Data Service
Adds missing endpoints for frontend compatibility
"""

from datetime import datetime, timedelta
import random
from typing import List, Dict, Any

def add_frontend_endpoints(app):
    """Add endpoints required by the frontend"""
    
    @app.get("/bars/{symbol}")
    async def get_bars(symbol: str, timeframe: str = "5Min", limit: int = 100):
        """Get historical bars for a symbol"""
        bars = []
        base_price = 180.0
        
        for i in range(limit):
            time_offset = timedelta(minutes=i * 5)
            timestamp = datetime.utcnow() - time_offset
            
            # Generate realistic OHLCV data
            open_price = base_price + random.uniform(-2, 2)
            close_price = open_price + random.uniform(-1, 1)
            high_price = max(open_price, close_price) + random.uniform(0, 0.5)
            low_price = min(open_price, close_price) - random.uniform(0, 0.5)
            volume = random.randint(100000, 1000000)
            
            bars.append({
                "t": timestamp.isoformat(),
                "o": round(open_price, 2),
                "h": round(high_price, 2),
                "l": round(low_price, 2),
                "c": round(close_price, 2),
                "v": volume,
                "n": volume // 100,
                "vw": round((open_price + close_price) / 2, 2)
            })
            
            base_price = close_price
        
        return bars
    
    @app.get("/quote/{symbol}")
    async def get_quote(symbol: str):
        """Get current quote for a symbol"""
        base_price = 180.0 + random.uniform(-5, 5)
        
        return {
            "symbol": symbol,
            "bid": round(base_price - 0.01, 2),
            "bid_size": random.randint(100, 1000),
            "ask": round(base_price + 0.01, 2),
            "ask_size": random.randint(100, 1000),
            "last": round(base_price, 2),
            "last_size": random.randint(1, 100),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @app.post("/quotes")
    async def get_multiple_quotes(symbols: Dict[str, List[str]]):
        """Get quotes for multiple symbols"""
        result = {}
        for symbol in symbols.get("symbols", []):
            base_price = 180.0 + random.uniform(-10, 10)
            result[symbol] = {
                "symbol": symbol,
                "bid": round(base_price - 0.01, 2),
                "ask": round(base_price + 0.01, 2),
                "last": round(base_price, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        return result