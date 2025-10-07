"""Pytest configuration shared across the test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.helpers import ensure_strategy_runtime_dependencies


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Automatically guard strategy tests behind their optional dependencies."""

    if item.get_closest_marker("requires_strategy_runtime"):
        ensure_strategy_runtime_dependencies()


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers used across the suite."""

    config.addinivalue_line(
        "markers",
        "requires_strategy_runtime: skip when strategy runtime dependencies are missing",
    )
