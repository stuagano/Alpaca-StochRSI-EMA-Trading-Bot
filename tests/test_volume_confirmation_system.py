"""
Comprehensive Test Suite for Volume Confirmation System

Tests all components of the volume confirmation filter system including:
- Volume analysis calculations
- Signal confirmation logic
- Performance tracking
- Dashboard data generation
- Integration with trading strategies

Author: Trading Bot System
Version: 1.0.0
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.volume_analysis import VolumeAnalyzer, VolumeConfirmationResult, VolumeProfileLevel
from strategies.enhanced_stoch_rsi_strategy import EnhancedStochRSIStrategy
from strategies.ma_crossover_strategy import MACrossoverStrategy
from backtesting.enhanced_backtesting_engine import EnhancedBacktestingEngine, run_volume_backtest
from config.config import Config, VolumeConfirmation


class TestVolumeAnalyzer(unittest.TestCase):
    """Test the VolumeAnalyzer core functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = Mock()
        self.config.volume_period = 20
        self.config.relative_volume_period = 50
        self.config.volume_confirmation_threshold = 1.2
        self.config.min_volume_ratio = 1.0
        self.config.profile_periods = 100
        
        self.analyzer = VolumeAnalyzer(self.config)
        
        # Create sample market data
        dates = pd.date_range(start='2023-01-01', periods=100, freq='1H')
        np.random.seed(42)  # For reproducible tests
        
        self.sample_data = pd.DataFrame({
            'open': np.random.normal(100, 5, 100),
            'high': np.random.normal(102, 5, 100),
            'low': np.random.normal(98, 5, 100),
            'close': np.random.normal(100, 5, 100),
            'volume': np.random.normal(1000000, 200000, 100),
            'timestamp': dates
        }, index=dates)
        
        # Ensure volume is positive
        self.sample_data['volume'] = np.abs(self.sample_data['volume'])
        
        # Ensure high >= low and close between low and high
        self.sample_data['high'] = np.maximum(self.sample_data['high'], self.sample_data['low'])
        self.sample_data['close'] = np.clip(
            self.sample_data['close'], 
            self.sample_data['low'], 
            self.sample_data['high']
        )
    
    def test_volume_moving_average_calculation(self):
        """Test volume moving average calculation"""
        result_df = self.analyzer.calculate_volume_moving_average(self.sample_data)
        
        # Check that required columns are added
        self.assertIn('volume_ma', result_df.columns)
        self.assertIn('volume_ratio', result_df.columns)
        self.assertIn('volume_trend', result_df.columns)
        
        # Check that volume MA is calculated correctly for last few periods
        last_20_volume = self.sample_data['volume'].tail(20).mean()
        calculated_ma = result_df['volume_ma'].iloc[-1]
        self.assertAlmostEqual(calculated_ma, last_20_volume, places=2)
        
        # Check volume ratio calculation
        expected_ratio = self.sample_data['volume'].iloc[-1] / calculated_ma
        calculated_ratio = result_df['volume_ratio'].iloc[-1]
        self.assertAlmostEqual(calculated_ratio, expected_ratio, places=2)
        
        # Check volume trend categories
        trend_values = result_df['volume_trend'].dropna().unique()
        valid_trends = {'high', 'normal', 'low'}
        self.assertTrue(all(trend in valid_trends for trend in trend_values))
    
    def test_relative_volume_calculation(self):
        """Test relative volume calculation"""
        result_df = self.analyzer.calculate_relative_volume(self.sample_data)
        
        # Check that required columns are added
        self.assertIn('relative_volume', result_df.columns)
        self.assertIn('rel_vol_strength', result_df.columns)
        
        # Check that relative volume values are reasonable
        rel_vol_values = result_df['relative_volume'].dropna()
        self.assertTrue(all(rel_vol_values >= 0))
        self.assertTrue(any(rel_vol_values > 0))  # Should have some non-zero values
    
    def test_volume_profile_analysis(self):
        """Test volume profile analysis for support/resistance levels"""
        profile_levels = self.analyzer.analyze_volume_profile(self.sample_data, lookback_periods=50)
        
        # Should return a list of VolumeProfileLevel objects
        self.assertIsInstance(profile_levels, list)
        
        if profile_levels:  # If levels were found
            for level in profile_levels:
                self.assertIsInstance(level, VolumeProfileLevel)
                self.assertIn(level.level_type, ['support', 'resistance'])
                self.assertGreaterEqual(level.strength, 0)
                self.assertLessEqual(level.strength, 1)
                self.assertGreater(level.volume, 0)
    
    def test_signal_confirmation_buy_signal(self):
        """Test volume confirmation for buy signals"""
        # Test with high volume (should confirm)
        high_volume_data = self.sample_data.copy()
        high_volume_data.loc[high_volume_data.index[-1], 'volume'] *= 2  # Double the last volume
        
        result = self.analyzer.confirm_signal_with_volume(high_volume_data, 1)
        
        self.assertIsInstance(result, VolumeConfirmationResult)
        self.assertIsInstance(result.is_confirmed, bool)
        self.assertGreaterEqual(result.volume_ratio, 0)
        self.assertGreaterEqual(result.relative_volume, 0)
        self.assertIn(result.volume_trend, ['high', 'normal', 'low', 'unknown'])
        self.assertGreaterEqual(result.confirmation_strength, 0)
        self.assertLessEqual(result.confirmation_strength, 1)
    
    def test_signal_confirmation_no_signal(self):
        """Test volume confirmation with no signal"""
        result = self.analyzer.confirm_signal_with_volume(self.sample_data, 0)
        
        self.assertFalse(result.is_confirmed)
        self.assertEqual(result.volume_ratio, 0.0)
        self.assertEqual(result.relative_volume, 0.0)
        self.assertEqual(result.volume_trend, 'none')
        self.assertEqual(result.confirmation_strength, 0.0)
    
    def test_dashboard_data_generation(self):
        """Test dashboard data generation"""
        dashboard_data = self.analyzer.get_volume_dashboard_data(self.sample_data)
        
        # Check required keys are present
        required_keys = [
            'current_volume', 'volume_ma', 'volume_ratio', 'relative_volume',
            'volume_trend', 'volume_strength', 'confirmation_threshold',
            'profile_levels', 'volume_confirmed'
        ]
        
        for key in required_keys:
            self.assertIn(key, dashboard_data)
        
        # Check data types and ranges
        self.assertIsInstance(dashboard_data['current_volume'], int)
        self.assertIsInstance(dashboard_data['volume_confirmed'], bool)
        self.assertGreaterEqual(dashboard_data['volume_ratio'], 0)
        self.assertIn('support', dashboard_data['profile_levels'])
        self.assertIn('resistance', dashboard_data['profile_levels'])


