"""Centralised optional runtime dependency metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class OptionalDependency:
    """Representation of an optional dependency and its import/package metadata."""

    module: str
    requirement: str


STRATEGY_RUNTIME_DEPENDENCIES: Tuple[OptionalDependency, ...] = (
    OptionalDependency("alpaca_trade_api", "alpaca-trade-api>=3.0.0"),
    OptionalDependency("alpaca", "alpaca-py"),
    OptionalDependency("dotenv", "python-dotenv>=0.19.0"),
    OptionalDependency("uvicorn", "uvicorn>=0.18.0"),
    OptionalDependency("websocket", "websocket-client>=1.6.0"),
)


def strategy_runtime_modules() -> tuple[str, ...]:
    """Return the module import paths for optional strategy runtime dependencies."""

    return tuple(dependency.module for dependency in STRATEGY_RUNTIME_DEPENDENCIES)


def strategy_runtime_requirement_specs() -> tuple[str, ...]:
    """Return pip requirement specifiers for optional strategy dependencies."""

    return tuple(dependency.requirement for dependency in STRATEGY_RUNTIME_DEPENDENCIES)
