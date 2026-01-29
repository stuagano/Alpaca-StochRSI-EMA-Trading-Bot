import asyncio
import logging
import os
import signal
import sys
import threading
from typing import Optional, Union

try:
    from prometheus_client import Counter, Gauge, start_http_server
except ImportError:  # pragma: no cover - optional dependency
    Counter = None  # type: ignore[assignment]
    Gauge = None  # type: ignore[assignment]

    def start_http_server(_port: int) -> None:  # type: ignore[override]
        """Fallback when ``prometheus_client`` is not installed."""

        return


from config.unified_config import get_config
from strategies.crypto_scalping_strategy import (
    CryptoDayTradingBot,
    create_crypto_day_trader,
    register_activity_logger,
)
from utils.logging_config import setup_logging
from utils.alpaca import load_alpaca_credentials

# Global reference to the trading bot for the dashboard
_active_bot: Optional[CryptoDayTradingBot] = None
_alpaca_client = None

# Activity log for dashboard stream-of-consciousness view
from collections import deque
from datetime import datetime

_activity_log: deque = deque(maxlen=200)  # Keep last 200 entries
_activity_lock = threading.Lock()


def log_activity(message: str, level: str = "info", symbol: str = None):
    """Add an entry to the activity log for dashboard display."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message,
        "symbol": symbol,
    }
    with _activity_lock:
        _activity_log.appendleft(entry)


# Register the activity logger callback with the strategy module
register_activity_logger(log_activity)


# Simple cache to avoid rate limiting
import time as _time

_quote_cache: dict = {}
_indicator_cache: dict = {}
_QUOTE_CACHE_TTL = 2.0  # seconds
_INDICATOR_CACHE_TTL = 5.0  # seconds (indicators change slower)


def _get_cached_quote(symbol: str) -> Optional[dict]:
    """Get quote from cache if not expired."""
    if symbol in _quote_cache:
        data, timestamp = _quote_cache[symbol]
        if _time.time() - timestamp < _QUOTE_CACHE_TTL:
            return data
    return None


def _set_cached_quote(symbol: str, data: dict) -> None:
    """Store quote in cache with timestamp."""
    _quote_cache[symbol] = (data, _time.time())


def _get_cached_indicators(cache_key: str) -> Optional[dict]:
    """Get indicators from cache if not expired."""
    if cache_key in _indicator_cache:
        data, timestamp = _indicator_cache[cache_key]
        if _time.time() - timestamp < _INDICATOR_CACHE_TTL:
            return data
    return None


def _set_cached_indicators(cache_key: str, data: dict) -> None:
    """Store indicators in cache with timestamp."""
    _indicator_cache[cache_key] = (data, _time.time())


ALPACA_IMPORT_ERROR: Optional[Exception]

# Import Alpaca client - prefer legacy SDK for compatibility with existing strategy code
try:
    import alpaca_trade_api as tradeapi

    ALPACA_IMPORT_ERROR = None
except ImportError as e:
    logging.error("Failed to import alpaca_trade_api: %s", e)
    logging.error(
        "Install alpaca_trade_api with 'pip install alpaca-trade-api' to enable live trading."
    )
    tradeapi = None  # type: ignore[assignment]
    ALPACA_IMPORT_ERROR = e

# Also try importing new SDK for potential future use
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import GetAssetsRequest
    from alpaca.data.historical import CryptoHistoricalDataClient
except ImportError:
    TradingClient = None  # type: ignore[assignment]
    GetAssetsRequest = None  # type: ignore[assignment]
    CryptoHistoricalDataClient = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def get_active_bot():
    """Get the currently running trading bot instance."""
    return _active_bot


def get_alpaca_client():
    """Get the Alpaca client instance."""
    return _alpaca_client


def start_dashboard_server(host="0.0.0.0", port=5001):
    """Start the Flask dashboard server in a background thread."""
    try:
        from flask import Flask, jsonify, send_from_directory
        from flask_cors import CORS

        # Get the project root directory for static files
        project_root = os.path.dirname(os.path.abspath(__file__))
        frontend_dir = os.path.join(project_root, "frontend")

        app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
        CORS(app)

        @app.route("/")
        def index():
            return send_from_directory(app.static_folder, "dashboard.html")

        @app.route("/<path:path>")
        def static_files(path):
            return send_from_directory(app.static_folder, path)

        @app.route("/api/v1/status")
        def api_status():
            bot = get_active_bot()
            return jsonify(
                {
                    "status": "running" if bot and bot.is_running else "stopped",
                    "trading_mode": "crypto",
                    "market_status": "OPEN",
                }
            )

        @app.route("/api/v1/activity")
        def api_activity():
            """Get recent activity log entries for dashboard stream."""
            from flask import request
            limit = request.args.get("limit", 50, type=int)
            since = request.args.get("since", None)  # ISO timestamp to get newer entries

            with _activity_lock:
                entries = list(_activity_log)

            # Filter by timestamp if 'since' provided
            if since:
                entries = [e for e in entries if e["timestamp"] > since]

            return jsonify({
                "entries": entries[:limit],
                "total": len(_activity_log),
            })

        @app.route("/api/v1/account")
        def api_account():
            client = get_alpaca_client()
            if not client:
                return jsonify({"error": "No client"}), 503
            try:
                account = client.get_account()
                return jsonify(
                    {
                        "portfolio_value": float(account.portfolio_value),
                        "buying_power": float(account.buying_power),
                        "cash": float(account.cash),
                        "equity": float(account.equity),
                        "status": account.status,
                    }
                )
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/positions")
        def api_positions():
            client = get_alpaca_client()
            if not client:
                return jsonify([])
            try:
                positions = client.list_positions()
                return jsonify(
                    [
                        {
                            "symbol": p.symbol,
                            "qty": float(p.qty),
                            "avg_entry_price": float(p.avg_entry_price),
                            "avg_price": float(p.avg_entry_price),
                            "current_price": float(p.current_price),
                            "unrealized_pl": float(p.unrealized_pl),
                            "unrealized_plpc": float(p.unrealized_plpc) * 100,
                            "market_value": float(p.market_value),
                            "side": p.side,
                        }
                        for p in positions
                    ]
                )
            except Exception as e:
                logger.error(f"Error fetching positions: {e}")
                return jsonify([])

        @app.route("/api/v1/positions/<symbol>/close", methods=["POST"])
        def api_close_position(symbol):
            """Manually close a position."""
            client = get_alpaca_client()
            if not client:
                return jsonify({"error": "No client"}), 500
            try:
                # Get current position
                position = client.get_position(symbol)
                qty = abs(float(position.qty))
                side = "sell" if float(position.qty) > 0 else "buy"

                # Place market order to close
                order = client.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    type="market",
                    time_in_force="ioc",
                )

                logger.info(f"Manually closed position: {symbol} qty={qty}")
                return jsonify(
                    {
                        "status": "success",
                        "symbol": symbol,
                        "qty_closed": qty,
                        "order_id": order.id,
                    }
                )
            except Exception as e:
                logger.error(f"Error closing position {symbol}: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/bot/status")
        def api_bot_status():
            bot = get_active_bot()
            if not bot:
                return jsonify({"status": "not_started", "bot": None})

            try:
                if hasattr(bot, "get_status"):
                    status = bot.get_status()
                    return jsonify(
                        {
                            "status": "running"
                            if status.get("is_running")
                            else "stopped",
                            "bot": status,
                        }
                    )
                else:
                    return jsonify(
                        {
                            "status": "running" if bot.is_running else "stopped",
                            "bot": {
                                "is_running": bot.is_running,
                                "active_positions_count": len(
                                    getattr(bot, "active_positions", {})
                                ),
                                "total_trades": getattr(bot, "total_trades", 0),
                                "daily_profit": getattr(bot, "daily_profit", 0),
                                "win_rate": getattr(bot, "win_rate", 0),
                                "positions": [],
                            },
                        }
                    )
            except Exception as e:
                logger.error(f"Error getting bot status: {e}")
                return jsonify({"status": "error", "bot": None})

        @app.route("/api/v1/signals")
        def api_signals():
            bot = get_active_bot()
            if not bot or not hasattr(bot, "scanner"):
                return jsonify([])
            try:
                # Get recent signals from scanner
                signals = bot.scanner.scan_for_opportunities() if bot.scanner else []
                return jsonify(
                    [
                        {
                            "symbol": s.symbol,
                            "action": s.action.upper(),
                            "confidence": s.confidence,
                            "price": s.price,
                            "strength": "strong"
                            if s.confidence >= 0.8
                            else "medium"
                            if s.confidence >= 0.6
                            else "weak",
                            "rsi": getattr(s, "rsi", None),
                            "timestamp": s.timestamp.isoformat()
                            if hasattr(s, "timestamp")
                            else None,
                        }
                        for s in signals[:20]
                    ]
                )
            except Exception as e:
                logger.error(f"Error getting signals: {e}")
                return jsonify([])

        @app.route("/api/v1/pnl/trades")
        def api_trades():
            bot = get_active_bot()
            if not bot or not hasattr(bot, "alpaca"):
                return jsonify({"trades": []})
            try:
                # Fetch recent closed orders from Alpaca using legacy REST API
                orders = bot.alpaca.list_orders(status="closed", limit=50)

                return jsonify(
                    {
                        "trades": [
                            {
                                "symbol": o.symbol,
                                "side": str(o.side),
                                "qty": float(o.filled_qty) if o.filled_qty else 0,
                                "price": float(o.filled_avg_price)
                                if o.filled_avg_price
                                else 0,
                                "status": str(o.status),
                                "pnl": 0,  # Alpaca orders don't include P&L
                                "timestamp": o.filled_at
                                if o.filled_at
                                else o.created_at,
                                "time": o.filled_at if o.filled_at else o.created_at,
                            }
                            for o in orders
                            if o.filled_qty and float(o.filled_qty) > 0
                        ]
                    }
                )
            except Exception as e:
                logger.error(f"Error getting trades from Alpaca: {e}")
                return jsonify({"trades": []})
            try:
                # Fetch recent closed orders from Alpaca using bot's client
                from alpaca.trading.requests import GetOrdersRequest
                from alpaca.trading.enums import QueryOrderStatus

                request = GetOrdersRequest(status=QueryOrderStatus.CLOSED, limit=50)
                orders = bot.alpaca.get_orders(filter=request)

                return jsonify(
                    {
                        "trades": [
                            {
                                "symbol": o.symbol,
                                "side": str(o.side.value)
                                if hasattr(o.side, "value")
                                else str(o.side),
                                "qty": float(o.filled_qty) if o.filled_qty else 0,
                                "price": float(o.filled_avg_price)
                                if o.filled_avg_price
                                else 0,
                                "status": str(o.status.value)
                                if hasattr(o.status, "value")
                                else str(o.status),
                                "pnl": 0,  # Alpaca orders don't include P&L
                                "timestamp": o.filled_at.isoformat()
                                if o.filled_at
                                else o.created_at.isoformat(),
                                "time": o.filled_at.isoformat()
                                if o.filled_at
                                else o.created_at.isoformat(),
                            }
                            for o in orders
                            if o.filled_qty and float(o.filled_qty) > 0
                        ]
                    }
                )
            except Exception as e:
                logger.error(f"Error getting trades from Alpaca: {e}")
                return jsonify({"trades": []})

        @app.route("/api/v1/bot/thresholds", methods=["GET", "POST"])
        def api_bot_thresholds():
            bot = get_active_bot()
            if not bot:
                return jsonify({"error": "Bot not running"}), 503
            # Return current thresholds from bot (frontend expects _pct suffix)
            return jsonify(
                {
                    "stop_loss_pct": getattr(bot, "stop_loss_pct", 0.015),
                    "take_profit_pct": getattr(bot, "min_profit_target", 0.02),
                    "trailing_stop_pct": getattr(bot, "trailing_stop_pct", 0.01),
                    "max_hold_time_seconds": getattr(bot, "max_hold_time", 3600),
                    "max_position_size": getattr(bot, "max_position_size", 25),
                    "max_positions": getattr(bot, "max_concurrent_positions", 50),
                }
            )

        @app.route("/api/v1/activity/summary")
        def api_activity_summary():
            bot = get_active_bot()
            return jsonify(
                {
                    "total_scans": getattr(bot, "total_scans", 0) if bot else 0,
                    "signals_generated": 0,
                    "trades_executed": getattr(bot, "total_trades", 0) if bot else 0,
                    "recent_activity": [],
                }
            )

        @app.route("/api/v1/signals/analysis")
        def api_signals_analysis():
            """Get full signal analysis for all tracked symbols - shows why trades are/aren't taken."""
            from strategies.constants import RISK

            bot = get_active_bot()
            if not bot or not hasattr(bot, "scanner"):
                return jsonify(
                    {"signals": [], "min_score_required": RISK.MIN_SIGNAL_SCORE}
                )

            try:
                scanner = bot.scanner
                signals_data = []
                min_score = RISK.MIN_SIGNAL_SCORE  # SCALPING: Lower threshold (2 pts)

                # Analyze ALL tracked symbols, not just ones with buy signals
                for symbol in scanner.high_volume_pairs:
                    try:
                        # Get current price data
                        prices = scanner.price_data.get(symbol, [])
                        if len(prices) < 2:
                            signals_data.append(
                                {
                                    "symbol": symbol,
                                    "action": "WAIT",
                                    "buy_score": 0,
                                    "sell_score": 0,
                                    "min_required": min_score,
                                    "would_trade": False,
                                    "price": 0,
                                    "indicators": {},
                                    "reasons": ["Insufficient price data"],
                                }
                            )
                            continue

                        current_price = prices[-1]

                        # Get indicators
                        indicators = scanner.get_indicators(symbol)
                        if not indicators:
                            signals_data.append(
                                {
                                    "symbol": symbol,
                                    "action": "WAIT",
                                    "buy_score": 0,
                                    "sell_score": 0,
                                    "min_required": min_score,
                                    "would_trade": False,
                                    "price": current_price,
                                    "indicators": {},
                                    "reasons": ["Waiting for indicator data"],
                                }
                            )
                            continue

                        rsi = indicators.get("rsi", 50)
                        macd_hist = indicators.get("macd_histogram", 0)
                        stoch_k = indicators.get("stoch_k", 50)
                        ema_cross = indicators.get("ema_cross", "neutral")

                        # Calculate volume surge
                        volumes = scanner.volume_data.get(symbol, [])
                        volume_surge = (
                            scanner.detect_volume_surge(volumes) if volumes else False
                        )

                        # Calculate buy score (STRICT - matches updated strategy)
                        buy_score = 0
                        buy_reasons = []

                        # BLOCK: Never buy when RSI shows overbought
                        if rsi > 55:
                            buy_score = -10
                            buy_reasons.append(f"BLOCKED: RSI extended ({rsi:.1f})")
                        elif stoch_k > 75:
                            buy_score = -10
                            buy_reasons.append(
                                f"BLOCKED: StochRSI high ({stoch_k:.1f})"
                            )
                        else:
                            # RSI scoring - must be below 50 to get points
                            if rsi < 25:
                                buy_score += 4
                                buy_reasons.append(f"RSI very low ({rsi:.1f})")
                            elif rsi < 30:
                                buy_score += 3
                                buy_reasons.append(f"RSI oversold ({rsi:.1f})")
                            elif rsi < 40:
                                buy_score += 2
                                buy_reasons.append(f"RSI low ({rsi:.1f})")
                            elif rsi < 50:
                                buy_score += 1
                                buy_reasons.append(f"RSI neutral ({rsi:.1f})")

                            # StochRSI scoring
                            if stoch_k < 15:
                                buy_score += 4
                                buy_reasons.append(f"StochRSI very low ({stoch_k:.1f})")
                            elif stoch_k < 25:
                                buy_score += 3
                                buy_reasons.append(f"StochRSI oversold ({stoch_k:.1f})")
                            elif stoch_k < 40:
                                buy_score += 2
                                buy_reasons.append(f"StochRSI low ({stoch_k:.1f})")
                            elif stoch_k < 50:
                                buy_score += 1
                                buy_reasons.append(f"StochRSI neutral ({stoch_k:.1f})")

                            if macd_hist > 0:
                                buy_score += 1
                                buy_reasons.append("MACD positive")

                            if ema_cross == "bullish":
                                buy_score += 1
                                buy_reasons.append("EMA bullish cross")

                            if volume_surge and buy_score >= 3:
                                buy_score += 1
                                buy_reasons.append("Volume surge")

                        # Calculate sell score
                        sell_score = 0
                        sell_reasons = []

                        if rsi > 75:
                            sell_score += 3
                            sell_reasons.append(f"RSI very high ({rsi:.1f})")
                        elif rsi > 70:
                            sell_score += 2
                            sell_reasons.append(f"RSI overbought ({rsi:.1f})")
                        elif rsi > 65:
                            sell_score += 1
                            sell_reasons.append(f"RSI high ({rsi:.1f})")

                        if macd_hist < 0:
                            sell_score += 1
                            sell_reasons.append("MACD negative")

                        if stoch_k > 80:
                            sell_score += 3
                            sell_reasons.append(f"StochRSI very high ({stoch_k:.1f})")
                        elif stoch_k > 70:
                            sell_score += 2
                            sell_reasons.append(f"StochRSI overbought ({stoch_k:.1f})")

                        if ema_cross == "bearish":
                            sell_score += 2
                            sell_reasons.append("EMA bearish cross")

                        if volume_surge:
                            sell_score += 1
                            sell_reasons.append("Volume surge")

                        # Determine action
                        if buy_score >= min_score and buy_score > sell_score:
                            action = "BUY"
                            reasons = buy_reasons
                            would_trade = True
                        elif sell_score >= min_score and sell_score > buy_score:
                            action = "SELL"
                            reasons = sell_reasons
                            would_trade = False  # No shorting
                            reasons.append("(No shorting - signal only)")
                        else:
                            action = "HOLD"
                            reasons = [
                                f"Buy score {buy_score}/{min_score}, Sell score {sell_score}/{min_score}"
                            ]
                            if buy_reasons:
                                reasons.append(f"Buy factors: {', '.join(buy_reasons)}")
                            if sell_reasons:
                                reasons.append(
                                    f"Sell factors: {', '.join(sell_reasons)}"
                                )
                            if not buy_reasons and not sell_reasons:
                                reasons.append("No strong signals detected")
                            would_trade = False

                        signals_data.append(
                            {
                                "symbol": symbol,
                                "action": action,
                                "buy_score": buy_score,
                                "sell_score": sell_score,
                                "min_required": min_score,
                                "would_trade": would_trade,
                                "price": float(current_price) if current_price else 0,
                                "indicators": {
                                    "rsi": float(rsi) if rsi is not None else None,
                                    "stoch_k": float(stoch_k)
                                    if stoch_k is not None
                                    else None,
                                    "macd_histogram": float(macd_hist)
                                    if macd_hist is not None
                                    else None,
                                    "ema_cross": str(ema_cross)
                                    if ema_cross
                                    else "neutral",
                                    "volume_surge": bool(volume_surge),
                                },
                                "reasons": reasons,
                            }
                        )

                    except Exception as symbol_err:
                        logger.warning(f"Error analyzing {symbol}: {symbol_err}")
                        signals_data.append(
                            {
                                "symbol": symbol,
                                "action": "ERROR",
                                "buy_score": 0,
                                "sell_score": 0,
                                "min_required": min_score,
                                "would_trade": False,
                                "price": 0,
                                "indicators": {},
                                "reasons": [str(symbol_err)],
                            }
                        )

                # Sort by action priority: BUY first, then SELL, then HOLD
                action_order = {"BUY": 0, "SELL": 1, "HOLD": 2, "WAIT": 3, "ERROR": 4}
                signals_data.sort(
                    key=lambda x: (action_order.get(x["action"], 5), -x["buy_score"])
                )

                return jsonify(
                    {
                        "signals": signals_data,
                        "min_score_required": min_score,
                        "total_symbols": len(scanner.high_volume_pairs),
                        "symbols_analyzed": len(signals_data),
                    }
                )

            except Exception as e:
                logger.error(f"Error in signal analysis: {e}")
                return jsonify(
                    {"signals": [], "min_score_required": 3, "error": str(e)}
                )

        @app.route("/api/v1/learning/insights")
        def api_learning_insights():
            """Get insights from the trade learning system."""
            try:
                from strategies.trade_learner import get_trade_learner

                learner = get_trade_learner()
                return jsonify(learner.get_insights_summary())
            except Exception as e:
                logger.error(f"Error getting learning insights: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/learning/analyze", methods=["POST"])
        def api_learning_analyze():
            """Trigger analysis of trade history to update insights."""
            try:
                from strategies.trade_learner import get_trade_learner

                learner = get_trade_learner()
                learner.analyze_and_learn()
                return jsonify(
                    {
                        "status": "success",
                        "message": "Analysis complete",
                        "insights": learner.get_insights_summary(),
                    }
                )
            except Exception as e:
                logger.error(f"Error running learning analysis: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/learning/trades")
        def api_learning_trades():
            """Get recorded trades from the learning system."""
            try:
                from strategies.trade_learner import get_trade_learner
                from dataclasses import asdict

                learner = get_trade_learner()
                limit = int(request.args.get("limit", 50))
                trades = learner.trades[-limit:] if learner.trades else []
                return jsonify(
                    {
                        "total_trades": len(learner.trades),
                        "trades": [asdict(t) for t in reversed(trades)],
                    }
                )
            except Exception as e:
                logger.error(f"Error getting learning trades: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/learning/save", methods=["POST"])
        def api_learning_save():
            """Force save the learning data to disk."""
            try:
                from strategies.trade_learner import get_trade_learner

                learner = get_trade_learner()
                learner._save_data()
                return jsonify(
                    {
                        "status": "success",
                        "message": f"Saved {len(learner.trades)} trades",
                        "insights_total": learner.insights.total_trades,
                    }
                )
            except Exception as e:
                logger.error(f"Error saving learning data: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/pnl/chart-data")
        def api_pnl_chart():
            client = get_alpaca_client()
            if not client:
                return jsonify({"labels": [], "datasets": []})

            try:
                # Get portfolio history from Alpaca (last 6 hours, 5-minute intervals for detail)
                from datetime import datetime, timedelta

                history = client.get_portfolio_history(period="6H", timeframe="5Min")

                if not history or not history.timestamp:
                    return jsonify({"labels": [], "datasets": []})

                # Build chart data from portfolio history
                labels = []
                equity_data = []
                hourly_pnl = []
                cumulative_pnl = []

                timestamps = history.timestamp
                equity = history.equity
                profit_loss = (
                    history.profit_loss if hasattr(history, "profit_loss") else []
                )

                # Get starting equity to calculate cumulative P&L
                base_equity = float(equity[0]) if equity else 0

                for i, ts in enumerate(timestamps):
                    # Convert timestamp to readable time (show every label, frontend will handle density)
                    dt = datetime.fromtimestamp(ts)
                    labels.append(dt.strftime("%H:%M"))  # 5-min intervals

                    if i < len(equity):
                        eq = round(float(equity[i]), 2)
                        equity_data.append(eq)
                        # Cumulative P&L = current equity - starting equity
                        cumulative_pnl.append(round(eq - base_equity, 2))

                    if profit_loss and i < len(profit_loss):
                        hourly_pnl.append(round(float(profit_loss[i]), 2))

                return jsonify(
                    {
                        "labels": labels,
                        "datasets": [
                            {
                                "label": "Hourly P&L",
                                "data": hourly_pnl if hourly_pnl else [0] * len(labels),
                            },
                            {
                                "label": "Cumulative P&L",
                                "data": cumulative_pnl,
                            },
                        ],
                    }
                )
            except Exception as e:
                logger.error(f"Error getting portfolio history: {e}")
                return jsonify({"labels": [], "datasets": []})

        @app.route("/api/v1/pnl/history")
        def api_pnl_history():
            """Get P&L history from database."""
            try:
                import sqlite3
                db_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "database",
                    "crypto_trading.db",
                )
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get recent P&L history
                cursor.execute("""
                    SELECT symbol, side, qty, price, pnl, timestamp
                    FROM trade_history
                    ORDER BY timestamp DESC
                    LIMIT 100
                """)
                rows = cursor.fetchall()
                conn.close()

                return jsonify({
                    "history": [
                        {
                            "symbol": row["symbol"],
                            "side": row["side"],
                            "qty": row["qty"],
                            "price": row["price"],
                            "pnl": row["pnl"],
                            "timestamp": row["timestamp"],
                        }
                        for row in rows
                    ],
                    "total_pnl": sum(row["pnl"] or 0 for row in rows),
                })
            except Exception as e:
                logger.error(f"Error getting P&L history: {e}")
                return jsonify({"history": [], "total_pnl": 0})

        @app.route("/api/v1/market/clock")
        def api_market_clock():
            """Get market hours and status"""
            bot = get_active_bot()
            if not bot or not hasattr(bot, "alpaca"):
                return jsonify({"error": "No client"}), 503
            try:
                clock = bot.alpaca.get_clock()
                return jsonify(
                    {
                        "is_open": clock.is_open,
                        "timestamp": str(clock.timestamp),
                        "next_open": str(clock.next_open),
                        "next_close": str(clock.next_close),
                    }
                )
            except Exception as e:
                logger.error(f"Error getting market clock: {e}")
                return jsonify({"is_open": True, "note": "Crypto markets 24/7"})

        @app.route("/api/v1/account/activities")
        def api_account_activities():
            """Get account activities (deposits, withdrawals, dividends, etc.)"""
            bot = get_active_bot()
            if not bot or not hasattr(bot, "alpaca"):
                return jsonify([])
            try:
                activities = bot.alpaca.get_activities()
                return jsonify(
                    [
                        {
                            "id": a.id,
                            "activity_type": a.activity_type,
                            "date": str(a.date) if hasattr(a, "date") else None,
                            "net_amount": float(a.net_amount)
                            if hasattr(a, "net_amount")
                            else None,
                            "symbol": getattr(a, "symbol", None),
                            "qty": float(a.qty) if hasattr(a, "qty") else None,
                            "price": float(a.price) if hasattr(a, "price") else None,
                            "side": getattr(a, "side", None),
                        }
                        for a in activities[:100]
                    ]
                )
            except Exception as e:
                logger.error(f"Error getting activities: {e}")
                return jsonify([])

        @app.route("/api/v1/market/snapshots")
        def api_market_snapshots():
            """Get real-time snapshots for traded symbols (bid/ask, last trade)"""
            from config.service_settings import DEFAULT_CRYPTO_SYMBOLS

            bot = get_active_bot()
            client = get_alpaca_client()

            # Get the Alpaca client - prefer bot's client, fall back to global
            alpaca_client = None
            if bot and hasattr(bot, "alpaca"):
                alpaca_client = bot.alpaca
            elif client:
                alpaca_client = client

            if not alpaca_client:
                return jsonify({})

            try:
                # Get symbols from scanner first, then active positions, then defaults
                symbols = []
                if (
                    bot
                    and hasattr(bot, "scanner")
                    and hasattr(bot.scanner, "get_enabled_symbols")
                ):
                    symbols = bot.scanner.get_enabled_symbols()
                if not symbols and bot:
                    symbols = list(getattr(bot, "active_positions", {}).keys())
                if not symbols:
                    # Use default crypto symbols from config
                    symbols = DEFAULT_CRYPTO_SYMBOLS[:5]  # Top 5 for quick loading

                # Normalize symbols to BTC/USD format for Alpaca API
                normalized_symbols = []
                for s in symbols:
                    if "/" not in s and s.endswith("USD"):
                        # Convert BTCUSD -> BTC/USD
                        normalized_symbols.append(s[:-3] + "/USD")
                    elif "/" in s:
                        normalized_symbols.append(s)
                    else:
                        normalized_symbols.append(s + "/USD")

                snapshots = alpaca_client.get_crypto_snapshots(normalized_symbols)
                result = {}
                for symbol, snap in snapshots.items():
                    result[symbol] = {
                        "latest_trade": {
                            "price": float(snap.latest_trade.price)
                            if snap.latest_trade
                            else None,
                            "size": float(snap.latest_trade.size)
                            if snap.latest_trade
                            else None,
                            "timestamp": str(snap.latest_trade.timestamp)
                            if snap.latest_trade
                            else None,
                        },
                        "latest_quote": {
                            "bid": float(snap.latest_quote.bid_price)
                            if snap.latest_quote
                            else None,
                            "ask": float(snap.latest_quote.ask_price)
                            if snap.latest_quote
                            else None,
                            "bid_size": float(snap.latest_quote.bid_size)
                            if snap.latest_quote
                            else None,
                            "ask_size": float(snap.latest_quote.ask_size)
                            if snap.latest_quote
                            else None,
                        },
                        "daily_bar": {
                            "open": float(snap.daily_bar.open)
                            if snap.daily_bar
                            else None,
                            "high": float(snap.daily_bar.high)
                            if snap.daily_bar
                            else None,
                            "low": float(snap.daily_bar.low)
                            if snap.daily_bar
                            else None,
                            "close": float(snap.daily_bar.close)
                            if snap.daily_bar
                            else None,
                            "volume": float(snap.daily_bar.volume)
                            if snap.daily_bar
                            else None,
                        },
                    }
                return jsonify(result)
            except Exception as e:
                logger.error(f"Error getting snapshots: {e}")
                return jsonify({})

        def normalize_symbol(symbol: str) -> str:
            """Normalize symbol format: 'BTC-USD' or 'BTCUSD' -> 'BTC/USD'"""
            symbol = symbol.replace("-", "/")
            if "/" not in symbol and symbol.endswith("USD"):
                # "BTCUSD" -> "BTC/USD"
                return symbol[:-3] + "/USD"
            elif not symbol.endswith("/USD"):
                return f"{symbol}/USD"
            return symbol

        @app.route("/api/v1/symbol/<symbol>/chart")
        def api_symbol_chart(symbol):
            """Get OHLCV chart data for a symbol with multiple timeframes."""
            from flask import request
            from datetime import datetime, timedelta
            from config.service_settings import DEFAULT_CRYPTO_SYMBOLS
            import pandas as pd

            # Parse query parameters
            timeframe = request.args.get("timeframe", "1Min")
            limit = min(int(request.args.get("limit", "200")), 1000)

            # Validate timeframe
            valid_timeframes = ["1Min", "5Min", "15Min", "1Hour", "1Day"]
            if timeframe not in valid_timeframes:
                return jsonify(
                    {"error": f"Invalid timeframe. Use: {valid_timeframes}"}
                ), 400

            # Normalize symbol format (accept BTC-USD, BTCUSD, or BTC/USD)
            symbol = normalize_symbol(symbol)

            bot = get_active_bot()
            client = get_alpaca_client()
            alpaca_client = bot.alpaca if bot and hasattr(bot, "alpaca") else client

            if not alpaca_client:
                return jsonify({"error": "No Alpaca client available"}), 503

            try:
                # Calculate time range based on timeframe
                end = datetime.now()
                if timeframe == "1Min":
                    start = end - timedelta(hours=limit / 60 + 1)
                elif timeframe == "5Min":
                    start = end - timedelta(hours=limit * 5 / 60 + 1)
                elif timeframe == "15Min":
                    start = end - timedelta(hours=limit * 15 / 60 + 1)
                elif timeframe == "1Hour":
                    start = end - timedelta(days=limit / 24 + 1)
                else:  # 1Day
                    start = end - timedelta(days=limit + 1)

                # Fetch bars from Alpaca (use RFC3339 format with Z suffix)
                bars = alpaca_client.get_crypto_bars(
                    symbol,
                    timeframe,
                    start=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    end=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                ).df

                if bars.empty:
                    return jsonify(
                        {"symbol": symbol, "timeframe": timeframe, "bars": []}
                    )

                # Reset index if it's a MultiIndex (symbol, timestamp)
                if isinstance(bars.index, pd.MultiIndex):
                    bars = bars.reset_index(level=0, drop=True)

                # Convert to list of OHLCV dicts
                chart_data = []
                for idx, row in bars.tail(limit).iterrows():
                    chart_data.append(
                        {
                            "time": idx.isoformat()
                            if hasattr(idx, "isoformat")
                            else str(idx),
                            "timestamp": int(idx.timestamp() * 1000)
                            if hasattr(idx, "timestamp")
                            else 0,
                            "open": float(row["open"]),
                            "high": float(row["high"]),
                            "low": float(row["low"]),
                            "close": float(row["close"]),
                            "volume": float(row["volume"]),
                        }
                    )

                return jsonify(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "bars": chart_data,
                        "count": len(chart_data),
                    }
                )

            except Exception as e:
                logger.error(f"Error fetching chart data for {symbol}: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/symbol/<symbol>/indicators")
        def api_symbol_indicators(symbol):
            """Get technical indicators for a symbol."""
            from flask import request
            import pandas as pd

            # Normalize symbol format
            symbol = normalize_symbol(symbol)

            bot = get_active_bot()

            if not bot:
                return jsonify({"error": "Bot not running"}), 503

            try:
                # Try to get indicators from the scanner
                indicators = {}
                if hasattr(bot, "scanner") and hasattr(bot.scanner, "get_indicators"):
                    indicators = bot.scanner.get_indicators(symbol)

                if not indicators:
                    # Fallback: Calculate indicators fresh
                    client = get_alpaca_client()
                    alpaca_client = bot.alpaca if hasattr(bot, "alpaca") else client

                    if alpaca_client:
                        from datetime import datetime, timedelta

                        end = datetime.now()
                        start = end - timedelta(hours=4)

                        bars = alpaca_client.get_crypto_bars(
                            symbol,
                            "1Min",
                            start=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            end=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        ).df

                        if not bars.empty:
                            if isinstance(bars.index, pd.MultiIndex):
                                bars = bars.reset_index(level=0, drop=True)

                            close = bars["close"].values
                            high = bars["high"].values
                            low = bars["low"].values

                            # Calculate basic indicators
                            from indicators.optimized_indicators import (
                                calculate_ema_optimized,
                                calculate_stoch_rsi_optimized,
                            )

                            import numpy as np

                            # RSI calculation
                            delta = pd.Series(close).diff()
                            gain = delta.where(delta > 0, 0).rolling(14).mean()
                            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                            rs = gain / loss
                            rsi_series = 100 - (100 / (1 + rs))
                            rsi_val = (
                                rsi_series.iloc[-1] if len(rsi_series) > 0 else None
                            )

                            # EMA
                            ema_fast = calculate_ema_optimized(close, 5)
                            ema_slow = calculate_ema_optimized(close, 13)

                            # StochRSI - requires DataFrame with 'close' column
                            stoch_df = calculate_stoch_rsi_optimized(
                                bars[["close"]], 14, 9, 3, 3
                            )
                            stoch_k = stoch_df["StochRSI %K"].values
                            stoch_d = stoch_df["StochRSI %D"].values

                            # MACD
                            ema12 = calculate_ema_optimized(close, 12)
                            ema26 = calculate_ema_optimized(close, 26)
                            macd_line = ema12 - ema26
                            signal_line = calculate_ema_optimized(macd_line, 9)
                            macd_hist = macd_line - signal_line

                            # Helper to safely get last value
                            def safe_last(arr):
                                if arr is None or len(arr) == 0:
                                    return None
                                val = arr[-1]
                                if pd.isna(val) or (
                                    isinstance(val, float) and np.isnan(val)
                                ):
                                    return None
                                return float(val)

                            indicators = {
                                "rsi": float(rsi_val)
                                if rsi_val is not None and not pd.isna(rsi_val)
                                else None,
                                "stoch_k": safe_last(stoch_k),
                                "stoch_d": safe_last(stoch_d),
                                "ema_fast": safe_last(ema_fast),
                                "ema_slow": safe_last(ema_slow),
                                "ema_cross": "bullish"
                                if len(ema_fast) > 0
                                and len(ema_slow) > 0
                                and ema_fast[-1] > ema_slow[-1]
                                else "bearish",
                                "macd": safe_last(macd_line),
                                "macd_signal": safe_last(signal_line),
                                "macd_histogram": safe_last(macd_hist),
                                "price": float(close[-1]) if len(close) > 0 else None,
                                "high_24h": float(high.max())
                                if len(high) > 0
                                else None,
                                "low_24h": float(low.min()) if len(low) > 0 else None,
                            }

                return jsonify(
                    {
                        "symbol": symbol,
                        "indicators": indicators,
                        "timestamp": datetime.now().isoformat()
                        if "datetime" in dir()
                        else None,
                    }
                )

            except Exception as e:
                logger.error(f"Error fetching indicators for {symbol}: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/symbol/<symbol>/indicators/history")
        def api_symbol_indicators_history(symbol):
            """Get historical indicator values for charting (RSI, StochRSI over time)."""
            from flask import request
            import pandas as pd
            import numpy as np

            # Normalize symbol format
            symbol = normalize_symbol(symbol)

            limit = int(request.args.get("limit", 100))
            timeframe = request.args.get("timeframe", "1Min")

            # Check cache first to avoid rate limiting
            cache_key = f"{symbol}:{timeframe}:{limit}"
            cached = _get_cached_indicators(cache_key)
            if cached:
                return jsonify(cached)

            bot = get_active_bot()
            client = get_alpaca_client()
            alpaca_client = bot.alpaca if bot and hasattr(bot, "alpaca") else client

            if not alpaca_client:
                return jsonify({"error": "No Alpaca client available"}), 503

            try:
                from datetime import datetime, timedelta
                from indicators.optimized_indicators import (
                    calculate_ema_optimized,
                    calculate_stoch_rsi_optimized,
                )

                end = datetime.now()
                # Get extra bars for indicator calculation warmup
                warmup_bars = 50
                total_bars = limit + warmup_bars

                if timeframe == "1Min":
                    start = end - timedelta(minutes=total_bars + 10)
                elif timeframe == "5Min":
                    start = end - timedelta(minutes=total_bars * 5 + 30)
                elif timeframe == "15Min":
                    start = end - timedelta(minutes=total_bars * 15 + 60)
                elif timeframe == "1Hour":
                    start = end - timedelta(hours=total_bars + 2)
                else:
                    start = end - timedelta(days=total_bars + 1)

                bars = alpaca_client.get_crypto_bars(
                    symbol,
                    timeframe,
                    start=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    end=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                ).df

                if bars.empty:
                    return jsonify({"symbol": symbol, "data": []})

                if isinstance(bars.index, pd.MultiIndex):
                    bars = bars.reset_index(level=0, drop=True)

                close = bars["close"].values

                # Calculate RSI
                delta = pd.Series(close).diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi_series = 100 - (100 / (1 + rs))

                # Calculate StochRSI
                stoch_df = calculate_stoch_rsi_optimized(bars[["close"]], 14, 9, 3, 3)
                stoch_k = stoch_df["StochRSI %K"].values
                stoch_d = stoch_df["StochRSI %D"].values

                # Calculate MACD
                ema12 = calculate_ema_optimized(close, 12)
                ema26 = calculate_ema_optimized(close, 26)
                macd_line = ema12 - ema26
                signal_line = calculate_ema_optimized(macd_line, 9)
                macd_hist = macd_line - signal_line

                # Build time series data (skip warmup period)
                data = []
                bars_list = list(bars.tail(limit).iterrows())
                offset = len(bars) - limit

                for i, (idx, row) in enumerate(bars_list):
                    actual_idx = offset + i

                    def safe_val(arr, idx):
                        if arr is None or idx >= len(arr):
                            return None
                        val = arr[idx]
                        if pd.isna(val) or (isinstance(val, float) and np.isnan(val)):
                            return None
                        return float(val)

                    data.append(
                        {
                            "time": idx.isoformat()
                            if hasattr(idx, "isoformat")
                            else str(idx),
                            "timestamp": int(idx.timestamp() * 1000)
                            if hasattr(idx, "timestamp")
                            else 0,
                            "rsi": safe_val(rsi_series.values, actual_idx),
                            "stoch_k": safe_val(stoch_k, actual_idx),
                            "stoch_d": safe_val(stoch_d, actual_idx),
                            "macd": safe_val(macd_line, actual_idx),
                            "macd_signal": safe_val(signal_line, actual_idx),
                            "macd_hist": safe_val(macd_hist, actual_idx),
                        }
                    )

                # Calculate current signal score
                latest = data[-1] if data else {}
                buy_score = 0
                signal_factors = []

                rsi = latest.get("rsi")
                stoch = latest.get("stoch_k")
                macd = latest.get("macd_hist")

                if rsi is not None:
                    if rsi < 25:
                        buy_score += 3
                        signal_factors.append(
                            {"name": "rsi", "active": True, "points": 3}
                        )
                    elif rsi < 30:
                        buy_score += 2
                        signal_factors.append(
                            {"name": "rsi", "active": True, "points": 2}
                        )
                    elif rsi < 35:
                        buy_score += 1
                        signal_factors.append(
                            {"name": "rsi", "active": True, "points": 1}
                        )
                    else:
                        signal_factors.append(
                            {"name": "rsi", "active": False, "points": 0}
                        )

                if stoch is not None:
                    if stoch < 20:
                        buy_score += 3
                        signal_factors.append(
                            {"name": "stoch", "active": True, "points": 3}
                        )
                    elif stoch < 30:
                        buy_score += 2
                        signal_factors.append(
                            {"name": "stoch", "active": True, "points": 2}
                        )
                    else:
                        signal_factors.append(
                            {"name": "stoch", "active": False, "points": 0}
                        )

                if macd is not None and macd > 0:
                    buy_score += 1
                    signal_factors.append({"name": "macd", "active": True, "points": 1})
                else:
                    signal_factors.append(
                        {"name": "macd", "active": False, "points": 0}
                    )

                result = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "data": data,
                    "count": len(data),
                    "thresholds": {
                        "rsi_oversold": 30,
                        "rsi_overbought": 70,
                        "stoch_oversold": 20,
                        "stoch_overbought": 80,
                    },
                    "current_signal": {
                        "buy_score": buy_score,
                        "min_required": 3,
                        "would_trade": buy_score >= 3,
                        "factors": signal_factors,
                    },
                }

                # Cache the result
                _set_cached_indicators(cache_key, result)
                return jsonify(result)

            except Exception as e:
                logger.error(f"Error fetching indicator history for {symbol}: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/symbol/<symbol>/quote")
        def api_symbol_quote(symbol):
            """Get real-time quote (bid/ask/last) for a symbol."""
            # Normalize symbol format
            symbol = normalize_symbol(symbol)

            # Check cache first to avoid rate limiting
            cached = _get_cached_quote(symbol)
            if cached:
                return jsonify(cached)

            bot = get_active_bot()
            client = get_alpaca_client()
            alpaca_client = bot.alpaca if bot and hasattr(bot, "alpaca") else client

            if not alpaca_client:
                return jsonify({"error": "No Alpaca client available"}), 503

            try:
                # Get snapshot for this symbol
                snapshots = alpaca_client.get_crypto_snapshots([symbol])
                snap = snapshots.get(symbol)

                if not snap:
                    return jsonify({"error": f"No data for {symbol}"}), 404

                quote_data = {
                    "symbol": symbol,
                    "last_price": float(snap.latest_trade.price)
                    if snap.latest_trade
                    else None,
                    "last_size": float(snap.latest_trade.size)
                    if snap.latest_trade
                    else None,
                    "last_time": str(snap.latest_trade.timestamp)
                    if snap.latest_trade
                    else None,
                    "bid": float(snap.latest_quote.bid_price)
                    if snap.latest_quote
                    else None,
                    "bid_size": float(snap.latest_quote.bid_size)
                    if snap.latest_quote
                    else None,
                    "ask": float(snap.latest_quote.ask_price)
                    if snap.latest_quote
                    else None,
                    "ask_size": float(snap.latest_quote.ask_size)
                    if snap.latest_quote
                    else None,
                    "spread": None,
                    "spread_pct": None,
                    "daily_open": float(snap.daily_bar.open)
                    if snap.daily_bar
                    else None,
                    "daily_high": float(snap.daily_bar.high)
                    if snap.daily_bar
                    else None,
                    "daily_low": float(snap.daily_bar.low) if snap.daily_bar else None,
                    "daily_close": float(snap.daily_bar.close)
                    if snap.daily_bar
                    else None,
                    "daily_volume": float(snap.daily_bar.volume)
                    if snap.daily_bar
                    else None,
                    "daily_change": None,
                    "daily_change_pct": None,
                }

                # Calculate spread
                if quote_data["bid"] and quote_data["ask"]:
                    quote_data["spread"] = quote_data["ask"] - quote_data["bid"]
                    quote_data["spread_pct"] = (
                        quote_data["spread"] / quote_data["ask"]
                    ) * 100

                # Calculate daily change
                if quote_data["daily_open"] and quote_data["last_price"]:
                    quote_data["daily_change"] = (
                        quote_data["last_price"] - quote_data["daily_open"]
                    )
                    quote_data["daily_change_pct"] = (
                        quote_data["daily_change"] / quote_data["daily_open"]
                    ) * 100

                # Cache the result
                _set_cached_quote(symbol, quote_data)
                return jsonify(quote_data)

            except Exception as e:
                logger.error(f"Error fetching quote for {symbol}: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/symbol/<symbol>/trades")
        def api_symbol_trades(symbol):
            """Get recent trades history for a symbol from our bot."""
            # Normalize symbol format
            symbol = normalize_symbol(symbol)

            bot = get_active_bot()
            client = get_alpaca_client()
            alpaca_client = bot.alpaca if bot and hasattr(bot, "alpaca") else client

            if not alpaca_client:
                return jsonify({"error": "No Alpaca client available"}), 503

            try:
                # Get closed orders for this symbol
                orders = alpaca_client.list_orders(
                    status="closed",
                    limit=50,
                    symbols=[
                        symbol.replace("/", "")
                    ],  # Alpaca uses BTCUSD not BTC/USD for orders
                )

                trades = []
                for order in orders:
                    if order.filled_qty and float(order.filled_qty) > 0:
                        trades.append(
                            {
                                "id": order.id,
                                "time": str(order.filled_at)
                                if order.filled_at
                                else str(order.created_at),
                                "side": order.side,
                                "qty": float(order.filled_qty),
                                "price": float(order.filled_avg_price)
                                if order.filled_avg_price
                                else None,
                                "value": float(order.filled_qty)
                                * float(order.filled_avg_price)
                                if order.filled_avg_price
                                else None,
                                "status": order.status,
                            }
                        )

                return jsonify(
                    {
                        "symbol": symbol,
                        "trades": trades,
                        "count": len(trades),
                    }
                )

            except Exception as e:
                logger.error(f"Error fetching trades for {symbol}: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/symbol/<symbol>/position")
        def api_symbol_position(symbol):
            """Get current position for a symbol if we have one."""
            # Normalize symbol format
            symbol = normalize_symbol(symbol)

            bot = get_active_bot()
            client = get_alpaca_client()
            alpaca_client = bot.alpaca if bot and hasattr(bot, "alpaca") else client

            if not alpaca_client:
                return jsonify({"error": "No Alpaca client available"}), 503

            try:
                # Try to get position from Alpaca
                alpaca_symbol = symbol.replace("/", "")  # BTCUSD format
                try:
                    position = alpaca_client.get_position(alpaca_symbol)

                    # Get stop/target/entry_time from bot's active_positions dict
                    stop_price = None
                    target_price = None
                    entry_price = None
                    entry_time = None
                    entry_reasons = []
                    is_synced = True  # Assume synced until proven otherwise
                    if bot and hasattr(bot, "active_positions"):
                        # Try both symbol formats: BTC/USD and BTCUSD
                        bot_pos = bot.active_positions.get(symbol) or bot.active_positions.get(alpaca_symbol)
                        if bot_pos:
                            stop_price = bot_pos.get("stop_price")
                            target_price = bot_pos.get("target_price")
                            entry_price = bot_pos.get("entry_price")
                            # Check if this was a fresh entry (has signal) or synced position
                            signal = bot_pos.get("signal")
                            is_synced = signal is None
                            # Only provide entry_time for fresh entries (not synced)
                            if not is_synced:
                                et = bot_pos.get("entry_time")
                                if et:
                                    entry_time = int(et.timestamp() * 1000)  # milliseconds
                                # Get entry reasons from signal
                                if hasattr(signal, "signal_reasons") and signal.signal_reasons:
                                    entry_reasons = signal.signal_reasons

                    return jsonify(
                        {
                            "symbol": symbol,
                            "has_position": True,
                            "is_synced": is_synced,  # True if position existed before bot started
                            "qty": float(position.qty),
                            "side": position.side,
                            "avg_entry_price": float(position.avg_entry_price),
                            "bot_entry_price": entry_price,  # Bot's tracked entry price
                            "entry_time": entry_time,  # Timestamp in ms when position was opened (None for synced)
                            "entry_reasons": entry_reasons,  # Why the bot entered
                            "current_price": float(position.current_price),
                            "market_value": float(position.market_value),
                            "unrealized_pl": float(position.unrealized_pl),
                            "unrealized_plpc": float(position.unrealized_plpc) * 100,
                            "cost_basis": float(position.cost_basis),
                            "stop_price": stop_price,
                            "target_price": target_price,
                        }
                    )
                except Exception:
                    # No position for this symbol
                    return jsonify(
                        {
                            "symbol": symbol,
                            "has_position": False,
                        }
                    )

            except Exception as e:
                logger.error(f"Error fetching position for {symbol}: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/symbol/<symbol>/buy", methods=["POST"])
        def api_symbol_buy(symbol):
            """Place a buy order for a symbol."""
            from flask import request

            # Normalize symbol format
            symbol = normalize_symbol(symbol)

            bot = get_active_bot()
            client = get_alpaca_client()
            alpaca_client = bot.alpaca if bot and hasattr(bot, "alpaca") else client

            if not alpaca_client:
                return jsonify({"error": "No Alpaca client available"}), 503

            try:
                data = request.get_json() or {}
                qty = data.get("qty")
                notional = data.get("notional")  # Dollar amount

                if not qty and not notional:
                    return jsonify({"error": "Either qty or notional required"}), 400

                alpaca_symbol = symbol.replace("/", "")

                order_params = {
                    "symbol": alpaca_symbol,
                    "side": "buy",
                    "type": "market",
                    "time_in_force": "gtc",
                }

                if qty:
                    order_params["qty"] = str(qty)
                else:
                    order_params["notional"] = str(notional)

                order = alpaca_client.submit_order(**order_params)

                return jsonify(
                    {
                        "status": "ok",
                        "order_id": order.id,
                        "order_status": order.status,
                        "symbol": symbol,
                        "side": "buy",
                        "qty": str(order.qty) if order.qty else None,
                        "filled_qty": str(order.filled_qty)
                        if order.filled_qty
                        else "0",
                        "filled_avg_price": str(order.filled_avg_price)
                        if order.filled_avg_price
                        else None,
                        "notional": notional,
                        "submitted_at": order.submitted_at.isoformat()
                        if order.submitted_at
                        else None,
                    }
                )

            except Exception as e:
                logger.error(f"Error placing buy order for {symbol}: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/order/<order_id>")
        def api_order_status(order_id):
            """Get status of a specific order."""
            bot = get_active_bot()
            client = get_alpaca_client()
            alpaca_client = bot.alpaca if bot and hasattr(bot, "alpaca") else client

            if not alpaca_client:
                return jsonify({"error": "No Alpaca client available"}), 503

            try:
                order = alpaca_client.get_order(order_id)

                return jsonify(
                    {
                        "order_id": order.id,
                        "symbol": order.symbol,
                        "side": order.side,
                        "status": order.status,
                        "qty": str(order.qty) if order.qty else None,
                        "filled_qty": str(order.filled_qty)
                        if order.filled_qty
                        else "0",
                        "filled_avg_price": str(order.filled_avg_price)
                        if order.filled_avg_price
                        else None,
                        "submitted_at": order.submitted_at.isoformat()
                        if order.submitted_at
                        else None,
                        "filled_at": order.filled_at.isoformat()
                        if order.filled_at
                        else None,
                        "type": order.type,
                        "time_in_force": order.time_in_force,
                    }
                )

            except Exception as e:
                logger.error(f"Error fetching order {order_id}: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/symbol/<symbol>/sell", methods=["POST"])
        def api_symbol_sell(symbol):
            """Place a sell order for a symbol."""
            from flask import request

            # Normalize symbol format
            symbol = normalize_symbol(symbol)

            bot = get_active_bot()
            client = get_alpaca_client()
            alpaca_client = bot.alpaca if bot and hasattr(bot, "alpaca") else client

            if not alpaca_client:
                return jsonify({"error": "No Alpaca client available"}), 503

            try:
                data = request.get_json() or {}
                qty = data.get("qty")
                close_all = data.get("close_all", False)

                alpaca_symbol = symbol.replace("/", "")

                if close_all:
                    # Close entire position
                    alpaca_client.close_position(alpaca_symbol)
                    return jsonify(
                        {
                            "status": "ok",
                            "symbol": symbol,
                            "action": "closed_position",
                        }
                    )

                if not qty:
                    return jsonify(
                        {"error": "qty required (or use close_all: true)"}
                    ), 400

                order = alpaca_client.submit_order(
                    symbol=alpaca_symbol,
                    qty=str(qty),
                    side="sell",
                    type="market",
                    time_in_force="gtc",
                )

                return jsonify(
                    {
                        "status": "ok",
                        "order_id": order.id,
                        "order_status": order.status,
                        "symbol": symbol,
                        "side": "sell",
                        "qty": str(order.qty) if order.qty else str(qty),
                        "filled_qty": str(order.filled_qty)
                        if order.filled_qty
                        else "0",
                        "filled_avg_price": str(order.filled_avg_price)
                        if order.filled_avg_price
                        else None,
                        "submitted_at": order.submitted_at.isoformat()
                        if order.submitted_at
                        else None,
                    }
                )

            except Exception as e:
                logger.error(f"Error placing sell order for {symbol}: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/trading/start", methods=["POST"])
        def api_trading_start():
            # Bot is already running - this is a no-op
            return jsonify(
                {"status": "ok", "message": "Trading bot is already running"}
            )

        @app.route("/api/v1/trading/stop", methods=["POST"])
        def api_trading_stop():
            # Can't stop from dashboard - would kill the process
            return jsonify({"status": "ok", "message": "Use Ctrl+C to stop the bot"})

        # Run Flask in a thread
        def run_flask():
            # Suppress Flask startup messages
            import logging as flask_logging

            flask_logging.getLogger("werkzeug").setLevel(flask_logging.WARNING)
            app.run(host=host, port=port, debug=False, use_reloader=False)

        thread = threading.Thread(target=run_flask, daemon=True)
        thread.start()
        logger.info(f"📊 Dashboard started at http://{host}:{port}")
        return thread

    except ImportError as e:
        logger.warning(f"Flask not available, dashboard disabled: {e}")
        return None


