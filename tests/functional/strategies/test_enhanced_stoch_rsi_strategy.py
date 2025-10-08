"""Regression-focused tests for the enhanced StochRSI strategy."""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
from typing import Callable, Optional

import pandas as pd
import pytest

import sys

if "yaml" not in sys.modules:
    yaml_stub = ModuleType("yaml")

    def _safe_load(_: object) -> dict:
        return {
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "timeframe": "1Min",
            "candle_lookback_period": 2,
            "investment_amount": 10000,
            "max_trades_active": 10,
            "trade_capital_percent": 5,
            "stop_loss": 0.2,
            "trailing_stop": 0.2,
            "activate_trailing_stop_loss_at": 0.1,
            "limit_price": 0.5,
            "exchange": "CBSE",
            "sleep_time_between_trades": 60,
            "extended_hours": True,
            "strategy": "StochRSI",
            "indicators": {
                "stochRSI": {
                    "enabled": True,
                    "lower_band": 35,
                    "upper_band": 100,
                    "K": 3,
                    "D": 3,
                    "rsi_length": 14,
                    "stoch_length": 14,
                    "source": "Close",
                    "dynamic_bands_enabled": True,
                    "atr_period": 20,
                    "atr_sensitivity": 1.5,
                    "band_adjustment_factor": 0.3,
                    "min_band_width": 10,
                    "max_band_width": 50,
                },
                "stoch": {
                    "enabled": True,
                    "lower_band": 35,
                    "upper_band": 80,
                    "K_Length": 14,
                    "smooth_K": 3,
                    "smooth_D": 3,
                },
                "EMA": {
                    "enabled": True,
                    "ema_period": 9,
                    "fast_period": 10,
                    "slow_period": 30,
                    "source": "Close",
                    "smoothing": 2,
                },
            },
            "risk_management": {
                "use_atr_stop_loss": True,
                "atr_period": 14,
                "atr_multiplier": 2.0,
                "use_atr_position_sizing": True,
            },
            "volume_confirmation": {
                "enabled": True,
                "volume_period": 20,
                "relative_volume_period": 50,
                "volume_confirmation_threshold": 1.2,
                "min_volume_ratio": 1.0,
                "profile_periods": 100,
                "require_volume_confirmation": True,
            },
        }

    yaml_stub.safe_load = _safe_load
    sys.modules["yaml"] = yaml_stub

from indicators.volume_analysis import VolumeConfirmationResult
from strategies.enhanced_stoch_rsi_strategy import EnhancedStochRSIStrategy


@dataclass
class _AnalyzerFactory:
    """Factory that mirrors the production factory signature."""

    result: Optional[VolumeConfirmationResult]

    def __call__(self, *_: object, **__: object) -> "_StubVolumeAnalyzer":
        return _StubVolumeAnalyzer(self.result)


class _StubVolumeAnalyzer:
    """Minimal stub to exercise volume confirmation branches."""

    def __init__(self, result: Optional[VolumeConfirmationResult]):
        self._result = result
        self.calls = 0

    def confirm_signal_with_volume(self, df: pd.DataFrame, signal: int) -> VolumeConfirmationResult:
        self.calls += 1
        if self._result is None:
            raise AssertionError("Volume analyzer should not be invoked for this scenario")
        return self._result

    def get_volume_dashboard_data(self, df: pd.DataFrame) -> dict:
        if self._result is None:
            return {"volume_confirmed": False}
        return {
            "volume_confirmed": self._result.is_confirmed,
            "volume_ratio": self._result.volume_ratio,
            "relative_volume": self._result.relative_volume,
        }


@pytest.fixture
def strategy_config():
    indicators = SimpleNamespace(stochRSI=SimpleNamespace(enabled=True))
    volume_confirmation = SimpleNamespace(enabled=True, require_volume_confirmation=True)
    return SimpleNamespace(
        indicators=indicators,
        candle_lookback_period=2,
        volume_confirmation=volume_confirmation,
    )


@pytest.fixture
def market_data() -> pd.DataFrame:
    index = pd.date_range("2023-01-01", periods=6, freq="min")
    return pd.DataFrame(
        {
            "open": [100.0, 100.5, 101.0, 101.5, 102.0, 102.5],
            "high": [100.6, 101.1, 101.5, 102.0, 102.6, 103.0],
            "low": [99.8, 100.2, 100.7, 101.2, 101.8, 102.1],
            "close": [100.4, 100.9, 101.4, 101.9, 102.4, 102.9],
            "volume": [1_000, 1_200, 1_400, 1_650, 1_900, 2_150],
        },
        index=index,
    )


