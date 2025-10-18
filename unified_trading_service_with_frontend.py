"""Lightweight compatibility module for legacy unified trading service.

Tests only rely on a subset of the original FastAPI monolith: the global
``trading_state`` object, the ``refresh_scanner_symbols`` helper and the
default background worker registrations. Recreating the entire application
brings a large dependency surface, so this shim provides a minimal,
dependency-free stand‑in that mirrors the expected interface.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from config.service_settings import AlpacaSettings, TradingServiceSettings
from services.unified_trading.background_workers import register_background_worker
from services.unified_trading.state import (
    TradingState,
    refresh_scanner_symbols as _refresh_scanner_symbols,
)


_DEFAULT_SYMBOLS = ["BTC/USD", "ETH/USD"]


def _default_settings() -> TradingServiceSettings:
    """Construct a minimal ``TradingServiceSettings`` instance."""

    return TradingServiceSettings(
        alpaca=AlpacaSettings(
            auth_file=Path("AUTH/authAlpaca.txt"),
            api_key=None,
            api_secret=None,
            api_base_url="https://paper-api.alpaca.markets",
        ),
        crypto_symbols=list(_DEFAULT_SYMBOLS),
        enabled_background_workers=None,
        crypto_scanner_interval_seconds=60,
        cache_refresh_seconds=30,
        scalper_poll_interval_seconds=10,
        scalper_cooldown_seconds=60,
        max_concurrent_positions=5,
        daily_loss_limit=1_000.0,
        crypto_metadata={symbol: {} for symbol in _DEFAULT_SYMBOLS},
    )


trading_state = TradingState(_default_settings())


async def update_cache(state: TradingState) -> None:  # pragma: no cover - trivial stub
    await asyncio.sleep(0)


async def crypto_scanner(state: TradingState) -> None:  # pragma: no cover - trivial stub
    await asyncio.sleep(0)


async def crypto_scalping_trader(state: TradingState) -> None:  # pragma: no cover - trivial stub
    await asyncio.sleep(0)


# Register default workers to preserve expected order on import.
register_background_worker(update_cache, name="update_cache")
register_background_worker(crypto_scanner, name="crypto_scanner")
register_background_worker(crypto_scalping_trader, name="crypto_scalping_trader")


def refresh_scanner_symbols(state: TradingState | None = None) -> list[str]:
    """Proxy to the shared helper while defaulting to the module state."""

    target_state = state or trading_state
    return _refresh_scanner_symbols(target_state)


__all__ = [
    "trading_state",
    "refresh_scanner_symbols",
    "update_cache",
    "crypto_scanner",
    "crypto_scalping_trader",
]

