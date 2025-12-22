"""Shared utilities for recording executed trades to persistent storage."""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# Callbacks for trade events (used by learning service)
_trade_callbacks: List[Callable] = []


def register_trade_callback(callback: Callable) -> None:
    """Register a callback to be called when trades are recorded."""
    _trade_callbacks.append(callback)


def unregister_trade_callback(callback: Callable) -> None:
    """Unregister a trade callback."""
    if callback in _trade_callbacks:
        _trade_callbacks.remove(callback)


def _get_default_db_path() -> Path:
    """Get database path from unified config, with fallback."""
    try:
        from config.unified_config import get_database_path
        return Path(get_database_path())
    except Exception:
        return Path("database/crypto_trading.db")


class TradeStore:
    """Lightweight SQLite-backed trade recorder shared between services."""

    _lock = threading.Lock()
    _db_path: Optional[Path] = None
    _initialised = False

    @classmethod
    def _get_db_path(cls) -> Path:
        """Get database path, initializing from config if needed."""
        if cls._db_path is None:
            cls._db_path = _get_default_db_path()
        return cls._db_path

    @classmethod
    def configure(cls, db_path: Optional[str] = None) -> None:
        """Override the backing database path and ensure schema exists.

        If db_path is None, uses the path from unified configuration.
        """
        if db_path:
            cls._db_path = Path(db_path)
        elif cls._db_path is None:
            cls._db_path = _get_default_db_path()
        cls._ensure_schema()

    @classmethod
    def get_db_path(cls) -> Path:
        """Return the currently configured database path."""
        return cls._get_db_path()

    @classmethod
    def record_trade(
        cls,
        *,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        pnl: float = 0.0,
        order_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        """Persist a trade execution into the trade history table."""

        logger.debug(
            "Recording trade: symbol=%s, side=%s, qty=%s, price=%s, pnl=%s, order_id=%s",
            symbol, side, qty, price, pnl, order_id
        )

        cls._ensure_schema()

        ts = timestamp or datetime.now(UTC).isoformat()
        order_ref = str(order_id) if order_id is not None else f"{symbol}-{ts}"

        with cls._lock:
            try:
                db_path = cls._get_db_path()
                db_path.parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO trade_history (
                        timestamp, symbol, side, qty, price, pnl, order_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (ts, symbol, side, float(qty), float(price), float(pnl), order_ref),
                )
                conn.commit()
                logger.debug(
                    "Trade recorded: timestamp=%s, order_ref=%s, rowid=%s",
                    ts, order_ref, cursor.lastrowid
                )
                conn.close()

                # Trigger callbacks for learning service
                trade_data = {
                    'symbol': symbol,
                    'side': side,
                    'qty': qty,
                    'price': price,
                    'pnl': pnl,
                    'order_id': order_ref,
                    'timestamp': ts
                }
                for callback in _trade_callbacks:
                    try:
                        callback(trade_data)
                    except Exception as cb_exc:
                        logger.debug("Trade callback error: %s", cb_exc)

            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Failed to record trade: %s", exc, exc_info=True)

    @classmethod
    def _ensure_schema(cls) -> None:
        """Create the trade history table if it is missing."""
        db_path = cls._get_db_path()

        if cls._initialised and db_path.exists():
            return

        with cls._lock:
            if cls._initialised and db_path.exists():
                return

            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT,
                    side TEXT,
                    qty REAL,
                    price REAL,
                    pnl REAL,
                    order_id TEXT UNIQUE
                )
                """
            )
            conn.commit()
            conn.close()
            cls._initialised = True