class TestVolumeConfirmationIntegration(unittest.TestCase):
    """Test integration with trading strategies"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock configuration
        self.config = Mock()
        
        # Volume confirmation config
        volume_config = Mock()
        volume_config.enabled = True
        volume_config.volume_period = 20
        volume_config.volume_confirmation_threshold = 1.2
        volume_config.min_volume_ratio = 1.0
        volume_config.require_volume_confirmation = True
        
        self.config.volume_confirmation = volume_config
        
        # Strategy-specific configs
        stoch_rsi_config = Mock()
        stoch_rsi_config.enabled = True
        stoch_rsi_config.lower_band = 20
        stoch_rsi_config.upper_band = 80
        
        ema_config = Mock()
        ema_config.enabled = True
        ema_config.fast_period = 12
        ema_config.slow_period = 26
        
        indicators_config = Mock()
        indicators_config.stochRSI = stoch_rsi_config
        indicators_config.EMA = ema_config
        
        self.config.indicators = indicators_config
        self.config.candle_lookback_period = 2
        
        # Create sample data
        dates = pd.date_range(start='2023-01-01', periods=100, freq='1H')
        np.random.seed(42)
        
        self.sample_data = pd.DataFrame({
            'open': np.random.normal(100, 2, 100),
            'high': np.random.normal(102, 2, 100),
            'low': np.random.normal(98, 2, 100),
            'close': np.random.normal(100, 2, 100),
            'volume': np.random.normal(1000000, 200000, 100)
        }, index=dates)
        
        # Ensure data consistency
        self.sample_data['volume'] = np.abs(self.sample_data['volume'])
        self.sample_data['high'] = np.maximum(self.sample_data['high'], self.sample_data['low'])
        self.sample_data['close'] = np.clip(
            self.sample_data['close'], 
            self.sample_data['low'], 
            self.sample_data['high']
        )
    
    @patch('indicators.volume_analysis.get_volume_analyzer')
    def test_stoch_rsi_strategy_with_volume_confirmation(self, mock_get_analyzer):
        """Test StochRSI strategy with volume confirmation"""
        # Mock volume analyzer
        mock_analyzer = Mock()
        mock_volume_result = Mock()
        mock_volume_result.is_confirmed = True
        mock_volume_result.volume_ratio = 1.5
        mock_volume_result.relative_volume = 1.3
        mock_volume_result.confirmation_strength = 0.8
        
        mock_analyzer.confirm_signal_with_volume.return_value = mock_volume_result
        mock_get_analyzer.return_value = mock_analyzer
        
        # Create strategy instance
        strategy = EnhancedStochRSIStrategy(self.config)
        
        # Test signal generation (will depend on actual indicator calculations)
        signal = strategy.generate_signal(self.sample_data)
        
        # Verify that the strategy was initialized with volume confirmation
        self.assertTrue(hasattr(strategy, 'volume_analyzer'))
        self.assertTrue(hasattr(strategy, 'require_volume_confirmation'))
    
    @patch('indicators.volume_analysis.get_volume_analyzer')
    def test_ma_crossover_strategy_with_volume_confirmation(self, mock_get_analyzer):
        """Test MA Crossover strategy with volume confirmation"""
        # Mock volume analyzer
        mock_analyzer = Mock()
        mock_volume_result = Mock()
        mock_volume_result.is_confirmed = True
        mock_volume_result.volume_ratio = 1.4
        mock_volume_result.relative_volume = 1.2
        mock_volume_result.confirmation_strength = 0.7
        
        mock_analyzer.confirm_signal_with_volume.return_value = mock_volume_result
        mock_get_analyzer.return_value = mock_analyzer
        
        # Create strategy instance
        strategy = MACrossoverStrategy(self.config)
        
        # Test signal generation
        signal = strategy.generate_signal(self.sample_data)
        
        # Verify that the strategy was initialized with volume confirmation
        self.assertTrue(hasattr(strategy, 'volume_analyzer'))
        self.assertTrue(hasattr(strategy, 'require_volume_confirmation'))


class TestEnhancedBacktestingEngine(unittest.TestCase):
    """Test the enhanced backtesting engine with volume confirmation"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock strategy
        self.mock_strategy = Mock()
        self.mock_strategy.generate_signal.side_effect = self._mock_signal_generator
        
        # Create mock config
        self.config = Mock()
        volume_config = Mock()
        volume_config.enabled = True
        volume_config.volume_period = 20
        volume_config.volume_confirmation_threshold = 1.2
        self.config.volume_confirmation = volume_config
        
        # Mock data manager
        self.sample_data = pd.DataFrame({
            'Open': [100, 101, 102, 103, 104],
            'High': [101, 102, 103, 104, 105],
            'Low': [99, 100, 101, 102, 103],
            'Close': [100.5, 101.5, 102.5, 103.5, 104.5],
            'Volume': [1000000, 1200000, 800000, 1500000, 900000]
        }, index=pd.date_range('2023-01-01', periods=5, freq='1D'))
    
    def _mock_signal_generator(self, df):
        """Mock signal generator that alternates between buy and sell"""
        if len(df) <= 2:
            return 0
        elif len(df) == 3:
            return 1  # Buy signal
        elif len(df) == 4:
            return 0  # No signal
        else:
            return -1  # Sell signal
    
    @patch('backtesting.enhanced_backtesting_engine.get_data_manager')
    @patch('indicators.volume_analysis.get_volume_analyzer')
    def test_backtest_engine_initialization(self, mock_get_analyzer, mock_get_data_manager):
        """Test backtesting engine initialization"""
        # Mock data manager
        mock_data_manager = Mock()
        mock_data_manager.get_historical_data.return_value = self.sample_data
        mock_get_data_manager.return_value = mock_data_manager
        
        # Mock volume analyzer
        mock_analyzer = Mock()
        mock_get_analyzer.return_value = mock_analyzer
        
        # Create engine
        engine = EnhancedBacktestingEngine(
            self.mock_strategy, 'AAPL', '2023-01-01', '2023-01-31', self.config
        )
        
        # Verify initialization
        self.assertEqual(engine.symbol, 'AAPL')
        self.assertEqual(engine.cash, 100000)
        self.assertIsNotNone(engine.volume_analyzer)
        self.assertIn('total_signals', engine.volume_stats)
    
    @patch('backtesting.enhanced_backtesting_engine.get_data_manager')
    @patch('indicators.volume_analysis.get_volume_analyzer')
    def test_backtest_run_with_volume_confirmation(self, mock_get_analyzer, mock_get_data_manager):
        """Test running backtest with volume confirmation"""
        # Mock data manager
        mock_data_manager = Mock()
        mock_data_manager.get_historical_data.return_value = self.sample_data
        mock_get_data_manager.return_value = mock_data_manager
        
        # Mock volume analyzer
        mock_analyzer = Mock()
        mock_volume_result = Mock()
        mock_volume_result.is_confirmed = True
        mock_volume_result.volume_ratio = 1.5
        mock_volume_result.relative_volume = 1.3
        mock_volume_result.volume_trend = 'high'
        mock_volume_result.confirmation_strength = 0.8
        mock_volume_result.profile_levels = {}
        
        mock_analyzer.confirm_signal_with_volume.return_value = mock_volume_result
        mock_get_analyzer.return_value = mock_analyzer
        
        # Create and run engine
        engine = EnhancedBacktestingEngine(
            self.mock_strategy, 'AAPL', '2023-01-01', '2023-01-31', self.config
        )
        
        results = engine.run()
        
        # Verify results structure
        self.assertIsNotNone(results)
        self.assertIn('trades', results.__dict__)
        self.assertIn('portfolio_value', results.__dict__)
        self.assertIn('performance_metrics', results.__dict__)
        self.assertIn('volume_analysis', results.__dict__)
        
        # Verify volume statistics are tracked
        volume_stats = results.volume_stats
        self.assertIn('total_signals', volume_stats)
        self.assertIn('volume_confirmed_signals', volume_stats)
        self.assertIn('volume_rejected_signals', volume_stats)


