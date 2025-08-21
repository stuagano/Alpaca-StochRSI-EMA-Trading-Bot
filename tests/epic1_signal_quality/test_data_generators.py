"""
Test Data Generators for Epic 1 Signal Quality Testing

Generates realistic market data scenarios for comprehensive testing of:
- Dynamic StochRSI band adjustments
- Volume confirmation systems  
- Multi-timeframe validation
- Signal quality metrics

Author: Testing & Validation System
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import random
from dataclasses import dataclass
from enum import Enum


class MarketCondition(Enum):
    """Market condition types for test scenarios."""
    VOLATILE = "volatile"
    CALM = "calm"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"


@dataclass
class MarketScenario:
    """Market scenario configuration for test data generation."""
    condition: MarketCondition
    duration_hours: int
    volatility_factor: float
    trend_strength: float
    volume_pattern: str
    price_range: Tuple[float, float]
    signal_frequency: float  # Expected signals per hour


class TestDataGenerator:
    """Generates realistic market data for Epic 1 testing."""
    
    def __init__(self, seed: int = 42):
        """Initialize the test data generator."""
        self.seed = seed
        np.random.seed(seed)
        random.seed(seed)
        
        # Base parameters
        self.base_price = 150.0
        self.base_volume = 100000
        
        # Market scenarios
        self.scenarios = {
            MarketCondition.VOLATILE: MarketScenario(
                condition=MarketCondition.VOLATILE,
                duration_hours=6,
                volatility_factor=3.0,
                trend_strength=0.3,
                volume_pattern="high_variable",
                price_range=(140, 160),
                signal_frequency=8.0
            ),
            MarketCondition.CALM: MarketScenario(
                condition=MarketCondition.CALM,
                duration_hours=8,
                volatility_factor=0.5,
                trend_strength=0.1,
                volume_pattern="low_stable",
                price_range=(148, 152),
                signal_frequency=2.0
            ),
            MarketCondition.TRENDING_UP: MarketScenario(
                condition=MarketCondition.TRENDING_UP,
                duration_hours=12,
                volatility_factor=1.2,
                trend_strength=0.8,
                volume_pattern="increasing",
                price_range=(145, 165),
                signal_frequency=4.0
            ),
            MarketCondition.TRENDING_DOWN: MarketScenario(
                condition=MarketCondition.TRENDING_DOWN,
                duration_hours=10,
                volatility_factor=1.5,
                trend_strength=-0.7,
                volume_pattern="decreasing",
                price_range=(135, 155),
                signal_frequency=3.5
            ),
            MarketCondition.SIDEWAYS: MarketScenario(
                condition=MarketCondition.SIDEWAYS,
                duration_hours=16,
                volatility_factor=0.8,
                trend_strength=0.0,
                volume_pattern="stable",
                price_range=(147, 153),
                signal_frequency=1.5
            ),
            MarketCondition.BREAKOUT: MarketScenario(
                condition=MarketCondition.BREAKOUT,
                duration_hours=4,
                volatility_factor=2.5,
                trend_strength=0.9,
                volume_pattern="spike",
                price_range=(150, 170),
                signal_frequency=6.0
            ),
            MarketCondition.REVERSAL: MarketScenario(
                condition=MarketCondition.REVERSAL,
                duration_hours=6,
                volatility_factor=2.0,
                trend_strength=-0.6,
                volume_pattern="high_early",
                price_range=(135, 150),
                signal_frequency=5.0
            )
        }
    
    def generate_market_data(
        self, 
        condition: MarketCondition,
        timeframe: str = '1Min',
        periods: int = 500
    ) -> pd.DataFrame:
        """
        Generate market data for specific market condition.
        
        Args:
            condition: Market condition to simulate
            timeframe: Data timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
            periods: Number of periods to generate
            
        Returns:
            DataFrame with OHLCV data
        """
        scenario = self.scenarios[condition]
        
        # Generate timestamps
        freq_map = {
            '1Min': '1min',
            '5Min': '5min', 
            '15Min': '15min',
            '1Hour': '1h',
            '1Day': '1D'
        }
        
        start_time = datetime(2024, 1, 1, 9, 30, 0)  # Market open
        timestamps = pd.date_range(
            start=start_time,
            periods=periods,
            freq=freq_map.get(timeframe, '1min')
        )
        
        # Generate base price series
        prices = self._generate_price_series(scenario, periods)
        
        # Generate OHLCV data
        ohlcv_data = self._generate_ohlcv_from_prices(prices, scenario)
        
        # Create DataFrame
        df = pd.DataFrame(ohlcv_data, index=timestamps)
        
        # Add metadata
        df.attrs['condition'] = condition.value
        df.attrs['scenario'] = scenario
        df.attrs['timeframe'] = timeframe
        
        return df
    
    def _generate_price_series(self, scenario: MarketScenario, periods: int) -> np.ndarray:
        """Generate base price series for the scenario."""
        prices = np.zeros(periods)
        prices[0] = self.base_price
        
        # Trend component
        trend_increment = scenario.trend_strength * 0.01  # 1% per period max
        
        # Volatility component
        volatility = 0.005 * scenario.volatility_factor  # Base 0.5% volatility
        
        for i in range(1, periods):
            # Trend
            trend = trend_increment
            
            # Add mean reversion for sideways markets
            if scenario.condition == MarketCondition.SIDEWAYS:
                deviation = (prices[i-1] - self.base_price) / self.base_price
                trend -= deviation * 0.1  # Mean reversion factor
            
            # Volatility (random walk component)
            noise = np.random.normal(0, volatility)
            
            # Special patterns
            if scenario.condition == MarketCondition.BREAKOUT and i > periods * 0.7:
                # Acceleration in latter part
                trend *= 1.5
                noise *= 1.2
            elif scenario.condition == MarketCondition.REVERSAL and i > periods * 0.5:
                # Reverse direction
                trend *= -1.5
            
            # Price change
            price_change = trend + noise
            prices[i] = prices[i-1] * (1 + price_change)
            
            # Ensure price stays within reasonable bounds
            prices[i] = np.clip(
                prices[i], 
                scenario.price_range[0], 
                scenario.price_range[1]
            )
        
        return prices
    
    def _generate_ohlcv_from_prices(self, prices: np.ndarray, scenario: MarketScenario) -> Dict:
        """Generate OHLCV data from price series."""
        periods = len(prices)
        
        # Generate volume pattern
        volumes = self._generate_volume_series(scenario, periods)
        
        ohlcv = {
            'open': np.zeros(periods),
            'high': np.zeros(periods),
            'low': np.zeros(periods),
            'close': prices.copy(),
            'volume': volumes
        }
        
        # Generate OHLC from close prices
        for i in range(periods):
            if i == 0:
                ohlcv['open'][i] = prices[i]
            else:
                ohlcv['open'][i] = ohlcv['close'][i-1]
            
            # High/Low based on volatility
            volatility_range = prices[i] * 0.002 * scenario.volatility_factor
            
            ohlcv['high'][i] = prices[i] + np.random.uniform(0, volatility_range)
            ohlcv['low'][i] = prices[i] - np.random.uniform(0, volatility_range)
            
            # Ensure OHLC relationships
            ohlcv['high'][i] = max(ohlcv['high'][i], ohlcv['open'][i], ohlcv['close'][i])
            ohlcv['low'][i] = min(ohlcv['low'][i], ohlcv['open'][i], ohlcv['close'][i])
        
        return ohlcv
    
    def _generate_volume_series(self, scenario: MarketScenario, periods: int) -> np.ndarray:
        """Generate volume series based on scenario pattern."""
        volumes = np.zeros(periods)
        
        base_volume = self.base_volume
        
        for i in range(periods):
            if scenario.volume_pattern == "high_variable":
                # High volume with high variability
                volume_factor = np.random.uniform(0.5, 3.0)
                volumes[i] = base_volume * volume_factor
                
            elif scenario.volume_pattern == "low_stable":
                # Low volume with low variability
                volume_factor = np.random.uniform(0.3, 0.8)
                volumes[i] = base_volume * volume_factor
                
            elif scenario.volume_pattern == "increasing":
                # Gradually increasing volume
                progress = i / periods
                volume_factor = 0.5 + progress * 1.5 + np.random.uniform(-0.2, 0.2)
                volumes[i] = base_volume * volume_factor
                
            elif scenario.volume_pattern == "decreasing":
                # Gradually decreasing volume
                progress = i / periods
                volume_factor = 2.0 - progress * 1.3 + np.random.uniform(-0.2, 0.2)
                volumes[i] = base_volume * volume_factor
                
            elif scenario.volume_pattern == "spike":
                # Volume spike in middle
                if 0.4 <= i/periods <= 0.6:
                    volume_factor = np.random.uniform(2.0, 4.0)
                else:
                    volume_factor = np.random.uniform(0.5, 1.2)
                volumes[i] = base_volume * volume_factor
                
            elif scenario.volume_pattern == "high_early":
                # High volume early, then decreasing
                if i < periods * 0.3:
                    volume_factor = np.random.uniform(1.5, 3.0)
                else:
                    volume_factor = np.random.uniform(0.3, 1.0)
                volumes[i] = base_volume * volume_factor
                
            else:  # stable
                volume_factor = np.random.uniform(0.8, 1.2)
                volumes[i] = base_volume * volume_factor
            
            # Ensure positive volume
            volumes[i] = max(volumes[i], 1000)
        
        return volumes.astype(int)
    
    def generate_multi_timeframe_data(
        self, 
        condition: MarketCondition,
        timeframes: List[str] = ['1Min', '5Min', '15Min', '1Hour']
    ) -> Dict[str, pd.DataFrame]:
        """
        Generate multi-timeframe data for the same market condition.
        
        Args:
            condition: Market condition to simulate
            timeframes: List of timeframes to generate
            
        Returns:
            Dictionary mapping timeframes to DataFrames
        """
        data_dict = {}
        
        # Generate base 1-minute data
        base_periods = 1440  # 24 hours of 1-minute data
        base_data = self.generate_market_data(condition, '1Min', base_periods)
        
        for timeframe in timeframes:
            if timeframe == '1Min':
                data_dict[timeframe] = base_data.copy()
            else:
                # Resample base data to target timeframe
                freq_map = {
                    '5Min': '5min',
                    '15Min': '15min',
                    '1Hour': '1h',
                    '1Day': '1D'
                }
                
                resampled = base_data.resample(freq_map[timeframe]).agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
                
                resampled.attrs = base_data.attrs.copy()
                resampled.attrs['timeframe'] = timeframe
                
                data_dict[timeframe] = resampled
        
        return data_dict
    
    def generate_signal_test_scenarios(self) -> Dict[str, Dict]:
        """
        Generate comprehensive test scenarios for signal validation.
        
        Returns:
            Dictionary of test scenarios with expected outcomes
        """
        scenarios = {}
        
        # Scenario 1: Perfect StochRSI buy signal in volatile market
        scenarios['volatile_oversold_bounce'] = {
            'condition': MarketCondition.VOLATILE,
            'description': 'Oversold bounce in volatile market',
            'expected_signals': 3,
            'expected_volume_confirmation': True,
            'expected_multi_timeframe_alignment': True,
            'success_probability': 0.75
        }
        
        # Scenario 2: False signal in calm market
        scenarios['calm_false_signal'] = {
            'condition': MarketCondition.CALM,
            'description': 'Weak signal in calm market',
            'expected_signals': 1,
            'expected_volume_confirmation': False,
            'expected_multi_timeframe_alignment': False,
            'success_probability': 0.25
        }
        
        # Scenario 3: Strong trending signal
        scenarios['trending_momentum'] = {
            'condition': MarketCondition.TRENDING_UP,
            'description': 'Strong momentum signal in uptrend',
            'expected_signals': 2,
            'expected_volume_confirmation': True,
            'expected_multi_timeframe_alignment': True,
            'success_probability': 0.85
        }
        
        # Scenario 4: Sideways whipsaw
        scenarios['sideways_whipsaw'] = {
            'condition': MarketCondition.SIDEWAYS,
            'description': 'Whipsaw signals in sideways market',
            'expected_signals': 4,
            'expected_volume_confirmation': False,
            'expected_multi_timeframe_alignment': False,
            'success_probability': 0.30
        }
        
        # Scenario 5: Breakout confirmation
        scenarios['breakout_confirmation'] = {
            'condition': MarketCondition.BREAKOUT,
            'description': 'Breakout with volume confirmation',
            'expected_signals': 2,
            'expected_volume_confirmation': True,
            'expected_multi_timeframe_alignment': True,
            'success_probability': 0.90
        }
        
        return scenarios
    
    def generate_historical_backtest_data(
        self, 
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '1Min'
    ) -> pd.DataFrame:
        """
        Generate historical-style data for backtesting.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            timeframe: Data timeframe
            
        Returns:
            DataFrame with realistic historical market data
        """
        # Calculate periods needed
        freq_map = {
            '1Min': '1min',
            '5Min': '5min',
            '15Min': '15min',
            '1Hour': '1h',
            '1Day': '1D'
        }
        
        timestamps = pd.date_range(
            start=start_date,
            end=end_date,
            freq=freq_map.get(timeframe, '1min')
        )
        periods = len(timestamps)
        
        # Mix different market conditions over time
        segment_size = periods // 7  # 7 different segments
        all_data = []
        
        conditions_cycle = [
            MarketCondition.VOLATILE,
            MarketCondition.TRENDING_UP,
            MarketCondition.CALM,
            MarketCondition.SIDEWAYS,
            MarketCondition.TRENDING_DOWN,
            MarketCondition.BREAKOUT,
            MarketCondition.REVERSAL
        ]
        
        current_price = self.base_price
        
        for i, condition in enumerate(conditions_cycle):
            start_idx = i * segment_size
            end_idx = min((i + 1) * segment_size, periods)
            segment_periods = end_idx - start_idx
            
            if segment_periods <= 0:
                break
            
            # Adjust base price for continuity
            self.base_price = current_price
            
            segment_data = self.generate_market_data(condition, timeframe, segment_periods)
            
            # Update current price for next segment
            current_price = segment_data['close'].iloc[-1]
            
            all_data.append(segment_data)
        
        # Combine all segments
        combined_data = pd.concat(all_data, ignore_index=False)
        combined_data.index = timestamps[:len(combined_data)]
        
        # Reset base price
        self.base_price = 150.0
        
        return combined_data
    
    def add_realistic_gaps_and_noise(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add realistic market gaps and noise to data."""
        df_copy = df.copy()
        
        # Add weekend gaps (if daily data)
        if 'Day' in df.attrs.get('timeframe', ''):
            # Add random weekend gaps
            gap_probability = 0.1
            gap_size_range = (0.005, 0.02)  # 0.5% to 2% gaps
            
            for i in range(1, len(df_copy)):
                if np.random.random() < gap_probability:
                    gap_size = np.random.uniform(*gap_size_range)
                    gap_direction = np.random.choice([-1, 1])
                    
                    gap_multiplier = 1 + (gap_size * gap_direction)
                    df_copy.iloc[i] *= gap_multiplier
        
        # Add micro-structure noise
        noise_factor = 0.0001  # 0.01% noise
        for col in ['open', 'high', 'low', 'close']:
            noise = np.random.normal(0, noise_factor, len(df_copy))
            df_copy[col] *= (1 + noise)
        
        # Ensure OHLC relationships remain valid
        for i in range(len(df_copy)):
            values = [df_copy['open'].iloc[i], df_copy['close'].iloc[i]]
            df_copy.loc[df_copy.index[i], 'high'] = max(df_copy['high'].iloc[i], *values)
            df_copy.loc[df_copy.index[i], 'low'] = min(df_copy['low'].iloc[i], *values)
        
        return df_copy
    
    def generate_performance_test_data(self, size: str = "medium") -> Dict[str, pd.DataFrame]:
        """
        Generate data sets for performance testing.
        
        Args:
            size: Dataset size - "small", "medium", "large", "xlarge"
            
        Returns:
            Dictionary with test datasets
        """
        size_config = {
            "small": {"periods": 1000, "timeframes": ['1Min', '5Min']},
            "medium": {"periods": 5000, "timeframes": ['1Min', '5Min', '15Min']},
            "large": {"periods": 20000, "timeframes": ['1Min', '5Min', '15Min', '1Hour']},
            "xlarge": {"periods": 100000, "timeframes": ['1Min', '5Min', '15Min', '1Hour', '1Day']}
        }
        
        config = size_config.get(size, size_config["medium"])
        
        datasets = {}
        
        for condition in MarketCondition:
            condition_data = {}
            
            for timeframe in config["timeframes"]:
                condition_data[timeframe] = self.generate_market_data(
                    condition, timeframe, config["periods"]
                )
            
            datasets[condition.value] = condition_data
        
        return datasets


# Factory function for easy test data generation
def create_test_data_generator(seed: int = None) -> TestDataGenerator:
    """Create a test data generator with optional seed."""
    if seed is None:
        seed = int(datetime.now().timestamp()) % 10000
    return TestDataGenerator(seed)


def generate_quick_test_data(
    condition: MarketCondition = MarketCondition.VOLATILE,
    timeframe: str = '1Min',
    periods: int = 500
) -> pd.DataFrame:
    """Quick helper to generate test data."""
    generator = create_test_data_generator()
    return generator.generate_market_data(condition, timeframe, periods)


# Export main classes and functions
__all__ = [
    'TestDataGenerator',
    'MarketCondition',
    'MarketScenario',
    'create_test_data_generator',
    'generate_quick_test_data'
]