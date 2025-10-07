"""Utilities for describing and loading the runtime environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from importlib import import_module, util
from pathlib import Path


def _resolve_dotenv_loader():
    """Return ``dotenv.load_dotenv`` when available, otherwise a no-op."""

    spec = util.find_spec("dotenv")
    if spec is None:
        def _noop(*_args, **_kwargs):  # pragma: no cover - exercised when dependency absent
            return False

        return _noop

    module = import_module("dotenv")
    return getattr(module, "load_dotenv")


load_dotenv = _resolve_dotenv_loader()


class RuntimeEnvironment(str, Enum):
    """Supported execution environments for the trading bot."""

    SANDBOX = "sandbox"
    PAPER = "paper"
    PRODUCTION = "production"

    @classmethod
    def from_value(cls, value: str | None) -> "RuntimeEnvironment":
        """Parse an environment name and fall back to ``SANDBOX`` when unknown."""

        if not value:
            return cls.SANDBOX

        normalized = value.strip().lower()
        for member in cls:
            if normalized == member.value:
                return member

        # Preserve backwards compatibility by accepting shorthand tokens.
        aliases = {
            "dev": cls.SANDBOX,
            "development": cls.SANDBOX,
            "test": cls.PAPER,
            "staging": cls.PAPER,
            "prod": cls.PRODUCTION,
            "live": cls.PRODUCTION,
        }
        return aliases.get(normalized, cls.SANDBOX)


@dataclass(frozen=True)
class EnvironmentConfig:
    """Container describing execution characteristics for the application."""

    name: RuntimeEnvironment
    alpaca_base_url: str
    enable_order_execution: bool


def _load_dotenv_file() -> None:
    """Load environment variables from ``.env`` if present.

    ``TRADING_DOTENV_FILE`` can be used to point to a non-standard file path.
    The loader runs once per interpreter lifecycle to avoid repeated disk IO
    and to guarantee the settings are available before other modules import
    configuration.
    """

    candidate = os.getenv("TRADING_DOTENV_FILE")
    if candidate:
        path = Path(candidate)
        if path.exists():
            load_dotenv(dotenv_path=path)
            return

    # Default to project root ``.env``. ``load_dotenv`` safely no-ops if the
    # file is missing which keeps production environments uncluttered.
    load_dotenv()


_load_dotenv_file()


DEFAULT_ALPACA_URLS: dict[RuntimeEnvironment, str] = {
    RuntimeEnvironment.SANDBOX: "https://paper-api.alpaca.markets",
    RuntimeEnvironment.PAPER: "https://paper-api.alpaca.markets",
    RuntimeEnvironment.PRODUCTION: "https://api.alpaca.markets",
}


@lru_cache(maxsize=1)
def get_environment_config() -> EnvironmentConfig:
    """Return the cached ``EnvironmentConfig`` for the current process."""

    runtime = RuntimeEnvironment.from_value(os.getenv("TRADING_RUNTIME_ENV"))

    # Never hard-code API hosts in multiple places. Users can still override
    # ``APCA_API_BASE_URL`` explicitly when they need a custom endpoint.
    alpaca_base_url = os.getenv("APCA_API_BASE_URL", DEFAULT_ALPACA_URLS[runtime])

    # Order execution remains opt-in for sandbox and paper environments.
    raw_execution_flag = os.getenv("TRADING_ENABLE_EXECUTION")
    if raw_execution_flag is None:
        enable_order_execution = runtime is RuntimeEnvironment.PRODUCTION
    else:
        enable_order_execution = raw_execution_flag.strip().lower() in {"1", "true", "yes", "on"}

    return EnvironmentConfig(
        name=runtime,
        alpaca_base_url=alpaca_base_url,
        enable_order_execution=enable_order_execution,
    )


def is_sandbox() -> bool:
    """Convenience helper to test whether the runtime is sandbox-like."""

    env = get_environment_config()
    return env.name in {RuntimeEnvironment.SANDBOX, RuntimeEnvironment.PAPER}


__all__ = [
    "EnvironmentConfig",
    "RuntimeEnvironment",
    "get_environment_config",
    "is_sandbox",
]
