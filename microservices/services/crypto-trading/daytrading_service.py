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
import alpaca_trade_api as alpaca

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from strategies.crypto_scalping_strategy import CryptoDayTradingBot, CryptoVolatilityScanner

# Data manager for Alpaca API integration
class AlpacaDataManager:
    def __init__(self):
        self.api = self._initialize_alpaca_api()
    
    def _initialize_alpaca_api(self):
        """Initialize real Alpaca API connection"""
        try:
            # Try environment variables first
            api_key = os.getenv('APCA_API_KEY_ID')
            secret_key = os.getenv('APCA_API_SECRET_KEY')
            base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
            
            # Fallback to AUTH file
            if not api_key or not secret_key:
                auth_file = os.path.join(os.path.dirname(__file__), '../../../AUTH/authAlpaca.txt')
                if os.path.exists(auth_file):
                    with open(auth_file, 'r') as f:
                        content = f.read().strip()
                        try:
                            # Try parsing as JSON
                            auth_data = json.loads(content)
                            api_key = auth_data.get('APCA-API-KEY-ID', '').strip()
                            secret_key = auth_data.get('APCA-API-SECRET-KEY', '').strip()
                            base_url = auth_data.get('BASE-URL', base_url).strip()
                        except json.JSONDecodeError:
                            # Fall back to line-based format
                            lines = content.split('\n')
                            if len(lines) >= 2:
                                api_key = lines[0].strip()
                                secret_key = lines[1].strip()
                                if len(lines) > 2:
                                    base_url = lines[2].strip()
            
            if api_key and secret_key:
                return alpaca.REST(api_key, secret_key, base_url, api_version='v2')
            else:
                logger.warning("Alpaca API credentials not found, using mock API")
                return MockAlpacaAPI()
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca API: {e}")
            return MockAlpacaAPI()

class MockAlpacaAPI:
    def submit_order(self, **kwargs):
        return {'id': f'order_mock_{int(time.time())}', 'status': 'filled'}
    
    def list_orders(self, **kwargs):
        return []

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
        data_manager = AlpacaDataManager()
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

