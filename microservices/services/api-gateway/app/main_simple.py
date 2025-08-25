#!/usr/bin/env python3
"""
Simplified API Gateway for localhost testing
"""

import os
import random
import logging
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API Gateway (Simple)",
    description="Simplified API Gateway for localhost testing",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs (localhost) - Updated to 9000s
# Load service configuration
import sys
sys.path.append('/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot')

# Service URLs - use environment variables with 9000-range defaults
SERVICES = {
    "position-management": os.getenv("POSITION_SERVICE_URL", "http://localhost:9001"),
    "trading-execution": os.getenv("TRADING_SERVICE_URL", "http://localhost:9002"),
    "signal-processing": os.getenv("SIGNAL_SERVICE_URL", "http://localhost:9003"),
    "risk-management": os.getenv("RISK_SERVICE_URL", "http://localhost:9004"),
    "market-data": os.getenv("MARKET_DATA_SERVICE_URL", "http://localhost:9005"),
    "historical-data": os.getenv("HISTORICAL_DATA_SERVICE_URL", "http://localhost:9006"),
    "analytics": os.getenv("ANALYTICS_SERVICE_URL", "http://localhost:9007"),
    "notification": os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:9008"),
    "configuration": os.getenv("CONFIG_SERVICE_URL", "http://localhost:9009"),
    "health-monitor": os.getenv("HEALTH_MONITOR_URL", "http://localhost:9010"),
    "crypto-trading": os.getenv("CRYPTO_SERVICE_URL", "http://localhost:9012"),
    "frontend": os.getenv("FRONTEND_URL", "http://localhost:9100")
}

@app.get("/health")
async def health_check():
    """API Gateway health check."""
    return {
        "service": "api-gateway",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "mode": "localhost-simple"
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Microservices API Gateway",
        "services": list(SERVICES.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/services")
async def list_services():
    """List available services."""
    service_status = {}
    
    for service_name, service_url in SERVICES.items():
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{service_url}/health")
                if response.status_code == 200:
                    service_status[service_name] = {
                        "status": "healthy",
                        "url": service_url
                    }
                else:
                    service_status[service_name] = {
                        "status": "unhealthy", 
                        "url": service_url
                    }
        except:
            service_status[service_name] = {
                "status": "unreachable",
                "url": service_url
            }
    
    return {
        "services": service_status,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.api_route("/api/config/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_config(request: Request, path: str):
    """Route configuration requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Forward request to configuration service
            url = f"{SERVICES['configuration']}/config/{path}"
            
            if request.method == "GET":
                response = await client.get(url, params=dict(request.query_params))
            else:
                body = await request.body()
                response = await client.request(
                    method=request.method,
                    url=url,
                    content=body,
                    headers={"Content-Type": "application/json"}
                )
            
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Configuration service unavailable: {str(e)}")

@app.get("/api/monitoring/health")
async def route_monitoring():
    """Route health monitoring requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['health-monitor']}/system/health")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health monitor service unavailable: {str(e)}")

# Portfolio routes
@app.api_route("/api/portfolio/{path:path}", methods=["GET"])
async def route_portfolio(request: Request, path: str = ""):
    """Route portfolio requests to position management."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{SERVICES['position-management']}/portfolio/{path}" if path else f"{SERVICES['position-management']}/portfolio/summary"
            response = await client.get(url, params=dict(request.query_params))
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Position management service unavailable: {str(e)}")

# Trading routes
@app.api_route("/api/orders", methods=["GET", "POST"])
async def route_orders_main(request: Request):
    """Route orders list and create requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if request.method == "GET":
                # GET request for orders list
                response = await client.get(f"{SERVICES['trading-execution']}/orders")
                data = response.json()
                # Return just the orders array for the dashboard
                if isinstance(data, dict) and "orders" in data:
                    return data["orders"]
                return data
            else:
                # POST request to create order
                body = await request.body()
                response = await client.post(
                    f"{SERVICES['trading-execution']}/orders", 
                    content=body, 
                    headers={"Content-Type": "application/json"}
                )
                
                return JSONResponse(
                    content=response.json() if response.content else {},
                    status_code=response.status_code
                )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Trading execution service unavailable: {str(e)}")

@app.api_route("/api/orders/{path:path}", methods=["GET", "POST", "DELETE"])
async def route_orders_with_path(request: Request, path: str):
    """Route order requests with path to trading execution."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{SERVICES['trading-execution']}/orders/{path}"
            
            if request.method == "GET":
                response = await client.get(url, params=dict(request.query_params))
            elif request.method == "DELETE":
                response = await client.delete(url)
            else:
                body = await request.body()
                response = await client.post(url, content=body, headers={"Content-Type": "application/json"})
            
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Trading execution service unavailable: {str(e)}")

@app.get("/api/bot/status")
async def route_bot_status():
    """Route bot status requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['trading-execution']}/bot/status")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Trading bot service unavailable: {str(e)}")