METRIC_BOT_STARTUPS = (
    Counter("trading_bot_startups_total", "Number of trading bot startups")
    if Counter
    else None
)
METRIC_BOT_EXCEPTIONS = (
    Counter(
        "trading_bot_exceptions_total", "Number of unhandled exceptions in trading bot"
    )
    if Counter
    else None
)
METRIC_READY_SERVICES = (
    Gauge("trading_services_ready", "Number of ready services registered")
    if Gauge
    else None
)
METRIC_TOTAL_SERVICES = (
    Gauge("trading_services_total", "Total services registered in the registry")
    if Gauge
    else None
)

_METRICS_INITIALISED = False


def _enable_metrics_if_configured() -> None:
    """Start the Prometheus exporter when metrics are enabled."""

    global _METRICS_INITIALISED
    if _METRICS_INITIALISED or METRIC_BOT_STARTUPS is None:
        return

    raw_toggle = os.getenv("ENABLE_PROMETHEUS_METRICS", "true").strip().lower()
    if raw_toggle not in {"1", "true", "yes", "on"}:
        return

    port = int(os.getenv("PROMETHEUS_EXPORTER_PORT", "9464"))
    start_http_server(port)
    METRIC_BOT_STARTUPS.inc()
    _METRICS_INITIALISED = True


