
"""Contract tests for ``config.service_settings`` parsing semantics."""

import json

import pytest

from config.environment import get_environment_config
from config.service_settings import (
    DEFAULT_CACHE_REFRESH_SECONDS,
    DEFAULT_CRYPTO_SYMBOLS,
    DEFAULT_DAILY_LOSS_LIMIT,
    DEFAULT_MAX_CONCURRENT_POSITIONS,
    DEFAULT_SCALPER_COOLDOWN_SECONDS,
    DEFAULT_SCALPER_POLL_SECONDS,
    DEFAULT_SCANNER_INTERVAL_SECONDS,
    get_service_settings,
)


@pytest.fixture(autouse=True)
def reset_runtime_caches():
    """Ensure each test observes a fresh configuration instance."""

    get_environment_config.cache_clear()
    get_service_settings.cache_clear()
    yield
    get_environment_config.cache_clear()
    get_service_settings.cache_clear()


def test_get_service_settings_defaults(monkeypatch, tmp_path):
    """When no overrides are set the defaults should be returned."""

    # Explicitly remove any environment variables that could interfere.
    for variable in [
        "TRADING_RUNTIME_ENV",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "APCA_API_BASE_URL",
        "ALPACA_AUTH_FILE",
        "TRADING_SERVICE_CRYPTO_SYMBOLS",
        "TRADING_SERVICE_CACHE_REFRESH_SECONDS",
        "TRADING_SERVICE_SCALPER_POLL_SECONDS",
        "TRADING_SERVICE_SCALPER_COOLDOWN_SECONDS",
        "TRADING_SERVICE_MAX_CONCURRENT_POSITIONS",
        "TRADING_SERVICE_DAILY_LOSS_LIMIT",
        "TRADING_SERVICE_CRYPTO_SCANNER_INTERVAL_SECONDS",
        "TRADING_SERVICE_CRYPTO_METADATA",
    ]:
        monkeypatch.delenv(variable, raising=False)

    auth_path = tmp_path / "auth.txt"
    monkeypatch.setenv("ALPACA_AUTH_FILE", str(auth_path))

    settings = get_service_settings()

    assert settings.crypto_symbols == DEFAULT_CRYPTO_SYMBOLS
    assert settings.cache_refresh_seconds == DEFAULT_CACHE_REFRESH_SECONDS
    assert settings.scalper_poll_interval_seconds == DEFAULT_SCALPER_POLL_SECONDS
    assert settings.scalper_cooldown_seconds == DEFAULT_SCALPER_COOLDOWN_SECONDS
    assert settings.max_concurrent_positions == DEFAULT_MAX_CONCURRENT_POSITIONS
    assert settings.daily_loss_limit == DEFAULT_DAILY_LOSS_LIMIT
    assert settings.crypto_scanner_interval_seconds == DEFAULT_SCANNER_INTERVAL_SECONDS
    assert settings.crypto_metadata.keys() == set(DEFAULT_CRYPTO_SYMBOLS)
    assert settings.enabled_background_workers is None

    assert settings.alpaca.auth_file == auth_path
    assert settings.alpaca.api_key is None
    assert settings.alpaca.api_secret is None
    assert "alpaca.markets" in settings.alpaca.api_base_url


def test_get_service_settings_environment_overrides(monkeypatch, tmp_path):
    """Environment variables should override the default configuration."""

    monkeypatch.setenv("TRADING_RUNTIME_ENV", "production")
    monkeypatch.setenv("APCA_API_KEY_ID", "unit-test-key")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "unit-test-secret")
    monkeypatch.setenv("APCA_API_BASE_URL", "https://example.com")

    auth_path = tmp_path / "overrides.json"
    monkeypatch.setenv("ALPACA_AUTH_FILE", str(auth_path))

    monkeypatch.setenv(
        "TRADING_SERVICE_CRYPTO_SYMBOLS",
        json.dumps(["BTC/USD", "ETH/USD"]),
    )
    monkeypatch.setenv("TRADING_SERVICE_CACHE_REFRESH_SECONDS", "7")
    monkeypatch.setenv("TRADING_SERVICE_SCALPER_POLL_SECONDS", "11")
    monkeypatch.setenv("TRADING_SERVICE_SCALPER_COOLDOWN_SECONDS", "19")
    monkeypatch.setenv("TRADING_SERVICE_MAX_CONCURRENT_POSITIONS", "4")
    monkeypatch.setenv("TRADING_SERVICE_DAILY_LOSS_LIMIT", "123.45")
    monkeypatch.setenv("TRADING_SERVICE_CRYPTO_SCANNER_INTERVAL_SECONDS", "23")
    monkeypatch.setenv(
        "TRADING_SERVICE_CRYPTO_METADATA",
        json.dumps(
            {
                "BTC/USD": {"name": "Bitcoin", "exchange": "CBSE"},
                "ETH/USD": {"name": "Ethereum", "exchange": "FTXU"},
            }
        ),
    )
    monkeypatch.setenv(
        "TRADING_SERVICE_BACKGROUND_WORKERS",
        "update_cache,crypto_scalper",
    )

    settings = get_service_settings()

    assert settings.crypto_symbols == ["BTC/USD", "ETH/USD"]
    assert settings.cache_refresh_seconds == 7
    assert settings.scalper_poll_interval_seconds == 11
    assert settings.scalper_cooldown_seconds == 19
    assert settings.max_concurrent_positions == 4
    assert settings.daily_loss_limit == 123.45
    assert settings.crypto_scanner_interval_seconds == 23
    assert settings.crypto_metadata["BTC/USD"]["exchange"] == "CBSE"
    assert settings.crypto_metadata["ETH/USD"]["name"] == "Ethereum"
    assert settings.enabled_background_workers == ["update_cache", "crypto_scalper"]

    assert settings.alpaca.auth_file == auth_path
    assert settings.alpaca.api_key == "unit-test-key"
    assert settings.alpaca.api_secret == "unit-test-secret"
    assert settings.alpaca.api_base_url == "https://example.com"


def test_background_worker_env_handles_blank_values(monkeypatch):
    monkeypatch.setenv("TRADING_SERVICE_BACKGROUND_WORKERS", "   ")

    settings = get_service_settings()

    assert settings.enabled_background_workers == []