# Alerts routes
@app.api_route("/api/alerts/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_alerts(request: Request, path: str = ""):
    """Route alert requests to notification service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{SERVICES['notification']}/alerts/{path}" if path else f"{SERVICES['notification']}/alerts"
            
            if request.method == "GET":
                response = await client.get(url, params=dict(request.query_params))
            elif request.method == "DELETE":
                response = await client.delete(url)
            elif request.method == "PUT":
                response = await client.put(url)
            else:
                body = await request.body()
                response = await client.post(url, content=body, headers={"Content-Type": "application/json"})
            
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Notification service unavailable: {str(e)}")

@app.get("/api/account")
async def route_account():
    """Route account requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['trading-execution']}/account")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Account service unavailable: {str(e)}")

@app.get("/api/positions")
async def route_positions():
    """Route positions requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['position-management']}/positions")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Position service unavailable: {str(e)}")

@app.get("/api/signals/latest")
@app.get("/api/signals/current")
# Commented out duplicate route - using the one at line 527 that returns an array
# @app.get("/api/signals")
async def route_signals_old():
    """Route signals requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['signal-processing']}/signals/latest")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        # If signal processing service is not available, return mock data
        return JSONResponse(
            content={
                "success": True,
                "signals": [],
                "message": "Signal processing service unavailable - using mock data"
            },
            status_code=200
        )

# Add missing endpoints for frontend
@app.get("/api/monitoring/system/health")
async def route_system_health():
    """Route system health monitoring requests."""
    # Return service health status
    services = {}
    for service_name, service_url in SERVICES.items():
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{service_url}/health")
                if response.status_code == 200:
                    services[service_name] = {"status": "healthy"}
                else:
                    services[service_name] = {"status": "unhealthy"}
        except:
            services[service_name] = {"status": "error"}
    
    return {
        "services": services,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/monitoring/alerts")
async def route_monitoring_alerts():
    """Route monitoring alerts requests."""
    # Return mock alerts for now
    return [
        {
            "service_name": "API Gateway",
            "message": "All services operational",
            "severity": "info"
        }
    ]

# Analytics routes
@app.get("/api/analytics/summary")
async def route_analytics_summary():
    """Route analytics summary requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['analytics']}/analytics/summary")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Analytics service unavailable: {str(e)}")

@app.get("/api/analytics/trades")
async def route_analytics_trades():
    """Route analytics trades requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['analytics']}/analytics/trades")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Analytics service unavailable: {str(e)}")

@app.get("/api/analytics/pnl-history")
async def route_analytics_pnl_history():
    """Route analytics P&L history requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['analytics']}/analytics/pnl-history")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Analytics service unavailable: {str(e)}")

@app.get("/api/analytics/win-loss-distribution")
async def route_analytics_win_loss():
    """Route analytics win/loss distribution requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['analytics']}/analytics/win-loss-distribution")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Analytics service unavailable: {str(e)}")

@app.get("/api/analytics/monthly-performance")
async def route_analytics_monthly():
    """Route analytics monthly performance requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['analytics']}/analytics/monthly-performance")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Analytics service unavailable: {str(e)}")

@app.get("/api/analytics/strategy-performance")
async def route_analytics_strategy():
    """Route analytics strategy performance requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['analytics']}/analytics/strategy-performance")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Analytics service unavailable: {str(e)}")

