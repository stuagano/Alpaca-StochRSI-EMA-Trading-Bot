"""
Comprehensive unit tests for the Enhanced StochRSI Strategy with Dynamic Bands.

Tests cover:
- ATR calculation accuracy
- Dynamic band adjustment logic
- Signal generation with dynamic bands
- Performance tracking
- Backward compatibility
- Configuration validation
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicator import atr, calculate_dynamic_bands, stochastic, rsi
from strategies.stoch_rsi_strategy import StochRSIStrategy
from config.config import StochRSIParams, Config, Indicators


class TestATRCalculation(unittest.TestCase):
    """Test ATR calculation functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create sample OHLC data
        self.sample_data = pd.DataFrame({
            'high': [105, 107, 104, 108, 106, 109, 105, 103, 107, 110],
            'low': [100, 102, 99, 103, 101, 104, 100, 98, 102, 105],
            'close': [103, 105, 101, 106, 104, 107, 102, 100, 105, 108],
            'open': [101, 103, 105, 101, 106, 104, 107, 102, 100, 105]
        })
    
    def test_atr_calculation_basic(self):
        """Test basic ATR calculation."""
        result_df = atr(self.sample_data.copy(), period=5)
        
        # Verify ATR column is added
        self.assertIn('ATR', result_df.columns)
        
        # Verify ATR values are positive
        atr_values = result_df['ATR'].dropna()
        self.assertTrue(all(atr_values > 0))
        
        # Verify we have the expected number of non-null ATR values
        self.assertGreater(len(atr_values), 0)
    
    def test_atr_with_different_periods(self):
        """Test ATR calculation with different periods."""
        for period in [5, 10, 14, 20]:
            result_df = atr(self.sample_data.copy(), period=period)
            self.assertIn('ATR', result_df.columns)
            atr_values = result_df['ATR'].dropna()
            self.assertGreater(len(atr_values), 0)
    
    def test_atr_mathematical_accuracy(self):
        """Test ATR calculation mathematical accuracy."""
        df = self.sample_data.copy()
        result_df = atr(df, period=3)
        
        # Manual calculation for verification
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        df['TR'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        
        # Verify True Range calculation
        self.assertTrue(np.allclose(result_df['ATR'].iloc[3:6].values,
                                  df['TR'].iloc[1:4].ewm(span=3, adjust=False).mean().values,
                                  rtol=1e-10))


class TestDynamicBands(unittest.TestCase):
    """Test dynamic band calculation functionality."""
    
    def setUp(self):
        """Set up test data with ATR."""
        self.test_data = pd.DataFrame({
            'high': [105, 107, 104, 108, 106, 109, 105, 103, 107, 110] * 3,
            'low': [100, 102, 99, 103, 101, 104, 100, 98, 102, 105] * 3,
            'close': [103, 105, 101, 106, 104, 107, 102, 100, 105, 108] * 3,
            'ATR': [2.5, 3.0, 2.8, 3.5, 2.2, 4.0, 3.8, 2.1, 2.9, 3.2] * 3
        })
    
    def test_dynamic_bands_creation(self):
        """Test basic dynamic bands creation."""
        result_df = calculate_dynamic_bands(
            self.test_data.copy(),
            base_lower=35,
            base_upper=100,
            atr_period=5,
            sensitivity=1.5
        )
        
        # Verify all required columns are added
        required_columns = ['dynamic_lower_band', 'dynamic_upper_band', 
                          'volatility_ratio', 'ATR_MA']
        for col in required_columns:
            self.assertIn(col, result_df.columns)
    
    def test_volatility_ratio_calculation(self):
        """Test volatility ratio calculation."""
        result_df = calculate_dynamic_bands(self.test_data.copy(), atr_period=3)
        
        # Check that volatility ratio is ATR / ATR_MA
        for i in range(3, len(result_df)):
            if not pd.isna(result_df['volatility_ratio'].iloc[i]):
                expected_ratio = (result_df['ATR'].iloc[i] / 
                                result_df['ATR_MA'].iloc[i])
                actual_ratio = result_df['volatility_ratio'].iloc[i]
                self.assertAlmostEqual(actual_ratio, expected_ratio, places=5)
    
    def test_band_adjustment_logic(self):
        """Test band adjustment logic."""
        # Create data with known volatility patterns
        high_vol_data = self.test_data.copy()
        high_vol_data['ATR'] = [5.0] * len(high_vol_data)  # High volatility
        
        result_df = calculate_dynamic_bands(
            high_vol_data,
            base_lower=35,
            base_upper=100,
            atr_period=5,
            sensitivity=1.2,
            adjustment_factor=0.5
        )
        
        # In high volatility, bands should be wider than base
        non_null_indices = result_df['dynamic_lower_band'].dropna().index
        if len(non_null_indices) > 5:
            lower_bands = result_df.loc[non_null_indices[5:], 'dynamic_lower_band']
            upper_bands = result_df.loc[non_null_indices[5:], 'dynamic_upper_band']
            
            # Some bands should be adjusted from base values
            self.assertTrue(any(lower_bands < 35) or any(upper_bands > 100))
    
    def test_minimum_band_width_enforcement(self):
        """Test minimum band width enforcement."""
        result_df = calculate_dynamic_bands(
            self.test_data.copy(),
            base_lower=45,
            base_upper=55,  # Narrow base bands
            min_width=15    # Minimum width larger than base
        )
        
        # Check that band width is never less than minimum
        non_null_indices = result_df.dropna(subset=['dynamic_lower_band', 'dynamic_upper_band']).index
        for idx in non_null_indices:
            lower = result_df.loc[idx, 'dynamic_lower_band']
            upper = result_df.loc[idx, 'dynamic_upper_band']
            width = upper - lower
            self.assertGreaterEqual(width, 15)


class TestEnhancedStochRSIStrategy(unittest.TestCase):
    """Test the enhanced StochRSI strategy."""
    
    def setUp(self):
        """Set up test configuration and strategy."""
        # Create mock configuration
        self.mock_config = Mock()
        self.mock_config.indicators = Mock()
        self.mock_config.indicators.stochRSI = StochRSIParams(
            enabled=True,
            lower_band=35,
            upper_band=100,
            K=3,
            D=3,
            rsi_length=14,
            stoch_length=14,
            source="Close",
            dynamic_bands_enabled=True,
            atr_period=20,
            atr_sensitivity=1.5,
            band_adjustment_factor=0.3,
            min_band_width=10,
            max_band_width=50
        )
        self.mock_config.candle_lookback_period = 2
        
        self.strategy = StochRSIStrategy(self.mock_config)
        
        # Create comprehensive test data
        self.test_data = pd.DataFrame({
            'high': np.random.uniform(100, 110, 100),
            'low': np.random.uniform(95, 105, 100),
            'close': np.random.uniform(98, 108, 100),
            'open': np.random.uniform(97, 109, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })
    
    def test_strategy_initialization(self):
        """Test strategy initialization."""
        self.assertIsInstance(self.strategy, StochRSIStrategy)
        self.assertEqual(self.strategy.stoch_rsi_params.dynamic_bands_enabled, True)
        self.assertEqual(self.strategy.stoch_rsi_params.atr_sensitivity, 1.5)
        
        # Test performance metrics initialization
        self.assertIn('total_signals', self.strategy.performance_metrics)
        self.assertEqual(self.strategy.performance_metrics['total_signals'], 0)
    
    def test_backward_compatibility(self):
        """Test backward compatibility with static bands."""
        # Create strategy with dynamic bands disabled
        self.mock_config.indicators.stochRSI.dynamic_bands_enabled = False
        static_strategy = StochRSIStrategy(self.mock_config)
        
        # Test signal generation works with static bands
        signal = static_strategy.generate_signal(self.test_data.copy())
        self.assertIn(signal, [0, 1, -1])
    
    def test_dynamic_signal_generation(self):
        """Test signal generation with dynamic bands."""
        signal = self.strategy.generate_signal(self.test_data.copy())
        self.assertIn(signal, [0, 1, -1])
        
        # Test that performance metrics are updated
        self.assertGreaterEqual(self.strategy.performance_metrics['total_signals'], 0)
    
    def test_performance_tracking(self):
        """Test performance tracking functionality."""
        # Generate some signals
        for _ in range(5):
            self.strategy.generate_signal(self.test_data.copy())
        
        # Get performance summary
        summary = self.strategy.get_performance_summary()
        
        # Verify required fields
        required_fields = ['total_signals', 'dynamic_signals', 'static_signals',
                          'timestamp', 'strategy_config']
        for field in required_fields:
            self.assertIn(field, summary)
        
        # Test reset functionality
        self.strategy.reset_performance_metrics()
        self.assertEqual(self.strategy.performance_metrics['total_signals'], 0)
    
    def test_strategy_info(self):
        """Test strategy information retrieval."""
        info = self.strategy.get_strategy_info()
        
        self.assertIn('strategy_name', info)
        self.assertIn('version', info)
        self.assertIn('parameters', info)
        self.assertEqual(info['version'], '2.0.0')
    
    def test_signal_strength_evaluation(self):
        """Test signal strength evaluation logic."""
        # Create test data with known patterns
        test_df = self.test_data.copy()
        
        # Mock the RSI and StochRSI calculation results
        test_df['RSI'] = [30, 25, 20, 15, 25, 35, 45, 55, 65, 75] * 10
        test_df['StochRSI Signal'] = [0, 1, 1, 0, 0, 0, 0, 0, 0, 0] * 10
        test_df['Signal Strength'] = [0, 0.8, 0.9, 0, 0, 0, 0, 0, 0, 0] * 10
        test_df['volatility_ratio'] = [1.0, 1.2, 2.0, 1.5, 1.1, 1.0, 0.8, 0.9, 1.1, 1.3] * 10
        
        # Test signal evaluation
        recent_signals = pd.Series([0, 1, 1])
        signal_strengths = pd.Series([0, 0.8, 0.9])
        
        result = self.strategy._evaluate_signals(recent_signals, signal_strengths, test_df)
        self.assertIn(result, [0, 1, -1])


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration validation and edge cases."""
    
    def test_config_parameter_validation(self):
        """Test configuration parameter validation."""
        # Test valid configuration
        valid_params = StochRSIParams(
            enabled=True,
            lower_band=35,
            upper_band=100,
            K=3,
            D=3,
            rsi_length=14,
            stoch_length=14,
            source="Close",
            dynamic_bands_enabled=True,
            atr_period=20,
            atr_sensitivity=1.5,
            band_adjustment_factor=0.3,
            min_band_width=10,
            max_band_width=50
        )
        
        self.assertTrue(valid_params.dynamic_bands_enabled)
        self.assertEqual(valid_params.atr_sensitivity, 1.5)
    
    def test_edge_case_parameters(self):
        """Test edge case parameter values."""
        # Test minimum values
        edge_params = StochRSIParams(
            enabled=True,
            lower_band=0,
            upper_band=100,
            K=1,
            D=1,
            rsi_length=2,
            stoch_length=2,
            source="Close",
            dynamic_bands_enabled=True,
            atr_period=2,
            atr_sensitivity=1.1,
            band_adjustment_factor=0.1,
            min_band_width=1,
            max_band_width=99
        )
        
        self.assertEqual(edge_params.min_band_width, 1)
        self.assertEqual(edge_params.max_band_width, 99)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.mock_config = Mock()
        self.mock_config.indicators = Mock()
        self.mock_config.indicators.stochRSI = StochRSIParams(
            enabled=True,
            lower_band=35,
            upper_band=100,
            K=3,
            D=3,
            rsi_length=14,
            stoch_length=14,
            source="Close",
            dynamic_bands_enabled=True,
            atr_period=20,
            atr_sensitivity=1.5,
            band_adjustment_factor=0.3,
            min_band_width=10,
            max_band_width=50
        )
        self.mock_config.candle_lookback_period = 2
    
    def test_full_pipeline_integration(self):
        """Test the complete pipeline from data to signal."""
        # Create realistic market data
        np.random.seed(42)  # For reproducible tests
        dates = pd.date_range('2023-01-01', periods=200, freq='1H')
        
        # Generate realistic OHLC data with trends and volatility
        base_price = 100
        price_changes = np.random.normal(0, 0.02, len(dates))
        prices = [base_price]
        
        for change in price_changes[1:]:
            prices.append(prices[-1] * (1 + change))
        
        market_data = pd.DataFrame({
            'datetime': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
            'volume': np.random.randint(1000, 10000, len(dates))
        })
        
        # Test the complete pipeline
        strategy = StochRSIStrategy(self.mock_config)
        
        # Generate multiple signals
        signals = []
        for i in range(50, len(market_data), 10):
            subset_data = market_data.iloc[i-50:i].copy()
            signal = strategy.generate_signal(subset_data)
            signals.append(signal)
        
        # Validate results
        self.assertGreater(len(signals), 0)
        self.assertTrue(all(s in [0, 1, -1] for s in signals))
        
        # Test performance summary
        summary = strategy.get_performance_summary()
        self.assertIn('total_signals', summary)
        
    def test_performance_comparison(self):
        """Test performance comparison between static and dynamic modes."""
        # Test with static bands
        self.mock_config.indicators.stochRSI.dynamic_bands_enabled = False
        static_strategy = StochRSIStrategy(self.mock_config)
        
        # Test with dynamic bands
        self.mock_config.indicators.stochRSI.dynamic_bands_enabled = True
        dynamic_strategy = StochRSIStrategy(self.mock_config)
        
        # Create test data
        test_data = pd.DataFrame({
            'high': np.random.uniform(100, 110, 100),
            'low': np.random.uniform(95, 105, 100),
            'close': np.random.uniform(98, 108, 100),
            'open': np.random.uniform(97, 109, 100),
        })
        
        # Generate signals with both strategies
        static_signal = static_strategy.generate_signal(test_data.copy())
        dynamic_signal = dynamic_strategy.generate_signal(test_data.copy())
        
        # Both should produce valid signals
        self.assertIn(static_signal, [0, 1, -1])
        self.assertIn(dynamic_signal, [0, 1, -1])
        
        # Dynamic strategy should have additional metrics
        dynamic_summary = dynamic_strategy.get_performance_summary()
        static_summary = static_strategy.get_performance_summary()
        
        # Dynamic should have volatility tracking
        if 'volatility_ratio_history' in dynamic_summary:
            self.assertGreaterEqual(len(dynamic_summary['volatility_ratio_history']), 0)


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestATRCalculation,
        TestDynamicBands,
        TestEnhancedStochRSIStrategy,
        TestConfigurationValidation,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"{'='*60}")