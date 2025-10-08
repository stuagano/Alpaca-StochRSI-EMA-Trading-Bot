#!/usr/bin/env python3
"""FastAPI application exposing risk analytics for local deployments."""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import asdict
from typing import Deque, Optional
from collections import deque

from fastapi import Depends, FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field, validator

from risk_management.risk_service import RiskManagementService
from utils.logging_config import setup_logging

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except ImportError:  # pragma: no cover - optional dependency
    Counter = Histogram = None  # type: ignore[assignment]
    CONTENT_TYPE_LATEST = "text/plain"

    def generate_latest(*_args, **_kwargs) -> bytes:  # type: ignore[override]
        return b""

LOGGER = logging.getLogger("risk.api")

app = FastAPI(
    title="Risk Management API",
    version="1.0.0",
    description="Provides portfolio risk analytics and position sizing helpers for the crypto scalper.",
)


class RateLimiter:
    """Simple thread-safe rate limiter."""

    def __init__(self, limit_per_minute: int):
        self.limit = max(limit_per_minute, 1)
        self._history: Deque[float] = deque()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            window_start = now - 60
            while self._history and self._history[0] < window_start:
                self._history.popleft()
            if len(self._history) >= self.limit:
                return False
            self._history.append(now)
            return True


class PositionSizeRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    entry_price: float = Field(..., gt=0)
    stop_loss_price: Optional[float] = Field(default=None, gt=0)
    method: str = Field(default="volatility_adjusted", min_length=1)

    @validator("method")
    def normalise_method(cls, value: str) -> str:
        return value.lower()


class PositionSizeResponse(BaseModel):
    recommendation: dict


class PortfolioRiskResponse(BaseModel):
    report: dict


def _setup_metrics() -> tuple[Optional[Counter], Optional[Histogram]]:
    if Counter is None or Histogram is None:
        return None, None

    request_counter = Counter(
        "risk_api_requests_total",
        "Number of risk API requests",
        ["endpoint"],
    )
    latency_histogram = Histogram(
        "risk_api_latency_seconds",
        "Latency of risk API requests",
        ["endpoint"],
    )
    return request_counter, latency_histogram


REQUEST_COUNTER, LATENCY_HISTOGRAM = _setup_metrics()
rate_limit = RateLimiter(int(os.getenv("RISK_API_RATE_LIMIT_PER_MINUTE", "120")))
risk_service = RiskManagementService()


def _rate_limiter() -> None:
    if not rate_limit.allow():
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")


def _observe(endpoint: str, duration: float) -> None:
    if REQUEST_COUNTER is not None:
        REQUEST_COUNTER.labels(endpoint=endpoint).inc()
    if LATENCY_HISTOGRAM is not None:
        LATENCY_HISTOGRAM.labels(endpoint=endpoint).observe(duration)


@app.on_event("startup")
def _startup() -> None:
    setup_logging()
    LOGGER.info("Risk API starting with rate limit %s/min", rate_limit.limit)


@app.get("/healthz", dependencies=[Depends(_rate_limiter)])
def healthcheck() -> dict[str, str]:
    start = time.monotonic()
    payload = {"status": "ok"}
    _observe("healthz", time.monotonic() - start)
    return payload


@app.get("/metrics")
def metrics() -> Response:
    if REQUEST_COUNTER is None or LATENCY_HISTOGRAM is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="prometheus_client is not installed")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/risk/portfolio", response_model=PortfolioRiskResponse, dependencies=[Depends(_rate_limiter)])
def portfolio_risk() -> PortfolioRiskResponse:
    start = time.monotonic()
    report = risk_service.assess_portfolio_risk()
    _observe("portfolio", time.monotonic() - start)
    return PortfolioRiskResponse(report=report)


@app.post("/v1/risk/position-size", response_model=PositionSizeResponse, dependencies=[Depends(_rate_limiter)])
def position_size(request: PositionSizeRequest) -> PositionSizeResponse:
    start = time.monotonic()
    recommendation = risk_service.calculate_position_size(
        symbol=request.symbol,
        entry_price=request.entry_price,
        stop_loss_price=request.stop_loss_price,
        method=request.method,
    )
    _observe("position_size", time.monotonic() - start)
    return PositionSizeResponse(recommendation=asdict(recommendation))


if __name__ == "__main__":  # pragma: no cover - manual execution
    import uvicorn

    bind = os.getenv("RISK_API_BIND", "0.0.0.0:8090")
    host, _, raw_port = bind.partition(":")
    uvicorn.run("services.risk_api_app:app", host=host or "0.0.0.0", port=int(raw_port or "8090"))
