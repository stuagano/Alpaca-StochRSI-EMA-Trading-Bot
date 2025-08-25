#!/usr/bin/env python3
"""
High-Frequency Crypto Day Trading Service
Microservice for rapid crypto trading with volatility-based strategies
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import websockets
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import numpy as np
import pandas as pd
from contextlib import asynccontextmanager
import httpx
import os
import sys

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from strategies.crypto_scalping_strategy import CryptoDayTradingBot, CryptoVolatilityScanner

# Mock data manager for standalone operation
class MockDataManager:
    def __init__(self):
        self.api = MockAlpacaAPI()

class MockAlpacaAPI:
    def submit_order(self, **kwargs):
        return {'id': f'order_mock_{int(time.time())}', 'status': 'filled'}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
day_trading_bot: Optional[CryptoDayTradingBot] = None
scanner: Optional[CryptoVolatilityScanner] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global day_trading_bot, scanner
    
    logger.info("🚀 Starting Crypto Day Trading Service")
    
    try:
        # Initialize components
        data_manager = MockDataManager()
        scanner = CryptoVolatilityScanner()
        
        # Create day trading bot
        config = {
            'crypto_capital': 25000,  # $25k for crypto day trading
            'max_position_size': 1250,  # $1250 per trade (5%)
            'max_positions': 15,       # Up to 15 concurrent positions
            'min_profit': 0.0025,      # 0.25% minimum profit target
            'max_daily_loss': 500      # $500 max daily loss
        }
        
        day_trading_bot = CryptoDayTradingBot(data_manager.api, config['crypto_capital'])
        day_trading_bot.max_position_size = config['max_position_size']
        day_trading_bot.max_concurrent_positions = config['max_positions']
        day_trading_bot.min_profit_target = config['min_profit']
        day_trading_bot.max_daily_loss = config['max_daily_loss']
        
        # Start the bot in background
        asyncio.create_task(day_trading_bot.start_trading())
        
        logger.info("✅ Crypto Day Trading Service initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        day_trading_bot = None
        scanner = None
    
    yield
    
    # Shutdown
    if day_trading_bot:
        day_trading_bot.stop()
    logger.info("🛑 Crypto Day Trading Service stopped")

# Create FastAPI app
app = FastAPI(
    title="Crypto Day Trading Service",
    description="High-frequency crypto trading with volatility-based strategies",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class TradingConfig(BaseModel):
    max_position_size: float = 1250
    max_positions: int = 15
    min_profit: float = 0.0025
    max_daily_loss: float = 500
    enable_trading: bool = True

class MarketScanRequest(BaseModel):
    symbols: Optional[List[str]] = None
    min_volatility: float = 0.02
    min_volume: float = 10000000

class OrderRequest(BaseModel):
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    order_type: str = 'market'

# Health check
@app.get("/health")
async def health_check():
    """Service health check"""
    global day_trading_bot
    
    status = "healthy" if day_trading_bot and day_trading_bot.is_running else "degraded"
    
    return {
        "service": "crypto-day-trading",
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "bot_running": day_trading_bot.is_running if day_trading_bot else False,
        "active_positions": len(day_trading_bot.active_positions) if day_trading_bot else 0
    }

# Trading Status
@app.get("/api/status")
async def get_trading_status():
    """Get current trading status"""
    if not day_trading_bot:
        raise HTTPException(status_code=503, detail="Trading bot not initialized")
    
    status = day_trading_bot.get_status()
    
    # Add scanner info
    if scanner:
        with scanner.lock:
            scanner_info = {
                'tracked_symbols': len(scanner.price_data),
                'data_points': sum(len(prices) for prices in scanner.price_data.values()),
                'last_scan': datetime.now().isoformat()
            }
            status['scanner'] = scanner_info
    
    return status

# Get Active Positions
@app.get("/api/positions")
async def get_active_positions():
    """Get all active trading positions"""
    if not day_trading_bot:
        raise HTTPException(status_code=503, detail="Trading bot not initialized")
    
    positions = []
    for symbol, position in day_trading_bot.active_positions.items():
        # Get current price
        current_price = await day_trading_bot._get_current_price(symbol)
        
        # Calculate current P&L
        entry_price = position['entry_price']
        side = position['side']
        
        if current_price:
            if side == 'buy':
                pnl_pct = (current_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - current_price) / entry_price
            
            pnl_dollar = position['quantity'] * entry_price * pnl_pct
        else:
            pnl_pct = 0.0
            pnl_dollar = 0.0
        
        positions.append({
            'symbol': symbol,
            'side': side,
            'quantity': position['quantity'],
            'entry_price': entry_price,
            'current_price': current_price,
            'target_price': position['target_price'],
            'stop_price': position['stop_price'],
            'pnl_percent': pnl_pct,
            'pnl_dollar': pnl_dollar,
            'entry_time': position['entry_time'].isoformat(),
            'hold_time_minutes': (datetime.now() - position['entry_time']).seconds // 60,
            'confidence': position['signal'].confidence
        })
    
    return {
        'positions': positions,
        'total_positions': len(positions),
        'total_value': sum(p['quantity'] * p['entry_price'] for p in positions),
        'total_pnl': sum(p['pnl_dollar'] for p in positions)
    }

# Market Scan
@app.post("/api/scan")
async def scan_market(request: MarketScanRequest):
    """Scan for high-volatility trading opportunities"""
    if not scanner:
        raise HTTPException(status_code=503, detail="Market scanner not initialized")
    
    # Update scanner criteria
    scanner.min_volatility = request.min_volatility
    scanner.min_24h_volume = request.min_volume
    
    if request.symbols:
        # Temporarily scan specific symbols
        original_pairs = scanner.high_volume_pairs
        scanner.high_volume_pairs = request.symbols
        signals = scanner.scan_for_opportunities()
        scanner.high_volume_pairs = original_pairs
    else:
        signals = scanner.scan_for_opportunities()
    
    # Convert signals to dict format
    opportunities = []
    for signal in signals:
        opportunities.append({
            'symbol': signal.symbol,
            'action': signal.action,
            'confidence': signal.confidence,
            'price': signal.price,
            'volatility': signal.volatility,
            'volume_surge': signal.volume_surge,
            'momentum': signal.momentum,
            'target_profit': signal.target_profit,
            'stop_loss': signal.stop_loss,
            'timestamp': signal.timestamp.isoformat()
        })
    
    return {
        'opportunities': opportunities,
        'scan_time': datetime.now().isoformat(),
        'criteria': {
            'min_volatility': request.min_volatility,
            'min_volume': request.min_volume
        }
    }

# Manual Order Execution
@app.post("/api/orders")
async def place_manual_order(order: OrderRequest):
    """Place a manual crypto order"""
    if not day_trading_bot:
        raise HTTPException(status_code=503, detail="Trading bot not initialized")
    
    try:
        # Get current price for position sizing
        current_price = await day_trading_bot._get_current_price(order.symbol)
        if not current_price:
            raise HTTPException(status_code=400, detail=f"Cannot get price for {order.symbol}")
        
        # Validate order
        if order.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be positive")
        
        position_value = order.quantity * current_price
        if position_value > day_trading_bot.max_position_size:
            raise HTTPException(status_code=400, detail="Position size exceeds maximum")
        
        # Place order
        result = await day_trading_bot._place_crypto_order(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            order_type=order.order_type
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Order placement failed")
        
        return {
            'success': True,
            'order_id': result.get('id'),
            'symbol': order.symbol,
            'side': order.side,
            'quantity': order.quantity,
            'estimated_value': position_value,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Manual order error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Configuration
@app.post("/api/config")
async def update_config(config: TradingConfig):
    """Update trading configuration"""
    if not day_trading_bot:
        raise HTTPException(status_code=503, detail="Trading bot not initialized")
    
    # Update bot configuration
    day_trading_bot.max_position_size = config.max_position_size
    day_trading_bot.max_concurrent_positions = config.max_positions
    day_trading_bot.min_profit_target = config.min_profit
    day_trading_bot.max_daily_loss = config.max_daily_loss
    
    # Stop/start trading based on enable flag
    if config.enable_trading and not day_trading_bot.is_running:
        asyncio.create_task(day_trading_bot.start_trading())
    elif not config.enable_trading and day_trading_bot.is_running:
        day_trading_bot.is_running = False
    
    return {
        'success': True,
        'config': config.dict(),
        'updated_at': datetime.now().isoformat()
    }

@app.get("/api/config")
async def get_config():
    """Get current trading configuration"""
    if not day_trading_bot:
        raise HTTPException(status_code=503, detail="Trading bot not initialized")
    
    return {
        'max_position_size': day_trading_bot.max_position_size,
        'max_positions': day_trading_bot.max_concurrent_positions,
        'min_profit': day_trading_bot.min_profit_target,
        'max_daily_loss': day_trading_bot.max_daily_loss,
        'enable_trading': day_trading_bot.is_running
    }

# Performance Metrics
@app.get("/api/metrics")
async def get_performance_metrics():
    """Get detailed performance metrics"""
    if not day_trading_bot:
        raise HTTPException(status_code=503, detail="Trading bot not initialized")
    
    # Calculate additional metrics
    total_capital = day_trading_bot.initial_capital
    current_capital = total_capital + day_trading_bot.daily_profit
    
    # Position analysis
    position_analysis = {
        'total_positions': len(day_trading_bot.active_positions),
        'capital_deployed': sum(
            pos['quantity'] * pos['entry_price'] 
            for pos in day_trading_bot.active_positions.values()
        ),
        'avg_hold_time_minutes': 0,
        'profitable_positions': 0
    }
    
    if day_trading_bot.active_positions:
        hold_times = []
        profitable = 0
        
        for pos in day_trading_bot.active_positions.values():
            hold_time = (datetime.now() - pos['entry_time']).seconds / 60
            hold_times.append(hold_time)
            
            # Check if position is currently profitable
            current_price = scanner.price_data.get(pos['signal'].symbol, [0])[-1] if scanner else 0
            if current_price:
                if pos['side'] == 'buy' and current_price > pos['entry_price']:
                    profitable += 1
                elif pos['side'] == 'sell' and current_price < pos['entry_price']:
                    profitable += 1
        
        position_analysis['avg_hold_time_minutes'] = np.mean(hold_times)
        position_analysis['profitable_positions'] = profitable
    
    return {
        'daily_metrics': {
            'profit_loss': day_trading_bot.daily_profit,
            'trades_today': day_trading_bot.daily_trades,
            'win_rate': day_trading_bot.win_rate,
            'total_trades': day_trading_bot.total_trades,
            'capital_utilization': position_analysis['capital_deployed'] / total_capital
        },
        'position_analysis': position_analysis,
        'risk_metrics': {
            'max_daily_loss_limit': day_trading_bot.max_daily_loss,
            'remaining_risk_budget': day_trading_bot.max_daily_loss - abs(day_trading_bot.daily_profit),
            'largest_position_size': max(
                [pos['quantity'] * pos['entry_price'] for pos in day_trading_bot.active_positions.values()],
                default=0
            ),
            'current_exposure': (position_analysis['capital_deployed'] / total_capital) * 100
        },
        'timestamp': datetime.now().isoformat()
    }

# WebSocket for real-time updates
@app.websocket("/ws/trading")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time trading updates"""
    await websocket.accept()
    
    try:
        while True:
            if day_trading_bot:
                # Send current status
                status = day_trading_bot.get_status()
                status['timestamp'] = datetime.now().isoformat()
                
                # Add position details
                positions = []
                for symbol, position in day_trading_bot.active_positions.items():
                    current_price = await day_trading_bot._get_current_price(symbol)
                    if current_price:
                        entry_price = position['entry_price']
                        side = position['side']
                        
                        if side == 'buy':
                            pnl_pct = (current_price - entry_price) / entry_price
                        else:
                            pnl_pct = (entry_price - current_price) / entry_price
                        
                        positions.append({
                            'symbol': symbol,
                            'side': side,
                            'pnl_percent': pnl_pct,
                            'current_price': current_price,
                            'entry_price': entry_price
                        })
                
                status['position_details'] = positions
                
                await websocket.send_text(json.dumps(status))
            
            await asyncio.sleep(2)  # Update every 2 seconds
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        "daytrading_service:app",
        host="0.0.0.0", 
        port=9012,
        reload=False,
        log_level="info"
    )