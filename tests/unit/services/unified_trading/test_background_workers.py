from __future__ import annotations

from typing import List

import pytest

from services.unified_trading import (
    list_named_background_workers,
    list_background_workers,
    register_background_worker,
    resolve_background_workers,
    reset_background_workers,
    set_background_workers,
)


@pytest.fixture()
def registry_snapshot() -> None:
    """Snapshot and restore the worker registry for each test."""

    original_workers = list_background_workers()
    yield
    set_background_workers(original_workers)


async def _dummy_worker(state) -> None:  # pragma: no cover - exercised via registry
    return None


def _worker_names() -> List[str]:
    return [worker.__name__ for worker in list_background_workers()]


def test_default_workers_are_registered_in_order(registry_snapshot) -> None:
    pytest.importorskip("alpaca_trade_api")
    import unified_trading_service_with_frontend  # noqa: F401

    reset_background_workers()
    import importlib

    importlib.reload(unified_trading_service_with_frontend)
    names = _worker_names()
    assert names[:3] == [
        "update_cache",
        "crypto_scanner",
        "crypto_scalping_trader",
    ]


def test_register_background_worker_is_idempotent(registry_snapshot) -> None:
    register_background_worker(_dummy_worker)
    names = _worker_names()
    assert names[-1] == "_dummy_worker"

    register_background_worker(_dummy_worker)
    names_after = _worker_names()
    assert names_after.count("_dummy_worker") == 1


def test_resolve_background_workers_filters_unknown_entries(registry_snapshot) -> None:
    register_background_worker(_dummy_worker)

    resolved = resolve_background_workers(["_dummy_worker", "missing_worker"])
    assert [_worker.__name__ for _worker in resolved] == ["_dummy_worker"]


def test_list_named_background_workers_exposes_names(registry_snapshot) -> None:
    register_background_worker(_dummy_worker)
    items = list_named_background_workers()

    assert any(name == "_dummy_worker" for name, _ in items)