from strategies import get_strategy


def setup_signal_handlers(bot: Optional[Union[TradingBot, CryptoDayTradingBot]] = None):
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")

        if bot:
            if isinstance(bot, CryptoDayTradingBot):
                logger.info("Stopping crypto scalping bot...")
            else:
                logger.info("Stopping trading bot...")
            bot.stop()

        logger.info("Cleaning up services...")
        cleanup_service_registry()

        logger.info("Shutdown complete")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def create_alpaca_client(config):
    """Create Alpaca trading client from configuration using legacy SDK.

    Uses alpaca_trade_api (legacy SDK) for compatibility with strategy code
    that expects list_positions(), get_crypto_bars(), etc.
    """
    if tradeapi is None:  # pragma: no cover - optional dependency fallback
        raise RuntimeError(
            "alpaca_trade_api is not installed; unable to create Alpaca client"
        ) from ALPACA_IMPORT_ERROR

    try:
        creds = load_alpaca_credentials(config)

        # Use legacy REST API for full compatibility with existing strategy code
        trading_client = tradeapi.REST(
            creds.key_id, creds.secret_key, creds.base_url, api_version="v2"
        )

        # Verify connection
        account = trading_client.get_account()
        logger.info(
            f"Alpaca trading client initialized successfully (Account status: {account.status})"
        )
        return trading_client

    except Exception as e:
        logger.error(f"Failed to create Alpaca client: {e}")
        raise


