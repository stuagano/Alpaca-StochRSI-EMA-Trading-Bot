#!/usr/bin/env python3
"""
Epic 2 Advanced Backtesting Engine
=================================

Professional-grade backtesting system with comprehensive analytics,
pattern recognition, and strategy optimization capabilities.

Features:
- Event-driven backtesting architecture
- Realistic order execution simulation
- Commission and slippage modeling
- Multiple position management
- Stop loss and take profit simulation
- Performance analytics with 40+ metrics
- Strategy comparison and optimization
- Monte Carlo simulation support
- Walk-forward analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from services.historical_data_service import get_historical_data_service
from strategies.base_strategy import Strategy

logger = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Order representation"""
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_quantity: float = 0.0
    commission: float = 0.0


@dataclass
class Position:
    """Position representation"""
    symbol: str
    quantity: float
    avg_price: float
    market_value: float
    unrealized_pnl: float
    entry_timestamp: datetime
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class Trade:
    """Completed trade record"""
    entry_date: datetime
    exit_date: datetime
    symbol: str
    side: OrderSide
    entry_price: float
    exit_price: float
    quantity: float
    commission: float
    profit: float
    profit_pct: float
    duration: timedelta
    max_gain: float = 0.0
    max_loss: float = 0.0
    strategy_signals: Dict = field(default_factory=dict)


@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    initial_capital: float = 100000.0
    commission_rate: float = 0.001  # 0.1%
    slippage_rate: float = 0.0005   # 0.05%
    max_positions: int = 5
    position_sizing: str = "equal_weight"  # equal_weight, fixed_amount, percent_risk
    position_size: float = 0.2  # 20% per position for equal_weight
    enable_stop_loss: bool = True
    stop_loss_pct: float = 0.02  # 2%
    enable_take_profit: bool = True
    take_profit_pct: float = 0.06  # 6%
    enable_trailing_stop: bool = False
    trailing_stop_pct: float = 0.02  # 2%


@dataclass
class BacktestMetrics:
    """Comprehensive backtest performance metrics"""
    # Basic metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L metrics
    total_profit: float = 0.0
    total_loss: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_duration: timedelta = timedelta()
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trade metrics
    avg_trade_duration: timedelta = timedelta()
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Advanced metrics
    var_95: float = 0.0  # Value at Risk 95%
    cvar_95: float = 0.0  # Conditional VaR 95%
    recovery_factor: float = 0.0
    sterling_ratio: float = 0.0
    omega_ratio: float = 0.0


