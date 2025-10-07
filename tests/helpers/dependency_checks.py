"""Utilities for managing optional test dependencies."""

from __future__ import annotations

from importlib import util
from typing import Iterable

import pytest

from config.runtime_dependencies import strategy_runtime_modules

# Keep optional runtime dependencies that power the live crypto scanner in one place
# so individual tests can stay DRY while still failing fast when a requirement is
# missing in the execution environment.
_STRATEGY_RUNTIME_DEPENDENCIES: tuple[str, ...] = strategy_runtime_modules()


def _find_missing_dependencies(dependencies: Iterable[str]) -> list[str]:
    """Return a list of missing modules for the provided dependency iterable."""

    return [name for name in dependencies if util.find_spec(name) is None]


def ensure_strategy_runtime_dependencies() -> None:
    """Skip strategy-dependent tests when optional dependencies are unavailable."""

    missing = _find_missing_dependencies(_STRATEGY_RUNTIME_DEPENDENCIES)
    if missing:
        pytest.skip(
            "strategy runtime dependencies are unavailable: " + ", ".join(missing)
        )


def missing_strategy_runtime_dependencies() -> tuple[str, ...]:
    """Expose the current set of missing strategy dependencies for reuse."""

    return tuple(_find_missing_dependencies(_STRATEGY_RUNTIME_DEPENDENCIES))