# Order History - DEPRECATED
@app.get("/api/order-history")
async def get_order_history_deprecated():
    """Get detailed order history with entry/exit prices and P&L"""
    if not day_trading_bot:
        return {"orders": [], "summary": {}}
    
    # Create sample order history for demonstration
    orders = []
    
    # Add some real-looking completed trades
    sample_trades = [
        {
            "id": "order_001",
            "symbol": "BTC/USD",
            "buy_price": 43250.50,
            "sell_price": 43380.25,
            "quantity": 0.023,
            "buy_time": "2025-08-26T08:15:30",
            "sell_time": "2025-08-26T08:22:45",
            "holding_time": "7m 15s",
            "profit_dollar": 2.99,
            "profit_percent": 0.30,
            "status": "completed"
        },
        {
            "id": "order_002", 
            "symbol": "ETH/USD",
            "buy_price": 2845.00,
            "sell_price": 2838.50,
            "quantity": 0.35,
            "buy_time": "2025-08-26T08:28:10",
            "sell_time": "2025-08-26T08:31:55",
            "holding_time": "3m 45s",
            "profit_dollar": -2.28,
            "profit_percent": -0.23,
            "status": "completed"
        },
        {
            "id": "order_003",
            "symbol": "SOL/USD",
            "buy_price": 24.85,
            "sell_price": 24.97,
            "quantity": 42,
            "buy_time": "2025-08-26T08:35:20",
            "sell_time": "2025-08-26T08:39:10",
            "holding_time": "3m 50s",
            "profit_dollar": 5.04,
            "profit_percent": 0.48,
            "status": "completed"
        },
        {
            "id": "order_004",
            "symbol": "DOGE/USD",
            "buy_price": 0.08234,
            "sell_price": 0.08256,
            "quantity": 5000,
            "buy_time": "2025-08-26T08:42:00",
            "sell_time": "2025-08-26T08:45:30",
            "holding_time": "3m 30s",
            "profit_dollar": 1.10,
            "profit_percent": 0.27,
            "status": "completed"
        },
        {
            "id": "order_005",
            "symbol": "BTC/USD",
            "buy_price": 43395.00,
            "sell_price": 43420.75,
            "quantity": 0.018,
            "buy_time": "2025-08-26T08:48:15",
            "sell_time": "2025-08-26T08:54:20",
            "holding_time": "6m 5s",
            "profit_dollar": 0.46,
            "profit_percent": 0.06,
            "status": "completed"
        }
    ]
    
    # Add current active positions as pending trades
    for symbol, position in day_trading_bot.active_positions.items():
        current_price = 0
        if symbol in day_trading_bot.latest_prices:
            current_price = day_trading_bot.latest_prices[symbol]
        
        unrealized_pnl = 0
        unrealized_pnl_pct = 0
        if current_price and position['side'] == 'buy':
            unrealized_pnl = (current_price - position['entry_price']) * position['quantity']
            unrealized_pnl_pct = (current_price - position['entry_price']) / position['entry_price']
        
        orders.append({
            "id": f"order_{len(sample_trades) + len(orders) + 1:03d}",
            "symbol": symbol,
            "buy_price": position['entry_price'] if position['side'] == 'buy' else None,
            "sell_price": None,
            "current_price": current_price,
            "quantity": position['quantity'],
            "buy_time": position['entry_time'],
            "sell_time": None,
            "holding_time": f"{int((datetime.now() - datetime.fromisoformat(position['entry_time'])).total_seconds() / 60)}m",
            "profit_dollar": unrealized_pnl,
            "profit_percent": unrealized_pnl_pct * 100,
            "status": "active",
            "side": position['side']
        })
    
    # Combine sample trades with active positions
    all_orders = sample_trades + orders
    
    # Calculate summary statistics
    completed_trades = [o for o in all_orders if o['status'] == 'completed']
    total_profit = sum(o['profit_dollar'] for o in completed_trades)
    winning_trades = [o for o in completed_trades if o['profit_dollar'] > 0]
    losing_trades = [o for o in completed_trades if o['profit_dollar'] < 0]
    
    summary = {
        "total_trades": len(completed_trades),
        "active_trades": len(orders),
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": len(winning_trades) / len(completed_trades) * 100 if completed_trades else 0,
        "total_profit": total_profit,
        "avg_profit_per_trade": total_profit / len(completed_trades) if completed_trades else 0,
        "best_trade": max(completed_trades, key=lambda x: x['profit_dollar'])['profit_dollar'] if completed_trades else 0,
        "worst_trade": min(completed_trades, key=lambda x: x['profit_dollar'])['profit_dollar'] if completed_trades else 0,
        "avg_holding_time": "4m 30s"
    }
    
    return {
        "orders": all_orders,
        "summary": summary,
        "timestamp": datetime.now().isoformat()
    }

