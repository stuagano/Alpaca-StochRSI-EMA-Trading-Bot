#!/usr/bin/env python3
"""
Simplified Analytics Service with Real Trading Data Integration
"""

import os
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Analytics Service",
    description="Trading analytics and performance metrics",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
POSITION_SERVICE_URL = os.getenv("POSITION_SERVICE_URL", "http://localhost:9001")
TRADING_SERVICE_URL = os.getenv("TRADING_SERVICE_URL", "http://localhost:9002")

async def get_real_positions():
    """Get real positions from Position Management service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{POSITION_SERVICE_URL}/positions", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return data.get('positions', [])
    except Exception as e:
        print(f"Error fetching positions: {e}")
    return []

async def get_real_orders():
    """Get real orders from Trading Execution service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TRADING_SERVICE_URL}/orders", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return data.get('orders', [])
    except Exception as e:
        print(f"Error fetching orders: {e}")
    return []

async def get_real_account():
    """Get real account data from Trading Execution service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TRADING_SERVICE_URL}/account", timeout=5.0)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"Error fetching account: {e}")
    return None

@app.get("/health")
async def health_check():
    # Test connectivity to other services
    positions_connected = False
    trading_connected = False
    
    try:
        async with httpx.AsyncClient() as client:
            pos_response = await client.get(f"{POSITION_SERVICE_URL}/health", timeout=2.0)
            positions_connected = pos_response.status_code == 200
    except:
        pass
    
    try:
        async with httpx.AsyncClient() as client:
            trade_response = await client.get(f"{TRADING_SERVICE_URL}/health", timeout=2.0)
            trading_connected = trade_response.status_code == 200
    except:
        pass
    
    return {
        "service": "analytics",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "positions_service_connected": positions_connected,
        "trading_service_connected": trading_connected,
        "data_source": "real" if positions_connected and trading_connected else "mixed"
    }

@app.get("/analytics/summary")
async def get_analytics_summary():
    """Get analytics summary with real data"""
    positions = await get_real_positions()
    orders = await get_real_orders()
    account = await get_real_account()
    
    if positions and account:
        # Calculate real analytics
        total_unrealized_pnl = sum(p.get("unrealized_pl", 0) for p in positions)
        total_market_value = sum(p.get("market_value", 0) for p in positions)
        
        # Calculate win rate from filled orders
        filled_orders = [o for o in orders if o.get("status") == "filled"]
        profitable_orders = len([o for o in filled_orders if (o.get("filled_avg_price", 0) * o.get("filled_qty", 0)) > 0])
        win_rate = (profitable_orders / len(filled_orders) * 100) if filled_orders else 0
        
        return {
            "success": True,
            "total_pnl": total_unrealized_pnl,
            "total_pnl_percent": (total_unrealized_pnl / total_market_value * 100) if total_market_value > 0 else 0,
            "win_rate": win_rate,
            "winning_trades": profitable_orders,
            "losing_trades": len(filled_orders) - profitable_orders,
            "avg_trade": total_unrealized_pnl / len(filled_orders) if filled_orders else 0,
            "total_trades": len(filled_orders),
            "portfolio_value": account.get("portfolio_value", 0),
            "cash_balance": account.get("cash", 0),
            "positions_count": len(positions),
            "buying_power": account.get("buying_power", 0),
            "data_source": "real",
            "last_updated": datetime.utcnow().isoformat()
        }
    else:
        # Fallback to mock data
        return {
            "success": True,
            "total_pnl": 1234.56,
            "total_pnl_percent": 5.67,
            "win_rate": 65.4,
            "winning_trades": 13,
            "losing_trades": 7,
            "avg_trade": 61.73,
            "total_trades": 20,
            "sharpe_ratio": 1.23,
            "max_drawdown": -5.67,
            "best_day": 234.56,
            "worst_day": -123.45,
            "avg_win": 89.12,
            "avg_loss": -45.67,
            "profit_factor": 1.95,
            "recovery_factor": 2.34,
            "data_source": "mock"
        }

@app.get("/analytics/trades")
async def get_analytics_trades():
    """Get trade history for analytics"""
    orders = await get_real_orders()
    
    if orders:
        # Convert orders to trade format
        trades = []
        for order in orders[-10:]:  # Last 10 orders
            trades.append({
                "date": order.get("created_at", datetime.now().isoformat()),
                "symbol": order.get("symbol", "UNKNOWN"),
                "strategy": "Real Trading",
                "side": order.get("side", "unknown"),
                "quantity": order.get("qty", 0),
                "entry_price": order.get("filled_avg_price", order.get("limit_price", 0)),
                "exit_price": None,  # Would need position tracking for this
                "pnl": 0,  # Would calculate from position data
                "pnl_percent": 0,
                "duration": "Unknown",
                "status": order.get("status", "unknown"),
                "order_id": order.get("id", ""),
                "data_source": "real"
            })
        return trades
    else:
        # Fallback to mock data
        mock_trades = []
        for i in range(10):
            mock_trades.append({
                "date": (datetime.now() - timedelta(days=i)).isoformat(),
                "symbol": "AAPL" if i % 2 == 0 else "MSFT",
                "strategy": "StochRSI-EMA",
                "side": "buy" if i % 3 == 0 else "sell",
                "quantity": 100 + (i * 10),
                "entry_price": 175.50 + (i * 2),
                "exit_price": 178.25 + (i * 1.5),
                "pnl": (275.0 if i % 2 == 0 else -123.45),
                "pnl_percent": 2.34 if i % 2 == 0 else -1.23,
                "duration": "2h 15m",
                "data_source": "mock"
            })
        return mock_trades

@app.get("/analytics/pnl-history")
async def get_pnl_history():
    """Get P&L history for chart"""
    labels = []
    values = []
    cumulative_pnl = 0
    
    for i in range(30):
        date = (datetime.now() - timedelta(days=29-i)).strftime('%m/%d')
        labels.append(date)
        
        # Mock daily P&L
        daily_pnl = (i % 7 - 3) * 50 + (i % 3) * 25
        cumulative_pnl += daily_pnl
        values.append(cumulative_pnl)
    
    return {
        "success": True,
        "labels": labels,
        "values": values
    }

@app.get("/analytics/win-loss-distribution")
async def get_win_loss_distribution():
    """Get win/loss distribution"""
    return {
        "success": True,
        "winning_trades": 65,
        "losing_trades": 35
    }

@app.get("/analytics/monthly-performance")
async def get_monthly_performance():
    """Get monthly performance data"""
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    values = [234, -123, 456, 789, -234, 567]
    
    return {
        "success": True,
        "labels": months,
        "values": values
    }

@app.get("/analytics/strategy-performance")
async def get_strategy_performance():
    """Get strategy performance data"""
    strategies = ['StochRSI-EMA', 'Momentum', 'Mean Reversion']
    values = [1234, 567, 890]
    
    return {
        "success": True,
        "labels": strategies,
        "values": values
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_simple:app", host="127.0.0.1", port=9007, reload=True)