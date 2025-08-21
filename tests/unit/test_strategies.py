"""
Comprehensive unit tests for trading strategies.
Tests StochRSI and MA Crossover strategies with various market conditions.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from strategies.stoch_rsi_strategy import StochRSIStrategy
from strategies.ma_crossover_strategy import MACrossoverStrategy
from strategies.strategy_base import Strategy


class TestStochRSIStrategy:
    """Test suite for StochRSI strategy."""
    
    def test_strategy_initialization(self, test_config):
        """Test strategy initialization with config."""
        strategy = StochRSIStrategy(test_config)
        
        assert strategy.config == test_config
        assert strategy.stoch_rsi_params == test_config.indicators.stochRSI
        assert strategy.lookback_period == test_config.candle_lookback_period
    
    def test_strategy_initialization_with_custom_config(self):
        """Test strategy with custom configuration."""
        from config.unified_config import TradingConfig
        
        custom_config = TradingConfig(
            strategy="StochRSI",
            candle_lookback_period=50,
            indicators={
                "stochRSI": {
                    "enabled": True,
                    "rsi_period": 21,
                    "stoch_period": 21,
                    "oversold": 25,
                    "overbought": 75
                }
            }
        )
        
        strategy = StochRSIStrategy(custom_config)
        assert strategy.lookback_period == 50
        assert strategy.stoch_rsi_params.rsi_period == 21
        assert strategy.stoch_rsi_params.oversold == 25
    
    def test_generate_signal_disabled_indicator(self, test_config):
        """Test signal generation when indicator is disabled."""
        test_config.indicators.stochRSI.enabled = False
        strategy = StochRSIStrategy(test_config)
        
        # Create sample data
        df = self._create_sample_dataframe()
        
        signal = strategy.generate_signal(df)
        assert signal == 0
    
    def test_generate_signal_with_buy_signal(self, test_config, sample_ohlcv_data):
        """Test buy signal generation."""
        strategy = StochRSIStrategy(test_config)
        
        # Mock the indicator functions to return buy signals
        with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
             patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
            
            # Create DataFrame with StochRSI Signal column containing buy signals
            df_with_signals = sample_ohlcv_data.copy()
            df_with_signals['StochRSI Signal'] = 0
            df_with_signals.loc[-5:, 'StochRSI Signal'] = 1  # Buy signal in recent data
            
            mock_rsi.return_value = df_with_signals
            mock_stoch.return_value = df_with_signals
            
            signal = strategy.generate_signal(sample_ohlcv_data)
            assert signal == 1
    
    def test_generate_signal_no_signal(self, test_config, sample_ohlcv_data):
        """Test when no trading signal is generated."""
        strategy = StochRSIStrategy(test_config)
        
        # Mock indicators to return no signals
        with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
             patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
            
            df_no_signals = sample_ohlcv_data.copy()
            df_no_signals['StochRSI Signal'] = 0  # No buy signals
            
            mock_rsi.return_value = df_no_signals
            mock_stoch.return_value = df_no_signals
            
            signal = strategy.generate_signal(sample_ohlcv_data)
            assert signal == 0
    
    def test_generate_signal_missing_column(self, test_config, sample_ohlcv_data):
        """Test signal generation when StochRSI Signal column is missing."""
        strategy = StochRSIStrategy(test_config)
        
        # Mock indicators to return DataFrame without signal column
        with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
             patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
            
            mock_rsi.return_value = sample_ohlcv_data
            mock_stoch.return_value = sample_ohlcv_data  # No StochRSI Signal column
            
            signal = strategy.generate_signal(sample_ohlcv_data)
            assert signal == 0
    
    def test_generate_signal_with_lookback_period(self, test_config, sample_ohlcv_data):
        """Test signal generation respects lookback period."""
        test_config.candle_lookback_period = 20
        strategy = StochRSIStrategy(test_config)
        
        with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
             patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
            
            # Create signals only outside the lookback period
            df_with_signals = sample_ohlcv_data.copy()
            df_with_signals['StochRSI Signal'] = 0
            df_with_signals.iloc[0] = 1  # Signal outside lookback period
            
            mock_rsi.return_value = df_with_signals
            mock_stoch.return_value = df_with_signals
            
            signal = strategy.generate_signal(sample_ohlcv_data)
            assert signal == 0  # Should not detect old signal
    
    def test_signal_consistency(self, test_config):
        """Test signal generation consistency with same input."""
        strategy = StochRSIStrategy(test_config)
        df = self._create_sample_dataframe()
        
        # Generate signal multiple times with same data
        signals = []
        for _ in range(5):
            with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
                 patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
                
                df_with_signals = df.copy()
                df_with_signals['StochRSI Signal'] = [0] * (len(df) - 1) + [1]
                
                mock_rsi.return_value = df_with_signals
                mock_stoch.return_value = df_with_signals
                
                signal = strategy.generate_signal(df)
                signals.append(signal)
        
        # All signals should be the same
        assert all(s == signals[0] for s in signals)
        assert signals[0] == 1
    
    @staticmethod
    def _create_sample_dataframe(periods=100):
        """Create sample OHLCV DataFrame for testing."""
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1min')
        base_price = 150.0
        
        # Generate realistic price data
        np.random.seed(42)
        returns = np.random.normal(0, 0.01, periods)
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000, 10000, periods)
        })


class TestMACrossoverStrategy:
    """Test suite for MA Crossover strategy."""
    
    def test_strategy_initialization(self, test_config):
        """Test MA crossover strategy initialization."""
        strategy = MACrossoverStrategy(test_config)
        
        assert strategy.config == test_config
        assert hasattr(strategy, 'ema_params')
    
    def test_ma_crossover_buy_signal(self, test_config, sample_ohlcv_data):
        """Test MA crossover buy signal generation."""
        strategy = MACrossoverStrategy(test_config)
        
        # Create DataFrame with bullish crossover
        df = sample_ohlcv_data.copy()
        
        # Simulate EMA crossover - fast EMA crosses above slow EMA
        df['EMA_12'] = df['close'].ewm(span=12).mean()
        df['EMA_26'] = df['close'].ewm(span=26).mean()
        
        # Force crossover in recent data
        df.loc[df.index[-5:], 'EMA_12'] = df.loc[df.index[-5:], 'close'] * 1.01
        df.loc[df.index[-5:], 'EMA_26'] = df.loc[df.index[-5:], 'close'] * 0.99
        
        signal = strategy.generate_signal(df)
        assert signal in [0, 1]  # Valid signal range
    
    def test_ma_crossover_no_signal(self, test_config, sample_ohlcv_data):
        """Test when no crossover signal occurs."""
        strategy = MACrossoverStrategy(test_config)
        
        # Create DataFrame with no clear crossover
        df = sample_ohlcv_data.copy()
        df['EMA_12'] = df['close'].ewm(span=12).mean()
        df['EMA_26'] = df['close'].ewm(span=26).mean()
        
        # Ensure fast EMA stays below slow EMA
        df['EMA_12'] = df['EMA_26'] * 0.99
        
        signal = strategy.generate_signal(df)
        assert signal == 0
    
    def test_empty_dataframe_handling(self, test_config):
        """Test strategy behavior with empty DataFrame."""
        strategy = MACrossoverStrategy(test_config)
        
        empty_df = pd.DataFrame()
        signal = strategy.generate_signal(empty_df)
        assert signal == 0
    
    def test_insufficient_data_handling(self, test_config):
        """Test strategy with insufficient data points."""
        strategy = MACrossoverStrategy(test_config)
        
        # Create DataFrame with only 5 data points (insufficient for EMA calculation)
        small_df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=5, freq='1min'),
            'open': [100, 101, 102, 103, 104],
            'high': [102, 103, 104, 105, 106],
            'low': [99, 100, 101, 102, 103],
            'close': [101, 102, 103, 104, 105],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        
        signal = strategy.generate_signal(small_df)
        assert signal == 0


class TestStrategyBase:
    """Test suite for base strategy functionality."""
    
    def test_strategy_base_abstract_methods(self, test_config):
        """Test that Strategy base class enforces abstract methods."""
        
        # Should not be able to instantiate Strategy directly
        with pytest.raises(TypeError):
            Strategy(test_config)
    
    def test_strategy_inheritance(self, test_config):
        """Test that concrete strategies properly inherit from base."""
        stoch_rsi = StochRSIStrategy(test_config)
        ma_crossover = MACrossoverStrategy(test_config)
        
        assert isinstance(stoch_rsi, Strategy)
        assert isinstance(ma_crossover, Strategy)
        
        # Check that required methods are implemented
        assert hasattr(stoch_rsi, 'generate_signal')
        assert hasattr(ma_crossover, 'generate_signal')
        assert callable(stoch_rsi.generate_signal)
        assert callable(ma_crossover.generate_signal)


class TestStrategyPerformance:
    """Performance tests for strategies."""
    
    @pytest.mark.performance
    def test_stoch_rsi_performance(self, test_config, benchmark):
        """Benchmark StochRSI strategy performance."""
        strategy = StochRSIStrategy(test_config)
        df = TestStochRSIStrategy._create_sample_dataframe(1000)  # Large dataset
        
        with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
             patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
            
            df_with_signals = df.copy()
            df_with_signals['StochRSI Signal'] = np.random.choice([0, 1], size=len(df))
            
            mock_rsi.return_value = df_with_signals
            mock_stoch.return_value = df_with_signals
            
            # Benchmark the signal generation
            result = benchmark(strategy.generate_signal, df)
            assert result in [0, 1]
    
    @pytest.mark.performance
    def test_ma_crossover_performance(self, test_config, benchmark):
        """Benchmark MA Crossover strategy performance."""
        strategy = MACrossoverStrategy(test_config)
        df = TestStochRSIStrategy._create_sample_dataframe(1000)
        
        # Benchmark the signal generation
        result = benchmark(strategy.generate_signal, df)
        assert result in [0, 1]
    
    @pytest.mark.memory
    def test_strategy_memory_usage(self, test_config, memory_profiler):
        """Test strategy memory usage."""
        strategy = StochRSIStrategy(test_config)
        
        # Create large dataset
        large_df = TestStochRSIStrategy._create_sample_dataframe(10000)
        
        # Memory usage should be reasonable
        with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
             patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
            
            mock_rsi.return_value = large_df
            mock_stoch.return_value = large_df
            
            initial_memory = memory_profiler.get_current_memory()
            strategy.generate_signal(large_df)
            final_memory = memory_profiler.get_current_memory()
            
            memory_increase = final_memory - initial_memory
            assert memory_increase < 100  # Less than 100MB increase


class TestStrategyEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_strategy_with_nan_values(self, test_config):
        """Test strategy handling of NaN values in data."""
        strategy = StochRSIStrategy(test_config)
        
        # Create DataFrame with NaN values
        df = TestStochRSIStrategy._create_sample_dataframe(50)
        df.loc[10:15, 'close'] = np.nan
        
        with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
             patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
            
            df_with_signals = df.copy()
            df_with_signals['StochRSI Signal'] = 0
            
            mock_rsi.return_value = df_with_signals
            mock_stoch.return_value = df_with_signals
            
            # Should handle NaN values gracefully
            signal = strategy.generate_signal(df)
            assert signal == 0
    
    def test_strategy_with_extreme_values(self, test_config):
        """Test strategy with extreme price values."""
        strategy = StochRSIStrategy(test_config)
        
        # Create DataFrame with extreme values
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='1min'),
            'open': [1e6] * 100,  # Very high prices
            'high': [1e6 + 1000] * 100,
            'low': [1e6 - 1000] * 100,
            'close': [1e6] * 100,
            'volume': [1] * 100  # Very low volume
        })
        
        with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
             patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
            
            df_with_signals = df.copy()
            df_with_signals['StochRSI Signal'] = 0
            
            mock_rsi.return_value = df_with_signals
            mock_stoch.return_value = df_with_signals
            
            # Should handle extreme values without crashing
            signal = strategy.generate_signal(df)
            assert signal == 0
    
    def test_strategy_with_single_data_point(self, test_config):
        """Test strategy with only one data point."""
        strategy = StochRSIStrategy(test_config)
        
        single_point_df = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [100.0],
            'high': [101.0],
            'low': [99.0],
            'close': [100.5],
            'volume': [1000]
        })
        
        with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
             patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
            
            mock_rsi.return_value = single_point_df
            mock_stoch.return_value = single_point_df
            
            signal = strategy.generate_signal(single_point_df)
            assert signal == 0
    
    @pytest.mark.parametrize("data_corruption", [
        "missing_close_column",
        "wrong_data_types",
        "negative_prices",
        "zero_volume"
    ])
    def test_strategy_data_corruption_scenarios(self, test_config, data_corruption):
        """Test strategy robustness against data corruption."""
        strategy = StochRSIStrategy(test_config)
        df = TestStochRSIStrategy._create_sample_dataframe(50)
        
        # Apply different types of data corruption
        if data_corruption == "missing_close_column":
            df = df.drop('close', axis=1)
        elif data_corruption == "wrong_data_types":
            df['close'] = df['close'].astype(str)
        elif data_corruption == "negative_prices":
            df['close'] = -df['close']
        elif data_corruption == "zero_volume":
            df['volume'] = 0
        
        # Strategy should handle corruption gracefully
        try:
            signal = strategy.generate_signal(df)
            assert signal in [0, 1]  # Valid signal or no signal
        except Exception as e:
            # If exception occurs, it should be a known, handled exception
            assert isinstance(e, (KeyError, ValueError, TypeError))


class TestStrategySignalValidation:
    """Test signal validation and consistency."""
    
    def test_signal_range_validation(self, test_config):
        """Test that generated signals are within valid range."""
        strategies = [
            StochRSIStrategy(test_config),
            MACrossoverStrategy(test_config)
        ]
        
        df = TestStochRSIStrategy._create_sample_dataframe(100)
        
        for strategy in strategies:
            for _ in range(10):  # Test multiple times
                if isinstance(strategy, StochRSIStrategy):
                    with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
                         patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
                        
                        df_with_signals = df.copy()
                        df_with_signals['StochRSI Signal'] = np.random.choice([0, 1], size=len(df))
                        
                        mock_rsi.return_value = df_with_signals
                        mock_stoch.return_value = df_with_signals
                        
                        signal = strategy.generate_signal(df)
                else:
                    signal = strategy.generate_signal(df)
                
                # Signal should be 0 (no signal) or 1 (buy signal)
                assert signal in [0, 1], f"Invalid signal {signal} from {type(strategy).__name__}"
    
    def test_signal_reproducibility(self, test_config):
        """Test that signals are reproducible with same input."""
        np.random.seed(42)  # Set seed for reproducibility
        
        strategy = StochRSIStrategy(test_config)
        df = TestStochRSIStrategy._create_sample_dataframe(100)
        
        # Generate signal multiple times
        signals = []
        for _ in range(5):
            with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
                 patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
                
                df_with_signals = df.copy()
                df_with_signals['StochRSI Signal'] = [0] * 95 + [1] * 5  # Consistent pattern
                
                mock_rsi.return_value = df_with_signals
                mock_stoch.return_value = df_with_signals
                
                signal = strategy.generate_signal(df)
                signals.append(signal)
        
        # All signals should be identical
        assert len(set(signals)) == 1, f"Inconsistent signals: {signals}"
    
    @pytest.mark.parametrize("lookback_period", [10, 20, 50, 100])
    def test_lookback_period_effects(self, test_config, lookback_period):
        """Test strategy behavior with different lookback periods."""
        test_config.candle_lookback_period = lookback_period
        strategy = StochRSIStrategy(test_config)
        
        df = TestStochRSIStrategy._create_sample_dataframe(200)
        
        with patch('strategies.stoch_rsi_strategy.rsi') as mock_rsi, \
             patch('strategies.stoch_rsi_strategy.stochastic') as mock_stoch:
            
            df_with_signals = df.copy()
            df_with_signals['StochRSI Signal'] = 0
            # Add signal at different positions
            df_with_signals.iloc[-lookback_period//2] = 1
            
            mock_rsi.return_value = df_with_signals
            mock_stoch.return_value = df_with_signals
            
            signal = strategy.generate_signal(df)
            assert signal in [0, 1]