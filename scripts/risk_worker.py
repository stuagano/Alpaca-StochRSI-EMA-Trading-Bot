#!/usr/bin/env python3
"""Background worker that periodically publishes portfolio risk reports."""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

import redis

from risk_management.risk_service import RiskManagementService
from utils.logging_config import setup_logging

LOGGER = logging.getLogger("risk.worker")
STOP_REQUESTED = False


def _handle_signal(signum: int, _frame) -> None:
    LOGGER.info("Received signal %s – stopping risk worker", signum)
    global STOP_REQUESTED
    STOP_REQUESTED = True


def _connect_redis(url: str) -> Optional[redis.Redis]:
    try:
        client = redis.Redis.from_url(url, decode_responses=True)
        client.ping()
        LOGGER.info("Connected to Redis at %s", url)
        return client
    except Exception as exc:  # pragma: no cover - defensive safeguard
        LOGGER.warning("Redis unavailable (%s); continuing with file persistence only", exc)
        return None


def _persist_to_disk(target_dir: Path, payload: dict) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    snapshot = target_dir / "last_report.json"
    snapshot.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    setup_logging()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    interval = max(int(os.getenv("RISK_WORKER_INTERVAL_SECONDS", "60")), 15)
    local_root = Path(os.getenv("LOCAL_DATA_ROOT", "./.localstack"))
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    redis_client = _connect_redis(redis_url)
    disk_target = local_root / "risk"

    service = RiskManagementService()

    LOGGER.info("Starting risk worker with %s second interval", interval)

    while not STOP_REQUESTED:
        start = time.monotonic()
        report = service.assess_portfolio_risk()
        payload = {
            "generated_at": time.time(),
            "report": report,
        }

        if redis_client is not None:
            try:
                redis_client.set("risk:last_report", json.dumps(payload))
            except Exception as exc:  # pragma: no cover - defensive safeguard
                LOGGER.warning("Failed to publish risk report to Redis: %s", exc)

        try:
            _persist_to_disk(disk_target, payload)
        except Exception as exc:  # pragma: no cover - defensive safeguard
            LOGGER.error("Failed to persist risk report locally: %s", exc)

        elapsed = time.monotonic() - start
        sleep_for = max(interval - elapsed, 0)
        time.sleep(sleep_for)

    LOGGER.info("Risk worker stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
