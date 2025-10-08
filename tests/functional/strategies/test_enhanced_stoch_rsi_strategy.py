"""Regression-focused tests for the enhanced StochRSI strategy."""

from __future__ import annotations

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
    def _apply(signal_value: int, *, indicator_payload: Optional[dict[str, list[float]]] = None) -> None:
        def _stub(self: EnhancedStochRSIStrategy, df: pd.DataFrame) -> pd.DataFrame:
            indicator_df = df.copy()
            indicator_df["StochRSI Signal"] = [0] * (len(df) - 1) + [signal_value]
            if indicator_payload:
                for column, values in indicator_payload.items():
                    indicator_df[column] = values
            return indicator_df

        monkeypatch.setattr(EnhancedStochRSIStrategy, "_calculate_stoch_rsi_indicators", _stub)

    return _apply


class _SequenceVolumeAnalyzer(_StubVolumeAnalyzer):
    """Stub that yields a sequence of volume confirmation results."""

    def __init__(self, results: list[VolumeConfirmationResult]):
        super().__init__(result=results[0] if results else None)
        self._sequence = iter(results)
        self._last_result: Optional[VolumeConfirmationResult] = None

    def confirm_signal_with_volume(self, df: pd.DataFrame, signal: int) -> VolumeConfirmationResult:
        self.calls += 1
        self._last_result = next(self._sequence)
        return self._last_result

    def get_volume_dashboard_data(self, df: pd.DataFrame) -> dict:
        source = self._last_result or self._result
        if source is None:
            return {"volume_confirmed": False}
        return {
            "volume_confirmed": source.is_confirmed,
            "volume_ratio": source.volume_ratio,
            "relative_volume": source.relative_volume,
        }


@pytest.fixture
def strategy_builder(
    monkeypatch: pytest.MonkeyPatch,
    strategy_config,
    patch_indicator,
) -> Callable[..., tuple[EnhancedStochRSIStrategy, _StubVolumeAnalyzer]]:
    def _build(
        *,
        signal_value: int,
        analyzer_results: Optional[object] = None,
        require_volume: bool = True,
        indicator_payload: Optional[dict[str, list[float]]] = None,
    ) -> tuple[EnhancedStochRSIStrategy, _StubVolumeAnalyzer]:
        patch_indicator(signal_value, indicator_payload=indicator_payload)
        strategy_config.volume_confirmation.require_volume_confirmation = require_volume

        if analyzer_results is None:
            analyzer = _StubVolumeAnalyzer(result=None)
        elif isinstance(analyzer_results, list):
            analyzer = _SequenceVolumeAnalyzer(results=analyzer_results)
        else:
            analyzer = _StubVolumeAnalyzer(result=analyzer_results)

        monkeypatch.setattr(
            "strategies.enhanced_stoch_rsi_strategy.get_volume_analyzer", lambda *_: analyzer
        )

        strategy = EnhancedStochRSIStrategy(strategy_config)
        return strategy, analyzer

    return _build


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


def test_generate_signal_confirms_volume(strategy_builder, market_data):
    result = _make_volume_result(
        is_confirmed=True,
        ratio=1.6,
        rel_volume=1.4,
        trend="high",
        strength=0.92,
    )
    strategy, analyzer = strategy_builder(signal_value=1, analyzer_results=result)
    result = strategy.generate_signal(market_data)

    assert result == 1
    assert strategy.volume_confirmation_stats == {
        "total_signals": 1,
        "volume_confirmed": 1,
        "volume_rejected": 0,
    }
    assert strategy.signal_history[-1]["volume_confirmed"] is True
    assert strategy.signal_history[-1]["volume_data"]["volume_ratio"] == pytest.approx(1.6)
    assert analyzer.calls == 1


