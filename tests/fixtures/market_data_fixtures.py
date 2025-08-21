"""
Comprehensive market data fixtures for testing.
Provides realistic market scenarios and edge cases.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os


class MarketDataGenerator:
    """Generate realistic market data for testing."""
    
    def __init__(self, seed: int = 42):
        """Initialize with random seed for reproducible data."""
        np.random.seed(seed)
    
    def generate_intraday_data(self, symbol: str, date: str, 
                              start_price: float = 150.0,
                              volatility: float = 0.02,
                              trend: float = 0.0,
                              periods: int = 390) -> pd.DataFrame:
        """
        Generate realistic intraday price data.
        
        Args:
            symbol: Stock symbol
            date: Trading date (YYYY-MM-DD)
            start_price: Opening price
            volatility: Daily volatility (0.02 = 2%)
            trend: Daily trend (-0.05 to 0.05 for -5% to +5%)
            periods: Number of minutes (390 = full trading day)
        """
        # Create minute-by-minute timestamps
        start_time = pd.to_datetime(f"{date} 09:30:00")
        timestamps = pd.date_range(start=start_time, periods=periods, freq='1min')
        
        # Generate price movement using geometric Brownian motion
        dt = 1/390  # Fraction of trading day per minute
        drift = trend / 390  # Drift per minute
        vol_per_minute = volatility / np.sqrt(390)  # Volatility per minute
        
        # Generate random walks
        returns = np.random.normal(drift, vol_per_minute, periods)
        
        # Add some autocorrelation for realism
        for i in range(1, len(returns)):
            returns[i] += 0.1 * returns[i-1]
        
        # Calculate cumulative prices
        log_prices = np.log(start_price) + np.cumsum(returns)
        prices = np.exp(log_prices)
        
        # Create OHLC data for each minute
        ohlc_data = []
        for i, price in enumerate(prices):
            # Add some intra-minute volatility
            intra_vol = vol_per_minute * 0.5
            high = price * (1 + abs(np.random.normal(0, intra_vol)))
            low = price * (1 - abs(np.random.normal(0, intra_vol)))
            
            # Ensure OHLC consistency
            open_price = prices[i-1] if i > 0 else start_price
            close_price = price
            
            high = max(high, open_price, close_price)
            low = min(low, open_price, close_price)
            
            # Generate realistic volume
            base_volume = np.random.randint(1000, 5000)
            # Higher volume at open/close and during price movements
            if i < 30 or i > periods - 30:  # First/last 30 minutes
                volume_multiplier = np.random.uniform(1.5, 3.0)
            elif abs(returns[i]) > vol_per_minute:  # High price movement
                volume_multiplier = np.random.uniform(1.2, 2.0)
            else:
                volume_multiplier = 1.0
            
            volume = int(base_volume * volume_multiplier)
            
            ohlc_data.append({
                'timestamp': timestamps[i],
                'symbol': symbol,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
        
        return pd.DataFrame(ohlc_data)
    
    def generate_multi_day_data(self, symbol: str, start_date: str, 
                               days: int, start_price: float = 150.0) -> pd.DataFrame:
        """Generate multi-day historical data."""
        all_data = []
        current_price = start_price
        
        for i in range(days):
            date = (pd.to_datetime(start_date) + timedelta(days=i)).strftime('%Y-%m-%d')
            
            # Skip weekends
            if pd.to_datetime(date).weekday() >= 5:
                continue
            
            # Generate daily volatility and trend
            daily_vol = np.random.uniform(0.01, 0.04)  # 1-4% daily volatility
            daily_trend = np.random.normal(0, 0.002)   # Slight random trend
            
            # Generate day's data
            day_data = self.generate_intraday_data(
                symbol=symbol,
                date=date,
                start_price=current_price,
                volatility=daily_vol,
                trend=daily_trend
            )
            
            all_data.append(day_data)
            
            # Update price for next day
            current_price = day_data.iloc[-1]['close']
        
        return pd.concat(all_data, ignore_index=True)
    
    def generate_volatile_period(self, symbol: str, date: str,
                                start_price: float = 150.0) -> pd.DataFrame:
        """Generate data for a highly volatile trading day."""
        return self.generate_intraday_data(
            symbol=symbol,
            date=date,
            start_price=start_price,
            volatility=0.08,  # 8% volatility
            trend=np.random.choice([-0.05, 0.05])  # Strong trend
        )
    
    def generate_gap_event(self, symbol: str, date: str,
                          start_price: float = 150.0,
                          gap_percent: float = 0.05) -> pd.DataFrame:
        """Generate data with a price gap (earnings, news, etc.)."""
        # Gap up or down at market open
        gap_price = start_price * (1 + gap_percent)
        
        return self.generate_intraday_data(
            symbol=symbol,
            date=date,
            start_price=gap_price,
            volatility=0.04  # Higher volatility after gap
        )
    
    def generate_low_volume_day(self, symbol: str, date: str,
                               start_price: float = 150.0) -> pd.DataFrame:
        """Generate data for a low-volume, range-bound day."""
        data = self.generate_intraday_data(
            symbol=symbol,
            date=date,
            start_price=start_price,
            volatility=0.005,  # Very low volatility
            trend=0.0
        )
        
        # Reduce all volumes by 50-80%
        data['volume'] = (data['volume'] * np.random.uniform(0.2, 0.5, len(data))).astype(int)
        
        return data


class ScenarioBuilder:
    """Build specific market scenarios for testing."""
    
    def __init__(self):
        self.generator = MarketDataGenerator()
    
    def bull_market_scenario(self, symbol: str = "AAPL", days: int = 30) -> pd.DataFrame:
        """Create a bull market scenario with upward trend."""
        data_frames = []
        current_price = 150.0
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i)).strftime('%Y-%m-%d')
            
            if pd.to_datetime(date).weekday() >= 5:
                continue
            
            # Gradual upward trend with occasional pullbacks
            if i % 5 == 0 and i > 0:
                trend = -0.02  # 2% pullback
            else:
                trend = np.random.uniform(0.005, 0.02)  # 0.5% to 2% up
            
            day_data = self.generator.generate_intraday_data(
                symbol=symbol,
                date=date,
                start_price=current_price,
                volatility=0.02,
                trend=trend
            )
            
            data_frames.append(day_data)
            current_price = day_data.iloc[-1]['close']
        
        return pd.concat(data_frames, ignore_index=True)
    
    def bear_market_scenario(self, symbol: str = "AAPL", days: int = 30) -> pd.DataFrame:
        """Create a bear market scenario with downward trend."""
        data_frames = []
        current_price = 150.0
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i)).strftime('%Y-%m-%d')
            
            if pd.to_datetime(date).weekday() >= 5:
                continue
            
            # Gradual downward trend with occasional bounces
            if i % 4 == 0 and i > 0:
                trend = 0.015  # 1.5% bounce
            else:
                trend = np.random.uniform(-0.025, -0.005)  # 0.5% to 2.5% down
            
            day_data = self.generator.generate_intraday_data(
                symbol=symbol,
                date=date,
                start_price=current_price,
                volatility=0.03,  # Higher volatility in bear market
                trend=trend
            )
            
            data_frames.append(day_data)
            current_price = day_data.iloc[-1]['close']
        
        return pd.concat(data_frames, ignore_index=True)
    
    def sideways_market_scenario(self, symbol: str = "AAPL", days: int = 30) -> pd.DataFrame:
        """Create a sideways/range-bound market scenario."""
        data_frames = []
        current_price = 150.0
        range_center = current_price
        range_width = 0.05  # 5% range
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i)).strftime('%Y-%m-%d')
            
            if pd.to_datetime(date).weekday() >= 5:
                continue
            
            # Mean-reverting behavior
            distance_from_center = (current_price - range_center) / range_center
            
            if distance_from_center > range_width/2:
                trend = -0.01  # Pull back down
            elif distance_from_center < -range_width/2:
                trend = 0.01   # Pull back up
            else:
                trend = np.random.uniform(-0.005, 0.005)  # Random walk
            
            day_data = self.generator.generate_intraday_data(
                symbol=symbol,
                date=date,
                start_price=current_price,
                volatility=0.015,
                trend=trend
            )
            
            data_frames.append(day_data)
            current_price = day_data.iloc[-1]['close']
        
        return pd.concat(data_frames, ignore_index=True)
    
    def earnings_announcement_scenario(self, symbol: str = "AAPL") -> pd.DataFrame:
        """Create earnings announcement scenario with gap and volatility."""
        date = datetime.now().strftime('%Y-%m-%d')
        
        # Random earnings surprise (positive or negative)
        surprise = np.random.choice([-1, 1]) * np.random.uniform(0.03, 0.08)
        
        return self.generator.generate_gap_event(
            symbol=symbol,
            date=date,
            start_price=150.0,
            gap_percent=surprise
        )
    
    def market_crash_scenario(self, symbol: str = "AAPL") -> pd.DataFrame:
        """Create market crash scenario with sharp decline."""
        date = datetime.now().strftime('%Y-%m-%d')
        
        return self.generator.generate_intraday_data(
            symbol=symbol,
            date=date,
            start_price=150.0,
            volatility=0.12,  # 12% volatility
            trend=-0.15       # 15% decline
        )


class IndicatorDataBuilder:
    """Build data with specific technical indicator patterns."""
    
    @staticmethod
    def create_oversold_rsi_pattern(base_data: pd.DataFrame) -> pd.DataFrame:
        """Create data pattern that would generate oversold RSI signals."""
        data = base_data.copy()
        
        # Force declining prices to create oversold condition
        decline_periods = 20
        for i in range(len(data) - decline_periods, len(data)):
            if i > 0:
                # Gradual decline
                data.loc[i, 'close'] = data.loc[i-1, 'close'] * 0.995
                data.loc[i, 'low'] = min(data.loc[i, 'low'], data.loc[i, 'close'])
                data.loc[i, 'high'] = max(data.loc[i, 'high'], data.loc[i, 'close'])
        
        return data
    
    @staticmethod
    def create_overbought_rsi_pattern(base_data: pd.DataFrame) -> pd.DataFrame:
        """Create data pattern that would generate overbought RSI signals."""
        data = base_data.copy()
        
        # Force rising prices to create overbought condition
        rise_periods = 20
        for i in range(len(data) - rise_periods, len(data)):
            if i > 0:
                # Gradual rise
                data.loc[i, 'close'] = data.loc[i-1, 'close'] * 1.005
                data.loc[i, 'high'] = max(data.loc[i, 'high'], data.loc[i, 'close'])
                data.loc[i, 'low'] = min(data.loc[i, 'low'], data.loc[i, 'close'])
        
        return data
    
    @staticmethod
    def create_ema_crossover_pattern(base_data: pd.DataFrame, 
                                   crossover_type: str = "bullish") -> pd.DataFrame:
        """Create EMA crossover pattern."""
        data = base_data.copy()
        
        if crossover_type == "bullish":
            # Create upward price movement for bullish crossover
            trend_periods = 30
            for i in range(len(data) - trend_periods, len(data)):
                if i > 0:
                    data.loc[i, 'close'] = data.loc[i-1, 'close'] * 1.003
                    data.loc[i, 'high'] = max(data.loc[i, 'high'], data.loc[i, 'close'])
                    data.loc[i, 'low'] = min(data.loc[i, 'low'], data.loc[i, 'close'])
        else:
            # Create downward price movement for bearish crossover
            trend_periods = 30
            for i in range(len(data) - trend_periods, len(data)):
                if i > 0:
                    data.loc[i, 'close'] = data.loc[i-1, 'close'] * 0.997
                    data.loc[i, 'low'] = min(data.loc[i, 'low'], data.loc[i, 'close'])
                    data.loc[i, 'high'] = max(data.loc[i, 'high'], data.loc[i, 'close'])
        
        return data


class FixtureManager:
    """Manage and provide market data fixtures."""
    
    def __init__(self, fixtures_dir: str = "tests/fixtures/data"):
        self.fixtures_dir = fixtures_dir
        self.scenario_builder = ScenarioBuilder()
        self.indicator_builder = IndicatorDataBuilder()
        
        # Ensure fixtures directory exists
        os.makedirs(fixtures_dir, exist_ok=True)
    
    def get_or_create_fixture(self, fixture_name: str, 
                             generator_func, *args, **kwargs) -> pd.DataFrame:
        """Get existing fixture or create new one."""
        fixture_path = os.path.join(self.fixtures_dir, f"{fixture_name}.csv")
        
        if os.path.exists(fixture_path):
            # Load existing fixture
            return pd.read_csv(fixture_path, parse_dates=['timestamp'])
        else:
            # Create new fixture
            data = generator_func(*args, **kwargs)
            data.to_csv(fixture_path, index=False)
            return data
    
    def create_all_standard_fixtures(self):
        """Create all standard market data fixtures."""
        fixtures = {
            'bull_market_30d': lambda: self.scenario_builder.bull_market_scenario(days=30),
            'bear_market_30d': lambda: self.scenario_builder.bear_market_scenario(days=30),
            'sideways_market_30d': lambda: self.scenario_builder.sideways_market_scenario(days=30),
            'volatile_day': lambda: self.scenario_builder.generator.generate_volatile_period(
                'AAPL', datetime.now().strftime('%Y-%m-%d')
            ),
            'earnings_gap': lambda: self.scenario_builder.earnings_announcement_scenario(),
            'market_crash': lambda: self.scenario_builder.market_crash_scenario(),
            'low_volume_day': lambda: self.scenario_builder.generator.generate_low_volume_day(
                'AAPL', datetime.now().strftime('%Y-%m-%d')
            )
        }
        
        for name, generator in fixtures.items():
            self.get_or_create_fixture(name, generator)
    
    def get_test_symbols_data(self, symbols: List[str], days: int = 30) -> Dict[str, pd.DataFrame]:
        """Get test data for multiple symbols."""
        data = {}
        
        for symbol in symbols:
            fixture_name = f"{symbol.lower()}_test_data_{days}d"
            data[symbol] = self.get_or_create_fixture(
                fixture_name,
                self.scenario_builder.generator.generate_multi_day_data,
                symbol=symbol,
                start_date=(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
                days=days
            )
        
        return data


# Utility functions for quick fixture access
def get_standard_market_data(symbol: str = "AAPL", periods: int = 100) -> pd.DataFrame:
    """Get standard market data for testing."""
    generator = MarketDataGenerator()
    return generator.generate_intraday_data(
        symbol=symbol,
        date=datetime.now().strftime('%Y-%m-%d'),
        periods=periods
    )


def get_trending_data(direction: str = "up", symbol: str = "AAPL") -> pd.DataFrame:
    """Get trending market data."""
    generator = MarketDataGenerator()
    trend = 0.02 if direction == "up" else -0.02
    
    return generator.generate_intraday_data(
        symbol=symbol,
        date=datetime.now().strftime('%Y-%m-%d'),
        trend=trend,
        volatility=0.015
    )


def get_high_volatility_data(symbol: str = "AAPL") -> pd.DataFrame:
    """Get high volatility market data."""
    generator = MarketDataGenerator()
    return generator.generate_volatile_period(
        symbol=symbol,
        date=datetime.now().strftime('%Y-%m-%d')
    )


def get_rsi_signal_data(signal_type: str = "oversold", symbol: str = "AAPL") -> pd.DataFrame:
    """Get data that would generate specific RSI signals."""
    base_data = get_standard_market_data(symbol, 100)
    
    if signal_type == "oversold":
        return IndicatorDataBuilder.create_oversold_rsi_pattern(base_data)
    elif signal_type == "overbought":
        return IndicatorDataBuilder.create_overbought_rsi_pattern(base_data)
    else:
        return base_data


def get_ema_crossover_data(crossover_type: str = "bullish", symbol: str = "AAPL") -> pd.DataFrame:
    """Get data that would generate EMA crossover signals."""
    base_data = get_standard_market_data(symbol, 100)
    return IndicatorDataBuilder.create_ema_crossover_pattern(base_data, crossover_type)


# Export commonly used fixtures
__all__ = [
    'MarketDataGenerator',
    'ScenarioBuilder', 
    'IndicatorDataBuilder',
    'FixtureManager',
    'get_standard_market_data',
    'get_trending_data',
    'get_high_volatility_data',
    'get_rsi_signal_data',
    'get_ema_crossover_data'
]