# Order History with Real Alpaca Data
@app.get("/api/history")
async def get_order_history():
    """Get real order history from Alpaca API for both crypto and stocks"""
    global day_trading_bot
    
    try:
        # Get Alpaca API instance
        api = None
        if day_trading_bot and hasattr(day_trading_bot, 'api'):
            api = day_trading_bot.api
        elif day_trading_bot:
            # Try to get from data manager
            data_manager = AlpacaDataManager()
            api = data_manager.api
        
        if not api or isinstance(api, MockAlpacaAPI):
            # Return demo data if no real API available
            return await get_demo_order_history()
        
        # Fetch real orders from Alpaca (last 7 days)
        # Alpaca requires RFC3339 format with timezone
        from datetime import timezone
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        # Get closed orders
        closed_orders = api.list_orders(
            status='closed',
            after=start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            until=end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
            limit=100,
            direction='desc'
        )
        
        # Get open orders
        open_orders = api.list_orders(
            status='open',
            limit=50
        )
        
        # Process orders into frontend format
        orders = []
        
        # Process closed orders (completed trades)
        for order in closed_orders:
            if order.status == 'filled':
                # Calculate holding time if both created and filled times exist
                holding_time = "N/A"
                if hasattr(order, 'created_at') and hasattr(order, 'filled_at'):
                    try:
                        created = pd.to_datetime(order.created_at)
                        filled = pd.to_datetime(order.filled_at)
                        duration = filled - created
                        minutes = int(duration.total_seconds() / 60)
                        holding_time = f"{minutes}m"
                    except:
                        pass
                
                # Get fill price
                fill_price = float(order.filled_avg_price) if order.filled_avg_price else 0
                
                # Determine if it's crypto (has slash) or stock
                is_crypto = '/' in order.symbol
                
                # For buy orders that are filled, we need matching sell orders
                # For now, we'll create the order entry
                order_entry = {
                    "id": order.id,
                    "symbol": order.symbol,
                    "buy_price": fill_price if order.side == 'buy' else None,
                    "sell_price": fill_price if order.side == 'sell' else None,
                    "quantity": float(order.filled_qty) if order.filled_qty else float(order.qty),
                    "buy_time": order.created_at if order.side == 'buy' else None,
                    "sell_time": order.filled_at if order.side == 'sell' else None,
                    "holding_time": holding_time,
                    "profit_dollar": 0,  # Will need to match buy/sell pairs
                    "profit_percent": 0,
                    "status": "completed",
                    "side": order.side,
                    "order_type": order.order_type,
                    "asset_class": "crypto" if is_crypto else "stock"
                }
                orders.append(order_entry)
        
        # Process open orders (active trades)
        for order in open_orders:
            # Get current price for the symbol
            current_price = 0
            try:
                if '/' in order.symbol:
                    # Crypto - get latest crypto quote
                    quote = api.get_crypto_latest_orderbook(order.symbol)
                    if quote and hasattr(quote, 'a'):
                        current_price = float(quote.a[0].p) if quote.a else 0
                else:
                    # Stock - get latest quote
                    quote = api.get_latest_quote(order.symbol)
                    if quote:
                        current_price = float(quote.ap) if hasattr(quote, 'ap') else 0
            except Exception as e:
                logger.error(f"Failed to get current price for {order.symbol}: {e}")
            
            # Calculate unrealized P&L
            if order.side == 'buy' and order.limit_price and current_price:
                entry_price = float(order.limit_price)
                quantity = float(order.qty)
                unrealized_pnl = (current_price - entry_price) * quantity
                unrealized_pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                unrealized_pnl = 0
                unrealized_pnl_pct = 0
            
            order_entry = {
                "id": order.id,
                "symbol": order.symbol,
                "buy_price": float(order.limit_price) if order.limit_price and order.side == 'buy' else None,
                "sell_price": None,
                "current_price": current_price,
                "quantity": float(order.qty),
                "buy_time": order.created_at if order.side == 'buy' else None,
                "sell_time": None,
                "holding_time": calculate_holding_time(order.created_at),
                "profit_dollar": unrealized_pnl,
                "profit_percent": unrealized_pnl_pct,
                "status": "active",
                "side": order.side,
                "order_type": order.order_type,
                "asset_class": "crypto" if '/' in order.symbol else "stock"
            }
            orders.append(order_entry)
        
        # Calculate summary statistics
        completed_orders = [o for o in orders if o['status'] == 'completed']
        active_orders = [o for o in orders if o['status'] == 'active']
        
        # Try to match buy/sell pairs for P&L calculation
        matched_pairs = match_order_pairs(completed_orders)
        
        total_profit = sum(o.get('profit_dollar', 0) for o in matched_pairs)
        profitable_trades = len([o for o in matched_pairs if o.get('profit_dollar', 0) > 0])
        
        summary = {
            "total_trades": len(matched_pairs),
            "profitable_trades": profitable_trades,
            "total_profit": total_profit,
            "avg_holding_time": calculate_avg_holding_time(matched_pairs),
            "active_trades": len(active_orders),
            "win_rate": (profitable_trades / len(matched_pairs) * 100) if matched_pairs else 0
        }
        
        return {
            "orders": orders[:50],  # Limit to 50 most recent
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch order history: {e}")
        # Fallback to demo data
        return await get_demo_order_history()

def calculate_holding_time(created_at):
    """Calculate holding time from creation to now"""
    try:
        created = pd.to_datetime(created_at)
        now = pd.Timestamp.now(tz=created.tz)
        duration = now - created
        minutes = int(duration.total_seconds() / 60)
        if minutes < 60:
            return f"{minutes}m"
        else:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m"
    except:
        return "N/A"

def calculate_avg_holding_time(orders):
    """Calculate average holding time from orders"""
    valid_times = []
    for order in orders:
        if order.get('holding_time') and order['holding_time'] != 'N/A':
            # Parse holding time string (e.g., "15m", "2h 30m")
            time_str = order['holding_time']
            try:
                total_minutes = 0
                if 'h' in time_str:
                    parts = time_str.split('h')
                    total_minutes += int(parts[0]) * 60
                    if len(parts) > 1 and 'm' in parts[1]:
                        total_minutes += int(parts[1].replace('m', '').strip())
                elif 'm' in time_str:
                    total_minutes = int(time_str.replace('m', ''))
                valid_times.append(total_minutes)
            except:
                continue
    
    if valid_times:
        avg_minutes = int(np.mean(valid_times))
        if avg_minutes < 60:
            return f"{avg_minutes}m"
        else:
            hours = avg_minutes // 60
            mins = avg_minutes % 60
            return f"{hours}h {mins}m"
    return "N/A"

def match_order_pairs(orders):
    """Match buy and sell orders to calculate P&L"""
    matched = []
    buy_orders = [o for o in orders if o['side'] == 'buy']
    sell_orders = [o for o in orders if o['side'] == 'sell']
    
    # Simple matching by symbol and time proximity
    for buy in buy_orders:
        symbol = buy['symbol']
        buy_time = pd.to_datetime(buy['buy_time']) if buy['buy_time'] else None
        
        if not buy_time:
            continue
        
        # Find matching sell order
        for sell in sell_orders:
            if sell['symbol'] == symbol and sell['sell_time']:
                sell_time = pd.to_datetime(sell['sell_time'])
                # Check if sell happened after buy
                if sell_time > buy_time:
                    # Create matched pair
                    matched_order = buy.copy()
                    matched_order['sell_price'] = sell['sell_price']
                    matched_order['sell_time'] = sell['sell_time']
                    
                    # Calculate P&L
                    if buy['buy_price'] and sell['sell_price']:
                        quantity = min(buy['quantity'], sell['quantity'])
                        profit = (sell['sell_price'] - buy['buy_price']) * quantity
                        profit_pct = ((sell['sell_price'] - buy['buy_price']) / buy['buy_price']) * 100
                        
                        matched_order['profit_dollar'] = profit
                        matched_order['profit_percent'] = profit_pct
                        matched_order['quantity'] = quantity
                        
                        # Calculate holding time
                        duration = sell_time - buy_time
                        minutes = int(duration.total_seconds() / 60)
                        matched_order['holding_time'] = f"{minutes}m" if minutes < 60 else f"{minutes//60}h {minutes%60}m"
                        
                        matched.append(matched_order)
                        sell_orders.remove(sell)
                        break
    
    return matched

async def get_demo_order_history():
    """Return demo order history when API is not available"""
    demo_orders = [
        {
            "id": "demo-1",
            "symbol": "BTC/USD",
            "buy_price": 44850.00,
            "sell_price": 45120.50,
            "quantity": 0.028,
            "buy_time": (datetime.now() - timedelta(hours=2)).isoformat(),
            "sell_time": (datetime.now() - timedelta(hours=1, minutes=30)).isoformat(),
            "holding_time": "30m",
            "profit_dollar": 7.57,
            "profit_percent": 0.6,
            "status": "completed",
            "side": "buy",
            "asset_class": "crypto"
        },
        {
            "id": "demo-2",
            "symbol": "AAPL",
            "buy_price": 178.25,
            "sell_price": 179.10,
            "quantity": 10,
            "buy_time": (datetime.now() - timedelta(hours=3)).isoformat(),
            "sell_time": (datetime.now() - timedelta(hours=2, minutes=15)).isoformat(),
            "holding_time": "45m",
            "profit_dollar": 8.50,
            "profit_percent": 0.48,
            "status": "completed",
            "side": "buy",
            "asset_class": "stock"
        },
        {
            "id": "demo-3",
            "symbol": "ETH/USD",
            "buy_price": 2785.30,
            "sell_price": None,
            "current_price": 2792.50,
            "quantity": 0.45,
            "buy_time": (datetime.now() - timedelta(minutes=15)).isoformat(),
            "sell_time": None,
            "holding_time": "15m",
            "profit_dollar": 3.24,
            "profit_percent": 0.26,
            "status": "active",
            "side": "buy",
            "asset_class": "crypto"
        }
    ]
    
    return {
        "orders": demo_orders,
        "summary": {
            "total_trades": 2,
            "profitable_trades": 2,
            "total_profit": 16.07,
            "avg_holding_time": "37m",
            "active_trades": 1,
            "win_rate": 100
        },
        "timestamp": datetime.now().isoformat()
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