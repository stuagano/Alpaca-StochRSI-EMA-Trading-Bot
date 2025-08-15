import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any, Callable
from datetime import datetime, timedelta
import os
import json
import pickle

from backtesting.backtesting_engine import BacktestingEngine, BacktestResult
from backtesting.strategies import BacktestingStrategies, ParameterOptimizer
from backtesting.visualization import BacktestVisualizer
from services.data_service import get_data_service
from config.config_manager import get_trading_config, get_indicator_config

class BacktestingService:
    """
    Comprehensive backtesting service that orchestrates all backtesting components
    """
    
    def __init__(self):
        self.logger = logging.getLogger('backtesting.service')
        self.data_service = get_data_service()
        self.engine = BacktestingEngine()
        self.strategies = BacktestingStrategies()
        self.optimizer = ParameterOptimizer()
        self.visualizer = BacktestVisualizer()
        
        # Results storage
        self.results_dir = "backtest_results"
        os.makedirs(self.results_dir, exist_ok=True)
        
        self.logger.info("Backtesting Service initialized")
    
    def run_single_strategy_backtest(self, 
                                   strategy_name: str,
                                   ticker: str = "SPY",
                                   start_date: str = None,
                                   end_date: str = None,
                                   parameters: Dict[str, Any] = None,
                                   initial_capital: float = 100000) -> BacktestResult:
        """
        Run backtest for a single strategy
        
        Args:
            strategy_name: Name of strategy to test
            ticker: Symbol to test on
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            parameters: Strategy parameters
            initial_capital: Starting capital
            
        Returns:
            BacktestResult object
        """
        
        self.logger.info(f"Starting single strategy backtest: {strategy_name}")
        
        try:
            # Get market data
            data = self._prepare_market_data(ticker, start_date, end_date)
            
            if data.empty:
                raise ValueError(f"No market data available for {ticker}")
            
            # Get strategy function
            strategy_func = self._get_strategy_function(strategy_name)
            
            # Use provided parameters or defaults
            if parameters is None:
                parameters = self._get_default_parameters(strategy_name)
            
            # Initialize engine with specified capital
            self.engine = BacktestingEngine(initial_capital=initial_capital)
            
            # Run backtest
            result = self.engine.run_backtest(
                data=data,
                strategy_func=strategy_func,
                strategy_params=parameters,
                strategy_name=strategy_name
            )
            
            # Save results
            self._save_backtest_result(result, ticker)
            
            self.logger.info(f"Backtest completed successfully for {strategy_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"Backtest failed for {strategy_name}: {e}")
            raise
    
    def run_strategy_comparison(self, 
                              strategy_names: List[str],
                              ticker: str = "SPY",
                              start_date: str = None,
                              end_date: str = None,
                              initial_capital: float = 100000) -> List[BacktestResult]:
        """
        Compare multiple strategies on the same data
        """
        
        self.logger.info(f"Running strategy comparison for {len(strategy_names)} strategies")
        
        results = []
        
        # Prepare data once for all strategies
        data = self._prepare_market_data(ticker, start_date, end_date)
        
        for strategy_name in strategy_names:
            try:
                self.logger.info(f"Testing strategy: {strategy_name}")
                
                strategy_func = self._get_strategy_function(strategy_name)
                parameters = self._get_default_parameters(strategy_name)
                
                # Create new engine for each strategy
                engine = BacktestingEngine(initial_capital=initial_capital)
                
                result = engine.run_backtest(
                    data=data,
                    strategy_func=strategy_func,
                    strategy_params=parameters,
                    strategy_name=strategy_name
                )
                
                results.append(result)
                self.logger.info(f"Completed {strategy_name}: {result.total_return_pct:.2f}% return")
                
            except Exception as e:
                self.logger.error(f"Failed to test {strategy_name}: {e}")
                continue
        
        # Save comparison results
        self._save_comparison_results(results, ticker)
        
        self.logger.info(f"Strategy comparison completed: {len(results)} strategies tested")
        return results
    
    def optimize_strategy_parameters(self, 
                                   strategy_name: str,
                                   ticker: str = "SPY",
                                   start_date: str = None,
                                   end_date: str = None) -> Dict[str, Any]:
        """
        Optimize parameters for a specific strategy
        """
        
        self.logger.info(f"Starting parameter optimization for {strategy_name}")
        
        try:
            # Get market data
            data = self._prepare_market_data(ticker, start_date, end_date)
            
            # Get strategy function
            strategy_func = self._get_strategy_function(strategy_name)
            
            # Get optimization function
            optimization_func = self._get_optimization_function(strategy_name)
            
            # Run optimization
            optimal_params = optimization_func(data, strategy_func)
            
            # Test optimized parameters
            self.engine = BacktestingEngine()
            optimized_result = self.engine.run_backtest(
                data=data,
                strategy_func=strategy_func,
                strategy_params=optimal_params,
                strategy_name=f"{strategy_name}_Optimized"
            )
            
            # Compare with default parameters
            default_params = self._get_default_parameters(strategy_name)
            default_engine = BacktestingEngine()
            default_result = default_engine.run_backtest(
                data=data,
                strategy_func=strategy_func,
                strategy_params=default_params,
                strategy_name=f"{strategy_name}_Default"
            )
            
            optimization_results = {
                'strategy_name': strategy_name,
                'ticker': ticker,
                'optimization_period': f"{data.index[0]} to {data.index[-1]}",
                'optimal_parameters': optimal_params,
                'default_parameters': default_params,
                'optimized_result': optimized_result,
                'default_result': default_result,
                'improvement': {
                    'return_pct': optimized_result.total_return_pct - default_result.total_return_pct,
                    'sharpe_ratio': optimized_result.sharpe_ratio - default_result.sharpe_ratio,
                    'max_drawdown': optimized_result.max_drawdown_pct - default_result.max_drawdown_pct
                }
            }
            
            # Save optimization results
            self._save_optimization_results(optimization_results, ticker)
            
            self.logger.info(f"Parameter optimization completed for {strategy_name}")
            self.logger.info(f"Optimized return: {optimized_result.total_return_pct:.2f}% "
                           f"vs Default: {default_result.total_return_pct:.2f}%")
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"Parameter optimization failed for {strategy_name}: {e}")
            raise
    
    def run_walk_forward_analysis(self, 
                                strategy_name: str,
                                ticker: str = "SPY",
                                start_date: str = None,
                                end_date: str = None,
                                window_size: int = 252,
                                step_size: int = 30) -> Dict[str, Any]:
        """
        Run walk-forward analysis for strategy validation
        """
        
        self.logger.info(f"Starting walk-forward analysis for {strategy_name}")
        
        try:
            # Get market data
            data = self._prepare_market_data(ticker, start_date, end_date)
            
            if len(data) < window_size * 2:
                raise ValueError(f"Insufficient data for walk-forward analysis. "
                               f"Need at least {window_size * 2} days, got {len(data)}")
            
            # Get strategy function
            strategy_func = self._get_strategy_function(strategy_name)
            
            # Get optimization function
            optimization_func = self._get_optimization_function(strategy_name)
            
            # Run walk-forward analysis
            wfa_results = self.engine.run_walk_forward_analysis(
                data=data,
                strategy_func=strategy_func,
                optimization_func=optimization_func,
                window_size=window_size,
                step_size=step_size
            )
            
            # Calculate aggregate statistics
            if wfa_results:
                aggregate_stats = self._calculate_wfa_statistics(wfa_results)
                
                wfa_analysis = {
                    'strategy_name': strategy_name,
                    'ticker': ticker,
                    'analysis_period': f"{data.index[0]} to {data.index[-1]}",
                    'window_size': window_size,
                    'step_size': step_size,
                    'num_periods': len(wfa_results),
                    'period_results': wfa_results,
                    'aggregate_statistics': aggregate_stats
                }
                
                # Save WFA results
                self._save_wfa_results(wfa_analysis, ticker)
                
                self.logger.info(f"Walk-forward analysis completed: {len(wfa_results)} periods tested")
                self.logger.info(f"Average return: {aggregate_stats['avg_return']:.2f}%, "
                               f"Consistency: {aggregate_stats['positive_periods']}/{aggregate_stats['total_periods']}")
                
                return wfa_analysis
            else:
                raise ValueError("Walk-forward analysis produced no results")
                
        except Exception as e:
            self.logger.error(f"Walk-forward analysis failed for {strategy_name}: {e}")
            raise
    
    def run_monte_carlo_analysis(self, 
                               strategy_name: str,
                               ticker: str = "SPY",
                               start_date: str = None,
                               end_date: str = None,
                               num_simulations: int = 1000) -> Dict[str, Any]:
        """
        Run Monte Carlo analysis on strategy trades
        """
        
        self.logger.info(f"Starting Monte Carlo analysis for {strategy_name}")
        
        try:
            # First run a regular backtest to get trades
            backtest_result = self.run_single_strategy_backtest(
                strategy_name=strategy_name,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date
            )
            
            if not backtest_result.trades:
                raise ValueError("No trades found for Monte Carlo analysis")
            
            # Convert trade data to Trade objects for Monte Carlo analysis
            from backtesting.backtesting_engine import Trade
            trades = []
            for trade_data in backtest_result.trades:
                trade = Trade(
                    entry_time=trade_data['entry_time'],
                    exit_time=trade_data['exit_time'],
                    symbol=ticker,
                    side='long',
                    entry_price=trade_data['entry_price'],
                    exit_price=trade_data['exit_price'],
                    quantity=trade_data['quantity'],
                    pnl=trade_data['pnl'],
                    pnl_pct=trade_data['pnl_pct'],
                    duration_hours=trade_data['duration_hours']
                )
                trades.append(trade)
            
            # Run Monte Carlo analysis
            mc_results = self.engine.monte_carlo_analysis(
                trades=trades,
                num_simulations=num_simulations
            )
            
            mc_analysis = {
                'strategy_name': strategy_name,
                'ticker': ticker,
                'base_backtest': backtest_result,
                'monte_carlo_results': mc_results,
                'analysis_date': datetime.now().isoformat()
            }
            
            # Save MC results
            self._save_monte_carlo_results(mc_analysis, ticker)
            
            self.logger.info(f"Monte Carlo analysis completed: "
                           f"{mc_results['probability_of_profit']:.1f}% chance of profit")
            
            return mc_analysis
            
        except Exception as e:
            self.logger.error(f"Monte Carlo analysis failed for {strategy_name}: {e}")
            raise
    
    def generate_comprehensive_report(self, 
                                    strategy_name: str,
                                    ticker: str = "SPY",
                                    start_date: str = None,
                                    end_date: str = None) -> Dict[str, Any]:
        """
        Generate comprehensive backtesting report with all analyses
        """
        
        self.logger.info(f"Generating comprehensive report for {strategy_name}")
        
        report = {
            'strategy_name': strategy_name,
            'ticker': ticker,
            'analysis_date': datetime.now().isoformat(),
            'analyses': {}
        }
        
        try:
            # 1. Basic backtest
            self.logger.info("Running basic backtest...")
            backtest_result = self.run_single_strategy_backtest(
                strategy_name=strategy_name,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date
            )
            report['analyses']['backtest'] = backtest_result
            
            # 2. Parameter optimization
            self.logger.info("Running parameter optimization...")
            try:
                optimization_results = self.optimize_strategy_parameters(
                    strategy_name=strategy_name,
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date
                )
                report['analyses']['optimization'] = optimization_results
            except Exception as e:
                self.logger.warning(f"Parameter optimization failed: {e}")
                report['analyses']['optimization'] = {'error': str(e)}
            
            # 3. Monte Carlo analysis
            self.logger.info("Running Monte Carlo analysis...")
            try:
                mc_results = self.run_monte_carlo_analysis(
                    strategy_name=strategy_name,
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    num_simulations=500  # Reduced for speed
                )
                report['analyses']['monte_carlo'] = mc_results
            except Exception as e:
                self.logger.warning(f"Monte Carlo analysis failed: {e}")
                report['analyses']['monte_carlo'] = {'error': str(e)}
            
            # 4. Generate visualizations
            self.logger.info("Generating visualizations...")
            try:
                data = self._prepare_market_data(ticker, start_date, end_date)
                
                # Performance dashboard
                dashboard_fig = self.visualizer.create_performance_dashboard(
                    backtest_result, data
                )
                
                # Save charts
                chart_filename = f"{strategy_name}_{ticker}_dashboard"
                chart_path = os.path.join(self.results_dir, f"{chart_filename}.html")
                dashboard_fig.write_html(chart_path)
                
                report['visualizations'] = {
                    'dashboard_path': chart_path
                }
                
            except Exception as e:
                self.logger.warning(f"Visualization generation failed: {e}")
                report['visualizations'] = {'error': str(e)}
            
            # 5. Generate text report
            text_report = self.engine.generate_report(backtest_result)
            report_path = os.path.join(
                self.results_dir, 
                f"{strategy_name}_{ticker}_report.md"
            )
            with open(report_path, 'w') as f:
                f.write(text_report)
            
            report['text_report_path'] = report_path
            
            # Save comprehensive report
            self._save_comprehensive_report(report, ticker)
            
            self.logger.info(f"Comprehensive report generated successfully for {strategy_name}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Comprehensive report generation failed: {e}")
            report['error'] = str(e)
            return report
    
    def _prepare_market_data(self, ticker: str, 
                           start_date: str = None, 
                           end_date: str = None) -> pd.DataFrame:
        """
        Prepare market data for backtesting
        """
        
        # For now, generate synthetic data since we don't have historical data integrated
        # In production, this would fetch real historical data
        
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Generate synthetic OHLCV data for demonstration
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Simple random walk with trend
        np.random.seed(42)  # For reproducible results
        returns = np.random.normal(0.0005, 0.02, len(date_range))  # Daily returns
        prices = 100 * (1 + returns).cumprod()  # Starting at $100
        
        # Generate OHLCV data
        data = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.005, len(prices))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(prices)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(prices)))),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(prices))
        }, index=date_range)
        
        # Ensure OHLC consistency
        data['high'] = data[['open', 'high', 'close']].max(axis=1)
        data['low'] = data[['open', 'low', 'close']].min(axis=1)
        
        self.logger.info(f"Prepared synthetic market data for {ticker}: "
                        f"{len(data)} days from {start_date} to {end_date}")
        
        return data
    
    def _get_strategy_function(self, strategy_name: str) -> Callable:
        """Get strategy function by name"""
        
        strategy_mapping = {
            'stochastic_rsi': self.strategies.stochastic_rsi_strategy,
            'ema': self.strategies.ema_strategy,
            'stochastic': self.strategies.stochastic_strategy,
            'macd': self.strategies.macd_strategy,
            'rsi': self.strategies.rsi_strategy,
            'bollinger_bands': self.strategies.bollinger_bands_strategy,
            'combined': self.strategies.combined_strategy
        }
        
        if strategy_name not in strategy_mapping:
            available_strategies = ', '.join(strategy_mapping.keys())
            raise ValueError(f"Unknown strategy: {strategy_name}. "
                           f"Available strategies: {available_strategies}")
        
        return strategy_mapping[strategy_name]
    
    def _get_optimization_function(self, strategy_name: str) -> Callable:
        """Get optimization function by strategy name"""
        
        optimization_mapping = {
            'stochastic_rsi': self.optimizer.optimize_stoch_rsi_parameters,
            'ema': self.optimizer.optimize_ema_parameters,
            'combined': self.optimizer.optimize_combined_parameters
        }
        
        # Default to StochRSI optimization if specific optimizer not available
        return optimization_mapping.get(strategy_name, 
                                      self.optimizer.optimize_stoch_rsi_parameters)
    
    def _get_default_parameters(self, strategy_name: str) -> Dict[str, Any]:
        """Get default parameters for a strategy"""
        
        # Get parameters from configuration
        indicator_config = get_indicator_config()
        trading_config = get_trading_config()
        
        default_params = {
            'stochastic_rsi': {
                'rsi_period': indicator_config.stoch_rsi_period,
                'stoch_period': indicator_config.stoch_rsi_period,
                'k_period': indicator_config.stoch_rsi_k_period,
                'd_period': indicator_config.stoch_rsi_d_period,
                'oversold_threshold': indicator_config.stoch_rsi_oversold,
                'overbought_threshold': indicator_config.stoch_rsi_overbought
            },
            'ema': {
                'fast_period': indicator_config.ema_fast_period,
                'slow_period': indicator_config.ema_slow_period
            },
            'stochastic': {
                'k_period': indicator_config.stoch_k_period,
                'd_period': indicator_config.stoch_d_period,
                'oversold': indicator_config.stoch_oversold,
                'overbought': indicator_config.stoch_overbought
            },
            'macd': {
                'fast_period': indicator_config.macd_fast,
                'slow_period': indicator_config.macd_slow,
                'signal_period': indicator_config.macd_signal
            },
            'rsi': {
                'period': indicator_config.rsi_period,
                'oversold': indicator_config.rsi_oversold,
                'overbought': indicator_config.rsi_overbought
            },
            'bollinger_bands': {
                'period': indicator_config.bollinger_period,
                'std_dev': indicator_config.bollinger_std
            },
            'combined': {
                'stoch_rsi_rsi_period': indicator_config.stoch_rsi_period,
                'stoch_rsi_oversold_threshold': indicator_config.stoch_rsi_oversold,
                'ema_fast_period': indicator_config.ema_fast_period,
                'ema_slow_period': indicator_config.ema_slow_period,
                'rsi_period': indicator_config.rsi_period,
                'rsi_oversold': indicator_config.rsi_oversold,
                'min_signals': 2
            }
        }
        
        return default_params.get(strategy_name, {})
    
    def _calculate_wfa_statistics(self, wfa_results: List[BacktestResult]) -> Dict[str, Any]:
        """Calculate aggregate statistics from walk-forward analysis"""
        
        returns = [result.total_return_pct for result in wfa_results]
        sharpe_ratios = [result.sharpe_ratio for result in wfa_results]
        win_rates = [result.win_rate for result in wfa_results]
        
        return {
            'total_periods': len(wfa_results),
            'positive_periods': sum(1 for r in returns if r > 0),
            'avg_return': np.mean(returns),
            'std_return': np.std(returns),
            'avg_sharpe': np.mean(sharpe_ratios),
            'avg_win_rate': np.mean(win_rates),
            'best_period_return': max(returns),
            'worst_period_return': min(returns),
            'consistency_score': sum(1 for r in returns if r > 0) / len(returns) * 100
        }
    
    def _save_backtest_result(self, result: BacktestResult, ticker: str):
        """Save backtest result to file"""
        
        filename = f"backtest_{result.strategy_name}_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        # Convert result to dictionary for JSON serialization
        result_dict = {
            'strategy_name': result.strategy_name,
            'start_date': result.start_date,
            'end_date': result.end_date,
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'win_rate': result.win_rate,
            'total_return': result.total_return,
            'total_return_pct': result.total_return_pct,
            'max_drawdown': result.max_drawdown,
            'max_drawdown_pct': result.max_drawdown_pct,
            'sharpe_ratio': result.sharpe_ratio,
            'sortino_ratio': result.sortino_ratio,
            'profit_factor': result.profit_factor,
            'trades': result.trades,
            'ticker': ticker
        }
        
        with open(filepath, 'w') as f:
            json.dump(result_dict, f, indent=2)
        
        self.logger.debug(f"Backtest result saved to {filepath}")
    
    def _save_comparison_results(self, results: List[BacktestResult], ticker: str):
        """Save strategy comparison results"""
        
        filename = f"comparison_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        comparison_data = {
            'ticker': ticker,
            'comparison_date': datetime.now().isoformat(),
            'strategies': []
        }
        
        for result in results:
            strategy_data = {
                'name': result.strategy_name,
                'total_return_pct': result.total_return_pct,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown_pct': result.max_drawdown_pct,
                'win_rate': result.win_rate,
                'total_trades': result.total_trades
            }
            comparison_data['strategies'].append(strategy_data)
        
        with open(filepath, 'w') as f:
            json.dump(comparison_data, f, indent=2)
        
        self.logger.debug(f"Comparison results saved to {filepath}")
    
    def _save_optimization_results(self, optimization_results: Dict[str, Any], ticker: str):
        """Save optimization results"""
        
        filename = f"optimization_{optimization_results['strategy_name']}_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'wb') as f:
            pickle.dump(optimization_results, f)
        
        self.logger.debug(f"Optimization results saved to {filepath}")
    
    def _save_wfa_results(self, wfa_analysis: Dict[str, Any], ticker: str):
        """Save walk-forward analysis results"""
        
        filename = f"wfa_{wfa_analysis['strategy_name']}_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'wb') as f:
            pickle.dump(wfa_analysis, f)
        
        self.logger.debug(f"WFA results saved to {filepath}")
    
    def _save_monte_carlo_results(self, mc_analysis: Dict[str, Any], ticker: str):
        """Save Monte Carlo analysis results"""
        
        filename = f"monte_carlo_{mc_analysis['strategy_name']}_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'wb') as f:
            pickle.dump(mc_analysis, f)
        
        self.logger.debug(f"Monte Carlo results saved to {filepath}")
    
    def _save_comprehensive_report(self, report: Dict[str, Any], ticker: str):
        """Save comprehensive report"""
        
        filename = f"comprehensive_report_{report['strategy_name']}_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'wb') as f:
            pickle.dump(report, f)
        
        self.logger.debug(f"Comprehensive report saved to {filepath}")
    
    def list_available_strategies(self) -> List[str]:
        """Get list of available strategies"""
        
        return [
            'stochastic_rsi',
            'ema', 
            'stochastic',
            'macd',
            'rsi',
            'bollinger_bands',
            'combined'
        ]
    
    def get_strategy_description(self, strategy_name: str) -> str:
        """Get description of a strategy"""
        
        descriptions = {
            'stochastic_rsi': "StochRSI strategy using RSI with stochastic smoothing for momentum signals",
            'ema': "Exponential Moving Average crossover strategy for trend following",
            'stochastic': "Traditional stochastic oscillator strategy for momentum trading",
            'macd': "MACD strategy using moving average convergence divergence",
            'rsi': "RSI strategy using Relative Strength Index for overbought/oversold signals",
            'bollinger_bands': "Bollinger Bands mean reversion strategy",
            'combined': "Combined multi-indicator strategy using StochRSI, EMA, and RSI confluence"
        }
        
        return descriptions.get(strategy_name, "Unknown strategy")

# Global backtesting service instance
_backtesting_service = None

def get_backtesting_service() -> BacktestingService:
    """Get singleton backtesting service instance"""
    global _backtesting_service
    if _backtesting_service is None:
        _backtesting_service = BacktestingService()
    return _backtesting_service