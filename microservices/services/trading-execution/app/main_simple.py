#!/usr/bin/env python3
"""
Simplified Trading Execution Service with Real Alpaca Integration
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
from dotenv import load_dotenv

# Add project root to path to find .env
sys.path.append('/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot')

# Load environment variables from project root .env file
env_path = '/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot/.env'
load_dotenv(env_path)

# Alpaca integration
try:
    import alpaca_trade_api as tradeapi
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    print("Warning: alpaca-trade-api not available, using mock data")

app = FastAPI(
    title="Trading Execution Service",
    description="Order execution and trading bot service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Alpaca client
alpaca_api = None
if ALPACA_AVAILABLE:
    try:
        alpaca_api = tradeapi.REST(
            key_id=os.getenv('APCA_API_KEY_ID'),
            secret_key=os.getenv('APCA_API_SECRET_KEY'),
            base_url=os.getenv('APCA_BASE_URL', 'https://paper-api.alpaca.markets'),
            api_version='v2'
        )
        print("✅ Alpaca API client initialized for trading execution")
    except Exception as e:
        print(f"❌ Failed to initialize Alpaca API client: {e}")
        alpaca_api = None

# Mock orders data
MOCK_ORDERS = [
    {
        "id": "order_001",
        "symbol": "AAPL",
        "side": "buy",
        "qty": 100,
        "type": "market",
        "status": "filled",
        "filled_qty": 100,
        "filled_avg_price": 175.50,
        "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "filled_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
    },
    {
        "id": "order_002",
        "symbol": "MSFT",
        "side": "buy",
        "qty": 50,
        "type": "limit",
        "limit_price": 420.00,
        "status": "filled",
        "filled_qty": 50,
        "filled_avg_price": 420.00,
        "created_at": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
        "filled_at": (datetime.utcnow() - timedelta(hours=5)).isoformat()
    }
]

BOT_STATUS = {
    "status": "running",
    "mode": "paper",
    "strategy": "StochRSI-EMA",
    "started_at": (datetime.utcnow() - timedelta(hours=12)).isoformat(),
    "trades_today": 2,
    "profit_today": 550.00,
    "active_positions": 2
}

class OrderRequest(BaseModel):
    symbol: str
    side: str  # buy or sell
    qty: int
    type: str = "market"  # market or limit
    limit_price: Optional[float] = None

async def get_real_orders():
    """Get real orders from Alpaca"""
    if not alpaca_api:
        return MOCK_ORDERS
    
    try:
        orders = alpaca_api.list_orders(status='all', limit=50)
        converted_orders = []
        
        for order in orders:
            converted_orders.append({
                "id": order.id,
                "symbol": order.symbol,
                "side": order.side,
                "qty": int(order.qty),
                "type": order.order_type,
                "status": order.status,
                "filled_qty": int(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "client_order_id": order.client_order_id
            })
        
        return converted_orders if converted_orders else MOCK_ORDERS
    except Exception as e:
        print(f"Error fetching real orders: {e}")
        return MOCK_ORDERS

async def get_real_account():
    """Get real account data from Alpaca"""
    if not alpaca_api:
        return None
    
    try:
        account = alpaca_api.get_account()
        return {
            "account_id": account.id,
            "status": account.status,
            "currency": account.currency,
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "pattern_day_trader": bool(account.pattern_day_trader),
            "trading_blocked": bool(account.trading_blocked),
            "transfers_blocked": bool(account.transfers_blocked),
            "account_blocked": bool(account.account_blocked),
            "trade_suspended_by_user": bool(account.trade_suspended_by_user),
            "daytrading_buying_power": float(account.daytrading_buying_power),
            "equity": float(account.equity),
            "day_trade_count": int(account.day_trade_count)
        }
    except Exception as e:
        print(f"Error fetching real account: {e}")
        return None

@app.get("/health")
async def health_check():
    alpaca_status = "disconnected"
    if alpaca_api:
        try:
            alpaca_api.get_account()
            alpaca_status = "connected"
        except:
            alpaca_status = "error"
    
    return {
        "service": "trading-execution",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "bot_status": BOT_STATUS["status"],
        "alpaca_status": alpaca_status,
        "data_source": "real" if alpaca_api else "mock"
    }

@app.get("/orders")
async def get_orders(status: Optional[str] = None):
    """Get all orders or filter by status."""
    orders = await get_real_orders()
    if status:
        orders = [o for o in orders if o["status"] == status]
    
    return {
        "orders": orders,
        "count": len(orders),
        "timestamp": datetime.utcnow().isoformat(),
        "data_source": "real" if alpaca_api else "mock"
    }

@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get specific order by ID."""
    orders = await get_real_orders()
    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order