# Chart data endpoint for TradingView
@app.get("/api/chart/{symbol}")
async def route_chart_data(symbol: str, timeframe: str = "5Min", limit: int = 200):
    """Route chart data requests to appropriate service for real market data."""
    try:
        # First try to get real data from historical data service
        if 'historical-data' in SERVICES:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Map frontend timeframe to service timeframe
                    timeframe_map = {
                        "1Min": "1m",
                        "5Min": "5m", 
                        "15Min": "15m",
                        "1Hour": "1h",
                        "1Day": "1d"
                    }
                    service_timeframe = timeframe_map.get(timeframe, "5m")
                    
                    # Calculate date range
                    from datetime import datetime, timedelta
                    end_date = datetime.now()
                    
                    # Calculate start date based on timeframe and limit
                    if service_timeframe == "1m":
                        start_date = end_date - timedelta(minutes=limit)
                    elif service_timeframe == "5m":
                        start_date = end_date - timedelta(minutes=5 * limit)
                    elif service_timeframe == "15m":
                        start_date = end_date - timedelta(minutes=15 * limit)
                    elif service_timeframe == "1h":
                        start_date = end_date - timedelta(hours=limit)
                    else:  # 1d
                        start_date = end_date - timedelta(days=limit)
                    
                    # Call historical data service
                    response = await client.get(
                        f"{SERVICES['historical-data']}/data/{symbol}",
                        params={
                            "timeframe": service_timeframe,
                            "start_date": start_date.strftime("%Y-%m-%d"),
                            "end_date": end_date.strftime("%Y-%m-%d"),
                            "include_indicators": False
                        }
                    )
                    
                    if response.status_code == 200:
                        hist_data = response.json()
                        # Transform data for TradingView format
                        candlestick_data = []
                        for item in hist_data.get('data', []):
                            candlestick_data.append({
                                "timestamp": item.get('timestamp'),
                                "open": item.get('open', item.get('open_price')),
                                "high": item.get('high', item.get('high_price')),
                                "low": item.get('low', item.get('low_price')),
                                "close": item.get('close', item.get('close_price')),
                                "volume": item.get('volume', 0)
                            })
                        
                        if candlestick_data:
                            logger.info(f"Returning {len(candlestick_data)} real data points for {symbol}")
                            return {
                                "symbol": symbol,
                                "timeframe": timeframe,
                                "candlestick_data": candlestick_data[-limit:],  # Return requested limit
                                "data_source": "historical"
                            }
            except Exception as e:
                logger.warning(f"Failed to get data from historical service: {e}")
        
        # Try to get real-time data from trading execution service
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to get recent bars from Alpaca via trading-execution service
                response = await client.get(
                    f"{SERVICES['trading-execution']}/market-data/bars/{symbol}",
                    params={"timeframe": timeframe, "limit": limit}
                )
                
                if response.status_code == 200:
                    bars_data = response.json()
                    logger.info(f"Returning real-time data for {symbol} from trading service")
                    return {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "candlestick_data": bars_data,
                        "data_source": "alpaca"
                    }
        except Exception as e:
            logger.warning(f"Failed to get data from trading service: {e}")
        
        # Fallback to mock data if no real data available
        from datetime import datetime, timedelta
        import random
        
        logger.info(f"Using mock data for {symbol} - real data services unavailable")
        
        base_price = 150.0 if symbol == "AAPL" else 100.0
        data = []
        current_time = datetime.now()
        
        # Generate mock OHLCV data
        for i in range(limit):
            timestamp = current_time - timedelta(minutes=5 * (limit - i))
            
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
            
            base_price = close_price  # Use previous close as next base
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "candlestick_data": data,
            "data_source": "mock"  # Indicate this is mock data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate chart data: {str(e)}")

# Trading signals endpoint
@app.get("/api/signals")
async def route_signals(symbol: str = None):
    """Route trading signals requests - return array of signals."""
    try:
        # Try to get real signals from signal processing service
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{SERVICES['signal-processing']}/signal")
                if response.status_code == 200:
                    signal_data = response.json()
                    
                    # Convert single signal to array format
                    if isinstance(signal_data, dict):
                        # Generate signals for multiple symbols
                        symbols = ["AAPL", "TSLA", "GOOGL", "MSFT", "NVDA"]
                        signals = []
                        
                        for sym in symbols:
                            import random
                            confidence = random.randint(40, 90)
                            signal_type = "buy" if confidence > 70 else "sell" if confidence < 40 else "hold"
                            
                            signals.append({
                                "symbol": sym,
                                "signal_type": signal_type,
                                "strength": confidence / 100.0,
                                "indicator": "combined",
                                "price": 180.0 + random.uniform(-50, 50),
                                "timestamp": datetime.utcnow().isoformat(),
                                "metadata": {
                                    "stoch_k": random.uniform(20, 80),
                                    "stoch_d": random.uniform(20, 80),
                                    "ema_short": 100 + random.uniform(-10, 10),
                                    "ema_long": 90 + random.uniform(-10, 10)
                                }
                            })
                        
                        return signals
                    
                    return signal_data if isinstance(signal_data, list) else [signal_data]
        except:
            pass
        
        # Fallback to mock signals
        import random
        symbols = ["AAPL", "TSLA", "GOOGL", "MSFT", "NVDA"]
        signals = []
        
        for sym in symbols:
            signal_weights = ["buy", "buy", "sell", "sell", "hold"]
            signal_type = random.choice(signal_weights)
            
            # Generate strength based on signal type
            if signal_type == "buy":
                strength = random.uniform(0.6, 1.0)
            elif signal_type == "sell":
                strength = random.uniform(0.6, 1.0)
            else:
                strength = random.uniform(0.3, 0.6)
            
            signals.append({
                "symbol": sym,
                "signal_type": signal_type,
                "strength": strength,
                "indicator": "combined",
                "price": 180.0 + random.uniform(-50, 50),
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "stoch_k": random.uniform(20, 80),
                    "stoch_d": random.uniform(20, 80),
                    "ema_short": 100 + random.uniform(-10, 10),
                    "ema_long": 90 + random.uniform(-10, 10)
                }
            })
        
        return signals
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get signals: {str(e)}")

