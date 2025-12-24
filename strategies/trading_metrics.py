"""
Trading Metrics Module
Handles trade logging, metrics tracking, and performance reporting
"""

import os
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TradeLog:
    """Comprehensive trade log entry with all required fields"""
    timestamp: str
    action: str  # 'BUY' or 'SELL'
    symbol: str
    quantity: float
    price: float
    status: str  # 'filled', 'partially_filled', 'failed', 'pending'
    error_notes: str = ""
    order_id: str = ""
    pnl: float = 0.0
    execution_time_ms: int = 0

    def to_console_string(self) -> str:
        """Format for clear console output"""
        status_emoji = {
            "filled": "✅",
            "partially_filled": "⚠️",
            "failed": "❌",
            "pending": "⏳"
        }.get(self.status, "❓")

        action_color = "\033[92m" if self.action == "BUY" else "\033[91m"
        reset_color = "\033[0m"

        return (
            f"{status_emoji} {self.timestamp} | "
            f"{action_color}{self.action:4s}{reset_color} | "
            f"{self.symbol:10s} | "
            f"Qty: {self.quantity:8.4f} | "
            f"Price: ${self.price:10.2f} | "
            f"Status: {self.status:15s} | "
            f"P&L: ${self.pnl:+8.2f} | "
            f"Exec: {self.execution_time_ms}ms | "
            f"{self.error_notes}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class TradingMetrics:
    """Tracks trading performance and metrics"""

    def __init__(
        self,
        initial_capital: float = 10000,
        log_file: str = 'logs/crypto_trade_timeline.log',
    ):
        self.initial_capital = initial_capital
        self.log_file = log_file

        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Daily metrics
        self.daily_trades = 0
        self.daily_profit = 0.0

        # Overall metrics
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.total_profit = 0.0

        # Trade log
        self.trade_log: List[TradeLog] = []

        # Error tracking
        self.error_count = 0
        self.rate_limit_errors = 0
        self.last_rate_limit_time: Optional[datetime] = None

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return 0.0
        return (self.wins / self.total_trades) * 100

    @property
    def profit_factor(self) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = sum(t.pnl for t in self.trade_log if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trade_log if t.pnl < 0))
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    def log_trade(self, trade: TradeLog) -> None:
        """Log a trade and update metrics"""
        self.trade_log.append(trade)

        if trade.status == 'filled':
            self.total_trades += 1
            self.daily_trades += 1
            self.total_profit += trade.pnl
            self.daily_profit += trade.pnl

            if trade.pnl > 0:
                self.wins += 1
            elif trade.pnl < 0:
                self.losses += 1

        # Log to console
        logger.info(trade.to_console_string())

        # Append to file
        self._write_to_file(trade)

    def _write_to_file(self, trade: TradeLog) -> None:
        """Write trade to log file"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(trade.to_console_string() + '\n')
        except Exception as e:
            logger.warning(f"Failed to write trade to file: {e}")

    def log_error(self, error_type: str = 'general') -> None:
        """Log an error"""
        self.error_count += 1
        if error_type == 'rate_limit':
            self.rate_limit_errors += 1
            self.last_rate_limit_time = datetime.now()

    def reset_daily_metrics(self) -> None:
        """Reset daily metrics (call at start of trading day)"""
        logger.info(f"📊 Resetting daily metrics. Previous: {self.daily_trades} trades, ${self.daily_profit:.2f} P&L")
        self.daily_trades = 0
        self.daily_profit = 0.0

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        return {
            'daily': {
                'trades': self.daily_trades,
                'profit': self.daily_profit,
            },
            'overall': {
                'total_trades': self.total_trades,
                'wins': self.wins,
                'losses': self.losses,
                'win_rate': self.win_rate,
                'total_profit': self.total_profit,
                'profit_factor': self.profit_factor,
            },
            'errors': {
                'total': self.error_count,
                'rate_limit': self.rate_limit_errors,
                'last_rate_limit': self.last_rate_limit_time.isoformat() if self.last_rate_limit_time else None,
            },
            'capital': {
                'initial': self.initial_capital,
                'current': self.initial_capital + self.total_profit,
                'return_pct': (self.total_profit / self.initial_capital) * 100 if self.initial_capital > 0 else 0,
            }
        }

    def print_timeline(self, last_n: int = 20) -> None:
        """Print recent trade timeline to console"""
        print("\n" + "=" * 120)
        print("📈 TRADE TIMELINE (Most Recent)")
        print("=" * 120)

        recent_trades = self.trade_log[-last_n:] if len(self.trade_log) > last_n else self.trade_log

        if not recent_trades:
            print("No trades recorded yet")
        else:
            for trade in recent_trades:
                print(trade.to_console_string())

        print("=" * 120)
        print(f"📊 Summary: {self.total_trades} trades | Win Rate: {self.win_rate:.1f}% | Total P&L: ${self.total_profit:+.2f}")
        print("=" * 120 + "\n")

    def get_recent_trades(self, last_n: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades as list of dicts"""
        recent = self.trade_log[-last_n:] if len(self.trade_log) > last_n else self.trade_log
        return [t.to_dict() for t in recent]


