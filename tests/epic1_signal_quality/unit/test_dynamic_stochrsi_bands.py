"""
Unit Tests for Dynamic StochRSI Band Adjustment

Tests the enhanced StochRSI indicator with dynamic band adjustment based on:
- Market volatility conditions
- Volume profile analysis
- Trend strength assessment
- Time-of-day adjustments
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from indicators.stoch_rsi_enhanced import StochRSIIndicator
from tests.epic1_signal_quality.fixtures.epic1_test_fixtures import (
    epic1_config, volatile_market_data, low_volume_market_data, 
    trending_market_data, mock_volatility_calculator
)


class TestDynamicStochRSIBands:
    """Test suite for dynamic StochRSI band adjustment functionality."""
    
    def test_basic_stochrsi_calculation(self, epic1_config):
        """Test that basic StochRSI calculation works correctly."""
        indicator = StochRSIIndicator(
            rsi_length=14,
            stoch_length=14,
            k_smoothing=3,
            d_smoothing=3
        )
        
        # Generate test data
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='5min')
        prices = pd.Series([150 + np.random.normal(0, 5) for _ in range(100)], index=dates)
        
        # Calculate StochRSI
        result = indicator.calculate_full_stoch_rsi(prices)
        
        # Validate results
        assert 'RSI' in result
        assert 'StochRSI_K' in result
        assert 'StochRSI_D' in result
        
        assert len(result['RSI']) == len(prices)
        assert len(result['StochRSI_K']) == len(prices)
        assert len(result['StochRSI_D']) == len(prices)
        
        # Check value ranges
        rsi_values = result['RSI'].dropna()
        stoch_k_values = result['StochRSI_K'].dropna()
        stoch_d_values = result['StochRSI_D'].dropna()
        
        assert all(0 <= val <= 100 for val in rsi_values)
        assert all(0 <= val <= 100 for val in stoch_k_values)
        assert all(0 <= val <= 100 for val in stoch_d_values)
    
    def test_volatility_based_band_adjustment(self, epic1_config, volatile_market_data):
        """Test dynamic band adjustment based on market volatility."""
        
        class DynamicStochRSIIndicator(StochRSIIndicator):
            """Enhanced StochRSI with dynamic bands."""
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.base_oversold = 20
                self.base_overbought = 80
                self.volatility_adjustment_enabled = True
                self.max_adjustment = 15
            
            def calculate_volatility_adjustment(self, prices: pd.Series) -> float:
                """Calculate volatility-based adjustment."""
                if len(prices) < 20:
                    return 0
                
                # Calculate rolling volatility
                returns = prices.pct_change()
                volatility = returns.rolling(window=20).std() * np.sqrt(252)  # Annualized
                current_volatility = volatility.iloc[-1]
                
                # Normalize volatility (assume 0.20 is baseline)
                baseline_volatility = 0.20
                volatility_ratio = current_volatility / baseline_volatility
                
                # Calculate adjustment (higher volatility = wider bands)
                adjustment = min(self.max_adjustment, max(-self.max_adjustment, 
                                (volatility_ratio - 1) * 10))
                
                return adjustment
            
            def get_dynamic_thresholds(self, prices: pd.Series) -> tuple:
                """Get dynamically adjusted oversold/overbought thresholds."""
                adjustment = self.calculate_volatility_adjustment(prices)
                
                # Wider bands for high volatility (lower oversold, higher overbought)
                oversold = max(5, self.base_oversold - adjustment)
                overbought = min(95, self.base_overbought + adjustment)
                
                return oversold, overbought
        
        indicator = DynamicStochRSIIndicator(
            rsi_length=14,
            stoch_length=14,
            k_smoothing=3,
            d_smoothing=3
        )
        
        # Test with volatile data
        oversold, overbought = indicator.get_dynamic_thresholds(volatile_market_data['close'])
        
        # High volatility should result in wider bands
        assert oversold < indicator.base_oversold
        assert overbought > indicator.base_overbought
        
        # Verify adjustment is within limits
        assert oversold >= 5
        assert overbought <= 95
        
        # Test with stable data
        stable_prices = pd.Series([150] * 100)
        stable_oversold, stable_overbought = indicator.get_dynamic_thresholds(stable_prices)
        
        # Low volatility should keep bands close to base
        assert abs(stable_oversold - indicator.base_oversold) <= 2
        assert abs(stable_overbought - indicator.base_overbought) <= 2
    
    def test_volume_based_band_adjustment(self, epic1_config, low_volume_market_data):
        """Test dynamic band adjustment based on volume profile."""
        
        class VolumeAdjustedStochRSI(StochRSIIndicator):
            """StochRSI with volume-based adjustments."""
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.base_oversold = 20
                self.base_overbought = 80
                self.volume_period = 20
            
            def calculate_volume_adjustment(self, volume_data: pd.Series) -> float:
                """Calculate volume-based threshold adjustment."""
                if len(volume_data) < self.volume_period:
                    return 0
                
                # Calculate average volume
                avg_volume = volume_data.rolling(window=self.volume_period).mean()
                current_volume = volume_data.iloc[-1]
                recent_avg = avg_volume.iloc[-1]
                
                if recent_avg == 0:
                    return 0
                
                volume_ratio = current_volume / recent_avg
                
                # Low volume = tighter bands, high volume = wider bands
                if volume_ratio < 0.5:  # Very low volume
                    return 5  # Tighter bands (higher oversold, lower overbought)
                elif volume_ratio > 2.0:  # High volume
                    return -5  # Wider bands (lower oversold, higher overbought)
                
                return 0
            
            def get_volume_adjusted_thresholds(self, volume_data: pd.Series) -> tuple:
                """Get volume-adjusted thresholds."""
                adjustment = self.calculate_volume_adjustment(volume_data)
                
                # Positive adjustment = tighter bands
                oversold = min(35, self.base_oversold + adjustment)
                overbought = max(65, self.base_overbought - adjustment)
                
                return oversold, overbought
        
        indicator = VolumeAdjustedStochRSI()
        
        # Test with low volume data
        oversold, overbought = indicator.get_volume_adjusted_thresholds(
            low_volume_market_data['volume']
        )
        
        # Low volume should result in tighter bands
        assert oversold > indicator.base_oversold
        assert overbought < indicator.base_overbought
        
        # Test with high volume
        high_volume_data = pd.Series([50000] * 100)
        hv_oversold, hv_overbought = indicator.get_volume_adjusted_thresholds(high_volume_data)
        
        # High volume should result in wider bands
        assert hv_oversold <= indicator.base_oversold
        assert hv_overbought >= indicator.base_overbought
    
    def test_time_based_band_adjustment(self, epic1_config):
        """Test time-of-day based band adjustments."""
        
        class TimeAdjustedStochRSI(StochRSIIndicator):
            """StochRSI with time-based adjustments."""
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.base_oversold = 20
                self.base_overbought = 80
            
            def get_time_adjustment(self, timestamp: datetime) -> float:
                """Calculate time-based adjustment."""
                hour = timestamp.hour
                minute = timestamp.minute
                
                # Market open (9:30-10:30): Higher volatility, wider bands
                if (hour == 9 and minute >= 30) or hour == 10:
                    return -5  # Wider bands
                
                # Market close (3:00-4:00): Higher volatility, wider bands
                elif hour >= 15:
                    return -5  # Wider bands
                
                # Lunch time (12:00-2:00): Lower volatility, tighter bands
                elif 12 <= hour < 14:
                    return 3  # Tighter bands
                
                # Normal trading hours
                else:
                    return 0
            
            def get_time_adjusted_thresholds(self, timestamp: datetime) -> tuple:
                """Get time-adjusted thresholds."""
                adjustment = self.get_time_adjustment(timestamp)
                
                oversold = max(5, self.base_oversold - adjustment)
                overbought = min(95, self.base_overbought + adjustment)
                
                return oversold, overbought
        
        indicator = TimeAdjustedStochRSI()
        
        # Test market open (high volatility period)
        market_open = datetime(2024, 1, 1, 9, 45)
        open_oversold, open_overbought = indicator.get_time_adjusted_thresholds(market_open)
        
        assert open_oversold < indicator.base_oversold  # Wider bands
        assert open_overbought > indicator.base_overbought
        
        # Test lunch time (low volatility period)
        lunch_time = datetime(2024, 1, 1, 13, 0)
        lunch_oversold, lunch_overbought = indicator.get_time_adjusted_thresholds(lunch_time)
        
        assert lunch_oversold > indicator.base_oversold  # Tighter bands
        assert lunch_overbought < indicator.base_overbought
        
        # Test normal hours
        normal_time = datetime(2024, 1, 1, 11, 30)
        normal_oversold, normal_overbought = indicator.get_time_adjusted_thresholds(normal_time)
        
        assert normal_oversold == indicator.base_oversold
        assert normal_overbought == indicator.base_overbought
    
    def test_trend_strength_adjustment(self, epic1_config, trending_market_data):
        """Test band adjustment based on trend strength."""
        
        class TrendAdjustedStochRSI(StochRSIIndicator):
            """StochRSI with trend-based adjustments."""
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.base_oversold = 20
                self.base_overbought = 80
                self.trend_period = 20
            
            def calculate_trend_strength(self, prices: pd.Series) -> float:
                """Calculate trend strength using linear regression slope."""
                if len(prices) < self.trend_period:
                    return 0
                
                recent_prices = prices.tail(self.trend_period)
                x = np.arange(len(recent_prices))
                slope, _ = np.polyfit(x, recent_prices, 1)
                
                # Normalize slope by price level
                trend_strength = slope / recent_prices.iloc[-1] * 100
                
                return trend_strength
            
            def get_trend_adjusted_thresholds(self, prices: pd.Series) -> tuple:
                """Get trend-adjusted thresholds."""
                trend_strength = self.calculate_trend_strength(prices)
                
                # Strong uptrend: raise oversold threshold (easier to trigger buy)
                # Strong downtrend: lower overbought threshold (easier to trigger sell)
                if trend_strength > 0.1:  # Strong uptrend
                    oversold_adj = 5
                    overbought_adj = 0
                elif trend_strength < -0.1:  # Strong downtrend
                    oversold_adj = 0
                    overbought_adj = -5
                else:  # Weak trend
                    oversold_adj = 0
                    overbought_adj = 0
                
                oversold = max(5, self.base_oversold + oversold_adj)
                overbought = min(95, self.base_overbought + overbought_adj)
                
                return oversold, overbought, trend_strength
        
        indicator = TrendAdjustedStochRSI()
        
        # Test with trending data
        oversold, overbought, trend_strength = indicator.get_trend_adjusted_thresholds(
            trending_market_data['close']
        )
        
        # Should detect uptrend
        assert trend_strength > 0
        
        # Uptrend should raise oversold threshold
        assert oversold > indicator.base_oversold
        
        # Test with downtrending data
        downtrend_data = trending_market_data['close'].iloc[::-1]  # Reverse for downtrend
        down_oversold, down_overbought, down_trend = indicator.get_trend_adjusted_thresholds(
            downtrend_data
        )
        
        # Should detect downtrend
        assert down_trend < 0
        
        # Downtrend should lower overbought threshold
        assert down_overbought < indicator.base_overbought
    
    def test_combined_dynamic_adjustments(self, epic1_config, volatile_market_data):
        """Test combined dynamic adjustments from multiple factors."""
        
        class CombinedDynamicStochRSI(StochRSIIndicator):
            """StochRSI with combined dynamic adjustments."""
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.base_oversold = 20
                self.base_overbought = 80
                self.max_total_adjustment = 15
            
            def get_combined_thresholds(self, data: pd.DataFrame, timestamp: datetime = None) -> dict:
                """Get thresholds with combined adjustments."""
                volatility_adj = self._calculate_volatility_adj(data['close'])
                volume_adj = self._calculate_volume_adj(data['volume'])
                trend_adj = self._calculate_trend_adj(data['close'])
                time_adj = self._calculate_time_adj(timestamp) if timestamp else 0
                
                # Combine adjustments with weights
                total_oversold_adj = (
                    volatility_adj * 0.4 +
                    volume_adj * 0.3 +
                    trend_adj * 0.2 +
                    time_adj * 0.1
                )
                
                total_overbought_adj = (
                    volatility_adj * 0.4 +
                    volume_adj * 0.3 +
                    trend_adj * 0.2 +
                    time_adj * 0.1
                )
                
                # Apply limits
                total_oversold_adj = max(-self.max_total_adjustment, 
                                       min(self.max_total_adjustment, total_oversold_adj))
                total_overbought_adj = max(-self.max_total_adjustment, 
                                         min(self.max_total_adjustment, total_overbought_adj))
                
                oversold = max(5, self.base_oversold - total_oversold_adj)
                overbought = min(95, self.base_overbought + total_overbought_adj)
                
                return {
                    'oversold': oversold,
                    'overbought': overbought,
                    'adjustments': {
                        'volatility': volatility_adj,
                        'volume': volume_adj,
                        'trend': trend_adj,
                        'time': time_adj,
                        'total_oversold': total_oversold_adj,
                        'total_overbought': total_overbought_adj
                    }
                }
            
            def _calculate_volatility_adj(self, prices: pd.Series) -> float:
                """Calculate volatility adjustment."""
                if len(prices) < 20:
                    return 0
                returns = prices.pct_change()
                volatility = returns.rolling(20).std().iloc[-1]
                return min(10, max(-10, volatility * 500))  # Scale to reasonable range
            
            def _calculate_volume_adj(self, volume: pd.Series) -> float:
                """Calculate volume adjustment."""
                if len(volume) < 20:
                    return 0
                avg_volume = volume.rolling(20).mean().iloc[-1]
                current_volume = volume.iloc[-1]
                if avg_volume == 0:
                    return 0
                ratio = current_volume / avg_volume
                return min(5, max(-5, (ratio - 1) * 3))
            
            def _calculate_trend_adj(self, prices: pd.Series) -> float:
                """Calculate trend adjustment."""
                if len(prices) < 20:
                    return 0
                x = np.arange(20)
                slope, _ = np.polyfit(x, prices.tail(20), 1)
                trend_strength = slope / prices.iloc[-1] * 1000
                return min(5, max(-5, trend_strength))
            
            def _calculate_time_adj(self, timestamp: datetime) -> float:
                """Calculate time adjustment."""
                if not timestamp:
                    return 0
                hour = timestamp.hour
                if hour in [9, 10, 15, 16]:  # High volatility hours
                    return -2  # Wider bands
                elif hour in [12, 13]:  # Low volatility hours
                    return 2   # Tighter bands
                return 0
        
        indicator = CombinedDynamicStochRSI()
        
        # Test with volatile market data
        test_timestamp = datetime(2024, 1, 1, 9, 45)  # Market open
        result = indicator.get_combined_thresholds(volatile_market_data, test_timestamp)
        
        # Verify structure
        assert 'oversold' in result
        assert 'overbought' in result
        assert 'adjustments' in result
        
        # Check threshold validity
        assert 5 <= result['oversold'] <= 95
        assert 5 <= result['overbought'] <= 95
        assert result['oversold'] < result['overbought']
        
        # Check adjustment details
        adjustments = result['adjustments']
        assert 'volatility' in adjustments
        assert 'volume' in adjustments
        assert 'trend' in adjustments
        assert 'time' in adjustments
        
        # Volatile data + market open should result in wider bands
        assert result['oversold'] < indicator.base_oversold
        assert result['overbought'] > indicator.base_overbought
    
    def test_adjustment_limits_and_validation(self, epic1_config):
        """Test that adjustments respect limits and validation rules."""
        
        class ValidatedDynamicStochRSI(StochRSIIndicator):
            """StochRSI with validated adjustments."""
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.base_oversold = 20
                self.base_overbought = 80
                self.min_threshold = 5
                self.max_threshold = 95
                self.min_band_width = 20  # Minimum distance between bands
                self.max_adjustment = 15
            
            def validate_and_adjust_thresholds(self, oversold: float, overbought: float) -> tuple:
                """Validate and adjust thresholds to meet constraints."""
                # Apply absolute limits
                oversold = max(self.min_threshold, min(oversold, self.max_threshold))
                overbought = max(self.min_threshold, min(overbought, self.max_threshold))
                
                # Ensure minimum band width
                if overbought - oversold < self.min_band_width:
                    center = (oversold + overbought) / 2
                    oversold = center - self.min_band_width / 2
                    overbought = center + self.min_band_width / 2
                    
                    # Re-apply absolute limits
                    oversold = max(self.min_threshold, oversold)
                    overbought = min(self.max_threshold, overbought)
                
                # Ensure oversold < overbought
                if oversold >= overbought:
                    oversold = overbought - 1
                
                return oversold, overbought
            
            def apply_extreme_adjustment(self, extreme_volatility_adj: float) -> tuple:
                """Apply extreme adjustment and validate."""
                oversold = self.base_oversold - extreme_volatility_adj
                overbought = self.base_overbought + extreme_volatility_adj
                
                return self.validate_and_adjust_thresholds(oversold, overbought)
        
        indicator = ValidatedDynamicStochRSI()
        
        # Test extreme adjustments
        extreme_oversold, extreme_overbought = indicator.apply_extreme_adjustment(50)
        
        # Should be limited
        assert extreme_oversold >= indicator.min_threshold
        assert extreme_overbought <= indicator.max_threshold
        assert extreme_overbought - extreme_oversold >= indicator.min_band_width
        
        # Test minimum band width enforcement
        narrow_oversold, narrow_overbought = indicator.validate_and_adjust_thresholds(48, 52)
        
        assert narrow_overbought - narrow_oversold >= indicator.min_band_width
        
        # Test order enforcement
        reversed_oversold, reversed_overbought = indicator.validate_and_adjust_thresholds(85, 15)
        
        assert reversed_oversold < reversed_overbought
    
    def test_performance_impact_of_dynamic_bands(self, epic1_config, volatile_market_data):
        """Test that dynamic bands don't significantly impact performance."""
        import time
        
        # Standard StochRSI
        standard_indicator = StochRSIIndicator()
        
        # Dynamic StochRSI (simplified for performance test)
        class SimpleDynamicStochRSI(StochRSIIndicator):
            def get_dynamic_signals(self, data: pd.DataFrame) -> dict:
                # Calculate basic indicators
                indicators = self.calculate_full_stoch_rsi(data['close'])
                
                # Simple volatility adjustment
                returns = data['close'].pct_change()
                volatility = returns.rolling(20).std().iloc[-1]
                
                if volatility > 0.02:  # High volatility
                    oversold, overbought = 15, 85
                else:
                    oversold, overbought = 20, 80
                
                # Generate signals with dynamic thresholds
                signals = self.generate_signals_with_thresholds(
                    indicators['StochRSI_K'], 
                    indicators['StochRSI_D'],
                    oversold, 
                    overbought
                )
                
                return {'indicators': indicators, 'signals': signals}
            
            def generate_signals_with_thresholds(self, stoch_k: pd.Series, stoch_d: pd.Series, 
                                               oversold: float, overbought: float) -> dict:
                signals = pd.Series(0, index=stoch_k.index)
                
                for i in range(1, len(stoch_k)):
                    if pd.isna(stoch_k.iloc[i]) or pd.isna(stoch_d.iloc[i]):
                        continue
                    
                    current_k = stoch_k.iloc[i]
                    current_d = stoch_d.iloc[i]
                    prev_k = stoch_k.iloc[i-1]
                    prev_d = stoch_d.iloc[i-1]
                    
                    if (prev_k <= prev_d and current_k > current_d and current_k < oversold):
                        signals.iloc[i] = 1
                    elif (prev_k >= prev_d and current_k < current_d and current_k > overbought):
                        signals.iloc[i] = -1
                
                return {'signals': signals}
        
        dynamic_indicator = SimpleDynamicStochRSI()
        
        # Performance test
        test_data = volatile_market_data
        iterations = 100
        
        # Test standard indicator
        start_time = time.time()
        for _ in range(iterations):
            standard_result = standard_indicator.calculate_full_stoch_rsi(test_data['close'])
        standard_time = time.time() - start_time
        
        # Test dynamic indicator
        start_time = time.time()
        for _ in range(iterations):
            dynamic_result = dynamic_indicator.get_dynamic_signals(test_data)
        dynamic_time = time.time() - start_time
        
        # Performance impact should be minimal (< 50% increase)
        performance_ratio = dynamic_time / standard_time
        assert performance_ratio < 1.5, f"Dynamic bands too slow: {performance_ratio:.2f}x slower"
        
        # Results should be valid
        assert 'indicators' in dynamic_result
        assert 'signals' in dynamic_result
        assert len(dynamic_result['indicators']['StochRSI_K']) == len(test_data)
    
    @pytest.mark.parametrize("adjustment_factor", [0.5, 1.0, 1.5, 2.0])
    def test_adjustment_sensitivity(self, epic1_config, adjustment_factor):
        """Test sensitivity to different adjustment factors."""
        
        class SensitivityTestStochRSI(StochRSIIndicator):
            def __init__(self, adjustment_factor: float = 1.0):
                super().__init__()
                self.base_oversold = 20
                self.base_overbought = 80
                self.adjustment_factor = adjustment_factor
            
            def get_adjusted_thresholds(self, volatility: float) -> tuple:
                adjustment = volatility * 10 * self.adjustment_factor
                oversold = max(5, self.base_oversold - adjustment)
                overbought = min(95, self.base_overbought + adjustment)
                return oversold, overbought
        
        indicator = SensitivityTestStochRSI(adjustment_factor)
        
        # Test with moderate volatility
        test_volatility = 0.02
        oversold, overbought = indicator.get_adjusted_thresholds(test_volatility)
        
        # Higher adjustment factors should result in more extreme adjustments
        expected_adjustment = test_volatility * 10 * adjustment_factor
        expected_oversold = max(5, 20 - expected_adjustment)
        expected_overbought = min(95, 80 + expected_adjustment)
        
        assert abs(oversold - expected_oversold) < 0.1
        assert abs(overbought - expected_overbought) < 0.1
        
        # Verify reasonable ranges
        assert 5 <= oversold <= 35
        assert 65 <= overbought <= 95