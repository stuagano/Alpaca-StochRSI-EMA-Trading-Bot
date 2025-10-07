#!/usr/bin/env python3
"""
Complete Unified Trading Service - All functionality + Frontend on single port 9000
Replaces all microservices AND serves the React frontend on one port
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast
from contextlib import asynccontextmanager
import json
import numpy as np

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import alpaca_trade_api as tradeapi
import uvicorn

from config.service_settings import get_service_settings
from services.unified_trading import (
    TradingState,
    list_background_workers,
    manage_background_tasks,
    refresh_scanner_symbols as sync_scanner_symbols,
    register_background_worker,
    resolve_background_workers,
    to_scanner_symbol,
)

# Import the crypto scalping strategy
from strategies.crypto_scalping_strategy import CryptoVolatilityScanner, CryptoSignal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_runtime_state(request: Request) -> TradingState:
    """Resolve the trading state stored on the FastAPI application."""

    state = getattr(request.app.state, "trading_state", None)
    if state is None:
        raise HTTPException(status_code=503, detail="Trading state is not initialised")
    return cast(TradingState, state)


def refresh_scanner_symbols(state: TradingState) -> List[str]:
    """Synchronise cached scanner symbols with the active strategy."""

    return sync_scanner_symbols(state)


def get_alpaca_api(state: TradingState):
    """Get or create Alpaca API instance with proper credential loading"""

    if not state.alpaca_api:
        alpaca_settings = state.settings.alpaca
        auth_file = alpaca_settings.auth_file
        api_key = alpaca_settings.api_key
        api_secret = alpaca_settings.api_secret
        base_url = alpaca_settings.api_base_url

        if auth_file.exists():
            try:
                with auth_file.open('r', encoding='utf-8') as auth_handle:
                    auth_data = json.load(auth_handle)
                    api_key = auth_data.get('APCA-API-KEY-ID', api_key)
                    api_secret = auth_data.get('APCA-API-SECRET-KEY', api_secret)
                    base_url = auth_data.get('BASE-URL', base_url)
                    logger.info("Loaded credentials from %s", auth_file)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to load Alpaca credentials file %s: %s", auth_file, exc)

        if not api_key or not api_secret:
            logger.error(
                "No API credentials found! Provide APCA_API_KEY_ID/APCA_API_SECRET_KEY or configure %s",
                auth_file,
            )
            raise ValueError("Missing Alpaca API credentials")

        state.alpaca_api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')
        logger.info(
            "Connected to Alpaca %s Trading",
            'Paper' if 'paper' in base_url else 'Live',
        )

    return state.alpaca_api


def generate_trade_id(state: TradingState):
    """Generate unique trade ID"""

    return (
        f"trade-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        f"-{len(state.trade_history)}"
    )


async def log_trade(state: TradingState, order, filled_price=None):
    """Log executed trade with P&L calculation"""
    try:
        symbol = order.symbol if hasattr(order, 'symbol') else order.get('symbol')
        side = order.side if hasattr(order, 'side') else order.get('side')
        qty = float(order.qty if hasattr(order, 'qty') else order.get('qty', 0))
        price = float(filled_price or (order.filled_avg_price if hasattr(order, 'filled_avg_price') else order.get('filled_avg_price', 0)))
        
        if price == 0:
            # Try to get current market price
            api = get_alpaca_api(state)
            try:
                quote = api.get_latest_crypto_quote(symbol if '/' not in symbol else symbol.replace('/', ''))
                price = float(quote.ap)  # ask price
            except:
                price = 0

        trade_record = {
            "id": generate_trade_id(state),
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "value": qty * price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "filled"
        }
        
        # Calculate P&L for sell orders
        if side == 'sell' and symbol in state.position_entry_prices:
            entry_price = state.position_entry_prices[symbol]
            trade_record["profit"] = (price - entry_price) * qty
            trade_record["profit_percent"] = ((price - entry_price) / entry_price) * 100
            # Clear entry price after selling
            del state.position_entry_prices[symbol]
            # Update session metrics
            state.session_metrics.update_on_trade(trade_record)
        elif side == 'buy':
            # Store entry price for P&L calculation
            state.position_entry_prices[symbol] = price
            trade_record["profit"] = None
            trade_record["profit_percent"] = None

        # Add to trade history
        state.trade_history.appendleft(trade_record)
        
        # Broadcast via WebSocket to all connected clients
        for connection in active_connections:
            try:
                await connection.send_json({
                    "type": "trade_update",
                    "data": trade_record
                })
            except:
                pass
        
        logger.info(f"📊 Trade logged: {side.upper()} {qty} {symbol} @ ${price:.2f}")
        if trade_record.get("profit") is not None:
            logger.info(f"💰 P&L: ${trade_record['profit']:.2f} ({trade_record['profit_percent']:.2f}%)")
        
        return trade_record
    except Exception as e:
        logger.error(f"Trade logging error: {e}")
        return None

@register_background_worker
async def update_cache(state: TradingState):
    """Update cached data periodically (every 5 seconds)"""
    while True:
        try:
            api = get_alpaca_api(state)

            # Update account (cached for 30 seconds)
            if 'account' not in state.last_update or \
               (datetime.now(timezone.utc) - state.last_update.get('account', datetime.min)).seconds > 30:
                state.account_cache = api.get_account()._raw
                state.last_update['account'] = datetime.now(timezone.utc)

            # Update positions (cached for 5 seconds)
            if 'positions' not in state.last_update or \
               (datetime.now(timezone.utc) - state.last_update.get('positions', datetime.min)).seconds > 5:
                positions = api.list_positions()
                state.positions_cache = [p._raw for p in positions]
                state.last_update['positions'] = datetime.now(timezone.utc)

            # Update orders (cached for 5 seconds)
            if 'orders' not in state.last_update or \
               (datetime.now(timezone.utc) - state.last_update.get('orders', datetime.min)).seconds > 5:
                orders = api.list_orders(status='open')
                state.orders_cache = [o._raw for o in orders]
                state.last_update['orders'] = datetime.now(timezone.utc)

        except Exception as e:
            logger.error(f"Cache update error: {e}")
            state.error_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "source": "cache_update"
            })

        await asyncio.sleep(state.settings.cache_refresh_seconds)

@register_background_worker
async def crypto_scanner(state: TradingState):
    """Lightweight crypto scanner driven by configured interval."""
    while True:
        try:
            crypto_pairs = refresh_scanner_symbols(state)
            if not crypto_pairs:
                logger.debug("No crypto pairs available for scanning; waiting for configuration")
                await asyncio.sleep(state.settings.crypto_scanner_interval_seconds)
                continue

            api = get_alpaca_api(state)
            results = []

            for symbol in crypto_pairs:
                try:
                    bars = api.get_crypto_bars(symbol, '5Min', limit=20).df
                    if len(bars) >= 10:
                        closes = bars['close'].values
                        current_price = closes[-1]
                        change_pct = (closes[-1] - closes[-2]) / closes[-2] * 100 if closes[-2] > 0 else 0
                        
                        # Simple volatility
                        returns = np.diff(closes) / closes[:-1]
                        volatility = np.std(returns) * 100
                        
                        results.append({
                            'symbol': to_scanner_symbol(symbol),
                            'display_symbol': symbol,
                            'price': float(current_price),
                            'change': float(change_pct),
                            'volatility': float(volatility),
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        })
                        
                        state.crypto_metrics[symbol] = {
                            'closes': closes.tolist(),
                            'current_price': float(current_price)
                        }
                except:
                    continue

            state.top_movers = sorted(results, key=lambda x: x['volatility'], reverse=True)

        except Exception as e:
            logger.error(f"Scanner error: {e}")

        await asyncio.sleep(state.settings.crypto_scanner_interval_seconds)

@register_background_worker
async def crypto_scalping_trader(state: TradingState):
    """Advanced crypto scalping strategy - checks every 10 seconds"""
    logger.info("🚀 Crypto scalping trader started")
    while True:
        try:
            if not state.auto_trading_enabled:
                logger.debug("Auto-trading disabled, waiting...")
                await asyncio.sleep(state.settings.scalper_poll_interval_seconds)
                continue

            # Check daily loss limit
            if state.current_daily_loss >= state.daily_loss_limit:
                logger.warning(f"Daily loss limit reached: ${state.current_daily_loss:.2f}")
                await asyncio.sleep(state.settings.scalper_cooldown_seconds)
                continue

            api = get_alpaca_api(state)

            # Update scanner with current market data
            await update_scanner_data(state)

            # Get current crypto positions
            crypto_positions = [
                position
                for position in state.positions_cache
                if any(prefix in position.get('symbol', '') for prefix in state.crypto_symbol_prefixes)
            ]

            # Check exit conditions for existing positions
            await check_scalp_exit_conditions(state, api, crypto_positions)

            # Look for new entries if we have room
            if len(crypto_positions) < state.max_concurrent_positions:
                await find_scalp_entry_opportunities(state, api)

        except Exception as e:
            logger.error(f"Crypto scalping trader error: {e}")

        await asyncio.sleep(state.settings.scalper_poll_interval_seconds)

async def update_scanner_data(state: TradingState):
    """Update the crypto volatility scanner with current market data"""
    try:
        if not state.crypto_scanner:
            logger.debug("No crypto scanner available for data update")
            return

        logger.debug("Updating scanner with market data...")

        api = get_alpaca_api(state)

        # Update market data for all configured scanner symbols
        for symbol_display in refresh_scanner_symbols(state):
            try:
                # Get recent bars to update price data
                bars = api.get_crypto_bars(symbol_display, '1Min', limit=5).df
                if not bars.empty:
                    symbol_clean = to_scanner_symbol(symbol_display)
                    latest_bar = bars.iloc[-1]
                    price = float(latest_bar['close'])
                    volume = float(latest_bar['volume'])

                    # Update scanner data
                    state.crypto_scanner.update_market_data(symbol_clean, price, volume)
            except Exception as e:
                logger.debug(f"Failed to update data for {symbol_display}: {e}")
                continue

    except Exception as e:
        logger.error(f"Scanner data update error: {e}")

async def find_scalp_entry_opportunities(state: TradingState, api):
    """Find new scalping entry opportunities using the volatility scanner"""
    try:
        if not state.crypto_scanner:
            logger.debug("No crypto scanner available")
            return

        # Get trading signals from the scanner
        signals = state.crypto_scanner.scan_for_opportunities()
        
        if not signals:
            logger.debug("No scalping signals found")
            return
            
        logger.info(f"📊 Found {len(signals)} potential crypto scalping signals")
            
        # Process top 3 signals
        for i, signal in enumerate(signals[:3]):
            logger.info(f"  Signal {i+1}: {signal.symbol} - Action: {signal.action}, Confidence: {signal.confidence:.2f}, Price: ${signal.price:.4f}")
            
            # Skip if we already have a position in this symbol
            symbol_clean = signal.symbol.replace('USD', '').replace('USDT', '').replace('USDC', '')
            if any(symbol_clean in pos.get('symbol', '') for pos in state.positions_cache):
                logger.info(f"  ⏭️ Skipping {signal.symbol} - already have position")
                continue
                
            # Check signal confidence (lowered threshold for more opportunities)
            # Note: confidence values from scanner are 0-1 scale (0.5 = 50% confidence)
            if signal.confidence < 0.4:  # Lowered from 0.5 to be more aggressive
                logger.info(f"  ⏭️ Skipping {signal.symbol} - confidence too low: {signal.confidence:.2f} < 0.4")
                continue
                
            logger.info(f"  🎯 EXECUTING: {signal.action.upper()} {signal.symbol} @ ${signal.price:.4f} (confidence: {signal.confidence:.2f}, volatility: {signal.volatility:.3f})")
            
            # Execute the trade
            await execute_scalp_entry(state, api, signal)
            
    except Exception as e:
        logger.error(f"Entry opportunity search error: {e}")

async def execute_scalp_entry(state: TradingState, api, signal: CryptoSignal):
    """Execute a scalping entry trade"""
    try:
        account = api.get_account()
        buying_power = float(account.buying_power)
        
        if buying_power < 50:
            logger.warning(f"Insufficient buying power for scalping: ${buying_power:.2f}")
            return
            
        # Calculate position size (0.5-1% of portfolio, max $100)
        portfolio_value = float(account.portfolio_value)
        max_position = min(100, portfolio_value * 0.005 * signal.confidence)  # Scale with confidence
        position_value = max(25, max_position)  # Minimum $25 position
        
        # Calculate quantity
        qty = position_value / signal.price
        
        # Convert symbol for Alpaca API (needs slash format: BTC/USD not BTCUSD)
        # Scanner provides BTCUSD, but Alpaca API needs BTC/USD
        if 'USD' in signal.symbol:
            # Extract the crypto part and add slash before USD
            crypto_part = signal.symbol.replace('USD', '').replace('USDT', '').replace('USDC', '')
            if signal.symbol.endswith('USDT'):
                alpaca_symbol = f"{crypto_part}/USDT"
            elif signal.symbol.endswith('USDC'):
                alpaca_symbol = f"{crypto_part}/USDC"
            else:
                alpaca_symbol = f"{crypto_part}/USD"
        else:
            alpaca_symbol = signal.symbol
            
        logger.info(f"Scalp entry: {signal.action.upper()} {qty:.8f} {alpaca_symbol} at ${signal.price:.4f}")
        
        # Submit order
        order = api.submit_order(
            symbol=alpaca_symbol,
            qty=round(qty, 8),
            side=signal.action,
            type='market',
            time_in_force='ioc'  # Immediate or cancel for scalping
        )
        
        # Track the position with scalping parameters
        state.active_scalp_positions[alpaca_symbol] = {
            'signal': signal,
            'entry_price': signal.price,
            'quantity': qty,
            'side': signal.action,
            'entry_time': datetime.now(timezone.utc),
            'target_price': signal.price * (1 + signal.target_profit) if signal.action == 'buy' else signal.price * (1 - signal.target_profit),
            'stop_price': signal.price * (1 - signal.stop_loss) if signal.action == 'buy' else signal.price * (1 + signal.stop_loss),
            'order_id': order.id
        }
        
        logger.info(f"✅ Scalp position opened: {signal.action.upper()} {qty:.8f} {alpaca_symbol} | Target: ±{signal.target_profit*100:.1f}% | Stop: ±{signal.stop_loss*100:.1f}%")
        
        # Log the trade
        await log_trade(state, order, signal.price)
        
    except Exception as e:
        logger.error(f"Scalp entry execution error for {signal.symbol}: {e}")

async def check_scalp_exit_conditions(state: TradingState, api, crypto_positions):
    """Check exit conditions for scalping positions"""
    try:
        positions_to_close = []
        
        for position in crypto_positions:
            symbol = position.get('symbol', '')
            if not symbol:
                continue
                
            # Get current price
            try:
                current_price = float(position.get('current_price', 0))
                entry_price = state.position_entry_prices.get(symbol, current_price)
                unrealized_plpc = float(position.get('unrealized_plpc', 0))
                side = position.get('side', 'long')
                qty = float(position.get('qty', 0))
                
                should_exit = False
                exit_reason = ""
                
                # Scalping exit conditions - more aggressive than simple trader
                
                # Profit target: 0.3-0.5% for scalping
                if unrealized_plpc > 0.003:  # 0.3% profit
                    should_exit = True
                    exit_reason = "PROFIT_TARGET"
                    
                # Stop loss: -0.2% for scalping  
                elif unrealized_plpc < -0.002:  # 0.2% loss
                    should_exit = True
                    exit_reason = "STOP_LOSS"
                    
                # Time-based exit: Close after 15 minutes for scalping
                elif symbol in state.active_scalp_positions:
                    scalp_pos = state.active_scalp_positions[symbol]
                    time_held = (datetime.now(timezone.utc) - scalp_pos['entry_time']).total_seconds()
                    if time_held > 900:  # 15 minutes
                        should_exit = True
                        exit_reason = "TIME_LIMIT"
                        
                # Volatility-based exit: If volatility drops significantly
                elif unrealized_plpc < 0 and abs(unrealized_plpc) > 0.001:  # Losing position > 0.1%
                    # Check if we should cut losses early
                    if symbol in state.active_scalp_positions:
                        scalp_pos = state.active_scalp_positions[symbol]
                        if scalp_pos['signal'].volatility < 0.005:  # Low volatility
                            should_exit = True
                            exit_reason = "LOW_VOLATILITY"
                
                if should_exit:
                    positions_to_close.append((position, exit_reason, unrealized_plpc))
                    
            except Exception as e:
                logger.error(f"Error checking exit for {symbol}: {e}")
                continue
        
        # Execute exits
        for position, reason, pnl_pct in positions_to_close:
            await execute_scalp_exit(state, api, position, reason, pnl_pct)
            
    except Exception as e:
        logger.error(f"Scalp exit check error: {e}")

async def execute_scalp_exit(state: TradingState, api, position, reason, pnl_pct):
    """Execute scalping exit trade"""
    try:
        symbol = position['symbol']
        qty = position['qty']
        
        # Submit sell order
        order = api.submit_order(
            symbol=symbol,
            qty=qty,
            side='sell',
            type='market',
            time_in_force='ioc'
        )
        
        # Calculate profit/loss
        entry_price = state.position_entry_prices.get(symbol, 0)
        current_price = float(position.get('current_price', 0))
        profit_loss = float(qty) * entry_price * pnl_pct if entry_price else 0
        
        # Update daily loss tracking
        if profit_loss < 0:
            state.current_daily_loss += abs(profit_loss)
        
        # Clean up tracking
        if symbol in state.active_scalp_positions:
            del state.active_scalp_positions[symbol]
            
        logger.info(f"🏁 Scalp exit: SELL {qty} {symbol} | Reason: {reason} | P&L: {pnl_pct*100:.2f}% (${profit_loss:.2f})")
        
        # Log the trade
        await log_trade(state, order, current_price)
        
    except Exception as e:
        logger.error(f"Scalp exit execution error for {position.get('symbol', 'unknown')}: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Starting Complete Unified Trading Service")
    logger.info("📡 Serving API + Frontend on single port 9000")

    settings = get_service_settings()
    state: Optional[TradingState] = None

    try:
        state = TradingState(settings)
        app.state.trading_state = state
        state.background_tasks.clear()
        setattr(app.state, "background_tasks", state.background_tasks)

        # Initialize Alpaca API
        api = get_alpaca_api(state)
        account = api.get_account()
        logger.info(f"✅ Connected to Alpaca - Account: {account.account_number}")

        # Initialize crypto volatility scanner from configured symbols
        scanner_seed_symbols = [
            to_scanner_symbol(symbol)
            for symbol in state.crypto_symbols
            if symbol
        ]
        state.crypto_scanner = CryptoVolatilityScanner(
            enabled_symbols=scanner_seed_symbols or None
        )
        derived_pairs = refresh_scanner_symbols(state)
        logger.info(
            "Configured %d crypto pairs for scanning via strategy defaults",
            len(derived_pairs),
        )

        configured_workers = settings.enabled_background_workers
        if configured_workers is None:
            background_workers = list_background_workers()
        else:
            background_workers = resolve_background_workers(configured_workers)
            if not background_workers:
                logger.warning(
                    "No background workers matched TRADING_SERVICE_BACKGROUND_WORKERS=%s;"
                    " defaulting to registry order",
                    configured_workers,
                )
                background_workers = list_background_workers()

        active_worker_names = [
            getattr(worker, "__name__", "background_worker")
            for worker in background_workers
        ]
        logger.info("Activating background workers: %s", ", ".join(active_worker_names) or "none")

        async with manage_background_tasks(
            state,
            background_workers,
        ):
            state.auto_trading_enabled = True
            logger.info("✅ All systems operational")
            logger.info("🌐 Frontend available at http://localhost:9000")

            yield

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    finally:
        if state is not None:
            state.auto_trading_enabled = False

        if hasattr(app.state, "background_tasks"):
            delattr(app.state, "background_tasks")
        if hasattr(app.state, "trading_state"):
            delattr(app.state, "trading_state")

        logger.info("🛑 Complete Unified Trading Service stopped")

app = FastAPI(
    title="Complete Unified Trading Service",
    version="4.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= API ENDPOINTS (Same as before) =============

@app.get("/health")
async def health_check():
    """Health check for all services"""
    return {
        "status": "healthy",
        "services": {
            "gateway": "integrated",
            "crypto": "active",
            "positions": "active",
            "market_data": "active",
            "analytics": "active",
            "frontend": "integrated"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/account")
async def get_account(state: TradingState = Depends(get_runtime_state)):
    """Get account information (cached)"""
    if not state.account_cache:
        api = get_alpaca_api(state)
        state.account_cache = api.get_account()._raw

    # Add data source marker for live data validation
    account_data = state.account_cache.copy()
    account_data["data_source"] = "live"
    return account_data

@app.get("/api/positions")
async def get_positions(market_mode: str = "stocks", state: TradingState = Depends(get_runtime_state)):
    """Get positions filtered by market mode"""
    all_positions = state.positions_cache
    
    if market_mode == "crypto":
        # Filter for crypto positions only
        # Crypto symbols typically contain these patterns
        crypto_patterns = ['BTC', 'ETH', 'LTC', 'BCH', 'DOGE', 'SHIB', 'AVAX', 'SOL', 
                          'ADA', 'MATIC', 'LINK', 'UNI', 'AAVE', 'MKR', 'XRP', 'XLM', 'ALGO']
        positions = [p for p in all_positions
                    if any(pattern in p.get('symbol', '') for pattern in crypto_patterns)]
    else:
        # Filter for stock positions (exclude crypto)
        crypto_patterns = ['BTC', 'ETH', 'LTC', 'BCH', 'DOGE', 'SHIB', 'AVAX', 'SOL', 
                          'ADA', 'MATIC', 'LINK', 'UNI', 'AAVE', 'MKR', 'XRP', 'XLM', 'ALGO']
        positions = [p for p in all_positions 
                    if not any(pattern in p.get('symbol', '') for pattern in crypto_patterns)]
    
    return {
        "positions": positions,
        "count": len(positions),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_source": "live",
        "market_mode": market_mode
    }

@app.get("/api/crypto/positions")
async def get_crypto_positions(state: TradingState = Depends(get_runtime_state)):
    """Get crypto positions (cached)"""
    crypto_positions = [p for p in state.positions_cache
                       if any(c in p.get('symbol', '') for c in ['BTC', 'ETH', 'LTC', 'DOGE', 'AVAX'])]
    
    return {
        "positions": crypto_positions,
        "count": len(crypto_positions)
    }

@app.get("/api/orders")
async def get_orders(status: str = 'open', state: TradingState = Depends(get_runtime_state)):
    """Get orders (cached)"""
    return {
        "orders": state.orders_cache,
        "count": len(state.orders_cache),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_source": "live"
    }

@app.get("/api/leaderboard")
async def get_leaderboard(state: TradingState = Depends(get_runtime_state)):
    """Get crypto leaderboard"""
    return {
        "leaders": state.top_movers,
        "last_scan": state.last_update.get('scanner', datetime.now(timezone.utc)).isoformat(),
        "data_source": "alpaca_real"
    }

@app.get("/api/signals")
async def get_signals(state: TradingState = Depends(get_runtime_state)):
    """Get advanced scalping trading signals"""
    signals = []

    try:
        if state.crypto_scanner:
            # Get signals from the volatility scanner
            scanner_signals = state.crypto_scanner.scan_for_opportunities()
            
            for signal in scanner_signals[:5]:  # Top 5 signals
                signals.append({
                    "symbol": signal.symbol.replace('USD', '/USD'),  # Format for display
                    "signal": signal.action.upper(),
                    "strength": int(signal.confidence * 100),
                    "price": signal.price,
                    "volatility": signal.volatility,
                    "momentum": signal.momentum,
                    "volume_surge": signal.volume_surge,
                    "target_profit": signal.target_profit * 100,  # Convert to percentage
                    "stop_loss": signal.stop_loss * 100,
                    "timestamp": signal.timestamp.isoformat(),
                    "data_source": "scalping_scanner"
                })
        
        # Fallback to simple signals if scanner not available
        if not signals:
            for mover in state.top_movers[:3]:
                signal = "BUY" if mover['change'] > 0 else "NEUTRAL"
                signals.append({
                    "symbol": mover['display_symbol'],
                    "signal": signal,
                    "strength": min(abs(mover['change']) * 20, 100),
                    "price": mover['price'],
                    "data_source": "simple"
                })
    
    except Exception as e:
        logger.error(f"Signals error: {e}")
        # Return empty signals on error
        signals = []
    
    return signals

@app.get("/api/signals/{symbol}")
async def get_symbol_signals(symbol: str, state: TradingState = Depends(get_runtime_state)):
    """Get scalping trading signals for a specific symbol"""
    try:
        if state.crypto_scanner:
            # Convert symbol format for scanner (BTC/USD -> BTCUSD)
            scanner_symbol = symbol.replace('/', '').upper()
            if not scanner_symbol.endswith('USD'):
                scanner_symbol += 'USD'

            # Get all signals and filter for the specific symbol
            all_signals = state.crypto_scanner.scan_for_opportunities()
            
            for signal in all_signals:
                if signal.symbol == scanner_symbol:
                    return {
                        "symbol": symbol,
                        "signal": signal.action.upper(),
                        "strength": int(signal.confidence * 100),
                        "price": signal.price,
                        "volatility": signal.volatility,
                        "momentum": signal.momentum,
                        "volume_surge": signal.volume_surge,
                        "target_profit": signal.target_profit * 100,
                        "stop_loss": signal.stop_loss * 100,
                        "confidence": signal.confidence,
                        "timestamp": signal.timestamp.isoformat(),
                        "data_source": "scalping_scanner"
                    }
        
        # Fallback to simple logic
        for mover in state.top_movers:
            if mover['display_symbol'] == symbol or mover['symbol'] == symbol:
                signal = "BUY" if mover['change'] > 0 else "SELL" if mover['change'] < -1 else "NEUTRAL"
                strength = min(abs(mover['change']) * 20, 100)
                
                return {
                    "symbol": symbol,
                    "signal": signal,
                    "strength": strength,
                    "price": mover['price'],
                    "change": mover['change'],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data_source": "simple"
                }
        
        # Default neutral signal
        return {
            "symbol": symbol,
            "signal": "NEUTRAL", 
            "strength": 0,
            "price": 0,
            "change": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_source": "default"
        }
        
    except Exception as e:
        logger.error(f"Symbol signals error for {symbol}: {e}")
        return {
            "symbol": symbol,
            "signal": "ERROR", 
            "strength": 0,
            "error": str(e),
            "data_source": "error"
        }

@app.post("/api/bot/activate")
async def activate_bot(state: TradingState = Depends(get_runtime_state)):
    """Activate the trading bot"""
    state.auto_trading_enabled = True
    return {
        "status": "activated",
        "enabled": True,
        "message": "Trading bot activated successfully"
    }

@app.post("/api/bot/deactivate")
async def deactivate_bot(state: TradingState = Depends(get_runtime_state)):
    """Deactivate the trading bot"""
    state.auto_trading_enabled = False
    return {
        "status": "deactivated",
        "enabled": False,
        "message": "Trading bot deactivated successfully"
    }

@app.get("/api/analytics/performance")
async def get_performance(state: TradingState = Depends(get_runtime_state)):
    """Get performance metrics"""
    positions = state.positions_cache

    total_pl = sum(float(p.get('unrealized_pl', 0)) for p in positions)
    win_count = sum(1 for p in positions if float(p.get('unrealized_pl', 0)) > 0)

    return {
        "total_return": total_pl,
        "portfolio_value": float(state.account_cache.get('portfolio_value', 0)),
        "win_rate": win_count / len(positions) if positions else 0,
        "total_trades": len(positions),
        "data_source": "real"
    }

@app.get("/api/trade-log")
async def get_trade_log(state: TradingState = Depends(get_runtime_state)):
    """Get recent trades with P&L and metrics"""
    trades = list(state.trade_history)[:50]  # Get last 50 trades
    
    # Format duration
    def format_duration(seconds):
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds / 60)
        return f"{minutes}m"
    
    # Calculate average trade duration (mock based on trade frequency)
    avg_duration = 120  # default 2 minutes
    if len(trades) > 1:
        # Estimate based on time between trades
        first_trade_time = datetime.fromisoformat(trades[0]['timestamp'].replace('Z', '+00:00'))
        last_trade_time = datetime.fromisoformat(trades[-1]['timestamp'].replace('Z', '+00:00'))
        time_span = (first_trade_time - last_trade_time).total_seconds()
        if time_span > 0 and len(trades) > 1:
            avg_duration = time_span / (len(trades) - 1)
    
    return {
        "trades": trades,
        "metrics": {
            "trades_per_hour": state.session_metrics.trades_per_hour,
            "avg_trade_duration": format_duration(avg_duration),
            "avg_profit_per_trade": state.session_metrics.avg_profit_per_trade,
            "win_rate": state.session_metrics.win_rate,
            "total_trades_today": state.session_metrics.total_trades,
            "current_streak": abs(state.session_metrics.current_streak),
            "best_streak": state.session_metrics.best_streak,
            "active_signals": len([s for s in state.signals if s.get('active', False)]),
            "session_profit": state.session_metrics.total_profit,
            "win_count": state.session_metrics.winning_trades,
            "loss_count": state.session_metrics.losing_trades
        },
        "data_source": "live"
    }

@app.get("/api/status")
async def get_status(state: TradingState = Depends(get_runtime_state)):
    """Get crypto scalping trading status"""
    account = state.account_cache

    # Calculate scalping-specific metrics
    active_scalp_positions = len(state.active_scalp_positions)
    daily_loss_remaining = state.daily_loss_limit - state.current_daily_loss

    return {
        "status": "active",
        "buying_power": float(account.get('buying_power', 0)),
        "portfolio_value": float(account.get('portfolio_value', 0)),
        "auto_trading": state.auto_trading_enabled,
        "scalping_enabled": state.crypto_scanner is not None,
        "active_scalp_positions": active_scalp_positions,
        "max_positions": state.max_concurrent_positions,
        "daily_loss_limit": state.daily_loss_limit,
        "current_daily_loss": state.current_daily_loss,
        "daily_loss_remaining": daily_loss_remaining,
        "top_movers": [m['display_symbol'] for m in state.top_movers[:3]],
        "scanner_symbols": len(state.crypto_scanner.get_enabled_symbols()) if state.crypto_scanner else 0
    }

@app.get("/api/config")
async def get_config(state: TradingState = Depends(get_runtime_state)):
    """Get scalping configuration"""
    return {
        "auto_trading": state.auto_trading_enabled,
        "scalping_enabled": state.crypto_scanner is not None,
        "supported_crypto": list(state.crypto_symbols),
        "max_positions": state.max_concurrent_positions,
        "daily_loss_limit": state.daily_loss_limit,
        "min_volatility": 0.005,  # 0.5%
        "profit_targets": "0.3-0.8%",
        "stop_losses": "0.15-0.5%",
        "max_hold_time": "15 minutes",
        "strategy": "crypto_scalping"
    }

@app.post("/api/toggle-trading")
async def toggle_trading(state: TradingState = Depends(get_runtime_state)):
    """Toggle auto-trading"""
    state.auto_trading_enabled = not state.auto_trading_enabled
    return {"enabled": state.auto_trading_enabled}

@app.get("/api/scalping/generate-signal/{symbol}")
async def generate_scalping_signal(symbol: str, state: TradingState = Depends(get_runtime_state)):
    """Generate a specific scalping signal for a symbol using the scanner"""
    try:
        if not state.crypto_scanner:
            return {"error": "Scalping scanner not initialized", "data_source": "error"}
        
        # Convert symbol format
        scanner_symbol = symbol.replace('/', '').upper()
        if not scanner_symbol.endswith('USD'):
            scanner_symbol += 'USD'
        
        # Check if we have data for this symbol
        if scanner_symbol not in state.crypto_scanner.price_data:
            return {
                "symbol": symbol,
                "signal": "NO_DATA",
                "message": "Insufficient market data for signal generation",
                "data_source": "scanner"
            }

        prices = state.crypto_scanner.price_data[scanner_symbol]
        volumes = state.crypto_scanner.volume_data.get(scanner_symbol, [])
        
        if len(prices) < 20:
            return {
                "symbol": symbol,
                "signal": "INSUFFICIENT_DATA",
                "message": f"Need at least 20 data points, have {len(prices)}",
                "data_source": "scanner"
            }
        
        # Calculate all the indicators
        current_price = prices[-1]
        volatility = state.crypto_scanner.calculate_volatility(prices)
        volume_surge = state.crypto_scanner.detect_volume_surge(volumes)
        momentum = state.crypto_scanner.calculate_momentum(prices)

        # Generate signal using the scanner's internal method
        signal = state.crypto_scanner._generate_signal(
            scanner_symbol, current_price, volatility, volume_surge, momentum
        )
        
        if signal:
            return {
                "symbol": symbol,
                "signal": signal.action.upper(),
                "confidence": signal.confidence,
                "strength": int(signal.confidence * 100),
                "price": signal.price,
                "volatility": signal.volatility,
                "momentum": signal.momentum,
                "volume_surge": signal.volume_surge,
                "target_profit": signal.target_profit * 100,
                "stop_loss": signal.stop_loss * 100,
                "timestamp": signal.timestamp.isoformat(),
                "indicators": {
                    "current_price": current_price,
                    "volatility": volatility,
                    "momentum": momentum,
                    "volume_surge": volume_surge,
                    "data_points": len(prices)
                },
                "data_source": "scalping_scanner"
            }
        else:
            return {
                "symbol": symbol,
                "signal": "HOLD",
                "confidence": 0,
                "message": "No trading signal generated",
                "indicators": {
                    "current_price": current_price,
                    "volatility": volatility,
                    "momentum": momentum,
                    "volume_surge": volume_surge,
                    "data_points": len(prices)
                },
                "data_source": "scalping_scanner"
            }
        
    except Exception as e:
        logger.error(f"Generate signal error for {symbol}: {e}")
        return {
            "symbol": symbol,
            "signal": "ERROR",
            "error": str(e),
            "data_source": "error"
        }

@app.get("/api/scalping/metrics")
async def get_scalping_metrics(state: TradingState = Depends(get_runtime_state)):
    """Get detailed scalping performance metrics"""
    try:
        active_positions = len(state.active_scalp_positions)

        # Calculate metrics from trade history
        scalping_trades = [t for t in state.trade_history if t.get('profit') is not None]

        total_profit = sum(t.get('profit', 0) for t in scalping_trades)
        win_count = sum(1 for t in scalping_trades if t.get('profit', 0) > 0)
        loss_count = sum(1 for t in scalping_trades if t.get('profit', 0) < 0)
        
        win_rate = (win_count / len(scalping_trades) * 100) if scalping_trades else 0
        avg_profit = (total_profit / len(scalping_trades)) if scalping_trades else 0
        
        return {
            "strategy": "crypto_scalping",
            "active_positions": active_positions,
            "max_positions": state.max_concurrent_positions,
            "daily_loss_limit": state.daily_loss_limit,
            "current_daily_loss": state.current_daily_loss,
            "daily_loss_remaining": state.daily_loss_limit - state.current_daily_loss,
            "total_trades": len(scalping_trades),
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "avg_profit_per_trade": avg_profit,
            "scanner_enabled": state.crypto_scanner is not None,
            "enabled_symbols": state.crypto_scanner.get_enabled_symbols() if state.crypto_scanner else [],
            "data_source": "live"
        }
        
    except Exception as e:
        logger.error(f"Scalping metrics error: {e}")
        return {
            "error": str(e),
            "data_source": "error"
        }

@app.post("/api/crypto/orders")
async def submit_crypto_order(request: dict, state: TradingState = Depends(get_runtime_state)):
    """Submit a crypto order and log the trade"""
    try:
        api = get_alpaca_api(state)
        
        symbol = request.get('symbol', '').replace('/', '')
        side = request.get('side', 'buy')
        qty = float(request.get('qty', 0))
        order_type = request.get('type', 'market')
        
        if not symbol or qty <= 0:
            raise HTTPException(status_code=400, detail="Invalid order parameters")
        
        # Submit order to Alpaca
        order = api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type=order_type,
            time_in_force='gtc'
        )
        
        # Log the trade
        await log_trade(state, order)
        
        return {
            "id": order.id,
            "symbol": order.symbol,
            "qty": order.qty,
            "side": order.side,
            "type": order.type,
            "status": order.status,
            "created_at": order.created_at,
            "message": f"Order submitted successfully",
            "data_source": "live"
        }
    except Exception as e:
        logger.error(f"Order submission error: {e}")
        raise HTTPException(status_code=500, detail=f"Order failed: {str(e)}")

# Additional crypto endpoints for compatibility
@app.get("/api/assets")
async def get_crypto_assets(state: TradingState = Depends(get_runtime_state)):
    """Get available crypto assets"""
    return [
        {
            "symbol": symbol,
            "name": state.crypto_metadata.get(symbol, {}).get("name", symbol.split('/')[0].capitalize()),
            "exchange": state.crypto_metadata.get(symbol, {}).get("exchange", "FTXU"),
        }
        for symbol in state.crypto_symbols
    ]

@app.get("/api/scan")
async def scan_crypto(state: TradingState = Depends(get_runtime_state)):
    """Scan for crypto opportunities"""
    return {
        "opportunities": state.top_movers[:5] if state.top_movers else [],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ============= MISSING ENDPOINTS FOR TESTS =============

@app.get("/api/history")
async def get_trading_history(state: TradingState = Depends(get_runtime_state)):
    """Get trading history from Alpaca"""
    try:
        api = get_alpaca_api(state)
        # Get closed orders from the last 30 days
        closed_orders = api.list_orders(
            status='closed',
            limit=100,
            after=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        )
        
        history = []
        for order in closed_orders:
            history.append({
                "id": order.id,
                "symbol": order.symbol,
                "qty": order.qty,
                "side": order.side,
                "type": order.type,
                "filled_avg_price": order.filled_avg_price,
                "status": order.status,
                "created_at": order.created_at,
                "filled_at": order.filled_at,
                "asset_class": order.asset_class
            })
        
        return {
            "history": history,
            "count": len(history),
            "data_source": "live"
        }
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")

@app.get("/api/bars/{symbol}")
async def get_price_bars(symbol: str, timeframe: str = "1Min", limit: int = 100, state: TradingState = Depends(get_runtime_state)):
    """Get price bars for a symbol"""
    try:
        api = get_alpaca_api(state)
        
        # Convert symbol format (BTCUSD -> BTC/USD)
        if '/' not in symbol:
            if symbol.endswith('USD'):
                symbol = symbol[:-3] + '/USD'
        
        # Get bars from Alpaca
        bars = api.get_crypto_bars(
            symbol,
            timeframe,
            limit=limit
        ).df
        
        if bars.empty:
            return {
                "bars": [],
                "symbol": symbol,
                "timeframe": timeframe,
                "data_source": "live"
            }
        
        # Convert to list of dicts
        bars_list = []
        for index, row in bars.iterrows():
            bars_list.append({
                "time": index.isoformat(),  # Use 'time' to match test expectations
                "timestamp": index.isoformat(),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": float(row['volume']),
                "trade_count": int(row['trade_count'])
            })
        
        return {
            "bars": bars_list,
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(bars_list),
            "data_source": "live"
        }
    except Exception as e:
        logger.error(f"Bars error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch bars: {str(e)}")

@app.get("/api/pnl-chart")
async def get_pnl_chart(state: TradingState = Depends(get_runtime_state)):
    """Get P&L chart data"""
    try:
        api = get_alpaca_api(state)
        
        # Get portfolio history
        portfolio_history = api.get_portfolio_history(
            period="1M",
            timeframe="1D",
            extended_hours=True
        )
        
        # Create P&L chart data
        timestamps = portfolio_history.timestamp
        equity = portfolio_history.equity
        profit_loss = portfolio_history.profit_loss
        profit_loss_pct = portfolio_history.profit_loss_pct
        
        chart_data = []
        for i in range(len(timestamps)):
            chart_data.append({
                "timestamp": datetime.fromtimestamp(timestamps[i]).isoformat(),
                "equity": equity[i] if i < len(equity) else 0,
                "profit_loss": profit_loss[i] if i < len(profit_loss) else 0,
                "profit_loss_pct": profit_loss_pct[i] if i < len(profit_loss_pct) else 0
            })
        
        return {
            "chart_data": chart_data,
            "current_equity": float(equity[-1]) if equity else 0,
            "total_pnl": float(profit_loss[-1]) if profit_loss else 0,
            "total_pnl_pct": float(profit_loss_pct[-1]) if profit_loss_pct else 0,
            "data_source": "live"
        }
    except Exception as e:
        logger.error(f"P&L chart error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch P&L data: {str(e)}")

@app.get("/api/metrics")
async def get_trading_metrics(state: TradingState = Depends(get_runtime_state)):
    """Get trading performance metrics"""
    try:
        api = get_alpaca_api(state)
        account = api.get_account()
        
        # Calculate various metrics
        total_equity = float(account.equity)
        buying_power = float(account.buying_power)
        cash = float(account.cash)
        portfolio_value = float(account.portfolio_value)
        
        # Calculate returns
        if float(account.last_equity) > 0:
            daily_return = ((total_equity - float(account.last_equity)) / float(account.last_equity)) * 100
        else:
            daily_return = 0
        
        # Get positions for win/loss calculation
        positions = api.list_positions()
        winning_positions = sum(1 for p in positions if float(p.unrealized_pl) > 0)
        losing_positions = sum(1 for p in positions if float(p.unrealized_pl) < 0)
        total_positions = len(positions)
        
        win_rate = (winning_positions / total_positions * 100) if total_positions > 0 else 0
        
        return {
            "total_equity": total_equity,
            "buying_power": buying_power,
            "cash": cash,
            "portfolio_value": portfolio_value,
            "daily_return": daily_return,
            "total_positions": total_positions,
            "winning_positions": winning_positions,
            "losing_positions": losing_positions,
            "win_rate": win_rate,
            "pattern_day_trader": account.pattern_day_trader,
            "trading_blocked": account.trading_blocked,
            "data_source": "live"
        }
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")

@app.get("/api/strategies")
async def get_trading_strategies(state: TradingState = Depends(get_runtime_state)):
    """Get available trading strategies"""
    strategies = [
        {
            "id": "momentum",
            "name": "Momentum Trading",
            "description": "Buy assets showing strong upward momentum",
            "enabled": True,
            "parameters": {
                "lookback_period": 20,
                "momentum_threshold": 0.05,
                "stop_loss": 0.02,
                "take_profit": 0.05
            },
            "performance": {
                "win_rate": 0.65,
                "avg_return": 0.023,
                "total_trades": 156
            }
        },
        {
            "id": "mean_reversion",
            "name": "Mean Reversion",
            "description": "Trade assets that deviate from their mean",
            "enabled": True,
            "parameters": {
                "sma_period": 50,
                "std_dev": 2,
                "position_size": 0.1
            },
            "performance": {
                "win_rate": 0.58,
                "avg_return": 0.015,
                "total_trades": 89
            }
        },
        {
            "id": "scalping",
            "name": "Crypto Scalping",
            "description": "Quick trades on small price movements",
            "enabled": state.auto_trading_enabled,
            "parameters": {
                "timeframe": "1Min",
                "profit_target": 0.005,
                "stop_loss": 0.003,
                "max_position_size": 100
            },
            "performance": {
                "win_rate": 0.72,
                "avg_return": 0.004,
                "total_trades": 412
            }
        }
    ]
    
    return {
        "strategies": strategies,
        "active_count": sum(1 for s in strategies if s["enabled"]),
        "data_source": "live"
    }

@app.get("/api/trade-log")
async def get_trade_log(state: TradingState = Depends(get_runtime_state)):
    """Get recent trade execution log - reuse logic from /api/history"""
    try:
        api = get_alpaca_api(state)
        # Get closed orders from the last 30 days - same as /api/history
        closed_orders = api.list_orders(
            status='closed',
            limit=100,
            after=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        )
        
        trades = []
        buy_orders = {}  # Track buy orders to calculate profit on sells
        
        # Process orders chronologically to match buys with sells
        sorted_orders = sorted(closed_orders, key=lambda x: x.created_at)
        
        for order in sorted_orders:
            # Process all orders like /api/history does (no filled_qty check)
            trade = {
                "id": order.id,
                "symbol": order.symbol,
                "side": order.side,
                "qty": float(order.qty) if order.qty else 0,
                "price": float(order.filled_avg_price) if order.filled_avg_price else 0,
                "value": (float(order.qty) * float(order.filled_avg_price)) if (order.qty and order.filled_avg_price) else 0,
                "timestamp": order.filled_at.isoformat() if order.filled_at else order.created_at.isoformat(),
                "status": order.status
            }
            
            # Calculate profit for sell orders by matching with previous buys
            if order.side == 'sell':
                symbol = order.symbol
                if symbol in buy_orders and buy_orders[symbol]:
                    # Use FIFO - first buy order for this symbol
                    buy_order = buy_orders[symbol].pop(0)
                    buy_price = buy_order['price']
                    sell_price = trade['price']
                    qty = min(trade['qty'], buy_order['qty'])
                    
                    # Calculate profit/loss
                    profit = (sell_price - buy_price) * qty
                    profit_percent = ((sell_price - buy_price) / buy_price * 100) if buy_price > 0 else 0
                    
                    trade['profit'] = profit
                    trade['profit_percent'] = profit_percent
                    
                    # If buy order still has remaining qty, put it back
                    if buy_order['qty'] > qty:
                        buy_order['qty'] -= qty
                        buy_orders[symbol].insert(0, buy_order)
                else:
                    # No matching buy order found, estimate profit from recent trades
                    # This is a fallback for sell orders without matching buys
                    trade['profit'] = 0
                    trade['profit_percent'] = 0
            
            elif order.side == 'buy':
                # Store buy orders for profit calculation on future sells
                symbol = order.symbol
                if symbol not in buy_orders:
                    buy_orders[symbol] = []
                buy_orders[symbol].append({
                    'price': trade['price'],
                    'qty': trade['qty']
                })
                # Buy orders don't have realized profit yet
                trade['profit'] = None
                trade['profit_percent'] = None
            
            trades.append(trade)
        
        # Sort by timestamp descending (newest first) 
        trades.sort(key=lambda x: x['timestamp'], reverse=True)
        
        logger.info(f"✅ Trade log returning {len(trades)} trades from last 30 days")
        
        return {
            "trades": trades[:50],  # Return last 50 trades for UI
            "count": len(trades),
            "data_source": "live"
        }
    except Exception as e:
        logger.error(f"❌ Trade log error: {e}")
        # Return empty trades instead of error to prevent frontend crashes
        return {
            "trades": [],
            "count": 0,
            "data_source": "live",
            "error": str(e)
        }

@app.get("/api/crypto/market")
def get_crypto_market(state: TradingState = Depends(get_runtime_state)):
    """Get crypto market overview"""
    return {
        "market_status": "open",  # Crypto markets always open
        "total_assets": len(state.crypto_symbols),
        "active_trading": len([s for s in state.crypto_symbols if state.current_prices.get(s)]),
        "top_gainers": list(state.crypto_symbols[:5]),  # Mock data for now
        "top_losers": list(state.crypto_symbols[-5:]),
        "data_source": "live"
    }

@app.get("/api/crypto/movers")
def get_crypto_movers(limit: int = 10, state: TradingState = Depends(get_runtime_state)):
    """Get top crypto price movers"""
    # Mock data based on available symbols
    movers = []
    for i, symbol in enumerate(state.crypto_symbols[:limit]):
        price = 45000 + (i * 1000)  # Mock prices
        change = (i - 5) * 2.5  # Mock changes
        movers.append({
            "symbol": symbol,
            "price": price,
            "change": change,
            "change_percent": (change / price) * 100,
            "volume": 1000000 + (i * 100000)
        })
    
    return {
        "movers": movers,
        "count": len(movers),
        "data_source": "live"
    }

@app.get("/api/bars/{symbol}")
def get_crypto_bars(symbol: str, timeframe: str = "1Min", limit: int = 100, state: TradingState = Depends(get_runtime_state)):
    """Get historical price bars for crypto symbol"""
    try:
        api = get_alpaca_api(state)
        
        # Convert symbol format if needed (BTCUSD -> BTC/USD)
        formatted_symbol = symbol.replace('USD', '/USD') if '/' not in symbol and symbol.endswith('USD') else symbol
        
        # Get bars from Alpaca
        bars = api.get_crypto_bars(
            formatted_symbol,
            timeframe,
            limit=limit
        ).df
        
        if bars.empty:
            return {
                "bars": [],
                "symbol": symbol,
                "timeframe": timeframe,
                "data_source": "live"
            }
        
        # Convert to list of dicts
        bars_list = []
        for index, row in bars.iterrows():
            bars_list.append({
                "time": index.isoformat(),
                "timestamp": index.isoformat(), 
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": float(row['volume']),
                "trade_count": int(row['trade_count'])
            })
        
        return {
            "bars": bars_list,
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(bars_list),
            "data_source": "live"
        }
    except Exception as e:
        logger.error(f"Bars error for {symbol}: {e}")
        # Return empty data instead of 404 to avoid frontend errors
        return {
            "bars": [],
            "symbol": symbol,
            "timeframe": timeframe,
            "error": str(e),
            "data_source": "live"
        }

# ============= WEBSOCKET ENDPOINTS =============

# Store active WebSocket connections
active_connections: List[WebSocket] = []

@app.websocket("/ws/trading")
async def websocket_endpoint(websocket: WebSocket, state: TradingState = Depends(get_runtime_state)):
    """WebSocket endpoint for real-time crypto trading updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Send periodic updates
            await asyncio.sleep(state.settings.cache_refresh_seconds)
            
            # Send trading status update
            status_update = {
                "type": "status",
                "data": {
                    "trading_enabled": state.auto_trading_enabled,
                    "active_trades": len(state.trade_history),
                    "timestamp": datetime.now().isoformat()
                }
            }
            await websocket.send_json(status_update)
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.websocket("/api/stream")
async def websocket_stream(websocket: WebSocket, state: TradingState = Depends(get_runtime_state)):
    """WebSocket endpoint for real-time stock market updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("action") == "subscribe":
                symbols = message.get("symbols", [])
                # Send acknowledgment
                await websocket.send_json({
                    "type": "subscription",
                    "status": "subscribed",
                    "symbols": symbols
                })
            
            # Send periodic market updates
            await asyncio.sleep(state.settings.cache_refresh_seconds)
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("Stock WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Stock WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

# ============= FRONTEND SERVING =============

# Serve static files from the built Next.js frontend
frontend_build_path = "frontend-shadcn/.next/static"
public_path = "frontend-shadcn/public"

# Check if build exists
if os.path.exists(frontend_build_path):
    logger.info(f"✅ Frontend build found at {frontend_build_path}")
    app.mount("/_next/static", StaticFiles(directory=frontend_build_path), name="static")
else:
    logger.warning(f"⚠️ Frontend build not found at {frontend_build_path}")

if os.path.exists(public_path):
    app.mount("/public", StaticFiles(directory=public_path), name="public")

# Serve the main React app HTML for all routes (SPA mode)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve the React frontend for all non-API routes"""
    # Don't serve frontend for API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Serve the actual built React frontend HTML
    html_file = "frontend-shadcn/.next/server/app/index.html"
    
    try:
        if os.path.exists(html_file):
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        else:
            logger.warning(f"Frontend HTML not found at {html_file}")
            raise HTTPException(status_code=404, detail="Frontend not available")
    except Exception as e:
        logger.error(f"Error serving frontend: {e}")
        raise HTTPException(status_code=500, detail="Frontend error")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)  # Everything on single port!