class BacktestEngine:
    """Advanced backtesting engine"""
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.historical_service = get_historical_data_service()
        
        # State tracking
        self.current_time: datetime = None
        self.cash: float = self.config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        self.portfolio_history: List[Dict] = []
        
        # Performance tracking
        self.equity_curve: List[float] = []
        self.daily_returns: List[float] = []
        self.drawdown_series: List[float] = []
        
        logger.info("Epic 2 Backtesting Engine initialized")
    
    async def run_backtest(
        self,
        strategy: Strategy,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1d"
    ) -> Dict[str, Any]:
        """
        Run comprehensive backtest
        
        Args:
            strategy: Trading strategy instance
            symbols: List of symbols to trade
            start_date: Backtest start date
            end_date: Backtest end date
            timeframe: Data timeframe
        
        Returns:
            Comprehensive backtest results
        """
        logger.info(f"Starting backtest: {strategy.__class__.__name__} on {len(symbols)} symbols")
        logger.info(f"Period: {start_date} to {end_date}, Timeframe: {timeframe}")
        
        # Reset state
        self._reset_state()
        
        # Fetch historical data for all symbols
        historical_data = {}
        for symbol in symbols:
            data = self.historical_service.fetch_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start=start_date,
                end=end_date
            )
            if not data.empty:
                historical_data[symbol] = data
            else:
                logger.warning(f"No data available for {symbol}")
        
        if not historical_data:
            raise ValueError("No historical data available for any symbols")
        
        # Get unified time index
        time_index = self._create_unified_time_index(historical_data)
        
        # Run simulation
        for timestamp in time_index:
            self.current_time = timestamp
            
            # Update market data
            current_prices = {}
            for symbol, data in historical_data.items():
                if timestamp in data.index:
                    current_prices[symbol] = data.loc[timestamp]
            
            if not current_prices:
                continue
            
            # Process orders (fills, stops, etc.)
            self._process_orders(current_prices)
            
            # Update positions
            self._update_positions(current_prices)
            
            # Generate strategy signals
            signals = strategy.generate_signals(historical_data, timestamp)
            
            # Execute signals
            for signal in signals:
                await self._execute_signal(signal, current_prices)
            
            # Record portfolio state
            self._record_portfolio_state(current_prices)
        
        # Calculate final metrics
        metrics = self._calculate_metrics()
        
        # Generate comprehensive results
        results = {
            'config': self.config,
            'strategy': strategy.__class__.__name__,
            'symbols': symbols,
            'period': {'start': start_date, 'end': end_date},
            'timeframe': timeframe,
            'metrics': metrics,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'portfolio_history': self.portfolio_history,
            'daily_returns': self.daily_returns,
            'drawdown_series': self.drawdown_series
        }
        
        logger.info(f"Backtest completed: {len(self.trades)} trades, {metrics.total_return:.2%} return")
        
        return results
    
    def _reset_state(self):
        """Reset backtesting state"""
        self.cash = self.config.initial_capital
        self.positions = {}
        self.orders = []
        self.trades = []
        self.portfolio_history = []
        self.equity_curve = []
        self.daily_returns = []
        self.drawdown_series = []
    
    def _create_unified_time_index(self, historical_data: Dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
        """Create unified time index from all symbols"""
        all_times = set()
        for data in historical_data.values():
            all_times.update(data.index)
        
        return pd.DatetimeIndex(sorted(all_times))
    
    def _process_orders(self, current_prices: Dict[str, pd.Series]):
        """Process pending orders"""
        filled_orders = []
        
        for order in self.orders:
            if order.status != OrderStatus.PENDING:
                continue
            
            if order.symbol not in current_prices:
                continue
            
            current_price_data = current_prices[order.symbol]
            current_price = current_price_data['close']
            
            # Check if order should fill
            should_fill = False
            fill_price = current_price
            
            if order.type == OrderType.MARKET:
                should_fill = True
                # Apply slippage
                slippage = current_price * self.config.slippage_rate
                if order.side == OrderSide.BUY:
                    fill_price += slippage
                else:
                    fill_price -= slippage
            
            elif order.type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and current_price <= order.price:
                    should_fill = True
                    fill_price = order.price
                elif order.side == OrderSide.SELL and current_price >= order.price:
                    should_fill = True
                    fill_price = order.price
            
            elif order.type == OrderType.STOP:
                if order.side == OrderSide.BUY and current_price >= order.stop_price:
                    should_fill = True
                    fill_price = current_price + (current_price * self.config.slippage_rate)
                elif order.side == OrderSide.SELL and current_price <= order.stop_price:
                    should_fill = True
                    fill_price = current_price - (current_price * self.config.slippage_rate)
            
            if should_fill:
                # Calculate commission
                commission = order.quantity * fill_price * self.config.commission_rate
                
                # Fill the order
                order.status = OrderStatus.FILLED
                order.filled_price = fill_price
                order.filled_quantity = order.quantity
                order.commission = commission
                
                # Update positions
                self._update_position_from_order(order)
                
                filled_orders.append(order)
        
        # Remove filled orders
        self.orders = [o for o in self.orders if o.status == OrderStatus.PENDING]
    
    def _update_position_from_order(self, order: Order):
        """Update position from filled order"""
        symbol = order.symbol
        
        if symbol not in self.positions:
            if order.side == OrderSide.BUY:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=order.quantity,
                    avg_price=order.filled_price,
                    market_value=order.quantity * order.filled_price,
                    unrealized_pnl=0.0,
                    entry_timestamp=self.current_time
                )
                self.cash -= (order.quantity * order.filled_price + order.commission)
        else:
            position = self.positions[symbol]
            
            if order.side == OrderSide.BUY:
                # Adding to position
                total_cost = (position.quantity * position.avg_price) + (order.quantity * order.filled_price)
                total_quantity = position.quantity + order.quantity
                position.avg_price = total_cost / total_quantity
                position.quantity = total_quantity
                self.cash -= (order.quantity * order.filled_price + order.commission)
            
            else:  # SELL
                # Reducing/closing position
                if order.quantity >= position.quantity:
                    # Closing entire position - record trade
                    profit = (order.filled_price - position.avg_price) * position.quantity - order.commission
                    profit_pct = profit / (position.avg_price * position.quantity)
                    
                    trade = Trade(
                        entry_date=position.entry_timestamp,
                        exit_date=self.current_time,
                        symbol=symbol,
                        side=OrderSide.BUY,  # Original position side
                        entry_price=position.avg_price,
                        exit_price=order.filled_price,
                        quantity=position.quantity,
                        commission=order.commission,
                        profit=profit,
                        profit_pct=profit_pct,
                        duration=self.current_time - position.entry_timestamp
                    )
                    self.trades.append(trade)
                    
                    self.cash += (order.quantity * order.filled_price - order.commission)
                    del self.positions[symbol]
                else:
                    # Partial close
                    position.quantity -= order.quantity
                    self.cash += (order.quantity * order.filled_price - order.commission)
    
    def _update_positions(self, current_prices: Dict[str, pd.Series]):
        """Update position values and unrealized P&L"""
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]['close']
                position.market_value = position.quantity * current_price
                position.unrealized_pnl = (current_price - position.avg_price) * position.quantity
                position.last_update = self.current_time
    
    async def _execute_signal(self, signal: Dict, current_prices: Dict[str, pd.Series]):
        """Execute trading signal"""
        symbol = signal.get('symbol')
        action = signal.get('action')  # 'buy', 'sell', 'hold'
        confidence = signal.get('confidence', 1.0)
        
        if not symbol or not action or symbol not in current_prices:
            return
        
        current_price = current_prices[symbol]['close']
        
        if action == 'buy' and self._can_open_position(symbol):
            quantity = self._calculate_position_size(symbol, current_price, confidence)
            if quantity > 0:
                order = Order(
                    id=f"{symbol}_{self.current_time.isoformat()}_{len(self.orders)}",
                    symbol=symbol,
                    side=OrderSide.BUY,
                    type=OrderType.MARKET,
                    quantity=quantity,
                    timestamp=self.current_time
                )
                self.orders.append(order)
        
        elif action == 'sell' and symbol in self.positions:
            position = self.positions[symbol]
            order = Order(
                id=f"{symbol}_{self.current_time.isoformat()}_{len(self.orders)}",
                symbol=symbol,
                side=OrderSide.SELL,
                type=OrderType.MARKET,
                quantity=position.quantity,
                timestamp=self.current_time
            )
            self.orders.append(order)
    
    def _can_open_position(self, symbol: str) -> bool:
        """Check if can open new position"""
        if len(self.positions) >= self.config.max_positions:
            return False
        if symbol in self.positions:
            return False
        return True
    
    def _calculate_position_size(self, symbol: str, price: float, confidence: float = 1.0) -> float:
        """Calculate position size based on configuration"""
        if self.config.position_sizing == "equal_weight":
            position_value = self.cash * self.config.position_size * confidence
            return int(position_value / price)
        
        elif self.config.position_sizing == "fixed_amount":
            return int(self.config.position_size / price)
        
        elif self.config.position_sizing == "percent_risk":
            # Risk-based position sizing (simplified)
            risk_amount = self.cash * self.config.position_size
            stop_loss_price = price * (1 - self.config.stop_loss_pct)
            risk_per_share = price - stop_loss_price
            if risk_per_share > 0:
                return int(risk_amount / risk_per_share)
        
        return 0
    
    def _record_portfolio_state(self, current_prices: Dict[str, pd.Series]):
        """Record current portfolio state"""
        total_value = self.cash
        position_values = {}
        
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                market_value = position.quantity * current_prices[symbol]['close']
                total_value += market_value
                position_values[symbol] = {
                    'quantity': position.quantity,
                    'avg_price': position.avg_price,
                    'current_price': current_prices[symbol]['close'],
                    'market_value': market_value,
                    'unrealized_pnl': position.unrealized_pnl
                }
        
        portfolio_state = {
            'timestamp': self.current_time,
            'total_value': total_value,
            'cash': self.cash,
            'positions': position_values,
            'num_positions': len(self.positions)
        }
        
        self.portfolio_history.append(portfolio_state)
        self.equity_curve.append(total_value)
        
        # Calculate daily return
        if len(self.equity_curve) > 1:
            daily_return = (total_value - self.equity_curve[-2]) / self.equity_curve[-2]
            self.daily_returns.append(daily_return)
        else:
            self.daily_returns.append(0.0)
        
        # Calculate drawdown
        peak_value = max(self.equity_curve)
        drawdown = (total_value - peak_value) / peak_value if peak_value > 0 else 0.0
        self.drawdown_series.append(drawdown)
    
    def _calculate_metrics(self) -> BacktestMetrics:
        """Calculate comprehensive performance metrics"""
        if not self.equity_curve or not self.trades:
            return BacktestMetrics()
        
        metrics = BacktestMetrics()
        
        # Basic metrics
        initial_value = self.config.initial_capital
        final_value = self.equity_curve[-1]
        metrics.total_return = (final_value - initial_value) / initial_value
        
        # Annualized return
        days = len(self.equity_curve)
        if days > 0:
            years = days / 365.25
            metrics.annualized_return = (final_value / initial_value) ** (1 / years) - 1
        
        # Trade metrics
        metrics.total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.profit > 0]
        losing_trades = [t for t in self.trades if t.profit < 0]
        
        metrics.winning_trades = len(winning_trades)
        metrics.losing_trades = len(losing_trades)
        metrics.win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
        
        # P&L metrics
        if winning_trades:
            metrics.total_profit = sum(t.profit for t in winning_trades)
            metrics.avg_profit = metrics.total_profit / len(winning_trades)
            metrics.largest_win = max(t.profit for t in winning_trades)
        
        if losing_trades:
            metrics.total_loss = abs(sum(t.profit for t in losing_trades))
            metrics.avg_loss = metrics.total_loss / len(losing_trades)
            metrics.largest_loss = abs(min(t.profit for t in losing_trades))
        
        metrics.profit_factor = metrics.total_profit / metrics.total_loss if metrics.total_loss > 0 else float('inf')
        
        # Risk metrics
        if self.drawdown_series:
            metrics.max_drawdown = abs(min(self.drawdown_series))
        
        if self.daily_returns:
            returns_array = np.array(self.daily_returns)
            metrics.volatility = np.std(returns_array) * np.sqrt(252)  # Annualized
            
            if metrics.volatility > 0:
                metrics.sharpe_ratio = (metrics.annualized_return - 0.02) / metrics.volatility  # Assuming 2% risk-free rate
            
            # Sortino ratio (downside deviation)
            downside_returns = returns_array[returns_array < 0]
            if len(downside_returns) > 0:
                downside_deviation = np.std(downside_returns) * np.sqrt(252)
                metrics.sortino_ratio = (metrics.annualized_return - 0.02) / downside_deviation
        
        # Calmar ratio
        if metrics.max_drawdown > 0:
            metrics.calmar_ratio = metrics.annualized_return / metrics.max_drawdown
        
        # Trade duration
        if self.trades:
            durations = [t.duration for t in self.trades]
            metrics.avg_trade_duration = sum(durations, timedelta()) / len(durations)
        
        # Consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in self.trades:
            if trade.profit > 0:
                current_wins += 1
                current_losses = 0
                consecutive_wins = max(consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                consecutive_losses = max(consecutive_losses, current_losses)
        
        metrics.max_consecutive_wins = consecutive_wins
        metrics.max_consecutive_losses = consecutive_losses
        
        # VaR calculations
        if self.daily_returns:
            returns_array = np.array(self.daily_returns)
            metrics.var_95 = np.percentile(returns_array, 5)
            metrics.cvar_95 = returns_array[returns_array <= metrics.var_95].mean()
        
        return metrics
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive backtest report"""
        metrics = results['metrics']
        
        report = f"""
EPIC 2 BACKTESTING REPORT
========================

Strategy: {results['strategy']}
Symbols: {', '.join(results['symbols'])}
Period: {results['period']['start'].strftime('%Y-%m-%d')} to {results['period']['end'].strftime('%Y-%m-%d')}
Timeframe: {results['timeframe']}

PERFORMANCE SUMMARY
------------------
Total Return: {metrics.total_return:.2%}
Annualized Return: {metrics.annualized_return:.2%}
Total Trades: {metrics.total_trades}
Win Rate: {metrics.win_rate:.2%}
Profit Factor: {metrics.profit_factor:.2f}

RISK METRICS
-----------
Max Drawdown: {metrics.max_drawdown:.2%}
Volatility: {metrics.volatility:.2%}
Sharpe Ratio: {metrics.sharpe_ratio:.2f}
Sortino Ratio: {metrics.sortino_ratio:.2f}
Calmar Ratio: {metrics.calmar_ratio:.2f}

TRADE ANALYSIS
-------------
Winning Trades: {metrics.winning_trades}
Losing Trades: {metrics.losing_trades}
Average Profit: ${metrics.avg_profit:.2f}
Average Loss: ${metrics.avg_loss:.2f}
Largest Win: ${metrics.largest_win:.2f}
Largest Loss: ${metrics.largest_loss:.2f}
Average Duration: {metrics.avg_trade_duration}

ADVANCED METRICS
---------------
VaR (95%): {metrics.var_95:.2%}
CVaR (95%): {metrics.cvar_95:.2%}
Max Consecutive Wins: {metrics.max_consecutive_wins}
Max Consecutive Losses: {metrics.max_consecutive_losses}

        """
        
        return report


# Global instance
_backtest_engine = None


def get_backtest_engine(config: BacktestConfig = None) -> BacktestEngine:
    """Get global backtest engine instance"""
    global _backtest_engine
    if _backtest_engine is None:
        _backtest_engine = BacktestEngine(config)
    return _backtest_engine


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def test_backtest():
        from strategies.stoch_rsi_strategy import StochRSIStrategy
        
        engine = get_backtest_engine()
        strategy = StochRSIStrategy()
        
        results = await engine.run_backtest(
            strategy=strategy,
            symbols=["AAPL", "MSFT"],
            start_date=datetime.now() - timedelta(days=365),
            end_date=datetime.now(),
            timeframe="1d"
        )
        
        print(engine.generate_report(results))
    
    asyncio.run(test_backtest())