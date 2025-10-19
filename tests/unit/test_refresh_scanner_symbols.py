"""Unit tests for ``refresh_scanner_symbols`` coordination logic."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from config.unified_config import CryptoScannerConfig

pytestmark = pytest.mark.requires_strategy_runtime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture(scope="module")
def uts_module():
    import importlib

    return importlib.import_module("unified_trading_service_with_frontend")


@pytest.fixture(autouse=True)
def restore_trading_state(uts_module):
    """Ensure tests do not leak scanner state between runs."""

    original_scanner = uts_module.trading_state.crypto_scanner
    original_symbols = list(uts_module.trading_state.crypto_scanner_symbols)
    try:
        yield
    finally:
        uts_module.trading_state.crypto_scanner = original_scanner
        uts_module.trading_state.crypto_scanner_symbols = original_symbols


def test_refresh_scanner_symbols_returns_cached_when_scanner_missing(uts_module):
    """If the scanner is not initialised, cached symbols should be returned."""

    expected = ["BTC/USD", "ETH/USD"]
    uts_module.trading_state.crypto_scanner = None
    uts_module.trading_state.crypto_scanner_symbols = list(expected)

    assert uts_module.refresh_scanner_symbols() == expected


@pytest.fixture(scope="module")
def crypto_scanner_cls():
    from strategies.crypto_scalping_strategy import CryptoVolatilityScanner

    return CryptoVolatilityScanner


def test_refresh_scanner_symbols_projects_strategy_output_to_display_list(
    crypto_scanner_cls,
    uts_module,
):
    """The derived list should mirror the enabled strategy symbols in display format."""

    uts_module.trading_state.crypto_scanner = crypto_scanner_cls(
        config=CryptoScannerConfig(universe=[]),
        enabled_symbols=[
            "ethusd",
            "BTCUSD",
            "DOGEUSD",
            "ETHUSD",
        ],
    )

    derived = uts_module.refresh_scanner_symbols()

    assert derived == ["BTC/USD", "DOGE/USD", "ETH/USD"]
    assert uts_module.trading_state.crypto_scanner_symbols == derived


def test_refresh_scanner_symbols_clears_cache_when_strategy_returns_empty(
    crypto_scanner_cls,
    uts_module,
):
    """An empty strategy response should clear the cached list."""

    scanner = crypto_scanner_cls(
        config=CryptoScannerConfig(universe=[]),
        enabled_symbols=["BTCUSD"],
    )
    scanner.update_enabled_symbols([], merge_with_defaults=False)
    uts_module.trading_state.crypto_scanner = scanner
    uts_module.trading_state.crypto_scanner_symbols = ["BTC/USD"]

    assert uts_module.refresh_scanner_symbols() == []
    assert uts_module.trading_state.crypto_scanner_symbols == []
