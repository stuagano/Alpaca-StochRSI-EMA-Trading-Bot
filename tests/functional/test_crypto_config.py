"""Lightweight checks that the default config is aligned with crypto trading."""

from config.unified_config import get_config


def test_crypto_strategy_defaults():
    config = get_config()

    assert config.crypto_only is True
    assert config.market_type == "crypto"
    assert config.strategy == "crypto_scalping"


def test_signal_filters_available():
    config = get_config()

    # ensure the simplified filters we rely on downstream are present
    assert hasattr(config, "signal_filters")
    filters = config.signal_filters

    assert filters.enabled is True
    assert filters.minimum_quality_score >= 0
