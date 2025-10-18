"""Ensure the runtime dispatch enters the crypto scalping path."""

from __future__ import annotations

from types import SimpleNamespace

import importlib
import sys
from types import ModuleType

import pytest

# Older modules reference strategies.strategy_base; provide a compatibility alias.
sys.modules.setdefault(
    "strategies.strategy_base",
    importlib.import_module("strategies.base_strategy")
)

# Provide a simple stub for numba so indicator imports do not fail during tests.
numba_stub = sys.modules.setdefault("numba", ModuleType("numba"))

def _decorator(*_args, **_kwargs):
    def _wrap(func):
        return func
    return _wrap

numba_stub.jit = _decorator
numba_stub.vectorize = _decorator

indicator_stub = sys.modules.setdefault("indicator", ModuleType("indicator"))
indicator_stub.rsi = lambda *_args, **_kwargs: None
indicator_stub.stochastic = lambda *_args, **_kwargs: None


class _StubIndicator:
    def __init__(self, *_args, **_kwargs):
        pass

    def calculate_rsi(self, *_args, **_kwargs):
        return 50.0

    def calculate_stochastic(self, *_args, **_kwargs):
        return 50.0, 50.0


indicator_stub.Indicator = _StubIndicator


class _StubStrategy:
    def __init__(self, *_args, **_kwargs):
        pass


stoch_stub = ModuleType("strategies.stoch_rsi_strategy")
stoch_stub.StochRSIStrategy = _StubStrategy
sys.modules["strategies.stoch_rsi_strategy"] = stoch_stub

ma_stub = ModuleType("strategies.ma_crossover_strategy")
ma_stub.MACrossoverStrategy = _StubStrategy
sys.modules["strategies.ma_crossover_strategy"] = ma_stub

import main as main_module


class _FakeScanner:
    def __init__(self):
        self.updated_symbols = None

    def update_enabled_symbols(self, symbols):
        self.updated_symbols = list(symbols)


class _FakeBot:
    def __init__(self):
        self.scanner = _FakeScanner()
        self.start_called = False
        self.stop_called = False

    async def start_trading(self):
        self.start_called = True

    def stop(self):
        self.stop_called = True


@pytest.mark.asyncio
async def test_main_launches_crypto_scalper(monkeypatch):
    config = SimpleNamespace(
        strategy="crypto_scalping",
        investment_amount=1000,
        risk_management=SimpleNamespace(max_position_size=0.1, max_daily_loss=0.05),
        max_trades_active=7,
        symbols=["BTC/USD", "ETH/USD"],
    )

    captured = {}
    fake_bot = _FakeBot()

    monkeypatch.setattr(main_module, "get_config", lambda: config)
    monkeypatch.setattr(main_module, "setup_logging", lambda: None)
    monkeypatch.setattr(main_module, "_enable_metrics_if_configured", lambda: None)
    monkeypatch.setattr(main_module, "setup_signal_handlers", lambda _bot: None)

    monkeypatch.setattr(main_module, "create_alpaca_client", lambda cfg: "alpaca-client")

    def fake_create_crypto_day_trader(client, scalper_config):
        captured["client"] = client
        captured["scalper_config"] = scalper_config
        return fake_bot

    monkeypatch.setattr(main_module, "create_crypto_day_trader", fake_create_crypto_day_trader)

    # Run the async entry point. Our fake bot returns immediately so this exits fast.
    await main_module.main()

    assert captured["client"] == "alpaca-client"
    assert captured["scalper_config"]["max_positions"] == config.max_trades_active
    assert fake_bot.start_called is True
    assert fake_bot.stop_called is True
    assert fake_bot.scanner.updated_symbols == config.symbols
