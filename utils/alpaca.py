"""Shared helpers for working with Alpaca API credentials."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from config.unified_config import TradingConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlpacaCredentials:
    """Structured Alpaca credential bundle."""

    key_id: str
    secret_key: str
    base_url: str

    @property
    def is_paper(self) -> bool:
        """Heuristic to detect paper trading endpoint."""
        return "paper" in self.base_url.lower()


def _resolve_auth_path(source: Union[TradingConfig, str, Path]) -> Path:
    if isinstance(source, TradingConfig):
        return Path(source.api.alpaca_auth_file)
    return Path(source)


def load_alpaca_credentials(source: Union[TradingConfig, str, Path]) -> AlpacaCredentials:
    """Load credentials from config or explicit path."""

    auth_path = _resolve_auth_path(source)
    try:
        with auth_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        logger.error("Alpaca authentication file not found: %s", auth_path)
        raise
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Alpaca auth file %s: %s", auth_path, exc)
        raise

    try:
        key_id = payload["APCA-API-KEY-ID"].strip()
        secret_key = payload["APCA-API-SECRET-KEY"].strip()
    except KeyError as exc:
        logger.error("Missing Alpaca credential field %s in %s", exc, auth_path)
        raise

    base_url = payload.get("BASE-URL", "https://paper-api.alpaca.markets").strip()

    if not key_id or not secret_key:
        raise ValueError(f"Incomplete Alpaca credentials in {auth_path}")

    return AlpacaCredentials(key_id=key_id, secret_key=secret_key, base_url=base_url)
