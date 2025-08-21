"""
Automated Backtesting Tests for Epic 1 Signal Quality Enhancements

Tests the automated backtesting framework that validates Epic 1 features against historical data:
- Historical signal validation
- Performance comparison against baselines
- Feature effectiveness analysis
- Market condition impact assessment
- Statistical significance testing
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Tuple, Optional
import warnings

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from indicators.stoch_rsi_enhanced import StochRSIIndicator
from tests.epic1_signal_quality.fixtures.epic1_test_fixtures import (
    epic1_config, backtesting_scenarios, TestDataGenerator
)


class BacktestingEngine:
    """Automated backtesting engine for Epic 1 enhancements."""
    
    def __init__(self, config: dict):
        self.commission = config.get('commission', 0.005)  # 0.5% per trade
        self.slippage = config.get('slippage', 0.001)      # 0.1% slippage
        self.initial_capital = config.get('initial_capital', 10000)
        self.position_size = config.get('position_size', 0.1)  # 10% of capital per trade
        self.stop_loss = config.get('stop_loss', 0.05)     # 5% stop loss
        self.take_profit = config.get('take_profit', 0.10) # 10% take profit
        self.max_holding_period = config.get('max_holding_period', 1440)  # 24 hours in minutes
        
        # Results storage
        self.trades = []
        self.equity_curve = []
        self.drawdown_curve = []
        
    def run_backtest(self, data: pd.DataFrame, signals: pd.Series, 
                     strategy_name: str = "Enhanced StochRSI") -> Dict:
        """Run comprehensive backtest on historical data."""
        
        # Initialize tracking variables
        capital = self.initial_capital
        position = None
        peak_capital = capital
        max_drawdown = 0.0
        
        # Reset results
        self.trades.clear()
        self.equity_curve.clear()
        self.drawdown_curve.clear()
        
        for i in range(len(data)):
            current_price = data['close'].iloc[i]
            current_time = data.index[i]
            current_signal = signals.iloc[i] if i < len(signals) else 0
            
            # Check if we have an open position
            if position is not None:
                # Calculate current position value
                if position['side'] == 'long':
                    current_value = position['shares'] * current_price
                    unrealized_pnl = current_value - position['cost_basis']
                else:  # short position
                    current_value = position['cost_basis'] - (position['shares'] * current_price)
                    unrealized_pnl = current_value - position['cost_basis']
                
                # Check exit conditions
                should_exit, exit_reason = self._check_exit_conditions(
                    position, current_price, current_time, current_signal
                )
                
                if should_exit:
                    # Close position
                    trade_result = self._close_position(position, current_price, current_time, exit_reason)
                    self.trades.append(trade_result)
                    
                    # Update capital
                    capital += trade_result['pnl']
                    position = None
            
            # Check for new position entry
            elif current_signal != 0:
                position = self._open_position(current_signal, current_price, current_time, capital)
            
            # Update equity curve
            total_equity = capital
            if position is not None:
                if position['side'] == 'long':
                    position_value = position['shares'] * current_price
                    unrealized_pnl = position_value - position['cost_basis']
                else:
                    position_value = position['cost_basis'] - (position['shares'] * current_price)
                    unrealized_pnl = position_value - position['cost_basis']
                total_equity += unrealized_pnl
            
            self.equity_curve.append({
                'timestamp': current_time,
                'equity': total_equity,
                'realized_pnl': capital - self.initial_capital
            })
            
            # Update drawdown
            peak_capital = max(peak_capital, total_equity)
            current_drawdown = (peak_capital - total_equity) / peak_capital
            max_drawdown = max(max_drawdown, current_drawdown)
            
            self.drawdown_curve.append({
                'timestamp': current_time,
                'drawdown': current_drawdown
            })
        
        # Close any remaining open position
        if position is not None:
            final_price = data['close'].iloc[-1]
            final_time = data.index[-1]
            trade_result = self._close_position(position, final_price, final_time, 'end_of_data')
            self.trades.append(trade_result)
            capital += trade_result['pnl']
        
        return self._calculate_performance_metrics(strategy_name)
    
    def compare_strategies(self, data: pd.DataFrame, 
                          strategy_results: Dict[str, pd.Series]) -> Dict:
        """Compare multiple strategy results."""
        comparison_results = {}
        
        for strategy_name, signals in strategy_results.items():
            result = self.run_backtest(data, signals, strategy_name)
            comparison_results[strategy_name] = result
        
        # Calculate relative performance metrics
        baseline_strategy = list(comparison_results.keys())[0]
        baseline_return = comparison_results[baseline_strategy]['total_return']
        
        for strategy_name, result in comparison_results.items():
            if strategy_name != baseline_strategy:
                result['relative_return'] = result['total_return'] - baseline_return
                result['return_improvement'] = (result['total_return'] / baseline_return - 1) * 100
        
        return comparison_results
    
    def run_monte_carlo_simulation(self, data: pd.DataFrame, signals: pd.Series,
                                 num_simulations: int = 1000) -> Dict:
        """Run Monte Carlo simulation to assess strategy robustness."""
        simulation_results = []
        
        for _ in range(num_simulations):
            # Add random noise to prices (bootstrap approach)
            noisy_data = data.copy()
            price_noise = np.random.normal(0, 0.005, len(data))  # 0.5% noise
            
            for col in ['open', 'high', 'low', 'close']:
                noisy_data[col] *= (1 + price_noise)
            
            # Run backtest on noisy data
            result = self.run_backtest(noisy_data, signals, f"simulation_{len(simulation_results)}")
            simulation_results.append(result)
        
        # Aggregate simulation results
        returns = [r['total_return'] for r in simulation_results]
        sharpe_ratios = [r['sharpe_ratio'] for r in simulation_results if not np.isnan(r['sharpe_ratio'])]
        max_drawdowns = [r['max_drawdown'] for r in simulation_results]
        
        return {
            'num_simulations': num_simulations,
            'return_stats': {
                'mean': np.mean(returns),
                'std': np.std(returns),
                'min': np.min(returns),
                'max': np.max(returns),
                'percentiles': {
                    '5': np.percentile(returns, 5),
                    '25': np.percentile(returns, 25),
                    '50': np.percentile(returns, 50),
                    '75': np.percentile(returns, 75),
                    '95': np.percentile(returns, 95)
                }
            },
            'sharpe_stats': {
                'mean': np.mean(sharpe_ratios) if sharpe_ratios else 0,
                'std': np.std(sharpe_ratios) if sharpe_ratios else 0
            },
            'drawdown_stats': {
                'mean': np.mean(max_drawdowns),
                'std': np.std(max_drawdowns),
                'max': np.max(max_drawdowns)
            },
            'probability_of_profit': sum(1 for r in returns if r > 0) / len(returns)
        }
    
    def _open_position(self, signal: int, price: float, timestamp: datetime, 
                      available_capital: float) -> Dict:
        """Open a new position."""
        position_value = available_capital * self.position_size
        
        if signal > 0:  # Long position
            shares = position_value / (price * (1 + self.slippage + self.commission))
            cost_basis = shares * price * (1 + self.slippage + self.commission)
            side = 'long'
        else:  # Short position  
            shares = position_value / (price * (1 - self.slippage + self.commission))
            cost_basis = shares * price * (1 - self.slippage + self.commission)
            side = 'short'
        
        return {
            'side': side,
            'shares': shares,
            'entry_price': price,
            'entry_time': timestamp,
            'cost_basis': cost_basis,
            'stop_loss_price': price * (1 - self.stop_loss) if side == 'long' else price * (1 + self.stop_loss),
            'take_profit_price': price * (1 + self.take_profit) if side == 'long' else price * (1 - self.take_profit)
        }
    
    def _close_position(self, position: Dict, price: float, timestamp: datetime, 
                       reason: str) -> Dict:
        """Close an existing position."""
        if position['side'] == 'long':
            gross_proceeds = position['shares'] * price
            net_proceeds = gross_proceeds * (1 - self.slippage - self.commission)
            pnl = net_proceeds - position['cost_basis']
        else:  # short position
            gross_cost = position['shares'] * price
            net_cost = gross_cost * (1 + self.slippage + self.commission)
            pnl = position['cost_basis'] - net_cost
        
        holding_period = (timestamp - position['entry_time']).total_seconds() / 60  # minutes
        
        return {
            'entry_time': position['entry_time'],
            'exit_time': timestamp,
            'side': position['side'],
            'shares': position['shares'],
            'entry_price': position['entry_price'],
            'exit_price': price,
            'cost_basis': position['cost_basis'],
            'gross_proceeds': gross_proceeds if position['side'] == 'long' else position['cost_basis'],
            'pnl': pnl,
            'return_pct': pnl / position['cost_basis'],
            'holding_period_minutes': holding_period,
            'exit_reason': reason
        }
    
    def _check_exit_conditions(self, position: Dict, current_price: float, 
                             current_time: datetime, current_signal: int) -> Tuple[bool, str]:
        """Check if position should be exited."""
        
        # Check holding period limit
        holding_period = (current_time - position['entry_time']).total_seconds() / 60
        if holding_period >= self.max_holding_period:
            return True, 'max_holding_period'
        
        # Check stop loss
        if position['side'] == 'long':
            if current_price <= position['stop_loss_price']:
                return True, 'stop_loss'
            if current_price >= position['take_profit_price']:
                return True, 'take_profit'
        else:  # short position
            if current_price >= position['stop_loss_price']:
                return True, 'stop_loss'
            if current_price <= position['take_profit_price']:
                return True, 'take_profit'
        
        # Check for opposing signal
        if position['side'] == 'long' and current_signal < 0:
            return True, 'opposing_signal'
        elif position['side'] == 'short' and current_signal > 0:
            return True, 'opposing_signal'
        
        return False, ''
    
    def _calculate_performance_metrics(self, strategy_name: str) -> Dict:
        """Calculate comprehensive performance metrics."""
        if not self.trades:
            return self._empty_performance_metrics(strategy_name)
        
        # Basic trade statistics
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        total_return = total_pnl / self.initial_capital
        
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        # Calculate Sharpe ratio
        if len(self.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.equity_curve)):
                prev_equity = self.equity_curve[i-1]['equity']
                curr_equity = self.equity_curve[i]['equity']
                returns.append((curr_equity - prev_equity) / prev_equity)
            
            if returns and np.std(returns) > 0:
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        # Maximum drawdown
        max_drawdown = max([d['drawdown'] for d in self.drawdown_curve]) if self.drawdown_curve else 0
        
        # Average holding period
        avg_holding_period = np.mean([t['holding_period_minutes'] for t in self.trades])
        
        # Exit reason distribution
        exit_reasons = {}
        for trade in self.trades:
            reason = trade['exit_reason']
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        return {
            'strategy_name': strategy_name,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_return': total_return,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'avg_holding_period_minutes': avg_holding_period,
            'exit_reason_distribution': exit_reasons,
            'final_equity': self.equity_curve[-1]['equity'] if self.equity_curve else self.initial_capital
        }
    
    def _empty_performance_metrics(self, strategy_name: str) -> Dict:
        """Return empty performance metrics structure."""
        return {
            'strategy_name': strategy_name,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_return': 0.0,
            'total_pnl': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'avg_holding_period_minutes': 0.0,
            'exit_reason_distribution': {},
            'final_equity': self.initial_capital
        }


class TestAutomatedBacktesting:
    """Test suite for automated backtesting framework."""
    
    def test_basic_backtest_execution(self, epic1_config):
        """Test basic backtest execution with simple data."""
        engine = BacktestingEngine({
            'initial_capital': 10000,
            'commission': 0.005,
            'slippage': 0.001,
            'position_size': 0.1
        })
        
        # Create simple test data
        dates = pd.date_range('2024-01-01', periods=100, freq='5min')
        test_data = pd.DataFrame({
            'open': [150] * 100,
            'high': [151] * 100,
            'low': [149] * 100,
            'close': [150 + i * 0.1 for i in range(100)],  # Gradual uptrend
            'volume': [20000] * 100
        }, index=dates)
        
        # Create simple signals (buy at start, sell at end)
        signals = pd.Series([0] * 100, index=dates)
        signals.iloc[10] = 1   # Buy signal
        signals.iloc[50] = -1  # Sell signal
        
        # Run backtest
        result = engine.run_backtest(test_data, signals, "Test Strategy")
        
        # Verify results structure
        assert 'strategy_name' in result
        assert 'total_trades' in result
        assert 'win_rate' in result
        assert 'total_return' in result
        assert 'sharpe_ratio' in result
        assert 'max_drawdown' in result
        
        # Should have generated at least one trade
        assert result['total_trades'] >= 1
        
        # Should have positive return for uptrending data
        assert result['total_return'] > 0
    
    def test_legacy_vs_enhanced_comparison(self, epic1_config):
        """Test comparison between legacy and enhanced StochRSI."""
        engine = BacktestingEngine({
            'initial_capital': 10000,
            'commission': 0.005,
            'position_size': 0.1
        })
        
        # Generate realistic test data
        test_data = TestDataGenerator.create_multi_signal_scenario(
            num_buy_signals=8, 
            num_sell_signals=6
        )
        
        # Create legacy StochRSI indicator
        legacy_indicator = StochRSIIndicator(
            rsi_length=14,
            stoch_length=14,
            k_smoothing=3,
            d_smoothing=3
        )
        
        # Generate legacy signals
        legacy_indicators = legacy_indicator.calculate_full_stoch_rsi(test_data['close'])
        legacy_signal_data = legacy_indicator.generate_signals(
            legacy_indicators['StochRSI_K'],
            legacy_indicators['StochRSI_D']
        )
        legacy_signals = legacy_signal_data['signals']
        
        # Create enhanced signals (simulate with volume confirmation)
        enhanced_signals = legacy_signals.copy()
        
        # Simulate volume confirmation filter (remove signals with low volume)
        avg_volume = test_data['volume'].rolling(20).mean()
        volume_threshold = avg_volume * 1.5
        
        for i in range(len(enhanced_signals)):
            if enhanced_signals.iloc[i] != 0:
                if test_data['volume'].iloc[i] < volume_threshold.iloc[i]:
                    enhanced_signals.iloc[i] = 0  # Filter out low volume signal
        
        # Compare strategies
        strategy_results = {
            'Legacy StochRSI': legacy_signals,
            'Enhanced StochRSI': enhanced_signals
        }
        
        comparison = engine.compare_strategies(test_data, strategy_results)
        
        # Verify comparison structure
        assert 'Legacy StochRSI' in comparison
        assert 'Enhanced StochRSI' in comparison
        
        legacy_result = comparison['Legacy StochRSI']
        enhanced_result = comparison['Enhanced StochRSI']
        
        # Enhanced version should have fewer trades (due to filtering)
        assert enhanced_result['total_trades'] <= legacy_result['total_trades']
        
        # Enhanced version should have improvement metrics
        assert 'relative_return' in enhanced_result
        assert 'return_improvement' in enhanced_result
    
    def test_monte_carlo_simulation(self, epic1_config):
        """Test Monte Carlo simulation for strategy robustness."""
        engine = BacktestingEngine({
            'initial_capital': 10000,
            'commission': 0.005,
            'position_size': 0.1
        })
        
        # Generate test data
        np.random.seed(42)  # For reproducible results
        dates = pd.date_range('2024-01-01', periods=200, freq='5min')
        test_data = pd.DataFrame({
            'open': [150] * 200,
            'high': [151] * 200,
            'low': [149] * 200,
            'close': [150 + np.random.normal(0, 2) for _ in range(200)],
            'volume': [20000] * 200
        }, index=dates)
        
        # Simple signal pattern
        signals = pd.Series([0] * 200, index=dates)
        for i in range(0, 200, 50):  # Signal every 50 periods
            if i < 190:
                signals.iloc[i] = 1 if i % 100 == 0 else -1
        
        # Run Monte Carlo simulation (small number for testing)
        mc_result = engine.run_monte_carlo_simulation(
            test_data, signals, num_simulations=50
        )
        
        # Verify results structure
        assert 'num_simulations' in mc_result
        assert 'return_stats' in mc_result
        assert 'sharpe_stats' in mc_result
        assert 'drawdown_stats' in mc_result
        assert 'probability_of_profit' in mc_result
        
        # Verify statistics structure
        return_stats = mc_result['return_stats']
        assert 'mean' in return_stats
        assert 'std' in return_stats
        assert 'percentiles' in return_stats
        
        # Verify percentiles
        percentiles = return_stats['percentiles']
        assert '5' in percentiles
        assert '50' in percentiles
        assert '95' in percentiles
        
        # Probability should be between 0 and 1
        assert 0 <= mc_result['probability_of_profit'] <= 1
    
    def test_historical_scenario_validation(self, epic1_config, backtesting_scenarios):
        """Test backtesting against predefined historical scenarios."""
        engine = BacktestingEngine({
            'initial_capital': 10000,
            'commission': 0.005,
            'position_size': 0.1
        })
        
        for scenario_name, scenario_config in backtesting_scenarios.items():
            # Generate data for scenario
            if scenario_config['market_condition'] == 'bull':
                # Bull market: generally uptrending with volatility
                base_price = 150
                trend = 0.0008  # 0.08% per period
                volatility = 0.015
            elif scenario_config['market_condition'] == 'bear':
                # Bear market: generally downtrending
                base_price = 150
                trend = -0.0005  # -0.05% per period
                volatility = 0.020
            elif scenario_config['market_condition'] == 'sideways':
                # Sideways market: no clear trend
                base_price = 150
                trend = 0.0
                volatility = 0.010
            else:  # volatile
                # Volatile market: high volatility, no clear trend
                base_price = 150
                trend = 0.0
                volatility = 0.030
            
            # Generate scenario data
            periods = 500
            dates = pd.date_range('2024-01-01', periods=periods, freq='5min')
            
            prices = [base_price]
            for i in range(periods - 1):
                change = trend + np.random.normal(0, volatility)
                prices.append(prices[-1] * (1 + change))
            
            scenario_data = pd.DataFrame({
                'open': prices[:-1] + [prices[-1]],
                'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
                'close': prices,
                'volume': [np.random.randint(15000, 25000) for _ in range(periods)]
            }, index=dates)
            
            # Generate signals using enhanced StochRSI
            indicator = StochRSIIndicator()
            indicators = indicator.calculate_full_stoch_rsi(scenario_data['close'])
            signal_data = indicator.generate_signals(
                indicators['StochRSI_K'],
                indicators['StochRSI_D']
            )
            
            # Run backtest
            result = engine.run_backtest(scenario_data, signal_data['signals'], scenario_name)
            
            # Validate against expected metrics
            expected_signals = scenario_config['expected_signals']
            expected_accuracy = scenario_config['expected_accuracy']
            
            # Signal count should be in reasonable range
            assert abs(result['total_trades'] - expected_signals) / expected_signals < 0.5
            
            # Accuracy should be in reasonable range for market condition
            if result['total_trades'] > 0:
                if scenario_config['market_condition'] == 'bull':
                    # Bull market should have decent performance
                    assert result['win_rate'] >= 0.4
                elif scenario_config['market_condition'] == 'volatile':
                    # Volatile market should have lower performance
                    assert result['win_rate'] >= 0.2
    
    def test_feature_impact_analysis(self, epic1_config):
        """Test analysis of individual Epic 1 feature impacts."""
        engine = BacktestingEngine({
            'initial_capital': 10000,
            'commission': 0.005,
            'position_size': 0.1
        })
        
        # Generate test data with deliberate volume patterns
        test_data = TestDataGenerator.create_multi_signal_scenario(
            num_buy_signals=6,
            num_sell_signals=4
        )
        
        # Generate base signals
        indicator = StochRSIIndicator()
        indicators = indicator.calculate_full_stoch_rsi(test_data['close'])
        base_signals = indicator.generate_signals(
            indicators['StochRSI_K'],
            indicators['StochRSI_D']
        )['signals']
        
        # Test different feature combinations
        features_to_test = {
            'Base StochRSI': base_signals,
            'With Volume Filter': self._apply_volume_filter(base_signals, test_data),
            'With Dynamic Bands': self._apply_dynamic_bands(base_signals, test_data),
            'All Features': self._apply_all_features(base_signals, test_data)
        }
        
        # Run comparison
        feature_comparison = engine.compare_strategies(test_data, features_to_test)
        
        # Analyze feature impacts
        base_performance = feature_comparison['Base StochRSI']
        
        for feature_name, result in feature_comparison.items():
            if feature_name != 'Base StochRSI':
                # Each feature should have some measurable impact
                assert 'relative_return' in result
                
                # Volume filter should reduce false signals
                if 'Volume' in feature_name:
                    assert result['total_trades'] <= base_performance['total_trades']
                
                # All features combined should show some improvement
                if feature_name == 'All Features':
                    # Should either improve return or reduce drawdown
                    improvement = (result['total_return'] > base_performance['total_return'] or
                                 result['max_drawdown'] < base_performance['max_drawdown'])
                    assert improvement, "All features should provide some improvement"
    
    def test_statistical_significance(self, epic1_config):
        """Test statistical significance of performance improvements."""
        engine = BacktestingEngine({
            'initial_capital': 10000,
            'commission': 0.005,
            'position_size': 0.1
        })
        
        # Generate multiple datasets for statistical testing
        num_tests = 20
        results = {'legacy': [], 'enhanced': []}
        
        for test_run in range(num_tests):
            np.random.seed(test_run)  # Different seed for each test
            
            # Generate test data
            test_data = TestDataGenerator.create_multi_signal_scenario(
                num_buy_signals=5,
                num_sell_signals=5
            )
            
            # Generate signals
            indicator = StochRSIIndicator()
            indicators = indicator.calculate_full_stoch_rsi(test_data['close'])
            legacy_signals = indicator.generate_signals(
                indicators['StochRSI_K'],
                indicators['StochRSI_D']
            )['signals']
            
            # Enhanced signals with volume filter
            enhanced_signals = self._apply_volume_filter(legacy_signals, test_data)
            
            # Run backtests
            legacy_result = engine.run_backtest(test_data, legacy_signals, f"Legacy_{test_run}")
            enhanced_result = engine.run_backtest(test_data, enhanced_signals, f"Enhanced_{test_run}")
            
            results['legacy'].append(legacy_result['total_return'])
            results['enhanced'].append(enhanced_result['total_return'])
        
        # Perform statistical tests
        from scipy import stats
        
        # T-test for difference in means
        legacy_returns = results['legacy']
        enhanced_returns = results['enhanced']
        
        if len(legacy_returns) > 1 and len(enhanced_returns) > 1:
            t_stat, p_value = stats.ttest_rel(enhanced_returns, legacy_returns)
            
            # Calculate effect size (Cohen's d)
            pooled_std = np.sqrt((np.var(legacy_returns) + np.var(enhanced_returns)) / 2)
            cohens_d = (np.mean(enhanced_returns) - np.mean(legacy_returns)) / pooled_std if pooled_std > 0 else 0
            
            # Results should show some statistical properties
            assert isinstance(p_value, float)
            assert isinstance(cohens_d, float)
            
            # Log the results for analysis
            print(f"Statistical Test Results:")
            print(f"P-value: {p_value:.4f}")
            print(f"Cohen's d: {cohens_d:.4f}")
            print(f"Mean Legacy Return: {np.mean(legacy_returns):.4f}")
            print(f"Mean Enhanced Return: {np.mean(enhanced_returns):.4f}")
    
    def test_performance_under_stress(self, epic1_config):
        """Test performance under stress conditions."""
        engine = BacktestingEngine({
            'initial_capital': 10000,
            'commission': 0.01,  # Higher commission
            'slippage': 0.005,   # Higher slippage
            'position_size': 0.2  # Larger position size
        })
        
        # Create stress test scenarios
        stress_scenarios = {
            'high_volatility': {
                'volatility': 0.05,  # 5% volatility
                'trend': 0.0
            },
            'strong_downtrend': {
                'volatility': 0.02,
                'trend': -0.002  # -0.2% per period
            },
            'low_liquidity': {
                'volatility': 0.015,
                'trend': 0.0,
                'volume_factor': 0.3  # 30% of normal volume
            }
        }
        
        stress_results = {}
        
        for scenario_name, scenario_params in stress_scenarios.items():
            # Generate stress test data
            periods = 300
            dates = pd.date_range('2024-01-01', periods=periods, freq='5min')
            
            base_price = 150
            prices = [base_price]
            
            for i in range(periods - 1):
                change = scenario_params['trend'] + np.random.normal(0, scenario_params['volatility'])
                prices.append(prices[-1] * (1 + change))
            
            volume_factor = scenario_params.get('volume_factor', 1.0)
            
            stress_data = pd.DataFrame({
                'open': prices[:-1] + [prices[-1]],
                'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
                'close': prices,
                'volume': [int(np.random.randint(15000, 25000) * volume_factor) for _ in range(periods)]
            }, index=dates)
            
            # Generate enhanced signals
            indicator = StochRSIIndicator()
            indicators = indicator.calculate_full_stoch_rsi(stress_data['close'])
            signals = indicator.generate_signals(
                indicators['StochRSI_K'],
                indicators['StochRSI_D']
            )['signals']
            
            # Apply enhancements
            enhanced_signals = self._apply_all_features(signals, stress_data)
            
            # Run stress test
            result = engine.run_backtest(stress_data, enhanced_signals, scenario_name)
            stress_results[scenario_name] = result
            
            # Stress tests should complete without errors
            assert 'total_return' in result
            assert 'max_drawdown' in result
            
            # Maximum drawdown should be reasonable even under stress
            assert result['max_drawdown'] < 0.8  # Less than 80% drawdown
    
    def _apply_volume_filter(self, signals: pd.Series, data: pd.DataFrame) -> pd.Series:
        """Apply volume confirmation filter to signals."""
        filtered_signals = signals.copy()
        avg_volume = data['volume'].rolling(20).mean()
        volume_threshold = avg_volume * 1.5
        
        for i in range(len(signals)):
            if signals.iloc[i] != 0:
                if data['volume'].iloc[i] < volume_threshold.iloc[i]:
                    filtered_signals.iloc[i] = 0
        
        return filtered_signals
    
    def _apply_dynamic_bands(self, signals: pd.Series, data: pd.DataFrame) -> pd.Series:
        """Apply dynamic band adjustment to signals."""
        # Simplified dynamic bands: adjust based on volatility
        adjusted_signals = signals.copy()
        returns = data['close'].pct_change()
        volatility = returns.rolling(20).std()
        
        # In high volatility, be more selective (reduce signal strength)
        high_vol_threshold = volatility.quantile(0.8)
        
        for i in range(len(signals)):
            if signals.iloc[i] != 0 and volatility.iloc[i] > high_vol_threshold.iloc[i]:
                # Reduce signal frequency in high volatility
                if np.random.random() < 0.5:  # 50% chance to filter out
                    adjusted_signals.iloc[i] = 0
        
        return adjusted_signals
    
    def _apply_all_features(self, signals: pd.Series, data: pd.DataFrame) -> pd.Series:
        """Apply all Epic 1 features to signals."""
        # Apply volume filter first
        volume_filtered = self._apply_volume_filter(signals, data)
        
        # Then apply dynamic bands
        fully_enhanced = self._apply_dynamic_bands(volume_filtered, data)
        
        return fully_enhanced