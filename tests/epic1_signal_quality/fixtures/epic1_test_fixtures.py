"""
Epic 1 Testing Fixtures and Test Data Generation

Provides comprehensive test data for Epic 1 signal quality enhancements including:
- Dynamic StochRSI band scenarios
- Volume profile test data
- Multi-timeframe market conditions
- Signal quality metrics baselines
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from unittest.mock import Mock, MagicMock

# Epic 1 Test Configurations
EPIC1_TEST_CONFIG = {
    "dynamic_stochrsi": {
        "enabled": True,
        "base_oversold": 20,
        "base_overbought": 80,
        "volatility_adjustment": True,
        "volume_adjustment": True,
        "max_adjustment": 15,
        "min_adjustment": 5
    },
    "volume_confirmation": {
        "enabled": True,
        "volume_threshold_multiplier": 1.5,
        "volume_period": 20,
        "require_volume_spike": True,
        "volume_spike_threshold": 2.0
    },
    "multi_timeframe": {
        "enabled": True,
        "primary_timeframe": "5Min",
        "confirmation_timeframes": ["15Min", "1Hour"],
        "signal_alignment_required": True,
        "min_confirmation_percentage": 60
    },
    "signal_quality": {
        "track_metrics": True,
        "confidence_threshold": 0.7,
        "false_positive_penalty": 0.2,
        "trend_alignment_bonus": 0.1
    }
}


@pytest.fixture
def epic1_config():
    """Configuration for Epic 1 features."""
    return EPIC1_TEST_CONFIG.copy()


@pytest.fixture
def volatile_market_data():
    """Generate high volatility market data for testing dynamic bands."""
    np.random.seed(42)
    periods = 200
    dates = pd.date_range(start='2024-01-01 09:30:00', periods=periods, freq='5min')
    
    # High volatility scenario
    base_price = 150.0
    volatility = 0.03  # 3% volatility
    
    prices = [base_price]
    for _ in range(periods - 1):
        # Create volatility clusters
        if np.random.random() < 0.1:  # 10% chance of volatility spike
            change = np.random.normal(0, volatility * 3)
        else:
            change = np.random.normal(0, volatility)
        prices.append(max(prices[-1] * (1 + change), 1.0))
    
    # Create OHLCV data
    opens = prices[:-1] + [prices[-1]]
    closes = prices
    
    highs = [max(o, c) * (1 + abs(np.random.normal(0, 0.005))) for o, c in zip(opens, closes)]
    lows = [min(o, c) * (1 - abs(np.random.normal(0, 0.005))) for o, c in zip(opens, closes)]
    
    # Generate volume with spikes during volatility
    base_volume = 10000
    volumes = []
    for i, price in enumerate(prices):
        if i > 0 and abs(price - prices[i-1]) / prices[i-1] > 0.02:  # 2% price change
            volume = base_volume * np.random.uniform(2, 5)  # Volume spike
        else:
            volume = base_volume * np.random.uniform(0.5, 1.5)
        volumes.append(int(volume))
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }).set_index('timestamp')


@pytest.fixture
def low_volume_market_data():
    """Generate low volume market data for volume confirmation testing."""
    np.random.seed(123)
    periods = 200
    dates = pd.date_range(start='2024-01-01 09:30:00', periods=periods, freq='5min')
    
    base_price = 150.0
    prices = [base_price]
    
    # Low volatility, sideways market
    for _ in range(periods - 1):
        change = np.random.normal(0, 0.005)  # 0.5% volatility
        prices.append(prices[-1] * (1 + change))
    
    opens = prices[:-1] + [prices[-1]]
    closes = prices
    highs = [max(o, c) + abs(np.random.normal(0, 0.001)) * c for o, c in zip(opens, closes)]
    lows = [min(o, c) - abs(np.random.normal(0, 0.001)) * c for o, c in zip(opens, closes)]
    
    # Consistently low volume
    base_volume = 2000
    volumes = [int(base_volume * np.random.uniform(0.8, 1.2)) for _ in range(periods)]
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }).set_index('timestamp')


@pytest.fixture
def trending_market_data():
    """Generate strong trending market data."""
    np.random.seed(456)
    periods = 200
    dates = pd.date_range(start='2024-01-01 09:30:00', periods=periods, freq='5min')
    
    base_price = 150.0
    trend_strength = 0.001  # 0.1% per period uptrend
    
    prices = [base_price]
    for i in range(periods - 1):
        # Strong uptrend with some noise
        trend = trend_strength * (1 + 0.5 * np.sin(i / 20))  # Varying trend strength
        noise = np.random.normal(0, 0.01)
        change = trend + noise
        prices.append(prices[-1] * (1 + change))
    
    opens = prices[:-1] + [prices[-1]]
    closes = prices
    highs = [max(o, c) + abs(np.random.normal(0, 0.002)) * c for o, c in zip(opens, closes)]
    lows = [min(o, c) - abs(np.random.normal(0, 0.002)) * c for o, c in zip(opens, closes)]
    
    # Higher volume during trend
    base_volume = 15000
    volumes = [int(base_volume * np.random.uniform(0.8, 2.0)) for _ in range(periods)]
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }).set_index('timestamp')


@pytest.fixture
def multi_timeframe_data():
    """Generate synchronized multi-timeframe test data."""
    np.random.seed(789)
    
    # Generate 1-minute data
    periods_1min = 1200  # 20 hours
    dates_1min = pd.date_range(start='2024-01-01 09:30:00', periods=periods_1min, freq='1min')
    
    base_price = 150.0
    prices_1min = [base_price]
    
    for _ in range(periods_1min - 1):
        change = np.random.normal(0, 0.008)
        prices_1min.append(prices_1min[-1] * (1 + change))
    
    df_1min = pd.DataFrame({
        'timestamp': dates_1min,
        'open': prices_1min[:-1] + [prices_1min[-1]],
        'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices_1min],
        'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices_1min],
        'close': prices_1min,
        'volume': [int(5000 * np.random.uniform(0.5, 2.0)) for _ in range(periods_1min)]
    }).set_index('timestamp')
    
    # Aggregate to 5-minute
    df_5min = df_1min.resample('5min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    
    # Aggregate to 15-minute
    df_15min = df_1min.resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    
    # Aggregate to 1-hour
    df_1hour = df_1min.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    
    return {
        '1Min': df_1min,
        '5Min': df_5min,
        '15Min': df_15min,
        '1Hour': df_1hour
    }


@pytest.fixture
def signal_quality_test_scenarios():
    """Pre-defined scenarios for signal quality testing."""
    return {
        'high_quality_signals': {
            'description': 'Strong trend with high volume confirmation',
            'expected_confidence': 0.85,
            'expected_false_positive_rate': 0.15,
            'market_conditions': 'trending_high_volume'
        },
        'medium_quality_signals': {
            'description': 'Moderate volatility with average volume',
            'expected_confidence': 0.65,
            'expected_false_positive_rate': 0.30,
            'market_conditions': 'moderate_volatility'
        },
        'low_quality_signals': {
            'description': 'Choppy market with low volume',
            'expected_confidence': 0.45,
            'expected_false_positive_rate': 0.50,
            'market_conditions': 'sideways_low_volume'
        },
        'extreme_volatility': {
            'description': 'High volatility with erratic volume',
            'expected_confidence': 0.30,
            'expected_false_positive_rate': 0.70,
            'market_conditions': 'extreme_volatility'
        }
    }


@pytest.fixture
def performance_baseline_metrics():
    """Baseline performance metrics for comparison testing."""
    return {
        'legacy_stochrsi': {
            'signal_accuracy': 0.58,
            'false_positive_rate': 0.42,
            'signal_frequency': 15.2,  # signals per day
            'avg_processing_time': 0.025,  # seconds
            'memory_usage': 45.8  # MB
        },
        'enhanced_stochrsi': {
            'expected_signal_accuracy': 0.72,
            'expected_false_positive_rate': 0.28,
            'expected_signal_frequency': 12.8,
            'max_processing_time': 0.040,
            'max_memory_usage': 60.0
        }
    }


@pytest.fixture
def mock_volume_profile():
    """Mock volume profile data for testing."""
    profile = Mock()
    profile.get_avg_volume = Mock(return_value=25000)
    profile.get_volume_percentile = Mock(return_value=0.65)
    profile.is_volume_spike = Mock(return_value=False)
    profile.get_volume_trend = Mock(return_value='stable')
    return profile


@pytest.fixture
def mock_volatility_calculator():
    """Mock volatility calculator for dynamic band testing."""
    calc = Mock()
    calc.get_current_volatility = Mock(return_value=0.025)
    calc.get_volatility_percentile = Mock(return_value=0.60)
    calc.is_high_volatility_period = Mock(return_value=False)
    calc.get_volatility_adjustment = Mock(return_value=5)
    return calc


@pytest.fixture
def edge_case_data():
    """Generate edge case scenarios for testing."""
    scenarios = {}
    
    # Market gap scenario
    gap_data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01 09:30:00', periods=100, freq='5min'),
        'open': [150] * 50 + [180] * 50,  # 20% gap up
        'high': [151] * 50 + [181] * 50,
        'low': [149] * 50 + [179] * 50,
        'close': [150] * 50 + [180] * 50,
        'volume': [10000] * 100
    }).set_index('timestamp')
    scenarios['market_gap'] = gap_data
    
    # Flash crash scenario
    crash_prices = [150] * 30 + list(np.linspace(150, 120, 20)) + [120] * 50
    crash_data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01 09:30:00', periods=100, freq='5min'),
        'open': crash_prices[:-1] + [crash_prices[-1]],
        'high': [p * 1.01 for p in crash_prices],
        'low': [p * 0.99 for p in crash_prices],
        'close': crash_prices,
        'volume': [50000] * 100  # High volume during crash
    }).set_index('timestamp')
    scenarios['flash_crash'] = crash_data
    
    # Zero volume scenario
    zero_vol_data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01 09:30:00', periods=100, freq='5min'),
        'open': [150] * 100,
        'high': [150.01] * 100,
        'low': [149.99] * 100,
        'close': [150] * 100,
        'volume': [0] * 100
    }).set_index('timestamp')
    scenarios['zero_volume'] = zero_vol_data
    
    return scenarios


@pytest.fixture
def backtesting_scenarios():
    """Historical scenarios for backtesting validation."""
    return {
        'bull_market_2023': {
            'start_date': '2023-01-01',
            'end_date': '2023-06-30',
            'market_condition': 'bull',
            'expected_signals': 145,
            'expected_accuracy': 0.68
        },
        'bear_market_2022': {
            'start_date': '2022-06-01',
            'end_date': '2022-12-31',
            'market_condition': 'bear',
            'expected_signals': 178,
            'expected_accuracy': 0.52
        },
        'sideways_2021': {
            'start_date': '2021-08-01',
            'end_date': '2021-11-30',
            'market_condition': 'sideways',
            'expected_signals': 89,
            'expected_accuracy': 0.45
        },
        'volatile_2020': {
            'start_date': '2020-03-01',
            'end_date': '2020-04-30',
            'market_condition': 'volatile',
            'expected_signals': 234,
            'expected_accuracy': 0.38
        }
    }


def generate_test_signal_data(scenario: str, periods: int = 100) -> pd.DataFrame:
    """Generate test data for specific signal scenarios."""
    np.random.seed(hash(scenario) % 2**32)
    
    dates = pd.date_range(start='2024-01-01 09:30:00', periods=periods, freq='5min')
    
    if scenario == 'strong_buy_signals':
        # Generate oversold conditions with volume spikes
        base_price = 150.0
        prices = []
        volumes = []
        
        for i in range(periods):
            if i < periods // 3:  # Declining phase
                price = base_price * (1 - i * 0.01)
                volume = 20000 * (1 + i * 0.05)  # Increasing volume
            else:  # Recovery phase
                price = base_price * (0.67 + (i - periods//3) * 0.005)
                volume = 30000
            
            prices.append(price)
            volumes.append(int(volume))
        
    elif scenario == 'false_signals':
        # Generate choppy, sideways market
        base_price = 150.0
        prices = []
        for i in range(periods):
            noise = np.random.normal(0, 0.02)
            oscillation = 0.01 * np.sin(i / 10)
            prices.append(base_price * (1 + noise + oscillation))
        volumes = [15000] * periods
        
    else:  # Default scenario
        prices = [150.0 + np.random.normal(0, 5) for _ in range(periods)]
        volumes = [20000] * periods
    
    opens = prices[:-1] + [prices[-1]]
    closes = prices
    highs = [max(o, c) + abs(np.random.normal(0, 0.5)) for o, c in zip(opens, closes)]
    lows = [min(o, c) - abs(np.random.normal(0, 0.5)) for o, c in zip(opens, closes)]
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }).set_index('timestamp')


# Test data validation utilities
def validate_test_data(df: pd.DataFrame) -> bool:
    """Validate test data integrity."""
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    
    if not all(col in df.columns for col in required_columns):
        return False
    
    if df.isnull().any().any():
        return False
    
    if (df['high'] < df[['open', 'close']].max(axis=1)).any():
        return False
    
    if (df['low'] > df[['open', 'close']].min(axis=1)).any():
        return False
    
    if (df['volume'] < 0).any():
        return False
    
    return True


class TestDataGenerator:
    """Advanced test data generator for complex scenarios."""
    
    @staticmethod
    def create_multi_signal_scenario(num_buy_signals: int = 5, num_sell_signals: int = 5) -> pd.DataFrame:
        """Create data with specific number of buy/sell signals."""
        periods = 200
        dates = pd.date_range(start='2024-01-01 09:30:00', periods=periods, freq='5min')
        
        # Initialize base data
        base_price = 150.0
        prices = [base_price]
        volumes = []
        
        # Calculate signal positions
        buy_positions = np.linspace(20, periods-20, num_buy_signals).astype(int)
        sell_positions = np.linspace(30, periods-10, num_sell_signals).astype(int)
        
        for i in range(periods - 1):
            if i in buy_positions:
                # Create oversold condition
                change = -0.03  # 3% drop
                volume = 40000  # High volume
            elif i in sell_positions:
                # Create overbought condition
                change = 0.03  # 3% rise
                volume = 35000  # High volume
            else:
                # Normal market noise
                change = np.random.normal(0, 0.01)
                volume = np.random.randint(15000, 25000)
            
            prices.append(prices[-1] * (1 + change))
            volumes.append(volume)
        
        volumes.append(volumes[-1])  # Match length
        
        opens = prices[:-1] + [prices[-1]]
        closes = prices
        highs = [max(o, c) + abs(np.random.normal(0, 0.5)) for o, c in zip(opens, closes)]
        lows = [min(o, c) - abs(np.random.normal(0, 0.5)) for o, c in zip(opens, closes)]
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        }).set_index('timestamp')