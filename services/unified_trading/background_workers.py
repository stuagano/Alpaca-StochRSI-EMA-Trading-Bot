from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Iterable, Tuple

from .state import BackgroundWorker


logger = logging.getLogger(__name__)


class BackgroundWorkerRegistry:
    """Registry for trading background workers.

    The registry centralises worker enrollment so services can reuse the same
    TaskGroup orchestration without modifying FastAPI entrypoints directly.
    """

    def __init__(self) -> None:
        self._workers: "OrderedDict[str, BackgroundWorker]" = OrderedDict()

    def register(
        self,
        worker: BackgroundWorker,
        *,
        name: str | None = None,
    ) -> BackgroundWorker:
        """Register a worker callable.

        If a worker with the same name exists it will be replaced to avoid
        duplicate execution while keeping registration idempotent.
        """

        worker_name = name or getattr(worker, "__name__", str(id(worker)))
        self._workers[worker_name] = worker
        return worker

    def unregister(self, name: str) -> None:
        """Remove a worker from the registry if present."""

        self._workers.pop(name, None)

    def clear(self) -> None:
        """Remove all workers from the registry."""

        self._workers.clear()

    def list(self) -> Tuple[BackgroundWorker, ...]:
        """Return the registered workers as an ordered tuple."""

        return tuple(self._workers.values())

    def items(self) -> Tuple[Tuple[str, BackgroundWorker], ...]:
        """Return ``(name, worker)`` tuples preserving registration order."""

        return tuple(self._workers.items())

    def extend(self, workers: Iterable[BackgroundWorker]) -> None:
        """Bulk register workers preserving order."""

        for worker in workers:
            self.register(worker)


_registry = BackgroundWorkerRegistry()


def register_background_worker(
    worker: BackgroundWorker,
    *,
    name: str | None = None,
) -> BackgroundWorker:
    """Module-level helper to register a background worker."""

    return _registry.register(worker, name=name)


def list_background_workers() -> Tuple[BackgroundWorker, ...]:
    """Return the currently registered workers."""

    return _registry.list()


def list_named_background_workers() -> Tuple[Tuple[str, BackgroundWorker], ...]:
    """Return the registered workers alongside their names."""

    return _registry.items()


def reset_background_workers() -> None:
    """Clear registered workers. Useful for tests."""

    _registry.clear()


def set_background_workers(workers: Iterable[BackgroundWorker]) -> None:
    """Replace the registry content with the provided workers."""

    _registry.clear()
    _registry.extend(workers)


def resolve_background_workers(
    worker_names: Iterable[str] | None,
) -> Tuple[BackgroundWorker, ...]:
    """Return workers matching ``worker_names`` or all registered when ``None``.

    Unknown worker names are ignored with a warning so misconfigurations do not
    prevent the service from starting locally.
    """

    if worker_names is None:
        return list_background_workers()

    normalized = []
    for name in worker_names:
        stripped = name.strip()
        if stripped:
            normalized.append(stripped.lower())

    if not normalized:
        return tuple()

    registered = {name.lower(): worker for name, worker in list_named_background_workers()}

    missing = sorted({name for name in normalized if name not in registered})
    if missing:
        logger.warning(
            "Unknown background workers requested via configuration: %s",
            ", ".join(missing),
        )

    resolved = [registered[name] for name in normalized if name in registered]
    return tuple(resolved)


__all__ = [
    "BackgroundWorkerRegistry",
    "list_named_background_workers",
    "list_background_workers",
    "register_background_worker",
    "reset_background_workers",
    "set_background_workers",
    "resolve_background_workers",
]
