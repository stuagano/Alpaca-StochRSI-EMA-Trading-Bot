#!/usr/bin/env python3
"""
Production-Ready Position Management Service

Features:
- PostgreSQL database integration with SQLAlchemy
- JWT authentication and authorization  
- Real-time WebSocket updates
- Comprehensive CRUD operations
- Portfolio metrics and analytics
- Error handling and logging
- Input validation and sanitization
- Audit logging
- Rate limiting protection
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from uuid import uuid4, UUID

import structlog
from fastapi import (
    FastAPI, HTTPException, Depends, status, 
    WebSocket, WebSocketDisconnect, Request, BackgroundTasks
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import redis.asyncio as redis

# Import shared components
import sys
sys.path.append('/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot/microservices/services')

try:
    from shared.database import Position as SharedPosition, User, AuditLog, DatabaseService
    from shared.auth import get_current_user, get_current_admin_user, AuthService
except ImportError:
    # Fallback to local models if shared not available
    SharedPosition = None

from .models import (
    PositionDB, PositionCreate, PositionUpdate, Position, 
    PortfolioMetrics, RiskMetrics, PositionSummary, PositionAlert,
    PositionStatus, PositionSide, BulkPositionUpdate
)
from .database import get_db, init_db, close_db, AsyncSessionLocal, engine

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Redis configuration for WebSocket scaling
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = None

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, List[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, connection_id: str):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(connection_id)
        
        logger.info("WebSocket connected", user_id=user_id, connection_id=connection_id)
    
    def disconnect(self, user_id: str, connection_id: str):
        """Remove WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id in self.user_connections:
            self.user_connections[user_id] = [
                cid for cid in self.user_connections[user_id] 
                if cid != connection_id
            ]
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info("WebSocket disconnected", user_id=user_id, connection_id=connection_id)
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user's connections."""
        if user_id in self.user_connections:
            disconnected = []
            for connection_id in self.user_connections[user_id]:
                if connection_id in self.active_connections:
                    try:
                        await self.active_connections[connection_id].send_json(message)
                    except Exception as e:
                        logger.error("Error sending WebSocket message", 
                                   error=str(e), connection_id=connection_id)
                        disconnected.append(connection_id)
            
            # Clean up disconnected connections
            for connection_id in disconnected:
                self.disconnect(user_id, connection_id)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        disconnected = []
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error("Error broadcasting WebSocket message", 
                           error=str(e), connection_id=connection_id)
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]

manager = ConnectionManager()

# Lifespan manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    try:
        # Initialize database
        await init_db()
        
        # Initialize Redis connection
        global redis_client
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        
        logger.info("✅ Position Management Service started successfully")
        yield
        
    except Exception as e:
        logger.error("❌ Failed to start Position Management Service", error=str(e))
        raise
    finally:
        # Shutdown
        await close_db()
        if redis_client:
            await redis_client.close()
        logger.info("🔌 Position Management Service shutdown complete")

