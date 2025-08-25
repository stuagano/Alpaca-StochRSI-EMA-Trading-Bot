#!/usr/bin/env python3
"""
High-Frequency Trading Execution Service
Rapid order execution, scalping automation, hundreds of trades per session
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uvicorn
import asyncio
import json
import random
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum

app = FastAPI(title="HFT Execution Service", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class TradingStrategy(str, Enum):
    SCALPING = "SCALPING"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    BREAKOUT = "BREAKOUT"

class Order(BaseModel):
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "DAY"
    strategy: Optional[TradingStrategy] = None
    created_at: datetime
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    commission: float = 0.0

class Position(BaseModel):
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    day_trades: int

class TradeExecution(BaseModel):
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    timestamp: datetime
    commission: float
    strategy: Optional[TradingStrategy] = None

# In-memory storage for high-frequency operations
class TradingEngine:
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.executions: List[TradeExecution] = []
        self.account_value = 100000.0  # Starting capital
        self.day_trades_count = 0
        self.total_trades = 0
        self.profit_target = 0.01  # 1% profit target per trade
        self.stop_loss = 0.005     # 0.5% stop loss
        self.max_position_size = 1000  # Max shares per position
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.win_rate = 0.0
        self.total_commission = 0.0
        
        # Risk management
        self.max_daily_loss = 2000.0
        self.max_position_risk = 0.02  # 2% of account per position

    async def execute_market_order(self, order: Order) -> bool:
        """Execute market order immediately"""
        try:
            # Simulate market execution with realistic slippage
            slippage = random.uniform(0.001, 0.005)  # 0.1-0.5% slippage
            
            if order.side == OrderSide.BUY:
                fill_price = order.price * (1 + slippage) if order.price else random.uniform(50, 200)
            else:
                fill_price = order.price * (1 - slippage) if order.price else random.uniform(50, 200)
            
            # Execute the order
            commission = max(0.50, order.quantity * 0.005)  # $0.50 min or $0.005 per share
            
            execution = TradeExecution(
                trade_id=str(uuid.uuid4()),
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=round(fill_price, 2),
                timestamp=datetime.utcnow(),
                commission=round(commission, 2),
                strategy=order.strategy
            )
            
            # Update order
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.filled_price = fill_price
            order.commission = commission
            
            # Update position
            await self.update_position(order.symbol, order.side, order.quantity, fill_price)
            
            # Track execution
            self.executions.append(execution)
            self.total_trades += 1
            self.total_commission += commission
            
            # Update daily P&L
            if order.side == OrderSide.SELL:
                self.calculate_realized_pnl(order)
            
            return True
            
        except Exception as e:
            order.status = OrderStatus.REJECTED
            print(f"Order execution failed: {e}")
            return False

    async def update_position(self, symbol: str, side: OrderSide, quantity: int, price: float):
        """Update position after trade execution"""
        if symbol not in self.positions:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=0,
                avg_price=0.0,
                current_price=price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                day_trades=0
            )
        
        position = self.positions[symbol]
        
        if side == OrderSide.BUY:
            # Add to position
            total_cost = (position.quantity * position.avg_price) + (quantity * price)
            total_quantity = position.quantity + quantity
            position.avg_price = total_cost / total_quantity if total_quantity > 0 else price
            position.quantity = total_quantity
        else:
            # Reduce position
            if position.quantity >= quantity:
                position.quantity -= quantity
                # Calculate realized P&L
                realized_pnl = quantity * (price - position.avg_price)
                position.realized_pnl += realized_pnl
                self.daily_pnl += realized_pnl
            else:
                # Going short or insufficient position
                position.quantity = quantity if position.quantity == 0 else position.quantity - quantity
                position.avg_price = price
        
        position.current_price = price
        position.day_trades += 1
        self.day_trades_count += 1

    def calculate_realized_pnl(self, order: Order):
        """Calculate realized P&L for completed trade"""
        if order.symbol in self.positions:
            position = self.positions[order.symbol]
            if order.side == OrderSide.SELL:
                pnl = order.quantity * (order.filled_price - position.avg_price)
                self.daily_pnl += pnl

    async def place_scalping_order(self, symbol: str, current_price: float, signal_direction: str) -> Order:
        """Place rapid scalping order with tight stops"""
        order_id = str(uuid.uuid4())
        
        if signal_direction == "BUY":
            side = OrderSide.BUY
            take_profit = current_price * (1 + self.profit_target)
            stop_loss = current_price * (1 - self.stop_loss)
        else:
            side = OrderSide.SELL
            take_profit = current_price * (1 - self.profit_target)
            stop_loss = current_price * (1 + self.stop_loss)
        
        # Calculate position size based on risk
        risk_amount = self.account_value * self.max_position_risk
        price_risk = abs(current_price - stop_loss)
        max_quantity = min(self.max_position_size, int(risk_amount / price_risk))
        
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=max_quantity,
            price=current_price,
            strategy=TradingStrategy.SCALPING,
            created_at=datetime.utcnow()
        )
        
        self.orders[order_id] = order
        
        # Execute immediately
        await self.execute_market_order(order)
        
        # Place stop loss and take profit orders
        await self.place_stop_orders(symbol, take_profit, stop_loss, max_quantity, side)
        
        return order

    async def place_stop_orders(self, symbol: str, take_profit: float, stop_loss: float, quantity: int, original_side: OrderSide):
        """Place stop loss and take profit orders"""
        # Take profit order
        tp_side = OrderSide.SELL if original_side == OrderSide.BUY else OrderSide.BUY
        tp_order = Order(
            order_id=str(uuid.uuid4()),
            symbol=symbol,
            side=tp_side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=take_profit,
            strategy=TradingStrategy.SCALPING,
            created_at=datetime.utcnow()
        )
        
        # Stop loss order
        sl_order = Order(
            order_id=str(uuid.uuid4()),
            symbol=symbol,
            side=tp_side,
            order_type=OrderType.STOP,
            quantity=quantity,
            stop_price=stop_loss,
            strategy=TradingStrategy.SCALPING,
            created_at=datetime.utcnow()
        )
        
        self.orders[tp_order.order_id] = tp_order
        self.orders[sl_order.order_id] = sl_order

# Global trading engine
trading_engine = TradingEngine()

# WebSocket manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_execution(self, execution: TradeExecution):
        message = {
            "type": "trade_execution",
            "data": execution.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message, default=str))
            except:
                pass

manager = ConnectionManager()

@app.get("/health")
async def health_check():
    return {
        "service": "hft-execution",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "trading_mode": "HIGH_FREQUENCY",
        "total_trades": trading_engine.total_trades,
        "daily_trades": trading_engine.day_trades_count,
        "active_positions": len(trading_engine.positions),
        "daily_pnl": round(trading_engine.daily_pnl, 2)
    }

@app.get("/account")
async def get_account_info():
    """Get account information"""
    positions_value = sum(pos.quantity * pos.current_price for pos in trading_engine.positions.values())
    
    return {
        "account_value": round(trading_engine.account_value + trading_engine.daily_pnl, 2),
        "buying_power": round(trading_engine.account_value * 4, 2),  # 4:1 day trading leverage
        "cash": round(trading_engine.account_value - positions_value, 2),
        "positions_value": round(positions_value, 2),
        "daily_pnl": round(trading_engine.daily_pnl, 2),
        "day_trades_used": trading_engine.day_trades_count,
        "day_trades_remaining": max(0, 3 - trading_engine.day_trades_count),  # PDT rule
        "total_commission": round(trading_engine.total_commission, 2),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/positions")
async def get_positions():
    """Get current positions"""
    return {
        "positions": [pos.dict() for pos in trading_engine.positions.values() if pos.quantity != 0],
        "count": len([pos for pos in trading_engine.positions.values() if pos.quantity != 0]),
        "total_unrealized_pnl": round(sum(pos.unrealized_pnl for pos in trading_engine.positions.values()), 2),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/orders")
async def get_orders(status: Optional[str] = None):
    """Get order history"""
    orders = list(trading_engine.orders.values())
    
    if status:
        orders = [order for order in orders if order.status.value == status.upper()]
    
    # Sort by creation time, most recent first
    orders.sort(key=lambda x: x.created_at, reverse=True)
    
    return {
        "orders": [order.dict() for order in orders[:50]],  # Last 50 orders
        "total_count": len(orders),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/executions")
async def get_executions(limit: int = 100):
    """Get recent trade executions"""
    recent_executions = sorted(trading_engine.executions, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    return {
        "executions": [exec.dict() for exec in recent_executions],
        "count": len(recent_executions),
        "total_executions": len(trading_engine.executions),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/orders/scalp")
async def create_scalping_order(
    symbol: str,
    current_price: float,
    signal_direction: str,  # BUY or SELL
    background_tasks: BackgroundTasks
):
    """Create rapid scalping order"""
    try:
        order = await trading_engine.place_scalping_order(symbol, current_price, signal_direction)
        
        # Broadcast execution
        if order.status == OrderStatus.FILLED:
            execution = next((e for e in trading_engine.executions if e.order_id == order.order_id), None)
            if execution:
                background_tasks.add_task(manager.broadcast_execution, execution)
        
        return {
            "success": True,
            "order": order.dict(),
            "message": f"Scalping order placed for {symbol}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/execute/signal")
async def execute_signal(
    symbol: str,
    signal: str,  # BUY, SELL, STRONG_BUY, STRONG_SELL
    confidence: float,
    urgency: str,
    entry_price: float,
    background_tasks: BackgroundTasks
):
    """Execute trading signal immediately"""
    try:
        # Only execute high-confidence signals
        if confidence < 70 or urgency not in ["HIGH", "CRITICAL"]:
            return {
                "success": False,
                "message": f"Signal not strong enough: {confidence}% confidence, {urgency} urgency",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Determine order parameters
        if signal in ["BUY", "STRONG_BUY"]:
            order = await trading_engine.place_scalping_order(symbol, entry_price, "BUY")
        elif signal in ["SELL", "STRONG_SELL"]:
            order = await trading_engine.place_scalping_order(symbol, entry_price, "SELL")
        else:
            return {
                "success": False,
                "message": f"Invalid signal: {signal}",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Broadcast execution
        if order.status == OrderStatus.FILLED:
            execution = next((e for e in trading_engine.executions if e.order_id == order.order_id), None)
            if execution:
                background_tasks.add_task(manager.broadcast_execution, execution)
        
        return {
            "success": True,
            "order": order.dict(),
            "execution_time_ms": 50,  # Simulate fast execution
            "message": f"Signal executed: {signal} {symbol} @ {entry_price}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/performance")
async def get_performance_metrics():
    """Get trading performance metrics"""
    total_pnl = trading_engine.daily_pnl
    winning_trades = len([e for e in trading_engine.executions if e.side == OrderSide.SELL])
    win_rate = (winning_trades / max(1, len(trading_engine.executions))) * 100
    
    return {
        "total_trades": trading_engine.total_trades,
        "day_trades": trading_engine.day_trades_count,
        "win_rate": round(win_rate, 1),
        "daily_pnl": round(total_pnl, 2),
        "total_commission": round(trading_engine.total_commission, 2),
        "net_pnl": round(total_pnl - trading_engine.total_commission, 2),
        "average_trade_size": round(sum(e.price * e.quantity for e in trading_engine.executions) / max(1, len(trading_engine.executions)), 2),
        "trades_per_hour": round(trading_engine.total_trades / max(1, (datetime.utcnow().hour or 1)), 1),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.websocket("/ws/executions")
async def websocket_executions(websocket: WebSocket):
    """Real-time trade execution stream"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Send heartbeat
            await websocket.send_text(json.dumps({
                "type": "heartbeat",
                "active_orders": len([o for o in trading_engine.orders.values() if o.status == OrderStatus.PENDING]),
                "positions": len(trading_engine.positions),
                "timestamp": datetime.utcnow().isoformat()
            }))
            
            await asyncio.sleep(10)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background task to simulate market movements and trigger stops
@app.on_event("startup")
async def startup_event():
    async def market_simulation():
        while True:
            # Update position prices
            for position in trading_engine.positions.values():
                # Simulate price movement
                change = random.gauss(0, 0.01)  # 1% volatility
                new_price = position.current_price * (1 + change)
                position.current_price = max(0.01, new_price)
                
                # Update unrealized P&L
                position.unrealized_pnl = position.quantity * (position.current_price - position.avg_price)
            
            # Check for stop orders to trigger
            for order in trading_engine.orders.values():
                if order.status == OrderStatus.PENDING and order.order_type in [OrderType.STOP, OrderType.LIMIT]:
                    # Simulate order triggering
                    if random.random() < 0.1:  # 10% chance per cycle
                        await trading_engine.execute_market_order(order)
            
            await asyncio.sleep(5)  # Update every 5 seconds
    
    asyncio.create_task(market_simulation())

if __name__ == "__main__":
    uvicorn.run("hft_service:app", host="127.0.0.1", port=9002, reload=True)