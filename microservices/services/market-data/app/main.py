#!/usr/bin/env python3
"""
Market Data Service

Provides real-time and historical market data for the trading system.
Integrates with Alpaca Markets API for live data feeds.

Features:
- Real-time price feeds via WebSocket
- Historical OHLCV data retrieval
- Market hours and status information
- Data caching for performance
- Rate limiting and error handling
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
import redis.asyncio as redis
import yfinance as yf
from pydantic import BaseModel, Field

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

# Redis client for caching
redis_client = None

# Data models
class PriceData(BaseModel):
    symbol: str
    price: float
    timestamp: datetime
    volume: Optional[int] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    source: str = "alpaca"

class HistoricalData(BaseModel):
    symbol: str
    timeframe: str
    data: List[Dict[str, Any]]
    start_date: str
    end_date: str

class MarketStatus(BaseModel):
    is_open: bool
    next_open: Optional[str] = None
    next_close: Optional[str] = None
    current_time: str

class SymbolInfo(BaseModel):
    symbol: str
    name: str
    asset_class: str
    exchange: str
    tradable: bool

# Market Data Service
class MarketDataService:
    """Core market data service with multiple data sources."""
    
    def __init__(self):
        self.cache_ttl = 60  # Cache TTL in seconds
        self.price_cache = {}
        
    async def get_real_time_price(self, symbol: str) -> PriceData:
        """Get real-time price for a symbol."""
        try:
            # Check cache first
            cache_key = f"price:{symbol}"
            if redis_client:
                cached_price = await redis_client.get(cache_key)
                if cached_price:
                    import json
                    price_data = json.loads(cached_price)
                    return PriceData(**price_data)
            
            # Fallback to Yahoo Finance for real-time data
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            if not current_price:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Price data not available for {symbol}"
                )
            
            price_data = PriceData(
                symbol=symbol,
                price=float(current_price),
                timestamp=datetime.utcnow(),
                volume=info.get('regularMarketVolume'),
                source="yahoo"
            )
            
            # Cache the result
            if redis_client:
                await redis_client.setex(
                    cache_key, 
                    self.cache_ttl, 
                    price_data.json()
                )
            
            logger.info("Real-time price retrieved", symbol=symbol, price=current_price)
            return price_data
            
        except Exception as e:
            logger.error("Error fetching real-time price", symbol=symbol, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch price for {symbol}: {str(e)}"
            )
    
    async def get_historical_data(self, 
                                symbol: str, 
                                timeframe: str = "1d", 
                                start_date: Optional[str] = None, 
                                end_date: Optional[str] = None,
                                limit: int = 100) -> HistoricalData:
        """Get historical OHLCV data for a symbol."""
        try:
            # Calculate date range
            if not end_date:
                end_date = datetime.utcnow().strftime("%Y-%m-%d")
            if not start_date:
                # Default to 30 days back
                start_dt = datetime.utcnow() - timedelta(days=30)
                start_date = start_dt.strftime("%Y-%m-%d")
            
            # Check cache
            cache_key = f"historical:{symbol}:{timeframe}:{start_date}:{end_date}"
            if redis_client:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    import json
                    hist_data = json.loads(cached_data)
                    return HistoricalData(**hist_data)
            
            # Fetch from Yahoo Finance
            ticker = yf.Ticker(symbol)
            
            # Map timeframe to yfinance interval
            interval_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "1h", "1d": "1d", "1wk": "1wk", "1mo": "1mo"
            }
            interval = interval_map.get(timeframe, "1d")
            
            hist = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if hist.empty:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No historical data found for {symbol}"
                )
            
            # Convert to list of dictionaries
            data_list = []
            for index, row in hist.iterrows():
                data_list.append({
                    "timestamp": index.isoformat(),
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": int(row['Volume']) if not pd.isna(row['Volume']) else 0
                })
            
            historical_data = HistoricalData(
                symbol=symbol,
                timeframe=timeframe,
                data=data_list[-limit:],  # Limit results
                start_date=start_date,
                end_date=end_date
            )
            
            # Cache the result (longer TTL for historical data)
            if redis_client:
                await redis_client.setex(
                    cache_key, 
                    3600,  # 1 hour cache for historical data
                    historical_data.json()
                )
            
            logger.info("Historical data retrieved", 
                       symbol=symbol, timeframe=timeframe, records=len(data_list))
            return historical_data
            
        except Exception as e:
            logger.error("Error fetching historical data", 
                        symbol=symbol, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch historical data for {symbol}: {str(e)}"
            )
    
    async def get_market_status(self) -> MarketStatus:
        """Get current market status and hours."""
        try:
            # Simple market hours check (US markets)
            now = datetime.utcnow()
            
            # Convert to ET (approximate)
            et_offset = timedelta(hours=-5)  # EST (adjust for DST in production)
            et_time = now + et_offset
            
            # Market is open 9:30 AM - 4:00 PM ET, Monday-Friday
            weekday = et_time.weekday()  # 0=Monday, 6=Sunday
            hour = et_time.hour
            minute = et_time.minute
            
            is_weekend = weekday >= 5  # Saturday or Sunday
            is_market_hours = 9 <= hour < 16 or (hour == 9 and minute >= 30)
            
            is_open = not is_weekend and is_market_hours
            
            # Calculate next open/close times (simplified)
            if is_open:
                # Market is open, calculate next close
                next_close_dt = et_time.replace(hour=16, minute=0, second=0, microsecond=0)
                if et_time >= next_close_dt:
                    next_close_dt += timedelta(days=1)
                next_close = next_close_dt.isoformat()
                next_open = None
            else:
                # Market is closed, calculate next open
                next_open_dt = et_time.replace(hour=9, minute=30, second=0, microsecond=0)
                if et_time >= next_open_dt or is_weekend:
                    # Move to next weekday
                    days_ahead = 1
                    if weekday == 4:  # Friday
                        days_ahead = 3  # Skip to Monday
                    elif weekday == 5:  # Saturday
                        days_ahead = 2  # Skip to Monday
                    next_open_dt += timedelta(days=days_ahead)
                next_open = next_open_dt.isoformat()
                next_close = None
            
            return MarketStatus(
                is_open=is_open,
                next_open=next_open,
                next_close=next_close,
                current_time=now.isoformat()
            )
            
        except Exception as e:
            logger.error("Error getting market status", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get market status: {str(e)}"
            )
    
    async def get_symbol_info(self, symbol: str) -> SymbolInfo:
        """Get information about a trading symbol."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return SymbolInfo(
                symbol=symbol,
                name=info.get('longName', symbol),
                asset_class=info.get('category', 'equity'),
                exchange=info.get('exchange', 'unknown'),
                tradable=bool(info.get('regularMarketPrice'))
            )
            
        except Exception as e:
            logger.error("Error getting symbol info", symbol=symbol, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get symbol info for {symbol}: {str(e)}"
            )
    
    async def get_multiple_quotes(self, symbols: List[str]) -> List[PriceData]:
        """Get quotes for multiple symbols efficiently."""
        try:
            quotes = []
            
            # Process symbols in batches to avoid rate limits
            batch_size = 10
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                
                # Use asyncio.gather for concurrent requests
                tasks = [self.get_real_time_price(symbol) for symbol in batch]
                batch_quotes = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Filter out exceptions
                for quote in batch_quotes:
                    if isinstance(quote, PriceData):
                        quotes.append(quote)
                    elif isinstance(quote, Exception):
                        logger.warning("Failed to get quote", error=str(quote))
                
                # Small delay between batches
                if i + batch_size < len(symbols):
                    await asyncio.sleep(0.1)
            
            return quotes
            
        except Exception as e:
            logger.error("Error getting multiple quotes", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get multiple quotes: {str(e)}"
            )