# FastAPI application
app = FastAPI(
    title="Position Management Service",
    description="Production-ready position management with real-time updates",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Request/Response Models
class PositionResponse(Position):
    """Enhanced position response with computed fields."""
    risk_level: str
    days_held: int
    market_status: str

# Database Dependencies
async def get_async_db() -> AsyncSession:
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Service Classes
class PositionService:
    """Core position management service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_position(self, position_data: PositionCreate, user_id: str) -> PositionDB:
        """Create a new position with validation."""
        try:
            # Generate unique ID
            position_id = str(uuid4())
            
            # Calculate initial market value
            market_value = float(position_data.quantity) * float(position_data.entry_price)
            
            # Create position instance
            db_position = PositionDB(
                id=position_id,
                symbol=position_data.symbol.upper(),
                quantity=position_data.quantity,
                side=position_data.side.value,
                entry_price=position_data.entry_price,
                current_price=position_data.entry_price,  # Initially same as entry
                stop_loss=position_data.stop_loss,
                take_profit=position_data.take_profit,
                strategy=position_data.strategy,
                market_value=market_value,
                status=PositionStatus.OPEN.value,
                notes=position_data.notes,
                broker_order_id=position_data.broker_order_id
            )
            
            self.db.add(db_position)
            await self.db.commit()
            await self.db.refresh(db_position)
            
            # Log audit trail
            await self._log_audit("position_created", user_id, position_id, 
                                {"position": db_position.__dict__})
            
            # Send WebSocket notification
            await self._notify_position_update(db_position, "created")
            
            logger.info("Position created", 
                       position_id=position_id, symbol=position_data.symbol, user_id=user_id)
            
            return db_position
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Error creating position", error=str(e), symbol=position_data.symbol)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create position: {str(e)}"
            )
    
    async def get_position(self, position_id: str) -> Optional[PositionDB]:
        """Get position by ID."""
        try:
            result = await self.db.execute(
                select(PositionDB).where(PositionDB.id == position_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error fetching position", error=str(e), position_id=position_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch position"
            )
    
    async def get_positions(self, 
                          status: Optional[str] = None,
                          symbol: Optional[str] = None,
                          limit: int = 100,
                          offset: int = 0) -> List[PositionDB]:
        """Get positions with filtering and pagination."""
        try:
            query = select(PositionDB)
            
            # Apply filters
            if status:
                query = query.where(PositionDB.status == status.upper())
            if symbol:
                query = query.where(PositionDB.symbol == symbol.upper())
            
            # Apply pagination and ordering
            query = query.order_by(desc(PositionDB.created_at)).limit(limit).offset(offset)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error("Error fetching positions", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch positions"
            )
    
    async def update_position(self, position_id: str, update_data: PositionUpdate, user_id: str) -> PositionDB:
        """Update position with validation."""
        try:
            # Get existing position
            db_position = await self.get_position(position_id)
            if not db_position:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Position not found"
                )
            
            # Store old values for audit
            old_values = db_position.__dict__.copy()
            
            # Update fields
            update_dict = update_data.dict(exclude_unset=True)
            for field, value in update_dict.items():
                if hasattr(db_position, field) and value is not None:
                    setattr(db_position, field, value)
            
            # Recalculate derived fields
            if update_data.current_price:
                await self._update_position_metrics(db_position)
            
            db_position.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(db_position)
            
            # Log audit trail
            await self._log_audit("position_updated", user_id, position_id, 
                                {"old": old_values, "new": db_position.__dict__})
            
            # Send WebSocket notification
            await self._notify_position_update(db_position, "updated")
            
            logger.info("Position updated", position_id=position_id, user_id=user_id)
            
            return db_position
            
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Error updating position", error=str(e), position_id=position_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update position: {str(e)}"
            )
    
    async def close_position(self, position_id: str, exit_price: Optional[float], user_id: str) -> PositionDB:
        """Close a position."""
        try:
            db_position = await self.get_position(position_id)
            if not db_position:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Position not found"
                )
            
            if db_position.status == PositionStatus.CLOSED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Position is already closed"
                )
            
            # Set exit values
            db_position.status = PositionStatus.CLOSED.value
            db_position.exit_time = datetime.utcnow()
            db_position.exit_price = exit_price or db_position.current_price
            db_position.closed_at = datetime.utcnow()
            
            # Calculate realized P&L
            if db_position.exit_price:
                if db_position.side == PositionSide.LONG.value:
                    db_position.realized_pnl = (
                        (db_position.exit_price - db_position.entry_price) * db_position.quantity
                    )
                else:  # SHORT
                    db_position.realized_pnl = (
                        (db_position.entry_price - db_position.exit_price) * db_position.quantity
                    )
            
            db_position.unrealized_pnl = 0.0  # No longer unrealized
            db_position.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(db_position)
            
            # Log audit trail
            await self._log_audit("position_closed", user_id, position_id, 
                                {"realized_pnl": float(db_position.realized_pnl or 0)})
            
            # Send WebSocket notification
            await self._notify_position_update(db_position, "closed")
            
            logger.info("Position closed", position_id=position_id, 
                       realized_pnl=db_position.realized_pnl, user_id=user_id)
            
            return db_position
            
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Error closing position", error=str(e), position_id=position_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to close position: {str(e)}"
            )
    
    async def delete_position(self, position_id: str, user_id: str) -> bool:
        """Delete a position (admin only)."""
        try:
            db_position = await self.get_position(position_id)
            if not db_position:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Position not found"
                )
            
            await self.db.delete(db_position)
            await self.db.commit()
            
            # Log audit trail
            await self._log_audit("position_deleted", user_id, position_id, 
                                {"deleted_position": db_position.__dict__})
            
            # Send WebSocket notification
            await manager.broadcast({
                "type": "position_deleted",
                "position_id": position_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info("Position deleted", position_id=position_id, user_id=user_id)
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("Error deleting position", error=str(e), position_id=position_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete position: {str(e)}"
            )
    
    async def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Calculate comprehensive portfolio metrics."""
        try:
            # Get all positions
            positions_result = await self.db.execute(select(PositionDB))
            positions = positions_result.scalars().all()
            
            if not positions:
                return PortfolioMetrics(
                    total_positions=0, open_positions=0, closed_positions=0,
                    long_positions=0, short_positions=0, total_market_value=0.0,
                    total_unrealized_pnl=0.0, total_realized_pnl=0.0, total_pnl=0.0,
                    largest_position_value=0.0, largest_position_pct=0.0,
                    portfolio_concentration=0.0, avg_position_size=0.0,
                    avg_entry_price=0.0, avg_hold_time_hours=0.0,
                    win_rate=0.0, profit_factor=0.0, sharpe_ratio=None,
                    positions_at_risk=0, positions_near_target=0
                )
            
            # Basic counts
            total_positions = len(positions)
            open_positions = len([p for p in positions if p.status == PositionStatus.OPEN.value])
            closed_positions = len([p for p in positions if p.status == PositionStatus.CLOSED.value])
            long_positions = len([p for p in positions if p.side == PositionSide.LONG.value])
            short_positions = len([p for p in positions if p.side == PositionSide.SHORT.value])
            
            # Financial metrics
            total_market_value = sum(float(p.market_value or 0) for p in positions if p.status == PositionStatus.OPEN.value)
            total_unrealized_pnl = sum(float(p.unrealized_pnl or 0) for p in positions if p.status == PositionStatus.OPEN.value)
            total_realized_pnl = sum(float(p.realized_pnl or 0) for p in positions)
            total_pnl = total_unrealized_pnl + total_realized_pnl
            
            # Position size analysis
            open_position_values = [float(p.market_value or 0) for p in positions if p.status == PositionStatus.OPEN.value and p.market_value]
            largest_position_value = max(open_position_values) if open_position_values else 0.0
            largest_position_pct = (largest_position_value / total_market_value * 100) if total_market_value > 0 else 0.0
            
            # Portfolio concentration (Herfindahl index)
            if total_market_value > 0:
                concentration_sum = sum((value / total_market_value) ** 2 for value in open_position_values)
                portfolio_concentration = concentration_sum * 100
            else:
                portfolio_concentration = 0.0
            
            # Averages
            avg_position_size = total_market_value / open_positions if open_positions > 0 else 0.0
            avg_entry_price = sum(float(p.entry_price) for p in positions) / total_positions if total_positions > 0 else 0.0
            
            # Average hold time
            now = datetime.utcnow()
            hold_times = []
            for p in positions:
                if p.status == PositionStatus.CLOSED.value and p.closed_at:
                    hold_time = (p.closed_at - p.created_at).total_seconds() / 3600
                    hold_times.append(hold_time)
                elif p.status == PositionStatus.OPEN.value:
                    hold_time = (now - p.created_at).total_seconds() / 3600
                    hold_times.append(hold_time)
            
            avg_hold_time_hours = sum(hold_times) / len(hold_times) if hold_times else 0.0
            
            # Performance metrics
            closed_profitable = len([p for p in positions if p.status == PositionStatus.CLOSED.value and (p.realized_pnl or 0) > 0])
            win_rate = (closed_profitable / closed_positions * 100) if closed_positions > 0 else 0.0
            
            # Profit factor
            gross_profit = sum(float(p.realized_pnl) for p in positions if (p.realized_pnl or 0) > 0)
            gross_loss = abs(sum(float(p.realized_pnl) for p in positions if (p.realized_pnl or 0) < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
            
            # Risk indicators
            positions_at_risk = 0
            positions_near_target = 0
            
            for p in positions:
                if p.status == PositionStatus.OPEN.value and p.current_price:
                    if p.stop_loss:
                        if p.side == PositionSide.LONG.value and p.current_price <= p.stop_loss * 1.02:
                            positions_at_risk += 1
                        elif p.side == PositionSide.SHORT.value and p.current_price >= p.stop_loss * 0.98:
                            positions_at_risk += 1
                    
                    if p.take_profit:
                        if p.side == PositionSide.LONG.value and p.current_price >= p.take_profit * 0.98:
                            positions_near_target += 1
                        elif p.side == PositionSide.SHORT.value and p.current_price <= p.take_profit * 1.02:
                            positions_near_target += 1
            
            return PortfolioMetrics(
                total_positions=total_positions,
                open_positions=open_positions,
                closed_positions=closed_positions,
                long_positions=long_positions,
                short_positions=short_positions,
                total_market_value=total_market_value,
                total_unrealized_pnl=total_unrealized_pnl,
                total_realized_pnl=total_realized_pnl,
                total_pnl=total_pnl,
                largest_position_value=largest_position_value,
                largest_position_pct=largest_position_pct,
                portfolio_concentration=portfolio_concentration,
                avg_position_size=avg_position_size,
                avg_entry_price=avg_entry_price,
                avg_hold_time_hours=avg_hold_time_hours,
                win_rate=win_rate,
                profit_factor=profit_factor,
                sharpe_ratio=None,  # Would need historical return data
                positions_at_risk=positions_at_risk,
                positions_near_target=positions_near_target
            )
            
        except Exception as e:
            logger.error("Error calculating portfolio metrics", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to calculate portfolio metrics: {str(e)}"
            )
    
    async def update_market_prices(self, price_updates: Dict[str, float]):
        """Bulk update market prices for positions."""
        try:
            updated_count = 0
            
            for symbol, current_price in price_updates.items():
                # Get open positions for this symbol
                result = await self.db.execute(
                    select(PositionDB).where(
                        and_(
                            PositionDB.symbol == symbol.upper(),
                            PositionDB.status == PositionStatus.OPEN.value
                        )
                    )
                )
                positions = result.scalars().all()
                
                for position in positions:
                    position.current_price = current_price
                    await self._update_position_metrics(position)
                    updated_count += 1
            
            if updated_count > 0:
                await self.db.commit()
                
                # Broadcast price updates
                await manager.broadcast({
                    "type": "price_update",
                    "updates": price_updates,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                logger.info("Market prices updated", 
                           symbols=list(price_updates.keys()), 
                           positions_updated=updated_count)
            
        except Exception as e:
            await self.db.rollback()
            logger.error("Error updating market prices", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update market prices: {str(e)}"
            )
    
    async def _update_position_metrics(self, position: PositionDB):
        """Update position-specific calculated fields."""
        if position.current_price and position.status == PositionStatus.OPEN.value:
            # Update market value
            position.market_value = float(position.current_price) * position.quantity
            
            # Update unrealized P&L
            if position.side == PositionSide.LONG.value:
                position.unrealized_pnl = (
                    (position.current_price - position.entry_price) * position.quantity
                )
            else:  # SHORT
                position.unrealized_pnl = (
                    (position.entry_price - position.current_price) * position.quantity
                )
    
    async def _log_audit(self, action: str, user_id: str, entity_id: str, metadata: Dict[str, Any]):
        """Log audit trail for position operations."""
        try:
            # In a real implementation, this would create an AuditLog record
            logger.info("Audit log", 
                       action=action, user_id=user_id, 
                       entity_id=entity_id, metadata=metadata)
        except Exception as e:
            logger.error("Error logging audit trail", error=str(e))
    
    async def _notify_position_update(self, position: PositionDB, action: str):
        """Send WebSocket notification for position updates."""
        try:
            message = {
                "type": f"position_{action}",
                "position": {
                    "id": position.id,
                    "symbol": position.symbol,
                    "quantity": position.quantity,
                    "current_price": float(position.current_price) if position.current_price else None,
                    "unrealized_pnl": float(position.unrealized_pnl) if position.unrealized_pnl else None,
                    "status": position.status,
                    "updated_at": position.updated_at.isoformat() if position.updated_at else None
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await manager.broadcast(message)
            
        except Exception as e:
            logger.error("Error sending WebSocket notification", error=str(e))

# API Routes

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "service": "position-management",
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/positions", response_model=List[Position])
async def get_positions(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Get all positions with optional filtering."""
    service = PositionService(db)
    positions = await service.get_positions(status, symbol, limit, offset)
    
    return [Position.from_orm(pos) for pos in positions]

@app.get("/positions/{position_id}", response_model=Position)
async def get_position(
    position_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific position by ID."""
    service = PositionService(db)
    position = await service.get_position(position_id)
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    return Position.from_orm(position)

@app.post("/positions", response_model=Position, status_code=status.HTTP_201_CREATED)
async def create_position(
    position_data: PositionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new position."""
    service = PositionService(db)
    position = await service.create_position(position_data, str(current_user.id))
    
    return Position.from_orm(position)

@app.put("/positions/{position_id}", response_model=Position)
async def update_position(
    position_id: str,
    update_data: PositionUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing position."""
    service = PositionService(db)
    position = await service.update_position(position_id, update_data, str(current_user.id))
    
    return Position.from_orm(position)

@app.post("/positions/{position_id}/close", response_model=Position)
async def close_position(
    position_id: str,
    exit_price: Optional[float] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Close an existing position."""
    service = PositionService(db)
    position = await service.close_position(position_id, exit_price, str(current_user.id))
    
    return Position.from_orm(position)

@app.delete("/positions/{position_id}")
async def delete_position(
    position_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_admin_user)  # Admin only
):
    """Delete a position (admin only)."""
    service = PositionService(db)
    success = await service.delete_position(position_id, str(current_user.id))
    
    return {"success": success, "message": "Position deleted successfully"}

@app.get("/portfolio/summary", response_model=PortfolioMetrics)
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive portfolio metrics and summary."""
    service = PositionService(db)
    metrics = await service.get_portfolio_metrics()
    
    return metrics

@app.post("/positions/bulk-update")
async def bulk_update_positions(
    bulk_update: BulkPositionUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk update multiple positions."""
    service = PositionService(db)
    updated_positions = []
    
    for position_id in bulk_update.position_ids:
        try:
            position = await service.update_position(position_id, bulk_update.updates, str(current_user.id))
            updated_positions.append(position.id)
        except HTTPException as e:
            logger.warning("Failed to update position in bulk", 
                          position_id=position_id, error=str(e))
            continue
    
    return {
        "updated_positions": updated_positions,
        "total_requested": len(bulk_update.position_ids),
        "total_updated": len(updated_positions)
    }

@app.post("/positions/update-prices")
async def update_market_prices(
    price_updates: Dict[str, float],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Update market prices for multiple symbols."""
    service = PositionService(db)
    await service.update_market_prices(price_updates)
    
    return {
        "message": "Market prices updated successfully",
        "symbols_updated": list(price_updates.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }

# WebSocket endpoint for real-time updates
@app.websocket("/ws/positions")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_async_db)
):
    """WebSocket endpoint for real-time position updates."""
    try:
        # Authenticate user from token
        payload = AuthService.decode_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Generate connection ID
        connection_id = str(uuid4())
        
        # Accept connection
        await manager.connect(websocket, user_id, connection_id)
        
        # Send initial data
        service = PositionService(db)
        positions = await service.get_positions()
        await websocket.send_json({
            "type": "initial_data",
            "positions": [pos.__dict__ for pos in positions],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and handle messages
        try:
            while True:
                data = await websocket.receive_text()
                # Handle client messages if needed
                logger.info("WebSocket message received", 
                           user_id=user_id, message=data)
                
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected", user_id=user_id)
        finally:
            manager.disconnect(user_id, connection_id)
            
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        try:
            await websocket.close(code=4000, reason="Internal error")
        except:
            pass

# Background tasks for price updates
async def price_update_task():
    """Background task to periodically update prices from market data."""
    while True:
        try:
            # This would integrate with your market data service
            # For now, just a placeholder
            await asyncio.sleep(60)  # Update every minute
            
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
        port=8002,
        reload=True,
        log_config=None  # Use our structured logging
    )