def test_generate_signal_rejects_when_volume_fails(strategy_builder, market_data):
    strategy, analyzer = strategy_builder(
        signal_value=1,
        analyzer_results=_make_volume_result(
            is_confirmed=False,
            ratio=0.7,
            rel_volume=0.6,
            trend="low",
            strength=0.35,
        ),
    )
    result = strategy.generate_signal(market_data)

    assert result == 0
    assert strategy.volume_confirmation_stats == {
        "total_signals": 1,
        "volume_confirmed": 0,
        "volume_rejected": 1,
    }
    assert strategy.signal_history[-1]["volume_confirmed"] is False
    assert strategy.signal_history[-1]["volume_data"]["volume_ratio"] == pytest.approx(0.7)
    assert analyzer.calls == 1


def test_generate_signal_skips_volume_when_not_required(strategy_builder, market_data):
    strategy, analyzer = strategy_builder(signal_value=1, analyzer_results=None, require_volume=False)
    result = strategy.generate_signal(market_data)

    assert result == 1
    assert strategy.volume_confirmation_stats == {
        "total_signals": 1,
        "volume_confirmed": 0,
        "volume_rejected": 0,
    }
    assert analyzer.calls == 0


def test_generate_signal_returns_zero_without_base_signal(strategy_builder, market_data):
    strategy, analyzer = strategy_builder(signal_value=0, analyzer_results=None)
    result = strategy.generate_signal(market_data)

    assert result == 0
    assert strategy.volume_confirmation_stats == {
        "total_signals": 0,
        "volume_confirmed": 0,
        "volume_rejected": 0,
    }
    assert strategy.signal_history == []
    assert analyzer.calls == 0


def test_get_strategy_performance_tracks_confirmed_and_rejected(strategy_builder, market_data):
    sequence = [
        _make_volume_result(is_confirmed=True, ratio=1.8, rel_volume=1.5, trend="rising", strength=0.85),
        _make_volume_result(is_confirmed=False, ratio=0.6, rel_volume=0.55, trend="falling", strength=0.25),
    ]
    strategy, analyzer = strategy_builder(signal_value=1, analyzer_results=sequence)

    first_signal = strategy.generate_signal(market_data)
    second_signal = strategy.generate_signal(market_data)

    assert first_signal == 1
    assert second_signal == 0
    assert analyzer.calls == 2

    stats = strategy.get_strategy_performance()

    assert stats["total_signals"] == 2
    assert stats["volume_confirmed"] == 1
    assert stats["volume_rejected"] == 1
    assert stats["confirmation_rate"] == pytest.approx(0.5)
    assert stats["rejection_rate"] == pytest.approx(0.5)
    assert stats["recent_confirmation_rate"] == pytest.approx(0.5)
    assert stats["avg_confirmed_volume_ratio"] == pytest.approx(1.8)
    assert stats["avg_confirmed_relative_volume"] == pytest.approx(1.5)
    assert stats["avg_confirmation_strength"] == pytest.approx(0.85)


def test_get_dashboard_data_surfaces_volume_and_indicator_metrics(strategy_builder, market_data):
    indicator_payload = {
        "RSI": [35, 45, 55, 60, 65, 70],
        "Stoch %K": [10, 20, 30, 40, 50, 60],
        "Stoch %D": [15, 25, 35, 45, 55, 65],
    }
    volume_result = _make_volume_result(
        is_confirmed=True,
        ratio=1.4,
        rel_volume=1.3,
        trend="surging",
        strength=0.9,
    )
    strategy, analyzer = strategy_builder(
        signal_value=1,
        analyzer_results=volume_result,
        indicator_payload=indicator_payload,
    )

    strategy.generate_signal(market_data)

    dashboard = strategy.get_dashboard_data(market_data)

    assert dashboard["strategy_name"] == "Enhanced StochRSI"
    assert dashboard["current_signal"] == 1
    assert dashboard["performance"]["volume_confirmed"] == 1
    assert dashboard["volume_analysis"] == {
        "volume_confirmed": True,
        "volume_ratio": pytest.approx(1.4),
        "relative_volume": pytest.approx(1.3),
    }
    assert dashboard["current_indicators"] == {
        "rsi": pytest.approx(70),
        "stoch_k": pytest.approx(60),
        "stoch_d": pytest.approx(65),
        "volume": market_data.iloc[-1]["volume"],
    }
    assert analyzer.calls == 1