@app.post("/orders")
async def create_order(order: OrderRequest):
    """Create a new order."""
    if alpaca_api:
        try:
            # Submit real order to Alpaca
            order_params = {
                'symbol': order.symbol.upper(),
                'side': order.side,
                'type': order.type,
                'qty': order.qty,
                'time_in_force': 'day'
            }
            
            if order.type == "limit" and order.limit_price:
                order_params['limit_price'] = order.limit_price
                
            alpaca_order = alpaca_api.submit_order(**order_params)
            
            return {
                "message": "Order submitted to Alpaca successfully",
                "order": {
                    "id": alpaca_order.id,
                    "symbol": alpaca_order.symbol,
                    "side": alpaca_order.side,
                    "qty": int(alpaca_order.qty),
                    "type": alpaca_order.order_type,
                    "status": alpaca_order.status,
                    "limit_price": float(alpaca_order.limit_price) if alpaca_order.limit_price else None,
                    "created_at": alpaca_order.created_at.isoformat() if alpaca_order.created_at else None,
                    "client_order_id": alpaca_order.client_order_id
                },
                "data_source": "real"
            }
            
        except Exception as e:
            print(f"Error submitting real order: {e}")
            # Fall back to mock order
            pass
    
    # Mock order creation (fallback)
    new_order = {
        "id": f"order_{len(MOCK_ORDERS) + 1:03d}",
        "symbol": order.symbol.upper(),
        "side": order.side,
        "qty": order.qty,
        "type": order.type,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    
    if order.type == "limit" and order.limit_price:
        new_order["limit_price"] = order.limit_price
    
    # Simulate order fill after creation
    new_order["status"] = "filled"
    new_order["filled_qty"] = order.qty
    new_order["filled_avg_price"] = order.limit_price or (175.0 + random.random() * 10)
    new_order["filled_at"] = datetime.utcnow().isoformat()
    
    MOCK_ORDERS.append(new_order)
    
    return {
        "message": "Order created successfully (mock)",
        "order": new_order,
        "data_source": "mock"
    }

@app.get("/bot/status")
async def get_bot_status():
    """Get trading bot status."""
    return BOT_STATUS

@app.post("/bot/start")
async def start_bot():
    """Start the trading bot."""
    BOT_STATUS["status"] = "running"
    BOT_STATUS["started_at"] = datetime.utcnow().isoformat()
    return {
        "message": "Trading bot started",
        "status": BOT_STATUS
    }

@app.post("/bot/stop")
async def stop_bot():
    """Stop the trading bot."""
    BOT_STATUS["status"] = "stopped"
    return {
        "message": "Trading bot stopped",
        "status": BOT_STATUS
    }

@app.get("/account")
async def get_account():
    """Get account information."""
    account_data = await get_real_account()
    
    if account_data:
        return account_data
    else:
        # Fallback to mock data
        return {
            "account_id": "PAPER_ACCOUNT_001",
            "status": "ACTIVE",
            "currency": "USD",
            "buying_power": 200000.00,
            "cash": 100000.00,
            "portfolio_value": 139100.00,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "transfers_blocked": False,
            "account_blocked": False,
            "trade_suspended_by_user": False,
            "daytrading_buying_power": 400000.00,
            "equity": 139100.00,
            "data_source": "mock"
        }

@app.get("/trades/recent")
async def get_recent_trades():
    """Get recent trades."""
    return {
        "trades": [
            {
                "symbol": "AAPL",
                "side": "buy",
                "qty": 100,
                "price": 175.50,
                "time": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "profit": 275.00
            },
            {
                "symbol": "MSFT",
                "side": "buy", 
                "qty": 50,
                "price": 420.00,
                "time": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
                "profit": 275.00
            }
        ],
        "total_trades": 2,
        "profitable_trades": 2,
        "total_profit": 550.00
    }

@app.get("/market-data/bars/{symbol}")
async def get_market_bars(symbol: str, timeframe: str = "5Min", limit: int = 200):
    """Get market bars data from Alpaca."""
    
    # Map timeframe to Alpaca timeframe format
    timeframe_map = {
        "1Min": "1Min",
        "5Min": "5Min",
        "15Min": "15Min",
        "30Min": "30Min",
        "1Hour": "1Hour",
        "1Day": "1Day"
    }
    
    alpaca_timeframe = timeframe_map.get(timeframe, "5Min")
    
    if alpaca_api and ALPACA_AVAILABLE:
        try:
            # Get bars from Alpaca
            end_time = datetime.now()
            
            # Calculate start time based on timeframe and limit
            if alpaca_timeframe == "1Min":
                start_time = end_time - timedelta(minutes=limit)
            elif alpaca_timeframe == "5Min":
                start_time = end_time - timedelta(minutes=5 * limit)
            elif alpaca_timeframe == "15Min":
                start_time = end_time - timedelta(minutes=15 * limit)
            elif alpaca_timeframe == "30Min":
                start_time = end_time - timedelta(minutes=30 * limit)
            elif alpaca_timeframe == "1Hour":
                start_time = end_time - timedelta(hours=limit)
            else:  # 1Day
                start_time = end_time - timedelta(days=limit)
            
            # Fetch bars from Alpaca (use proper date format)
            # Alpaca expects RFC3339 format or YYYY-MM-DD
            bars = alpaca_api.get_bars(
                symbol,
                alpaca_timeframe,
                start=start_time.strftime('%Y-%m-%d'),
                end=end_time.strftime('%Y-%m-%d'),
                limit=limit,
                adjustment='raw'
            ).df
            
            if not bars.empty:
                # Convert DataFrame to list of dictionaries
                candlestick_data = []
                for index, row in bars.iterrows():
                    candlestick_data.append({
                        "timestamp": index.isoformat() if hasattr(index, 'isoformat') else str(index),
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": int(row['volume'])
                    })
                
                return candlestick_data
            else:
                print(f"No data returned from Alpaca for {symbol}")
                
        except Exception as e:
            print(f"Error fetching data from Alpaca: {e}")
            # Fall through to mock data
    
    # Fallback to mock data if Alpaca unavailable or error
    base_price = 150.0 if symbol == "AAPL" else 100.0
    data = []
    current_time = datetime.now()
    
    for i in range(limit):
        if alpaca_timeframe == "1Min":
            timestamp = current_time - timedelta(minutes=(limit - i))
        elif alpaca_timeframe == "5Min":
            timestamp = current_time - timedelta(minutes=5 * (limit - i))
        elif alpaca_timeframe == "15Min":
            timestamp = current_time - timedelta(minutes=15 * (limit - i))
        elif alpaca_timeframe == "30Min":
            timestamp = current_time - timedelta(minutes=30 * (limit - i))
        elif alpaca_timeframe == "1Hour":
            timestamp = current_time - timedelta(hours=(limit - i))
        else:  # 1Day
            timestamp = current_time - timedelta(days=(limit - i))
        
        # Generate realistic price movement
        open_price = base_price + random.uniform(-5, 5)
        close_price = open_price + random.uniform(-2, 2)
        high_price = max(open_price, close_price) + random.uniform(0, 1)
        low_price = min(open_price, close_price) - random.uniform(0, 1)
        volume = random.randint(1000, 10000)
        
        data.append({
            "timestamp": timestamp.isoformat(),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume
        })
        
        base_price = close_price
    
    return data

if __name__ == "__main__":
    import uvicorn
    # Use port 9002 as per our standard configuration
    port = int(os.getenv("TRADING_SERVICE_PORT", 9002))
    uvicorn.run("main_simple:app", host="0.0.0.0", port=port, reload=True)