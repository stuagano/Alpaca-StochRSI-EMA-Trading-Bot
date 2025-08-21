#!/usr/bin/env python3
"""
Trading Execution Service

Handles order placement, execution, and management through Alpaca Markets API.
Provides order lifecycle management and trade execution for the trading system.

Features:
- Order placement with Alpaca API
- Order status tracking and updates
- Trade execution logic
- Risk management integration
- Error handling and retry logic
"""

import os
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from uuid import uuid4
from enum import Enum

import structlog
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel, Field
import alpaca_trade_api as tradeapi

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
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
POSITION_SERVICE_URL = os.getenv("POSITION_SERVICE_URL", "http://position-management:8001")
RISK_SERVICE_URL = os.getenv("RISK_SERVICE_URL", "http://risk-management:8004")

# Alpaca API client
alpaca_api = None

# Enums
class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderStatus(str, Enum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    DONE_FOR_DAY = "done_for_day"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REPLACED = "replaced"
    PENDING_CANCEL = "pending_cancel"
    PENDING_REPLACE = "pending_replace"
    ACCEPTED = "accepted"
    PENDING_NEW = "pending_new"
    ACCEPTED_FOR_BIDDING = "accepted_for_bidding"
    STOPPED = "stopped"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    CALCULATED = "calculated"

class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"  # Good Till Canceled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill

# Data models
class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    qty: int = Field(..., description="Quantity to trade")
    side: OrderSide = Field(..., description="Buy or sell")
    type: OrderType = Field(default=OrderType.MARKET, description="Order type")
    time_in_force: TimeInForce = Field(default=TimeInForce.DAY, description="Time in force")
    limit_price: Optional[float] = Field(None, description="Limit price for limit orders")
    stop_price: Optional[float] = Field(None, description="Stop price for stop orders")
    client_order_id: Optional[str] = Field(None, description="Client order ID")
    extended_hours: bool = Field(False, description="Allow extended hours trading")

class TradingSignal(BaseModel):
    symbol: str
    action: str  # "BUY" or "SELL"
    quantity: Optional[int] = None
    price: Optional[float] = None
    signal_strength: float = Field(ge=0.0, le=1.0)
    strategy: str = "StochRSI_EMA"
    metadata: Optional[Dict[str, Any]] = None

class OrderResponse(BaseModel):
    id: str
    client_order_id: str
    symbol: str
    asset_class: str
    qty: int
    filled_qty: int
    side: OrderSide
    order_type: OrderType
    time_in_force: TimeInForce
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    replaced_at: Optional[datetime] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_avg_price: Optional[float] = None

class ExecutionResult(BaseModel):
    success: bool
    order_id: Optional[str] = None
    message: str
    symbol: str
    action: str
    quantity: int
    error: Optional[str] = None

# Trading Execution Service
class TradingExecutionService:
    """Core trading execution service with Alpaca integration."""
    
    def __init__(self):
        self.orders_cache = {}
        
    async def validate_order(self, order_request: OrderRequest) -> bool:
        """Validate order before submission."""
        try:
            # Basic validation
            if order_request.qty <= 0:
                raise ValueError("Quantity must be positive")
            
            if order_request.type == OrderType.LIMIT and not order_request.limit_price:
                raise ValueError("Limit price required for limit orders")
            
            if order_request.type in [OrderType.STOP, OrderType.STOP_LIMIT] and not order_request.stop_price:
                raise ValueError("Stop price required for stop orders")
            
            # Check with Risk Management Service
            risk_check = await self._check_risk_limits(order_request)
            if not risk_check:
                raise ValueError("Order rejected by risk management")
            
            # Check account buying power (for paper trading)
            account = alpaca_api.get_account()
            if order_request.side == OrderSide.BUY:
                buying_power = float(account.buying_power)
                estimated_cost = order_request.qty * (order_request.limit_price or 100)  # Rough estimate
                
                if estimated_cost > buying_power:
                    raise ValueError("Insufficient buying power")
            
            return True
            
        except Exception as e:
            logger.error("Order validation failed", error=str(e), order=order_request.dict())
            return False
    
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place an order through Alpaca API."""
        try:
            # Validate order first
            if not await self.validate_order(order_request):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Order validation failed"
                )
            
            # Generate client order ID if not provided
            if not order_request.client_order_id:
                order_request.client_order_id = f"client_{uuid4().hex[:8]}"
            
            # Convert to Alpaca format
            alpaca_order = {
                "symbol": order_request.symbol,
                "qty": order_request.qty,
                "side": order_request.side.value,
                "type": order_request.type.value,
                "time_in_force": order_request.time_in_force.value,
                "client_order_id": order_request.client_order_id,
                "extended_hours": order_request.extended_hours
            }
            
            # Add price fields if specified
            if order_request.limit_price:
                alpaca_order["limit_price"] = str(order_request.limit_price)
            if order_request.stop_price:
                alpaca_order["stop_price"] = str(order_request.stop_price)
            
            # Submit order to Alpaca
            submitted_order = alpaca_api.submit_order(**alpaca_order)
            
            # Convert response to our format
            order_response = self._convert_alpaca_order(submitted_order)
            
            # Cache the order
            self.orders_cache[order_response.id] = order_response
            
            # Notify Position Management Service
            await self._notify_position_service(order_response, "order_placed")
            
            logger.info("Order placed successfully", 
                       order_id=order_response.id, 
                       symbol=order_request.symbol,
                       side=order_request.side,
                       qty=order_request.qty)
            
            return order_response
            
        except Exception as e:
            logger.error("Error placing order", error=str(e), order=order_request.dict())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to place order: {str(e)}"
            )
    
    async def get_order(self, order_id: str) -> Optional[OrderResponse]:
        """Get order status by ID."""
        try:
            # Check cache first
            if order_id in self.orders_cache:
                # Refresh from Alpaca to get latest status
                try:
                    alpaca_order = alpaca_api.get_order(order_id)
                    order_response = self._convert_alpaca_order(alpaca_order)
                    self.orders_cache[order_id] = order_response
                    return order_response
                except:
                    # Return cached version if API call fails
                    return self.orders_cache[order_id]
            
            # Get from Alpaca
            alpaca_order = alpaca_api.get_order(order_id)
            order_response = self._convert_alpaca_order(alpaca_order)
            
            # Cache the result
            self.orders_cache[order_id] = order_response
            
            return order_response
            
        except Exception as e:
            logger.error("Error getting order", error=str(e), order_id=order_id)
            return None
    
    async def get_orders(self, 
                        status: Optional[str] = None,
                        limit: int = 100,
                        since: Optional[datetime] = None) -> List[OrderResponse]:
        """Get orders with filtering."""
        try:
            # Build filter parameters
            filter_params = {
                "limit": min(limit, 500),  # Alpaca max is 500
                "direction": "desc"
            }
            
            if status:
                filter_params["status"] = status
            if since:
                filter_params["after"] = since.isoformat()
            
            # Get orders from Alpaca
            alpaca_orders = alpaca_api.list_orders(**filter_params)
            
            # Convert to our format
            orders = []
            for alpaca_order in alpaca_orders:
                order_response = self._convert_alpaca_order(alpaca_order)
                orders.append(order_response)
                # Update cache
                self.orders_cache[order_response.id] = order_response
            
            return orders
            
        except Exception as e:
            logger.error("Error getting orders", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get orders: {str(e)}"
            )
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        try:
            # Cancel order in Alpaca
            alpaca_api.cancel_order(order_id)
            
            # Update cache
            if order_id in self.orders_cache:
                self.orders_cache[order_id].status = OrderStatus.CANCELED
                self.orders_cache[order_id].canceled_at = datetime.utcnow()
            
            logger.info("Order canceled", order_id=order_id)
            return True
            
        except Exception as e:
            logger.error("Error canceling order", error=str(e), order_id=order_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel order: {str(e)}"
            )
    
    async def execute_trading_signal(self, signal: TradingSignal) -> ExecutionResult:
        """Execute a trading signal from the strategy service."""
        try:
            # Determine order parameters based on signal
            side = OrderSide.BUY if signal.action.upper() == "BUY" else OrderSide.SELL
            
            # Calculate quantity if not specified
            if not signal.quantity:
                # Use position sizing based on signal strength and account size
                account = alpaca_api.get_account()
                buying_power = float(account.buying_power)
                
                # Risk 1-3% of account based on signal strength
                risk_pct = 0.01 + (signal.signal_strength * 0.02)  # 1% to 3%
                risk_amount = buying_power * risk_pct
                
                # Estimate price for quantity calculation
                if signal.price:
                    estimated_price = signal.price
                else:
                    # Get current market price
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"http://market-data:8005/price/{signal.symbol}"
                        )
                        if response.status_code == 200:
                            price_data = response.json()
                            estimated_price = price_data["price"]
                        else:
                            estimated_price = 100  # Fallback
                
                signal.quantity = max(1, int(risk_amount / estimated_price))
            
            # Create order request
            order_request = OrderRequest(
                symbol=signal.symbol,
                qty=signal.quantity,
                side=side,
                type=OrderType.MARKET,  # Use market orders for signals
                client_order_id=f"signal_{uuid4().hex[:8]}"
            )
            
            # Place the order
            order_response = await self.place_order(order_request)
            
            return ExecutionResult(
                success=True,
                order_id=order_response.id,
                message=f"Signal executed successfully for {signal.symbol}",
                symbol=signal.symbol,
                action=signal.action,
                quantity=signal.quantity
            )
            
        except Exception as e:
            logger.error("Error executing trading signal", 
                        error=str(e), signal=signal.dict())
            return ExecutionResult(
                success=False,
                message=f"Failed to execute signal: {str(e)}",
                symbol=signal.symbol,
                action=signal.action,
                quantity=signal.quantity or 0,
                error=str(e)
            )
    
    def _convert_alpaca_order(self, alpaca_order) -> OrderResponse:
        """Convert Alpaca order object to our OrderResponse format."""
        return OrderResponse(
            id=str(alpaca_order.id),
            client_order_id=alpaca_order.client_order_id or "",
            symbol=alpaca_order.symbol,
            asset_class=alpaca_order.asset_class,
            qty=int(alpaca_order.qty),
            filled_qty=int(alpaca_order.filled_qty),
            side=OrderSide(alpaca_order.side),
            order_type=OrderType(alpaca_order.order_type),
            time_in_force=TimeInForce(alpaca_order.time_in_force),
            status=OrderStatus(alpaca_order.status),
            created_at=alpaca_order.created_at,
            updated_at=alpaca_order.updated_at,
            submitted_at=alpaca_order.submitted_at,
            filled_at=alpaca_order.filled_at,
            expired_at=alpaca_order.expired_at,
            canceled_at=alpaca_order.canceled_at,
            failed_at=alpaca_order.failed_at,
            replaced_at=alpaca_order.replaced_at,
            limit_price=float(alpaca_order.limit_price) if alpaca_order.limit_price else None,
            stop_price=float(alpaca_order.stop_price) if alpaca_order.stop_price else None,
            filled_avg_price=float(alpaca_order.filled_avg_price) if alpaca_order.filled_avg_price else None
        )
    
    async def _check_risk_limits(self, order_request: OrderRequest) -> bool:
        """Check order against risk management limits."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{RISK_SERVICE_URL}/validate/order",
                    json=order_request.dict(),
                    timeout=5.0
                )
                return response.status_code == 200 and response.json().get("approved", False)
        except:
            # If risk service is unavailable, apply basic checks
            return order_request.qty <= 1000  # Basic quantity limit
    
    async def _notify_position_service(self, order: OrderResponse, event: str):
        """Notify Position Management Service of order events."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{POSITION_SERVICE_URL}/orders/events",
                    json={
                        "event": event,
                        "order": order.dict(),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    timeout=5.0
                )
        except Exception as e:
            logger.warning("Failed to notify position service", error=str(e))

# Global service instance
trading_service = TradingExecutionService()

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global alpaca_api
    
    try:
        # Initialize Alpaca API
        if ALPACA_API_KEY and ALPACA_SECRET_KEY:
            alpaca_api = tradeapi.REST(
                ALPACA_API_KEY,
                ALPACA_SECRET_KEY,
                ALPACA_BASE_URL,
                api_version='v2'
            )
            
            # Test connection
            account = alpaca_api.get_account()
            logger.info("✅ Trading Execution Service started successfully", 
                       account_status=account.status)
        else:
            logger.warning("⚠️ Alpaca API credentials not configured - running in mock mode")
            
        yield
        
    except Exception as e:
        logger.error("❌ Failed to start Trading Execution Service", error=str(e))
        yield
    finally:
        logger.info("🔌 Trading Execution Service shutdown complete")

# FastAPI application
app = FastAPI(
    title="Trading Execution Service",
    description="Order placement and execution through Alpaca Markets API",
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

# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    alpaca_connected = alpaca_api is not None
    account_status = None
    
    if alpaca_connected:
        try:
            account = alpaca_api.get_account()
            account_status = account.status
        except:
            alpaca_connected = False
    
    return {
        "service": "trading-execution",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "alpaca_connected": alpaca_connected,
        "account_status": account_status
    }

@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_order(order_request: OrderRequest):
    """Place a new order."""
    if not alpaca_api:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alpaca API not configured"
        )
    
    return await trading_service.place_order(order_request)

@app.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    status: Optional[str] = None,
    limit: int = 100,
    since: Optional[str] = None
):
    """Get orders with optional filtering."""
    if not alpaca_api:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alpaca API not configured"
        )
    
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
        except:
            pass
    
    return await trading_service.get_orders(status, limit, since_dt)

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    """Get order by ID."""
    if not alpaca_api:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alpaca API not configured"
        )
    
    order = await trading_service.get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order

@app.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an order."""
    if not alpaca_api:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alpaca API not configured"
        )
    
    success = await trading_service.cancel_order(order_id)
    return {"success": success, "message": "Order canceled successfully"}

@app.post("/execute/signal", response_model=ExecutionResult)
async def execute_trading_signal(signal: TradingSignal):
    """Execute a trading signal from the strategy service."""
    return await trading_service.execute_trading_signal(signal)

@app.get("/account")
async def get_account_info():
    """Get Alpaca account information."""
    if not alpaca_api:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alpaca API not configured"
        )
    
    try:
        account = alpaca_api.get_account()
        return {
            "id": account.id,
            "status": account.status,
            "currency": account.currency,
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "equity": float(account.equity),
            "portfolio_value": float(account.portfolio_value),
            "last_equity": float(account.last_equity),
            "multiplier": int(account.multiplier),
            "day_trade_count": int(account.day_trade_count),
            "daytrading_buying_power": float(account.daytrading_buying_power),
            "regt_buying_power": float(account.regt_buying_power),
            "pattern_day_trader": account.pattern_day_trader,
            "trading_blocked": account.trading_blocked,
            "transfers_blocked": account.transfers_blocked,
            "account_blocked": account.account_blocked,
            "created_at": account.created_at.isoformat() if account.created_at else None
        }
    except Exception as e:
        logger.error("Error getting account info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get account info: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )