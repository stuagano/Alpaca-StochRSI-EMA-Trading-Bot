#!/usr/bin/env python3
"""Aggregate lightweight sentiment signals for the trading stack."""

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

from utils.logging_config import setup_logging

LOGGER = logging.getLogger("sentiment.worker")
STOP_REQUESTED = False


def _handle_signal(signum: int, _frame) -> None:
    LOGGER.info("Received signal %s – stopping sentiment worker", signum)
    global STOP_REQUESTED
    STOP_REQUESTED = True


def _connect_redis(url: str) -> Optional[redis.Redis]:
    try:
        client = redis.Redis.from_url(url, decode_responses=True)
        client.ping()
        LOGGER.info("Connected to Redis at %s", url)
        return client
    except Exception as exc:  # pragma: no cover - defensive safeguard
        LOGGER.warning("Redis unavailable (%s); sentiment results will persist to disk only", exc)
        return None


def _load_signal_file(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive safeguard
        LOGGER.warning("Failed to parse %s: %s", path, exc)
        return None


def _persist(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    setup_logging()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    interval = max(int(os.getenv("SENTIMENT_POLL_INTERVAL_SECONDS", "300")), 60)
    weight = float(os.getenv("SENTIMENT_SIGNAL_WEIGHT", "0.15"))
    local_root = Path(os.getenv("LOCAL_DATA_ROOT", "./.localstack"))
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    redis_client = _connect_redis(redis_url)
    sentiment_path = local_root / "sentiment" / "last_sentiment.json"
    ml_signal_path = local_root / "signals" / "last_signal.json"

    LOGGER.info("Starting sentiment worker (interval=%ss, weight=%s)", interval, weight)

    while not STOP_REQUESTED:
        start = time.monotonic()
        ml_signal = _load_signal_file(ml_signal_path) or {}
        base_score = ml_signal.get("report", {}).get("score", 0)
        weighted_score = base_score * weight

        payload = {
            "generated_at": time.time(),
            "weighted_score": weighted_score,
            "source_score": base_score,
        }

        if redis_client is not None:
            try:
                redis_client.set("sentiment:last_score", json.dumps(payload))
            except Exception as exc:  # pragma: no cover - defensive safeguard
                LOGGER.warning("Failed to publish sentiment score to Redis: %s", exc)

        try:
            _persist(sentiment_path, payload)
        except Exception as exc:  # pragma: no cover - defensive safeguard
            LOGGER.error("Failed to persist sentiment score: %s", exc)

        elapsed = time.monotonic() - start
        sleep_for = max(interval - elapsed, 0)
        time.sleep(sleep_for)

    LOGGER.info("Sentiment worker stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
