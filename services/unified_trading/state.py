"""State containers and helpers for the unified trading service."""

from __future__ import annotations

from asyncio import Task, TaskGroup
from collections import deque
from collections.abc import Awaitable, Callable, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from config.service_settings import TradingServiceSettings

QUOTE_SUFFIXES: tuple[str, ...] = ("USDT", "USDC", "USD")


def to_scanner_symbol(symbol: str) -> str:
    """Convert display symbols (e.g. ``BTC/USD``) to scanner friendly format."""

    return symbol.replace("/", "").upper()


def to_display_symbol(symbol: str) -> str:
    """Convert scanner symbols back to Alpaca display format."""

    if "/" in symbol:
        return symbol

    upper_symbol = symbol.upper()
    for suffix in QUOTE_SUFFIXES:
        if upper_symbol.endswith(suffix):
            base = upper_symbol[: -len(suffix)]
            return f"{base}/{suffix}"

    if len(upper_symbol) > 3:
        return f"{upper_symbol[:-3]}/{upper_symbol[-3:]}"

    return upper_symbol


@dataclass
class SessionMetrics:
    """Track win rates and profitability metrics for the session."""

    session_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_profit: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    current_streak: int = 0
    best_streak: int = 0
    trades_per_hour: float = 0.0
    avg_profit_per_trade: float = 0.0
    win_rate: float = 0.0

    def update_on_trade(self, trade: Dict[str, Any]) -> None:
        """Update win/loss ratios and derived metrics for a completed trade."""

        self.total_trades += 1
        profit = trade.get("profit")
        if profit is not None:
            self.total_profit += profit
            if profit > 0:
                self.winning_trades += 1
                self.current_streak = max(0, self.current_streak) + 1
                self.best_streak = max(self.best_streak, self.current_streak)
            else:
                self.losing_trades += 1
                self.current_streak = min(0, self.current_streak) - 1

        hours_elapsed = max(
            0.1,
            (datetime.now(timezone.utc) - self.session_start).total_seconds() / 3600,
        )
        self.trades_per_hour = self.total_trades / hours_elapsed

        if self.total_trades > 0:
            self.avg_profit_per_trade = self.total_profit / self.total_trades
            completed_trades = self.winning_trades + self.losing_trades
            if completed_trades > 0:
                self.win_rate = self.winning_trades / completed_trades


@dataclass
class TradingState:
    """Aggregate caches and runtime state for the trading service."""

    settings: TradingServiceSettings
    alpaca_api: Optional[Any] = None
    account_cache: Dict[str, Any] = field(default_factory=dict)
    positions_cache: List[Any] = field(default_factory=list)
    orders_cache: List[Any] = field(default_factory=list)
    crypto_metrics: Dict[str, Any] = field(default_factory=dict)
    top_movers: List[Any] = field(default_factory=list)
    error_log: Deque[Any] = field(default_factory=lambda: deque(maxlen=100))
    last_update: Dict[str, datetime] = field(default_factory=dict)
    auto_trading_enabled: bool = False
    trade_history: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=500))
    position_entry_prices: Dict[str, float] = field(default_factory=dict)
    session_metrics: SessionMetrics = field(default_factory=SessionMetrics)
    current_positions: Dict[str, Any] = field(default_factory=dict)
    current_prices: Dict[str, float] = field(default_factory=dict)
    signals: List[Any] = field(default_factory=list)
    crypto_scanner: Any = None
    active_scalp_positions: Dict[str, Any] = field(default_factory=dict)
    crypto_symbols: List[str] = field(init=False)
    crypto_metadata: Dict[str, Dict[str, str]] = field(init=False)
    crypto_symbol_prefixes: List[str] = field(init=False)
    crypto_scanner_symbols: List[str] = field(default_factory=list)
    max_concurrent_positions: int = field(init=False)
    daily_loss_limit: float = field(init=False)
    current_daily_loss: float = 0.0
    background_tasks: List[Task[Any]] = field(default_factory=list)
    background_task_group: Optional[TaskGroup] = None

    def __post_init__(self) -> None:
        self.crypto_symbols = list(self.settings.crypto_symbols)
        self.crypto_metadata = dict(self.settings.crypto_metadata)
        self.crypto_symbol_prefixes = [symbol.replace("/", "") for symbol in self.crypto_symbols]
        self.max_concurrent_positions = self.settings.max_concurrent_positions
        self.daily_loss_limit = self.settings.daily_loss_limit


def refresh_scanner_symbols(state: TradingState) -> List[str]:
    """Synchronise cached scanner symbols with the active strategy."""

    if not state.crypto_scanner:
        return state.crypto_scanner_symbols

    enabled_symbols = state.crypto_scanner.get_enabled_symbols()
    if not enabled_symbols:
        state.crypto_scanner_symbols = []
        return state.crypto_scanner_symbols

    state.crypto_scanner_symbols = sorted(
        {to_display_symbol(symbol) for symbol in enabled_symbols}
    )
    return state.crypto_scanner_symbols


BackgroundWorker = Callable[[TradingState], Awaitable[Any]]


@asynccontextmanager
async def manage_background_tasks(
    state: TradingState,
    workers: Iterable[BackgroundWorker],
) -> None:
    """Run background workers inside a shared ``TaskGroup``.

    The helper keeps ``TradingState.background_tasks`` in sync so FastAPI
    extensions can introspect active jobs and ensures tasks are cancelled and
    awaited before the application shuts down.
    """

    async with TaskGroup() as task_group:
        state.background_task_group = task_group
        tasks = state.background_tasks
        tasks.clear()

        try:
            for worker in workers:
                coroutine = worker(state)
                tasks.append(
                    task_group.create_task(
                        coroutine,
                        name=getattr(worker, "__name__", "background_worker"),
                    )
                )

            yield
        finally:
            for task in tasks:
                task.cancel()

            tasks.clear()
            state.background_task_group = None


__all__ = [
    "QUOTE_SUFFIXES",
    "SessionMetrics",
    "TradingState",
    "manage_background_tasks",
    "refresh_scanner_symbols",
    "to_display_symbol",
    "to_scanner_symbol",
]