async def main():
    """Main entry point for the crypto trading bot."""
    global _active_bot, _alpaca_client
    bot = None

    try:
        # Load configuration
        config = get_config()

        # Setup logging
        setup_logging()
        _enable_metrics_if_configured()

        logger.info("🚀 Starting Crypto Scalping Bot - High Frequency Trading")

        # Create Alpaca client
        alpaca_client = create_alpaca_client(config)
        _alpaca_client = alpaca_client  # Store globally for dashboard

        # Create crypto day trading bot
        bot = create_crypto_day_trader(alpaca_client, config)
        _active_bot = bot  # Store globally for dashboard

        logger.info("Crypto scalping bot created and configured")

        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(bot)

        if config.symbols:
            logger.info("Using configured symbols: %s", config.symbols)
        else:
            logger.info("No symbols configured, will use dynamic selection")

        # Start the dashboard server
        dashboard_port = int(os.getenv("DASHBOARD_PORT", "5001"))
        start_dashboard_server(port=dashboard_port)

        # Start the crypto scalping bot
        logger.info("🎯 Starting crypto scalping execution...")
        await bot.start_trading()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        if METRIC_BOT_EXCEPTIONS:
            METRIC_BOT_EXCEPTIONS.inc()
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        raise
    finally:
        if bot:
            bot.stop()
        logger.info("Trading bot shutdown completed")


if __name__ == "__main__":
    asyncio.run(main())
