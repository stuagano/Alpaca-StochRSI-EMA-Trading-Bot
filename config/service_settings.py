"""Centralized runtime configuration for the unified trading service.

This module keeps service level configuration in one place so application
modules can stay focused on behaviour. All values originate from the
environment (typically via ``.env`` for local development) with sensible
defaults for rapid onboarding. Keeping configuration here avoids scattering
magic numbers throughout the codebase and makes the runtime surface area
explicit for review and observability.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from config.environment import get_environment_config

logger = logging.getLogger(__name__)

DEFAULT_CRYPTO_SYMBOLS = [
    "BTC/USD",
    "ETH/USD",
    "LTC/USD",
    "BCH/USD",
    "LINK/USD",
    "UNI/USD",
    "AAVE/USD",
    "MKR/USD",
    "MATIC/USD",
    "AVAX/USD",
    "DOGE/USD",
    "SHIB/USD",
    "XRP/USD",
    "ADA/USD",
    "SOL/USD",
]

DEFAULT_CACHE_REFRESH_SECONDS = 5
DEFAULT_SCALPER_POLL_SECONDS = 10
DEFAULT_SCALPER_COOLDOWN_SECONDS = 60
DEFAULT_SCANNER_INTERVAL_SECONDS = 60
DEFAULT_DAILY_LOSS_LIMIT = 200.0
DEFAULT_MAX_CONCURRENT_POSITIONS = 3

DEFAULT_CRYPTO_METADATA = {
    "BTC/USD": {"name": "Bitcoin", "exchange": "FTXU"},
    "ETH/USD": {"name": "Ethereum", "exchange": "FTXU"},
    "LTC/USD": {"name": "Litecoin", "exchange": "FTXU"},
    "BCH/USD": {"name": "Bitcoin Cash", "exchange": "FTXU"},
    "LINK/USD": {"name": "Chainlink", "exchange": "FTXU"},
    "UNI/USD": {"name": "Uniswap", "exchange": "FTXU"},
    "AAVE/USD": {"name": "Aave", "exchange": "FTXU"},
    "MKR/USD": {"name": "Maker", "exchange": "FTXU"},
    "MATIC/USD": {"name": "Polygon", "exchange": "FTXU"},
    "AVAX/USD": {"name": "Avalanche", "exchange": "FTXU"},
    "DOGE/USD": {"name": "Dogecoin", "exchange": "FTXU"},
    "SHIB/USD": {"name": "Shiba Inu", "exchange": "FTXU"},
    "XRP/USD": {"name": "XRP", "exchange": "FTXU"},
    "ADA/USD": {"name": "Cardano", "exchange": "FTXU"},
    "SOL/USD": {"name": "Solana", "exchange": "FTXU"},
}


@dataclass(frozen=True)
class AlpacaSettings:
    """Connection details for the Alpaca API."""

    auth_file: Path
    api_key: Optional[str]
    api_secret: Optional[str]
    api_base_url: str


@dataclass(frozen=True)
class TradingServiceSettings:
    """Container for the runtime settings used by the unified service."""

    alpaca: AlpacaSettings
    crypto_symbols: List[str]
    enabled_background_workers: Optional[List[str]]
    crypto_scanner_interval_seconds: int
    cache_refresh_seconds: int
    scalper_poll_interval_seconds: int
    scalper_cooldown_seconds: int
    max_concurrent_positions: int
    daily_loss_limit: float
    crypto_metadata: Dict[str, Dict[str, str]]


def _parse_list(value: Optional[str], default: List[str]) -> List[str]:
    if not value:
        return default

    cleaned_value = value.strip()
    if not cleaned_value:
        return default

    if cleaned_value.startswith("["):
        try:
            parsed = json.loads(cleaned_value)
        except json.JSONDecodeError:
            logger.warning(
                "Unable to parse JSON list from environment value '%s'; falling back to default %s",
                value,
                default,
            )
            return default
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        logger.warning(
            "JSON value for list environment variable '%s' is not a list; falling back to default %s",
            value,
            default,
        )
        return default

    return [item.strip() for item in cleaned_value.split(",") if item.strip()]


def _parse_optional_list(value: Optional[str]) -> Optional[List[str]]:
    if value is None:
        return None

    parsed = _parse_list(value, [])
    return parsed


def _parse_int(value: Optional[str], default: int, env_name: str) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(
            "Environment variable %s='%s' is not a valid integer; falling back to %s",
            env_name,
            value,
            default,
        )
        return default


def _parse_float(value: Optional[str], default: float, env_name: str) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning(
            "Environment variable %s='%s' is not a valid float; falling back to %s",
            env_name,
            value,
            default,
        )
        return default


def _derive_symbol_metadata(symbol: str) -> Dict[str, str]:
    base_metadata = DEFAULT_CRYPTO_METADATA.get(symbol)
    if base_metadata:
        return base_metadata

    ticker = symbol.split("/")[0]
    return {"name": ticker.capitalize(), "exchange": "FTXU"}


def _parse_metadata(value: Optional[str], symbols: List[str]) -> Dict[str, Dict[str, str]]:
    if value:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            logger.warning(
                "TRADING_SERVICE_CRYPTO_METADATA is not valid JSON; using defaults",
            )
        else:
            if isinstance(parsed, dict):
                metadata: Dict[str, Dict[str, str]] = {}
                for symbol in symbols:
                    entry = parsed.get(symbol)
                    if isinstance(entry, dict):
                        metadata[symbol] = {
                            "name": str(entry.get("name", _derive_symbol_metadata(symbol)["name"])),
                            "exchange": str(entry.get("exchange", _derive_symbol_metadata(symbol)["exchange"])),
                        }
                    else:
                        metadata[symbol] = _derive_symbol_metadata(symbol)
                return metadata
            logger.warning("TRADING_SERVICE_CRYPTO_METADATA must be a JSON object; using defaults")

    return {symbol: _derive_symbol_metadata(symbol) for symbol in symbols}


def _resolve_alpaca_credentials() -> AlpacaSettings:
    env_config = get_environment_config()

    auth_file = Path(os.getenv("ALPACA_AUTH_FILE", "AUTH/authAlpaca.txt"))
    api_key = os.getenv("APCA_API_KEY_ID")
    api_secret = os.getenv("APCA_API_SECRET_KEY")
    api_base_url = os.getenv("APCA_API_BASE_URL", env_config.alpaca_base_url)

    return AlpacaSettings(
        auth_file=auth_file,
        api_key=api_key,
        api_secret=api_secret,
        api_base_url=api_base_url,
    )


@lru_cache(maxsize=1)
def get_service_settings() -> TradingServiceSettings:
    """Return cached service settings derived from environment variables."""

    alpaca_settings = _resolve_alpaca_credentials()

    crypto_symbols = _parse_list(
        os.getenv("TRADING_SERVICE_CRYPTO_SYMBOLS"),
        DEFAULT_CRYPTO_SYMBOLS,
    )
    enabled_background_workers = _parse_optional_list(
        os.getenv("TRADING_SERVICE_BACKGROUND_WORKERS")
    )
    cache_refresh_seconds = _parse_int(
        os.getenv("TRADING_SERVICE_CACHE_REFRESH_SECONDS"),
        DEFAULT_CACHE_REFRESH_SECONDS,
        "TRADING_SERVICE_CACHE_REFRESH_SECONDS",
    )
    scalper_poll_seconds = _parse_int(
        os.getenv("TRADING_SERVICE_SCALPER_POLL_SECONDS"),
        DEFAULT_SCALPER_POLL_SECONDS,
        "TRADING_SERVICE_SCALPER_POLL_SECONDS",
    )
    scalper_cooldown_seconds = _parse_int(
        os.getenv("TRADING_SERVICE_SCALPER_COOLDOWN_SECONDS"),
        DEFAULT_SCALPER_COOLDOWN_SECONDS,
        "TRADING_SERVICE_SCALPER_COOLDOWN_SECONDS",
    )
    max_positions = _parse_int(
        os.getenv("TRADING_SERVICE_MAX_CONCURRENT_POSITIONS"),
        DEFAULT_MAX_CONCURRENT_POSITIONS,
        "TRADING_SERVICE_MAX_CONCURRENT_POSITIONS",
    )
    daily_loss_limit = _parse_float(
        os.getenv("TRADING_SERVICE_DAILY_LOSS_LIMIT"),
        DEFAULT_DAILY_LOSS_LIMIT,
        "TRADING_SERVICE_DAILY_LOSS_LIMIT",
    )
    crypto_scanner_interval = _parse_int(
        os.getenv("TRADING_SERVICE_CRYPTO_SCANNER_INTERVAL_SECONDS"),
        DEFAULT_SCANNER_INTERVAL_SECONDS,
        "TRADING_SERVICE_CRYPTO_SCANNER_INTERVAL_SECONDS",
    )
    crypto_metadata = _parse_metadata(os.getenv("TRADING_SERVICE_CRYPTO_METADATA"), crypto_symbols)

    return TradingServiceSettings(
        alpaca=alpaca_settings,
        crypto_symbols=crypto_symbols,
        enabled_background_workers=enabled_background_workers,
        crypto_scanner_interval_seconds=crypto_scanner_interval,
        cache_refresh_seconds=cache_refresh_seconds,
        scalper_poll_interval_seconds=scalper_poll_seconds,
        scalper_cooldown_seconds=scalper_cooldown_seconds,
        max_concurrent_positions=max_positions,
        daily_loss_limit=daily_loss_limit,
        crypto_metadata=crypto_metadata,
    )


__all__ = ["AlpacaSettings", "TradingServiceSettings", "get_service_settings"]