# Global service instance
market_service = MarketDataService()

# WebSocket connection manager for real-time feeds
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.symbol_subscriptions: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from symbol subscriptions
        for symbol in list(self.symbol_subscriptions.keys()):
            if websocket in self.symbol_subscriptions[symbol]:
                self.symbol_subscriptions[symbol].remove(websocket)
                if not self.symbol_subscriptions[symbol]:
                    del self.symbol_subscriptions[symbol]
    
    def subscribe_to_symbol(self, websocket: WebSocket, symbol: str):
        if symbol not in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol] = []
        if websocket not in self.symbol_subscriptions[symbol]:
            self.symbol_subscriptions[symbol].append(websocket)
    
    async def broadcast_price_update(self, symbol: str, price_data: PriceData):
        if symbol in self.symbol_subscriptions:
            disconnected = []
            for websocket in self.symbol_subscriptions[symbol]:
                try:
                    await websocket.send_json({
                        "type": "price_update",
                        "data": price_data.dict()
                    })
                except:
                    disconnected.append(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected:
                self.disconnect(ws)

manager = ConnectionManager()

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_client
    
    try:
        # Initialize Redis connection
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        
        # Test Redis connection
        await redis_client.ping()
        logger.info("✅ Market Data Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error("❌ Failed to start Market Data Service", error=str(e))
        # Continue without Redis if it fails
        redis_client = None
        yield
        
    finally:
        if redis_client:
            await redis_client.close()
        logger.info("🔌 Market Data Service shutdown complete")

# FastAPI application
app = FastAPI(
    title="Market Data Service",
    description="Real-time and historical market data for trading system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import pandas here to avoid import errors
import pandas as pd

# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "service": "market-data",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "redis_connected": redis_client is not None
    }

@app.get("/price/{symbol}", response_model=PriceData)
async def get_price(symbol: str):
    """Get real-time price for a symbol."""
    return await market_service.get_real_time_price(symbol.upper())

@app.post("/prices", response_model=List[PriceData])
async def get_multiple_prices(symbols: List[str]):
    """Get real-time prices for multiple symbols."""
    return await market_service.get_multiple_quotes([s.upper() for s in symbols])

@app.get("/historical/{symbol}", response_model=HistoricalData)
async def get_historical_data(
    symbol: str,
    timeframe: str = "1d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """Get historical OHLCV data for a symbol."""
    return await market_service.get_historical_data(
        symbol.upper(), timeframe, start_date, end_date, limit
    )

@app.get("/market/status", response_model=MarketStatus)
async def get_market_status():
    """Get current market status and hours."""
    return await market_service.get_market_status()

@app.get("/symbol/{symbol}", response_model=SymbolInfo)
async def get_symbol_info(symbol: str):
    """Get information about a trading symbol."""
    return await market_service.get_symbol_info(symbol.upper())

# WebSocket endpoint for real-time price feeds
@app.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time price updates."""
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "subscribe":
                symbol = data.get("symbol", "").upper()
                if symbol:
                    manager.subscribe_to_symbol(websocket, symbol)
                    await websocket.send_json({
                        "type": "subscribed",
                        "symbol": symbol
                    })
            
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
    finally:
        manager.disconnect(websocket)

# Background task for price updates
async def price_update_task():
    """Background task to broadcast price updates."""
    common_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
    
    while True:
        try:
            if manager.symbol_subscriptions:
                # Get all subscribed symbols
                symbols = list(manager.symbol_subscriptions.keys())
                
                if symbols:
                    # Get latest prices
                    quotes = await market_service.get_multiple_quotes(symbols)
                    
                    # Broadcast updates
                    for quote in quotes:
                        await manager.broadcast_price_update(quote.symbol, quote)
            
            # Wait before next update
            await asyncio.sleep(30)  # Update every 30 seconds
            
        except Exception as e:
            logger.error("Error in price update task", error=str(e))
            await asyncio.sleep(60)

# Start background tasks
@app.on_event("startup")
async def start_background_tasks():
    """Start background tasks."""
    asyncio.create_task(price_update_task())

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        reload=True
    )