@pytest.fixture
def patch_indicator(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], None]:
    def _apply(signal_value: int) -> None:
        def _stub(self: EnhancedStochRSIStrategy, df: pd.DataFrame) -> pd.DataFrame:
            indicator_df = df.copy()
            indicator_df["StochRSI Signal"] = [0] * (len(df) - 1) + [signal_value]
            return indicator_df

        monkeypatch.setattr(EnhancedStochRSIStrategy, "_calculate_stoch_rsi_indicators", _stub)

    return _apply


def _make_volume_result(
    *,
    is_confirmed: bool,
    ratio: float,
    rel_volume: float,
    trend: str,
    strength: float,
) -> VolumeConfirmationResult:
    return VolumeConfirmationResult(
        is_confirmed=is_confirmed,
        volume_ratio=ratio,
        relative_volume=rel_volume,
        volume_trend=trend,
        profile_levels={"support_0": 99.5, "resistance_0": 103.0},
        confirmation_strength=strength,
    )


def test_generate_signal_confirms_volume(
    monkeypatch: pytest.MonkeyPatch,
    strategy_config,
    market_data,
    patch_indicator,
):
    patch_indicator(1)
    analyzer_factory = _AnalyzerFactory(
        _make_volume_result(is_confirmed=True, ratio=1.6, rel_volume=1.4, trend="high", strength=0.92)
    )
    monkeypatch.setattr("strategies.enhanced_stoch_rsi_strategy.get_volume_analyzer", analyzer_factory)

    strategy = EnhancedStochRSIStrategy(strategy_config)
    result = strategy.generate_signal(market_data)

    assert result == 1
    assert strategy.volume_confirmation_stats == {
        "total_signals": 1,
        "volume_confirmed": 1,
        "volume_rejected": 0,
    }
    assert strategy.signal_history[-1]["volume_confirmed"] is True
    assert strategy.signal_history[-1]["volume_data"]["volume_ratio"] == pytest.approx(1.6)


def test_generate_signal_rejects_when_volume_fails(
    monkeypatch: pytest.MonkeyPatch,
    strategy_config,
    market_data,
    patch_indicator,
):
    patch_indicator(1)
    analyzer_factory = _AnalyzerFactory(
        _make_volume_result(is_confirmed=False, ratio=0.7, rel_volume=0.6, trend="low", strength=0.35)
    )
    monkeypatch.setattr("strategies.enhanced_stoch_rsi_strategy.get_volume_analyzer", analyzer_factory)

    strategy = EnhancedStochRSIStrategy(strategy_config)
    result = strategy.generate_signal(market_data)

    assert result == 0
    assert strategy.volume_confirmation_stats == {
        "total_signals": 1,
        "volume_confirmed": 0,
        "volume_rejected": 1,
    }
    assert strategy.signal_history[-1]["volume_confirmed"] is False
    assert strategy.signal_history[-1]["volume_data"]["volume_ratio"] == pytest.approx(0.7)


def test_generate_signal_skips_volume_when_not_required(
    monkeypatch: pytest.MonkeyPatch,
    strategy_config,
    market_data,
    patch_indicator,
):
    strategy_config.volume_confirmation.require_volume_confirmation = False
    patch_indicator(1)

    analyzer_factory = _AnalyzerFactory(result=None)
    monkeypatch.setattr("strategies.enhanced_stoch_rsi_strategy.get_volume_analyzer", analyzer_factory)

    strategy = EnhancedStochRSIStrategy(strategy_config)
    result = strategy.generate_signal(market_data)

    assert result == 1
    assert strategy.volume_confirmation_stats == {
        "total_signals": 1,
        "volume_confirmed": 0,
        "volume_rejected": 0,
    }


def test_generate_signal_returns_zero_without_base_signal(
    monkeypatch: pytest.MonkeyPatch,
    strategy_config,
    market_data,
    patch_indicator,
):
    patch_indicator(0)

    analyzer_factory = _AnalyzerFactory(result=None)
    monkeypatch.setattr("strategies.enhanced_stoch_rsi_strategy.get_volume_analyzer", analyzer_factory)

    strategy = EnhancedStochRSIStrategy(strategy_config)
    result = strategy.generate_signal(market_data)

    assert result == 0
    assert strategy.volume_confirmation_stats == {
        "total_signals": 0,
        "volume_confirmed": 0,
        "volume_rejected": 0,
    }
    assert strategy.signal_history == []
