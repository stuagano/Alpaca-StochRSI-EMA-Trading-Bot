"""Shared utilities for recording executed trades to persistent storage."""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TradeStore:
    """Lightweight SQLite-backed trade recorder shared between services."""

    _lock = threading.Lock()
    _db_path: Path = Path("database/trading_data.db")
    _initialised = False

    @classmethod
    def configure(cls, db_path: Optional[str]) -> None:
        """Override the backing database path and ensure schema exists."""

        if db_path:
            cls._db_path = Path(db_path)
        cls._ensure_schema()

    @classmethod
    def get_db_path(cls) -> Path:
        """Return the currently configured database path."""

        return cls._db_path

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

        cls._ensure_schema()

        ts = timestamp or datetime.now(UTC).isoformat()
        order_ref = str(order_id) if order_id is not None else f"{symbol}-{ts}"

        with cls._lock:
            try:
                cls._db_path.parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(cls._db_path)
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
                conn.close()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Failed to record trade: %s", exc, exc_info=True)

    @classmethod
    def _ensure_schema(cls) -> None:
        """Create the trade history table if it is missing."""

        if cls._initialised and cls._db_path.exists():
            return

        with cls._lock:
            if cls._initialised and cls._db_path.exists():
                return

            cls._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(cls._db_path)
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
