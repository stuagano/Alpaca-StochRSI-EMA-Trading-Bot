"""Ensure optional strategy dependency metadata stays DRY across the repo."""

from __future__ import annotations

from pathlib import Path

from importlib import import_module

import pytest

from config.runtime_dependencies import strategy_runtime_requirement_specs


def test_strategy_dependency_manifest_matches_configured_requirements():
    """The requirements manifest should mirror the dependency configuration."""

    manifest_path = Path(__file__).resolve().parents[2] / "requirements" / "strategy-runtime.txt"
    manifest_requirements = {
        line.strip()
        for line in manifest_path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert manifest_requirements == set(strategy_runtime_requirement_specs())


def test_strategy_extra_uses_configured_requirements():
    """The package extras should be sourced from the shared dependency metadata."""

    pytest.importorskip("setuptools")
    setup_module = import_module("setup")

    assert set(setup_module.STRATEGY_RUNTIME_EXTRAS) == set(
        strategy_runtime_requirement_specs()
    )
