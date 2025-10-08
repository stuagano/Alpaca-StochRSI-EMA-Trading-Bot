#!/usr/bin/env python3
"""Validate required environment variables for local deployments."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse, urlunparse

try:
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover - ensures helpful error without dependency
    print("python-dotenv is required to run scripts/check_env.py", file=sys.stderr)
    sys.exit(1)

REQUIRED_KEYS = {
    "DATABASE_URL",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
    "DB_PORT",
    "REDIS_URL",
    "REDIS_PORT",
    "LOCAL_DATA_ROOT",
    "PROMETHEUS_CONFIG_PATH",
    "GRAFANA_PROVISIONING_PATH",
}


def _load_env(env_files: list[Path]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for env_file in env_files:
        if env_file.exists():
            # ``dotenv_values`` silently ignores malformed lines which keeps the
            # script resilient to comments and blank lines.
            values.update({k: v for k, v in dotenv_values(env_file).items() if v is not None})
    # Environment variables should take precedence over files.
    for key, value in os.environ.items():
        values[key] = value
    return values


def _derive_compose_database_url(values: Dict[str, str]) -> str | None:
    database_url = values.get("DATABASE_URL")
    host_override = values.get("COMPOSE_POSTGRES_HOST", "postgres")
    if not database_url:
        return None

    parsed = urlparse(database_url)
    # ``netloc`` might already include credentials, preserve them when present.
    hostname = host_override
    port = values.get("DB_PORT") or (str(parsed.port) if parsed.port else None)
    user_info = parsed.username
    if parsed.password:
        user_info = f"{parsed.username}:{parsed.password}"
    elif parsed.username:
        user_info = parsed.username

    if user_info:
        netloc = f"{user_info}@{hostname}"
    else:
        netloc = hostname

    if port:
        netloc = f"{netloc}:{port}"

    return urlunparse((parsed.scheme, netloc, parsed.path or "", parsed.params, parsed.query, parsed.fragment))


def _derive_compose_redis_url(values: Dict[str, str]) -> str | None:
    redis_url = values.get("REDIS_URL")
    if not redis_url:
        return None

    parsed = urlparse(redis_url)
    host_override = values.get("COMPOSE_REDIS_HOST", "redis")
    port = values.get("REDIS_PORT") or (str(parsed.port) if parsed.port else None)

    netloc = host_override
    if parsed.username:
        if parsed.password:
            netloc = f"{parsed.username}:{parsed.password}@{netloc}"
        else:
            netloc = f"{parsed.username}@{netloc}"
    elif parsed.password:
        netloc = f":{parsed.password}@{netloc}"

    if port:
        netloc = f"{netloc}:{port}"

    return urlunparse((parsed.scheme or "redis", netloc, parsed.path or "/0", parsed.params, parsed.query, parsed.fragment))


def _validate_required(values: Dict[str, str]) -> list[str]:
    missing = [key for key in sorted(REQUIRED_KEYS) if not values.get(key)]
    return missing


def _ensure_paths(values: Dict[str, str]) -> list[str]:
    warnings: list[str] = []
    root = Path(values.get("LOCAL_DATA_ROOT", "."))
    if not root.exists():
        warnings.append(f"LOCAL_DATA_ROOT directory will be created: {root}")
    prometheus_path = Path(values.get("PROMETHEUS_CONFIG_PATH", ""))
    if not prometheus_path.exists():
        warnings.append(f"Prometheus configuration not found at {prometheus_path}")
    grafana_path = Path(values.get("GRAFANA_PROVISIONING_PATH", ""))
    if not grafana_path.exists():
        warnings.append(f"Grafana provisioning path not found at {grafana_path}")
    return warnings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        action="append",
        dest="env_files",
        default=[Path(".env")],
        type=Path,
        help="Path(s) to .env files (defaults to project .env)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env_values = _load_env(args.env_files)
    missing = _validate_required(env_values)
    if missing:
        print("Missing required environment variables:", ", ".join(missing), file=sys.stderr)
        return 1

    warnings = _ensure_paths(env_values)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    compose_db_url = _derive_compose_database_url(env_values)
    compose_redis_url = _derive_compose_redis_url(env_values)

    if compose_db_url:
        print(f"COMPOSE_DATABASE_URL={compose_db_url}")
    if compose_redis_url:
        print(f"COMPOSE_REDIS_URL={compose_redis_url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
