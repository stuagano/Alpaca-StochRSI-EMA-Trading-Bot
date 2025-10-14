"""Helpers for working with signal filtering configuration."""

from __future__ import annotations

from typing import Any, Union

from config.unified_config import TradingConfig, VolumeConfirmationConfig

SignalFilterSource = Union[TradingConfig, VolumeConfirmationConfig, dict]


def ensure_signal_filters(source: SignalFilterSource) -> VolumeConfirmationConfig:
    """Normalise different config inputs into a VolumeConfirmationConfig."""

    if isinstance(source, VolumeConfirmationConfig):
        return source

    if isinstance(source, TradingConfig):
        candidate = getattr(source, "signal_filters", None)
        return ensure_signal_filters(candidate) if candidate is not None else VolumeConfirmationConfig()

    if isinstance(source, dict):
        return VolumeConfirmationConfig(**source)

    return VolumeConfirmationConfig()


def minimum_strength_percent(filters: VolumeConfirmationConfig) -> float:
    """Return the minimum required signal strength in percent form."""

    return max(0.0, filters.minimum_quality_score * 100)


def confirmation_window(filters: VolumeConfirmationConfig) -> int:
    return filters.confirmation_window


def minimum_signal_gap(filters: VolumeConfirmationConfig) -> int:
    return max(0, int(filters.min_signal_gap_seconds))