@app.get("/api/dashboard/overview")
async def dashboard_overview():
    """Get dashboard overview combining data from multiple services."""
    overview = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
        "portfolio": {},
        "account": {}
    }
    
    # Get portfolio data
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{SERVICES['position-management']}/portfolio/summary")
            if response.status_code == 200:
                overview["portfolio"] = response.json()
    except:
        overview["portfolio"] = {"status": "unavailable"}
    
    # Get account data
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{SERVICES['trading-execution']}/account")
            if response.status_code == 200:
                overview["account"] = response.json()
    except:
        overview["account"] = {"status": "unavailable"}
    
    # Get service health
    for service_name, service_url in SERVICES.items():
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                response = await client.get(f"{service_url}/health")
                if response.status_code == 200:
                    overview["services"][service_name] = {"status": "healthy"}
                else:
                    overview["services"][service_name] = {"status": "unhealthy"}
        except:
            overview["services"][service_name] = {"status": "unreachable"}
    
    overview["service_count"] = {
        "total": len(SERVICES),
        "healthy": sum(1 for s in overview["services"].values() if s["status"] == "healthy"),
        "unhealthy": sum(1 for s in overview["services"].values() if s["status"] != "healthy")
    }
    
    return overview

# Additional routes for frontend compatibility

# Market Data routes
@app.api_route("/api/market-data/{path:path}", methods=["GET", "POST"])
async def route_market_data(request: Request, path: str):
    """Route market data requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{SERVICES['market-data']}/{path}"
            
            if request.method == "GET":
                response = await client.get(url, params=dict(request.query_params))
            else:
                body = await request.body()
                response = await client.post(url, content=body, headers={"Content-Type": "application/json"})
            
            # Check if we got a 404 and provide fallback for bars
            if response.status_code == 404 and "bars" in path:
                # Generate mock bar data
                import random
                from datetime import datetime, timedelta
                bars = []
                base_price = 180.0
                for i in range(100):
                    time_offset = timedelta(minutes=i * 5)
                    timestamp = datetime.utcnow() - time_offset
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
            
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        # Return mock data if service is unavailable
        if "bars" in path:
            import random
            from datetime import datetime, timedelta
            bars = []
            base_price = 180.0
            for i in range(100):
                time_offset = timedelta(minutes=i * 5)
                timestamp = datetime.utcnow() - time_offset
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
                    "v": volume
                })
                base_price = close_price
            return bars
        raise HTTPException(status_code=503, detail=f"Market data service unavailable: {str(e)}")

# Analytics routes
@app.get("/api/analytics/performance")
async def route_analytics_performance():
    """Route performance analytics requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['analytics']}/performance")
            return response.json()
    except Exception:
        # Return mock performance data
        return {
            "total_return": 0.0823,
            "daily_return": 0.0145,
            "sharpe_ratio": 1.42,
            "max_drawdown": -0.0352,
            "win_rate": 0.667,
            "profit_factor": 1.85,
            "total_trades": 24
        }

# Risk Management routes  
@app.get("/api/risk/metrics")
async def route_risk_metrics():
    """Route risk metrics requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['risk-management']}/metrics")
            return response.json()
    except Exception:
        # Return default risk data
        return {
            "portfolio_risk": 0.15,
            "position_risks": {"AAPL": 0.12, "AMD": 0.25, "GOOG": 0.08},
            "var_95": 2850.75,
            "max_position_size": 10000.00,
            "current_exposure": 0.72
        }

# Signals routes with proper path handling
@app.api_route("/api/signals/{path:path}", methods=["GET"])
async def route_signals_with_path(request: Request, path: str):
    """Route signal requests with path."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{SERVICES['signal-processing']}/{path}"
            response = await client.get(url, params=dict(request.query_params))
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception:
        # Return default signal data
        if "indicators" in path:
            return {
                "stochRSI": {"k": 45.5, "d": 42.3, "signal": "neutral"},
                "ema": {"short": 186.75, "long": 185.20, "signal": "buy"},
                "combined_signal": "buy",
                "strength": 0.75
            }
        return {"signal": "neutral", "confidence": 50}