class RiskManager:
    """Manages trading risk and position limits"""

    def __init__(
        self,
        initial_capital: float = 10000,
        max_daily_loss_pct: float = 0.03,
        max_drawdown_pct: float = 0.08,
        max_position_pct: float = 0.03,
        max_position_value: float = 100.0,
    ):
        self.initial_capital = initial_capital
        self.max_daily_loss = initial_capital * max_daily_loss_pct
        self.max_drawdown = initial_capital * max_drawdown_pct
        self.max_position_pct = max_position_pct
        self.max_position_value = max_position_value

        # Tracking
        self.daily_pnl = 0.0
        self.peak_capital = initial_capital
        self.current_capital = initial_capital

    def update_pnl(self, pnl: float) -> None:
        """Update P&L tracking"""
        self.daily_pnl += pnl
        self.current_capital += pnl
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital

    def reset_daily(self) -> None:
        """Reset daily tracking"""
        self.daily_pnl = 0.0

    @property
    def current_drawdown(self) -> float:
        """Calculate current drawdown from peak"""
        return self.peak_capital - self.current_capital

    @property
    def drawdown_pct(self) -> float:
        """Calculate drawdown percentage"""
        if self.peak_capital == 0:
            return 0.0
        return (self.current_drawdown / self.peak_capital) * 100

    def can_trade(self) -> tuple[bool, str]:
        """Check if trading is allowed based on risk limits"""
        if self.daily_pnl <= -self.max_daily_loss:
            return False, f"Daily loss limit reached (${self.daily_pnl:.2f})"

        if self.current_drawdown >= self.max_drawdown:
            return False, f"Max drawdown reached ({self.drawdown_pct:.1f}%)"

        return True, "OK"

    def calculate_position_size(
        self,
        price: float,
        available_cash: float,
    ) -> float:
        """Calculate maximum position size based on risk rules"""
        # Calculate based on percentage of capital
        pct_based = self.current_capital * self.max_position_pct

        # Apply max absolute value
        max_value = min(pct_based, self.max_position_value)

        # Apply available cash constraint
        max_value = min(max_value, available_cash * 0.995)  # 0.5% buffer

        # Calculate quantity
        if price <= 0:
            return 0.0

        return max_value / price

    def get_status(self) -> Dict[str, Any]:
        """Get risk status"""
        can_trade, reason = self.can_trade()
        return {
            'can_trade': can_trade,
            'reason': reason,
            'daily_pnl': self.daily_pnl,
            'max_daily_loss': self.max_daily_loss,
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'drawdown_pct': self.drawdown_pct,
            'current_capital': self.current_capital,
        }
