"""
Enhanced Backtesting Engine with Volume Confirmation Analysis

This enhanced backtesting engine provides comprehensive analysis of volume confirmation
effectiveness and detailed performance metrics for trading strategies.

Features:
- Volume confirmation tracking and analysis
- Detailed performance comparison (confirmed vs non-confirmed signals)
- False signal reduction calculations
- Volume effectiveness metrics
- Enhanced reporting and visualization

Author: Trading Bot System
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
from dataclasses import dataclass

from backtesting.strategies import *
from services.unified_data_manager import get_data_manager
from indicators.volume_analysis import get_volume_analyzer

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Enhanced trade record with volume confirmation data"""
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    profit: float
    profit_pct: float
    volume_confirmed: bool
    volume_data: Dict
    signal_strength: float = 0.0


@dataclass
class BacktestResults:
    """Comprehensive backtest results"""
    trades: List[TradeRecord]
    portfolio_value: List[float]
    performance_metrics: Dict
    volume_analysis: Dict
    volume_stats: Dict
    summary_report: str


class EnhancedBacktestingEngine:
    """
    Enhanced backtesting engine with volume confirmation analysis
    """
    
    def __init__(self, strategy, symbol: str, start_date: str, end_date: str, config=None):
        """
        Initialize the enhanced backtesting engine
        
        Args:
            strategy: Trading strategy instance
            symbol: Stock symbol to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
            config: Configuration object
        """
        self.strategy = strategy
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.config = config
        
        # Data management
        self.data_manager = get_data_manager()
        self.data = self.data_manager.get_historical_data(
            symbol, '1Day', start_hours_ago=90*24
        )  # Approx 3 months
        
        # Trading state
        self.trades = []
        self.trade_records = []
        self.position = None
        self.cash = 100000  # Starting cash
        self.portfolio_value = []
        
        # Volume confirmation setup
        self.volume_analyzer = get_volume_analyzer(
            config.volume_confirmation if config else None
        )
        self.volume_stats = {
            'total_signals': 0,
            'volume_confirmed_signals': 0,
            'volume_rejected_signals': 0,
            'confirmed_trades': [],
            'non_confirmed_trades': [],
            'signal_details': []
        }
        
        # Performance tracking
        self.daily_returns = []
        self.drawdowns = []
        self.max_drawdown = 0
        
        logger.info(f"Enhanced backtesting engine initialized for {symbol}")
    
    def run(self) -> BacktestResults:
        """
        Run the enhanced backtest with volume confirmation analysis
        
        Returns:
            BacktestResults object with comprehensive analysis
        """
        logger.info(f"Starting enhanced backtest for {self.symbol}")
        
        initial_portfolio_value = self.cash
        peak_value = self.cash
        
        for i in range(len(self.data)):
            row = self.data.iloc[i]
            current_data = self.data.iloc[:i+1]
            
            # Generate signal from strategy
            signal = self.strategy.generate_signal(current_data)
            
            # Track volume confirmation if signal exists
            volume_confirmed = False
            volume_data = {}
            signal_strength = 0.0
            
            if signal != 0:
                self.volume_stats['total_signals'] += 1
                
                # Get volume confirmation
                try:
                    volume_result = self.volume_analyzer.confirm_signal_with_volume(
                        current_data, signal
                    )
                    volume_confirmed = volume_result.is_confirmed
                    signal_strength = volume_result.confirmation_strength
                    volume_data = {
                        'volume_ratio': volume_result.volume_ratio,
                        'relative_volume': volume_result.relative_volume,
                        'volume_trend': volume_result.volume_trend,
                        'confirmation_strength': signal_strength,
                        'profile_levels': volume_result.profile_levels
                    }
                    
                    # Track signal statistics
                    if volume_confirmed:
                        self.volume_stats['volume_confirmed_signals'] += 1
                    else:
                        self.volume_stats['volume_rejected_signals'] += 1
                    
                    # Store signal details for analysis
                    self.volume_stats['signal_details'].append({
                        'date': row.name,
                        'signal': signal,
                        'volume_confirmed': volume_confirmed,
                        'volume_data': volume_data,
                        'price': row['Close']
                    })
                        
                except Exception as e:
                    logger.warning(f"Volume confirmation error at index {i}: {e}")
            
            # Execute trades based on signals
            if signal == 1 and not self.position:
                # Buy signal
                entry_price = row['Close']
                self.position = {
                    'entry_price': entry_price,
                    'entry_date': row.name,
                    'entry_index': i,
                    'volume_confirmed': volume_confirmed,
                    'volume_data': volume_data,
                    'signal_strength': signal_strength
                }
                self.trades.append(('buy', row.name, entry_price, volume_confirmed, volume_data))
                logger.debug(f"Buy signal at {row.name}: ${entry_price:.2f} (Volume confirmed: {volume_confirmed})")
                
            elif signal == -1 and self.position:
                # Sell signal
                exit_price = row['Close']
                profit = exit_price - self.position['entry_price']
                profit_pct = (profit / self.position['entry_price']) * 100
                
                # Create trade record
                trade_record = TradeRecord(
                    entry_date=self.position['entry_date'],
                    exit_date=row.name,
                    entry_price=self.position['entry_price'],
                    exit_price=exit_price,
                    profit=profit,
                    profit_pct=profit_pct,
                    volume_confirmed=self.position['volume_confirmed'],
                    volume_data=self.position['volume_data'],
                    signal_strength=self.position['signal_strength']
                )
                
                self.trade_records.append(trade_record)
                
                # Categorize trade by volume confirmation
                if self.position['volume_confirmed']:
                    self.volume_stats['confirmed_trades'].append(trade_record)
                else:
                    self.volume_stats['non_confirmed_trades'].append(trade_record)
                
                # Update cash
                self.cash += profit
                
                self.trades.append(('sell', row.name, exit_price))
                logger.debug(f"Sell signal at {row.name}: ${exit_price:.2f} (Profit: ${profit:.2f})")
                
                self.position = None
            
            # Calculate portfolio value
            current_value = self.cash
            if self.position:
                unrealized_profit = row['Close'] - self.position['entry_price']
                current_value += unrealized_profit
            
            self.portfolio_value.append(current_value)
            
            # Track drawdown
            if current_value > peak_value:
                peak_value = current_value
            
            drawdown = (peak_value - current_value) / peak_value
            self.drawdowns.append(drawdown)
            self.max_drawdown = max(self.max_drawdown, drawdown)
            
            # Calculate daily returns
            if len(self.portfolio_value) > 1:
                daily_return = (current_value - self.portfolio_value[-2]) / self.portfolio_value[-2]
                self.daily_returns.append(daily_return)
        
        # Generate comprehensive results
        results = self._generate_results()
        logger.info(f"Backtest completed. Total trades: {len(self.trade_records)}")
        
        return results
    
    def _generate_results(self) -> BacktestResults:
        """
        Generate comprehensive backtest results
        
        Returns:
            BacktestResults object with detailed analysis
        """
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics()
        
        # Calculate volume analysis
        volume_analysis = self._calculate_volume_performance()
        
        # Generate summary report
        summary_report = self._generate_summary_report(performance_metrics, volume_analysis)
        
        return BacktestResults(
            trades=self.trade_records,
            portfolio_value=self.portfolio_value,
            performance_metrics=performance_metrics,
            volume_analysis=volume_analysis,
            volume_stats=self.volume_stats,
            summary_report=summary_report
        )
    
    def _calculate_performance_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not self.portfolio_value:
            return {}
        
        total_return = (self.portfolio_value[-1] / self.portfolio_value[0]) - 1
        
        # Calculate Sharpe ratio
        if self.daily_returns and len(self.daily_returns) > 1:
            daily_returns_series = pd.Series(self.daily_returns)
            sharpe_ratio = (daily_returns_series.mean() / daily_returns_series.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        # Win rate calculation
        profitable_trades = [t for t in self.trade_records if t.profit > 0]
        win_rate = len(profitable_trades) / len(self.trade_records) if self.trade_records else 0
        
        # Average trade metrics
        avg_profit = np.mean([t.profit for t in self.trade_records]) if self.trade_records else 0
        avg_profit_pct = np.mean([t.profit_pct for t in self.trade_records]) if self.trade_records else 0
        
        # Profit factor
        gross_profit = sum(t.profit for t in self.trade_records if t.profit > 0)
        gross_loss = abs(sum(t.profit for t in self.trade_records if t.profit < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown * 100,
            'total_trades': len(self.trade_records),
            'winning_trades': len(profitable_trades),
            'losing_trades': len(self.trade_records) - len(profitable_trades),
            'win_rate': win_rate,
            'win_rate_pct': win_rate * 100,
            'avg_profit': avg_profit,
            'avg_profit_pct': avg_profit_pct,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'final_portfolio_value': self.portfolio_value[-1],
            'initial_capital': self.portfolio_value[0]
        }
    
    def _calculate_volume_performance(self) -> Dict:
        """Calculate volume confirmation performance metrics"""
        confirmed_trades = self.volume_stats['confirmed_trades']
        non_confirmed_trades = self.volume_stats['non_confirmed_trades']
        
        metrics = {
            'total_signals': self.volume_stats['total_signals'],
            'volume_confirmed_signals': self.volume_stats['volume_confirmed_signals'],
            'volume_rejected_signals': self.volume_stats['volume_rejected_signals'],
            'confirmation_rate': (
                self.volume_stats['volume_confirmed_signals'] / self.volume_stats['total_signals']
                if self.volume_stats['total_signals'] > 0 else 0
            )
        }
        
        # Analyze confirmed trades
        if confirmed_trades:
            confirmed_profits = [t.profit for t in confirmed_trades]
            confirmed_profitable = [t for t in confirmed_trades if t.profit > 0]
            
            metrics.update({
                'confirmed_trades_count': len(confirmed_trades),
                'confirmed_win_rate': len(confirmed_profitable) / len(confirmed_trades),
                'confirmed_avg_profit': np.mean(confirmed_profits),
                'confirmed_total_profit': sum(confirmed_profits),
                'confirmed_avg_profit_pct': np.mean([t.profit_pct for t in confirmed_trades]),
                'confirmed_profit_factor': self._calculate_profit_factor(confirmed_trades)
            })
        else:
            metrics.update({
                'confirmed_trades_count': 0,
                'confirmed_win_rate': 0,
                'confirmed_avg_profit': 0,
                'confirmed_total_profit': 0,
                'confirmed_avg_profit_pct': 0,
                'confirmed_profit_factor': 0
            })
        
        # Analyze non-confirmed trades
        if non_confirmed_trades:
            non_confirmed_profits = [t.profit for t in non_confirmed_trades]
            non_confirmed_profitable = [t for t in non_confirmed_trades if t.profit > 0]
            
            metrics.update({
                'non_confirmed_trades_count': len(non_confirmed_trades),
                'non_confirmed_win_rate': len(non_confirmed_profitable) / len(non_confirmed_trades),
                'non_confirmed_avg_profit': np.mean(non_confirmed_profits),
                'non_confirmed_total_profit': sum(non_confirmed_profits),
                'non_confirmed_avg_profit_pct': np.mean([t.profit_pct for t in non_confirmed_trades]),
                'non_confirmed_profit_factor': self._calculate_profit_factor(non_confirmed_trades)
            })
        else:
            metrics.update({
                'non_confirmed_trades_count': 0,
                'non_confirmed_win_rate': 0,
                'non_confirmed_avg_profit': 0,
                'non_confirmed_total_profit': 0,
                'non_confirmed_avg_profit_pct': 0,
                'non_confirmed_profit_factor': 0
            })
        
        # Calculate improvements
        if metrics['non_confirmed_win_rate'] > 0:
            metrics['win_rate_improvement'] = (
                (metrics['confirmed_win_rate'] - metrics['non_confirmed_win_rate']) /
                metrics['non_confirmed_win_rate']
            )
        else:
            metrics['win_rate_improvement'] = 0
        
        if metrics['non_confirmed_avg_profit'] != 0:
            metrics['avg_profit_improvement'] = (
                (metrics['confirmed_avg_profit'] - metrics['non_confirmed_avg_profit']) /
                abs(metrics['non_confirmed_avg_profit'])
            )
        else:
            metrics['avg_profit_improvement'] = 0
        
        # False signal reduction
        total_losing_trades = len([t for t in self.trade_records if t.profit <= 0])
        confirmed_losing_trades = len([t for t in confirmed_trades if t.profit <= 0])
        
        if total_losing_trades > 0:
            metrics['false_signal_reduction'] = (
                (total_losing_trades - confirmed_losing_trades) / total_losing_trades
            )
        else:
            metrics['false_signal_reduction'] = 0
        
        # Volume effectiveness metrics
        if confirmed_trades:
            volume_ratios = [t.volume_data.get('volume_ratio', 0) for t in confirmed_trades]
            relative_volumes = [t.volume_data.get('relative_volume', 0) for t in confirmed_trades]
            confirmation_strengths = [t.signal_strength for t in confirmed_trades]
            
            metrics.update({
                'avg_volume_ratio': np.mean(volume_ratios),
                'avg_relative_volume': np.mean(relative_volumes),
                'avg_confirmation_strength': np.mean(confirmation_strengths)
            })
        
        return metrics
    
    def _calculate_profit_factor(self, trades: List[TradeRecord]) -> float:
        """Calculate profit factor for a list of trades"""
        if not trades:
            return 0
        
        gross_profit = sum(t.profit for t in trades if t.profit > 0)
        gross_loss = abs(sum(t.profit for t in trades if t.profit < 0))
        
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    def _generate_summary_report(self, performance: Dict, volume_analysis: Dict) -> str:
        """Generate a comprehensive summary report"""
        report = f"""
ENHANCED BACKTEST RESULTS - {self.symbol}
{'='*50}

OVERALL PERFORMANCE:
- Total Return: {performance.get('total_return_pct', 0):.2f}%
- Sharpe Ratio: {performance.get('sharpe_ratio', 0):.2f}
- Max Drawdown: {performance.get('max_drawdown_pct', 0):.2f}%
- Total Trades: {performance.get('total_trades', 0)}
- Win Rate: {performance.get('win_rate_pct', 0):.1f}%
- Profit Factor: {performance.get('profit_factor', 0):.2f}

VOLUME CONFIRMATION ANALYSIS:
- Total Signals: {volume_analysis.get('total_signals', 0)}
- Confirmed Signals: {volume_analysis.get('volume_confirmed_signals', 0)}
- Confirmation Rate: {volume_analysis.get('confirmation_rate', 0)*100:.1f}%

VOLUME-CONFIRMED TRADES:
- Count: {volume_analysis.get('confirmed_trades_count', 0)}
- Win Rate: {volume_analysis.get('confirmed_win_rate', 0)*100:.1f}%
- Avg Profit: ${volume_analysis.get('confirmed_avg_profit', 0):.2f}
- Total Profit: ${volume_analysis.get('confirmed_total_profit', 0):.2f}

NON-CONFIRMED TRADES:
- Count: {volume_analysis.get('non_confirmed_trades_count', 0)}
- Win Rate: {volume_analysis.get('non_confirmed_win_rate', 0)*100:.1f}%
- Avg Profit: ${volume_analysis.get('non_confirmed_avg_profit', 0):.2f}
- Total Profit: ${volume_analysis.get('non_confirmed_total_profit', 0):.2f}

VOLUME CONFIRMATION EFFECTIVENESS:
- Win Rate Improvement: {volume_analysis.get('win_rate_improvement', 0)*100:.1f}%
- False Signal Reduction: {volume_analysis.get('false_signal_reduction', 0)*100:.1f}%
- Avg Profit Improvement: {volume_analysis.get('avg_profit_improvement', 0)*100:.1f}%

VOLUME METRICS (Confirmed Trades):
- Avg Volume Ratio: {volume_analysis.get('avg_volume_ratio', 0):.2f}x
- Avg Relative Volume: {volume_analysis.get('avg_relative_volume', 0):.2f}x
- Avg Confirmation Strength: {volume_analysis.get('avg_confirmation_strength', 0):.2f}

PERFORMANCE IMPACT:
{"✅ Volume confirmation IMPROVES performance" if volume_analysis.get('false_signal_reduction', 0) > 0.3 else "❌ Volume confirmation shows LIMITED benefit"}
False Signal Reduction Target: >30% (Actual: {volume_analysis.get('false_signal_reduction', 0)*100:.1f}%)
"""
        return report.strip()
    
    def export_results(self, filename: str = None):
        """Export backtest results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_{self.symbol}_{timestamp}.json"
        
        results = self.run()
        
        # Convert results to serializable format
        export_data = {
            'symbol': self.symbol,
            'backtest_period': f"{self.start_date} to {self.end_date}",
            'performance_metrics': results.performance_metrics,
            'volume_analysis': results.volume_analysis,
            'summary_report': results.summary_report,
            'trade_count': len(results.trades),
            'portfolio_final_value': results.portfolio_value[-1] if results.portfolio_value else 0
        }
        
        import json
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Backtest results exported to {filename}")
        return filename


# Convenience function for quick backtests
def run_volume_backtest(strategy, symbol: str, config, days: int = 90) -> BacktestResults:
    """
    Run a quick volume confirmation backtest
    
    Args:
        strategy: Trading strategy instance
        symbol: Stock symbol
        config: Configuration object
        days: Number of days to backtest
        
    Returns:
        BacktestResults object
    """
    from datetime import datetime, timedelta
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    engine = EnhancedBacktestingEngine(strategy, symbol, start_date, end_date, config)
    return engine.run()