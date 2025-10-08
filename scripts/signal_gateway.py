#!/usr/bin/env python3
"""Poll an ML endpoint for trading signals and cache the latest response."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

import aiohttp
import redis

from utils.logging_config import setup_logging

LOGGER = logging.getLogger("ml.signal-gateway")
STOP_EVENT = asyncio.Event()


def _handle_signal(signum: int, _frame) -> None:
    LOGGER.info("Received signal %s – stopping signal gateway", signum)
    STOP_EVENT.set()


def _connect_redis(url: str) -> Optional[redis.Redis]:
    try:
        client = redis.Redis.from_url(url, decode_responses=True)
        client.ping()
        LOGGER.info("Connected to Redis at %s", url)
        return client
    except Exception as exc:  # pragma: no cover - defensive safeguard
        LOGGER.warning("Redis unavailable (%s); continuing without Redis cache", exc)
        return None


def _persist_to_disk(target_dir: Path, payload: dict) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    snapshot = target_dir / "last_signal.json"
    snapshot.write_text(json.dumps(payload, indent=2), encoding="utf-8")


async def _poll_endpoint(session: aiohttp.ClientSession, endpoint: str) -> dict:
    async with session.get(endpoint) as response:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return await response.json()
        text = await response.text()
        return {"raw": text}


async def main_async() -> int:
    setup_logging()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    endpoint = os.getenv("ML_MODEL_ENDPOINT")
    timeout_seconds = float(os.getenv("ML_MODEL_TIMEOUT_SECONDS", "2"))
    poll_interval = max(int(os.getenv("SENTIMENT_POLL_INTERVAL_SECONDS", "300")), 30)
    local_root = Path(os.getenv("LOCAL_DATA_ROOT", "./.localstack"))
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    redis_client = _connect_redis(redis_url)
    disk_target = local_root / "signals"

    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    LOGGER.info("Starting signal gateway (endpoint=%s, interval=%ss)", endpoint or "<disabled>", poll_interval)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        while not STOP_EVENT.is_set():
            if not endpoint:
                LOGGER.info("ML_MODEL_ENDPOINT not configured; waiting before retry")
                try:
                    await asyncio.wait_for(STOP_EVENT.wait(), timeout=poll_interval)
                except asyncio.TimeoutError:
                    continue
                break

            try:
                payload = await _poll_endpoint(session, endpoint)
                payload["fetched_at"] = asyncio.get_running_loop().time()
                if redis_client is not None:
                    try:
                        redis_client.set("ml:last_signal", json.dumps(payload))
                    except Exception as exc:  # pragma: no cover - defensive safeguard
                        LOGGER.warning("Failed to publish ML signal to Redis: %s", exc)
                _persist_to_disk(disk_target, payload)
                LOGGER.debug("Updated ML signal cache from %s", endpoint)
            except asyncio.CancelledError:  # pragma: no cover - cancellation path
                raise
            except Exception as exc:
                LOGGER.warning("Unable to refresh ML signals: %s", exc)

            try:
                await asyncio.wait_for(STOP_EVENT.wait(), timeout=poll_interval)
            except asyncio.TimeoutError:
                continue

    LOGGER.info("Signal gateway stopped")
    return 0


def main() -> int:
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