class TestVolumeConfirmationPerformance(unittest.TestCase):
    """Test volume confirmation performance tracking and analysis"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create sample trade data
        self.trades_data = pd.DataFrame({
            'entry_date': pd.date_range('2023-01-01', periods=10, freq='1D'),
            'exit_date': pd.date_range('2023-01-02', periods=10, freq='1D'),
            'profit': [100, -50, 200, -30, 150, -80, 300, -20, 250, -100],
            'volume_confirmed': [True, False, True, False, True, False, True, False, True, False]
        })
        
        self.analyzer = VolumeAnalyzer()
    
    def test_performance_metrics_calculation(self):
        """Test calculation of volume confirmation performance metrics"""
        metrics = self.analyzer.calculate_volume_performance_metrics(self.trades_data)
        
        # Should return comprehensive metrics
        expected_keys = [
            'total_trades', 'confirmed_trades', 'non_confirmed_trades',
            'confirmation_rate', 'confirmed_win_rate', 'non_confirmed_win_rate',
            'false_signal_reduction'
        ]
        
        for key in expected_keys:
            self.assertIn(key, metrics)
        
        # Test specific calculations
        self.assertEqual(metrics['total_trades'], 10)
        self.assertEqual(metrics['confirmed_trades'], 5)
        self.assertEqual(metrics['non_confirmed_trades'], 5)
        self.assertEqual(metrics['confirmation_rate'], 0.5)
        
        # Test win rates
        confirmed_wins = sum(1 for i, row in self.trades_data.iterrows() 
                           if row['volume_confirmed'] and row['profit'] > 0)
        expected_confirmed_win_rate = confirmed_wins / 5
        self.assertEqual(metrics['confirmed_win_rate'], expected_confirmed_win_rate)
    
    def test_false_signal_reduction_calculation(self):
        """Test false signal reduction calculation"""
        metrics = self.analyzer.calculate_volume_performance_metrics(self.trades_data)
        
        # Calculate expected false signal reduction
        total_losing_trades = sum(1 for profit in self.trades_data['profit'] if profit <= 0)
        confirmed_losing_trades = sum(1 for i, row in self.trades_data.iterrows() 
                                    if row['volume_confirmed'] and row['profit'] <= 0)
        
        expected_reduction = (total_losing_trades - confirmed_losing_trades) / total_losing_trades
        
        self.assertAlmostEqual(metrics['false_signal_reduction'], expected_reduction, places=3)
        
        # Should be greater than 0 if volume confirmation is effective
        if confirmed_losing_trades < total_losing_trades:
            self.assertGreater(metrics['false_signal_reduction'], 0)


class TestVolumeConfirmationEdgeCases(unittest.TestCase):
    """Test edge cases and error handling in volume confirmation system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = VolumeAnalyzer()
    
    def test_empty_dataframe(self):
        """Test handling of empty dataframes"""
        empty_df = pd.DataFrame()
        
        # Should handle gracefully without errors
        result_ma = self.analyzer.calculate_volume_moving_average(empty_df)
        self.assertTrue(result_ma.empty)
        
        result_rel = self.analyzer.calculate_relative_volume(empty_df)
        self.assertTrue(result_rel.empty)
        
        profile_levels = self.analyzer.analyze_volume_profile(empty_df)
        self.assertEqual(len(profile_levels), 0)
    
    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        # Create dataframe with only 5 rows (less than volume_period)
        small_df = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'close': [100.5, 101.5, 102.5, 103.5, 104.5],
            'volume': [1000, 1200, 800, 1500, 900]
        })
        
        # Should handle gracefully
        result = self.analyzer.calculate_volume_moving_average(small_df)
        self.assertEqual(len(result), len(small_df))
        
        # Volume confirmation should still work
        confirmation_result = self.analyzer.confirm_signal_with_volume(small_df, 1)
        self.assertIsInstance(confirmation_result, VolumeConfirmationResult)
    
    def test_zero_volume_handling(self):
        """Test handling of zero volume data"""
        zero_volume_df = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [0, 0, 0]
        })
        
        # Should handle without crashing
        result = self.analyzer.confirm_signal_with_volume(zero_volume_df, 1)
        self.assertIsInstance(result, VolumeConfirmationResult)
        self.assertFalse(result.is_confirmed)  # Should not confirm with zero volume
    
    def test_invalid_signal_values(self):
        """Test handling of invalid signal values"""
        sample_df = pd.DataFrame({
            'volume': [1000, 1200, 1500, 1800, 2000]
        })
        
        # Test with invalid signal values
        for invalid_signal in [None, 'invalid', 1.5, []]:
            try:
                result = self.analyzer.confirm_signal_with_volume(sample_df, invalid_signal)
                # Should handle gracefully or return appropriate result
                self.assertIsInstance(result, VolumeConfirmationResult)
            except Exception as e:
                # If exception is raised, it should be handled appropriately
                self.assertIsInstance(e, (TypeError, ValueError))


def run_volume_confirmation_tests():
    """Run all volume confirmation tests"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestVolumeAnalyzer,
        TestVolumeConfirmationIntegration,
        TestEnhancedBacktestingEngine,
        TestVolumeConfirmationPerformance,
        TestVolumeConfirmationEdgeCases
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print("VOLUME CONFIRMATION SYSTEM TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"- {test}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"- {test}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_volume_confirmation_tests()
    exit(0 if success else 1)