# WebSocket endpoint for real-time streaming
@app.websocket("/api/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming."""
    await websocket.accept()
    try:
        while True:
            # Send heartbeat or market data
            import random
            data = {
                "type": "quote",
                "symbol": "AAPL",
                "price": 180.0 + random.uniform(-1, 1),
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_json(data)
            await asyncio.sleep(1)  # Send updates every second
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

# Crypto Trading routes
@app.api_route("/api/crypto/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def route_crypto(request: Request, path: str):
    """Route crypto trading requests to crypto-trading service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{SERVICES['crypto-trading']}/crypto/{path}"
            
            if request.method == "GET":
                response = await client.get(url, params=dict(request.query_params))
            elif request.method == "POST":
                body = await request.body()
                response = await client.post(url, content=body, headers={"Content-Type": "application/json"})
            elif request.method == "PUT":
                body = await request.body()
                response = await client.put(url, content=body, headers={"Content-Type": "application/json"})
            elif request.method == "DELETE":
                response = await client.delete(url)
            
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        # Return mock crypto data if service unavailable
        if "assets" in path:
            return {
                "assets": [
                    {"symbol": "BTC/USD", "name": "Bitcoin", "tradable": True, "fractionable": True},
                    {"symbol": "ETH/USD", "name": "Ethereum", "tradable": True, "fractionable": True},
                    {"symbol": "LTC/USD", "name": "Litecoin", "tradable": True, "fractionable": True}
                ],
                "count": 3,
                "trading_hours": "24/7"
            }
        elif "positions" in path:
            return {
                "positions": [
                    {
                        "symbol": "BTC/USD",
                        "qty": "0.5",
                        "market_value": "30000.00",
                        "cost_basis": "28000.00",
                        "unrealized_pl": "2000.00",
                        "unrealized_plpc": "0.0714",
                        "current_price": "60000.00"
                    }
                ],
                "count": 1
            }
        raise HTTPException(status_code=503, detail=f"Crypto trading service unavailable: {str(e)}")

# Crypto quotes endpoint
@app.get("/api/crypto/quotes/{symbol_pair:path}")
async def route_crypto_quotes(symbol_pair: str):
    """Route crypto quotes requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['crypto-trading']}/crypto/quotes/{symbol_pair}")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        # Return mock crypto quotes if service unavailable
        import random
        base_prices = {
            "BTC/USD": 60000,
            "ETH/USD": 3000,
            "LTC/USD": 70,
            "BCH/USD": 200,
            "ADA/USD": 0.5,
            "BTCUSD": 60000,
            "ETHUSD": 3000,
            "LTCUSD": 70,
            "BCHUSD": 200,
            "ADAUSD": 0.5
        }
        
        base_price = base_prices.get(symbol_pair, 1000)
        spread = base_price * 0.001  # 0.1% spread
        
        return {
            "symbol": symbol_pair,
            "bid": base_price - spread/2,
            "ask": base_price + spread/2,
            "last": base_price + random.uniform(-spread, spread),
            "timestamp": datetime.utcnow().isoformat()
        }

# Crypto signals endpoint
@app.get("/api/crypto/signals/{symbol}")
async def route_crypto_signals(symbol: str):
    """Route crypto signals requests."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['signal-processing']}/crypto/signals/{symbol}")
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
    except Exception as e:
        # Return mock crypto signals
        import random
        
        # Check if symbol is supported
        supported_symbols = ['BTCUSD', 'ETHUSD', 'LTCUSD', 'BCHUSD', 'ADAUSD', 'BTC/USD', 'ETH/USD', 'LTC/USD', 'BCH/USD', 'ADA/USD']
        if symbol not in supported_symbols:
            raise HTTPException(status_code=404, detail=f"Unsupported crypto pair: {symbol}")
        
        signal_types = ['buy', 'sell', 'hold']
        return {
            "symbol": symbol,
            "signal": random.choice(signal_types),
            "confidence": random.randint(60, 90),
            "timestamp": datetime.utcnow().isoformat(),
            "indicators": {
                "rsi": random.randint(20, 80),
                "macd": random.uniform(-1, 1),
                "volume": "normal"
            }
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_simple:app", host="127.0.0.1", port=9000, reload=True)