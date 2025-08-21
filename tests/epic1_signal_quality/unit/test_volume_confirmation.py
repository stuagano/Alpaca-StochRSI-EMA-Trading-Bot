"""
Unit Tests for Volume Confirmation Filter

Tests the volume confirmation system that validates signals based on:
- Volume spike detection
- Volume profile analysis
- Volume trend confirmation
- Average volume comparisons
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

from tests.epic1_signal_quality.fixtures.epic1_test_fixtures import (
    epic1_config, low_volume_market_data, volatile_market_data, mock_volume_profile
)


class VolumeConfirmationFilter:
    """Enhanced volume confirmation filter for signal validation."""
    
    def __init__(self, config: dict):
        self.volume_threshold_multiplier = config.get('volume_threshold_multiplier', 1.5)
        self.volume_period = config.get('volume_period', 20)
        self.require_volume_spike = config.get('require_volume_spike', True)
        self.volume_spike_threshold = config.get('volume_spike_threshold', 2.0)
        self.min_volume_percentile = config.get('min_volume_percentile', 0.3)
    
    def calculate_volume_metrics(self, volume_data: pd.Series) -> dict:
        """Calculate comprehensive volume metrics."""
        if len(volume_data) < self.volume_period:
            return {
                'avg_volume': volume_data.mean(),
                'current_volume': volume_data.iloc[-1] if len(volume_data) > 0 else 0,
                'volume_ratio': 1.0,
                'volume_percentile': 0.5,
                'is_volume_spike': False,
                'volume_trend': 'stable'
            }
        
        current_volume = volume_data.iloc[-1]
        avg_volume = volume_data.rolling(window=self.volume_period).mean().iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Calculate percentile
        recent_volumes = volume_data.tail(self.volume_period * 2)
        volume_percentile = (recent_volumes < current_volume).sum() / len(recent_volumes)
        
        # Detect volume spike
        is_volume_spike = volume_ratio >= self.volume_spike_threshold
        
        # Calculate volume trend
        if len(volume_data) >= self.volume_period * 2:
            recent_avg = volume_data.tail(self.volume_period).mean()
            older_avg = volume_data.tail(self.volume_period * 2).head(self.volume_period).mean()
            trend_ratio = recent_avg / older_avg if older_avg > 0 else 1.0
            
            if trend_ratio > 1.2:
                volume_trend = 'increasing'
            elif trend_ratio < 0.8:
                volume_trend = 'decreasing'
            else:
                volume_trend = 'stable'
        else:
            volume_trend = 'stable'
        
        return {
            'avg_volume': avg_volume,
            'current_volume': current_volume,
            'volume_ratio': volume_ratio,
            'volume_percentile': volume_percentile,
            'is_volume_spike': is_volume_spike,
            'volume_trend': volume_trend
        }
    
    def validate_signal_volume(self, volume_data: pd.Series, signal_type: str = 'buy') -> dict:
        """Validate a signal based on volume confirmation."""
        metrics = self.calculate_volume_metrics(volume_data)
        
        # Base volume validation
        volume_confirmed = metrics['volume_ratio'] >= self.volume_threshold_multiplier
        
        # Additional validation rules
        validation_score = 0.0
        validation_reasons = []
        
        # Volume ratio check
        if metrics['volume_ratio'] >= self.volume_threshold_multiplier:
            validation_score += 0.3
            validation_reasons.append(f"Volume {metrics['volume_ratio']:.2f}x above average")
        else:
            validation_reasons.append(f"Volume only {metrics['volume_ratio']:.2f}x average (below {self.volume_threshold_multiplier}x threshold)")
        
        # Volume spike check
        if self.require_volume_spike and metrics['is_volume_spike']:
            validation_score += 0.3
            validation_reasons.append("Volume spike detected")
        elif self.require_volume_spike:
            validation_reasons.append("No volume spike detected")
        
        # Volume percentile check
        if metrics['volume_percentile'] >= self.min_volume_percentile:
            validation_score += 0.2
            validation_reasons.append(f"Volume in {metrics['volume_percentile']:.0%} percentile")
        else:
            validation_reasons.append(f"Volume below {self.min_volume_percentile:.0%} percentile")
        
        # Volume trend check
        if metrics['volume_trend'] == 'increasing':
            validation_score += 0.2
            validation_reasons.append("Volume trend increasing")
        elif metrics['volume_trend'] == 'stable':
            validation_score += 0.1
            validation_reasons.append("Volume trend stable")
        else:
            validation_reasons.append("Volume trend decreasing")
        
        return {
            'volume_confirmed': volume_confirmed,
            'validation_score': validation_score,
            'validation_reasons': validation_reasons,
            'metrics': metrics,
            'confidence': min(1.0, validation_score)
        }
    
    def get_volume_quality_score(self, volume_data: pd.Series) -> float:
        """Calculate overall volume quality score (0.0 to 1.0)."""
        metrics = self.calculate_volume_metrics(volume_data)
        
        score = 0.0
        
        # Volume ratio component (0-0.4)
        ratio_score = min(0.4, (metrics['volume_ratio'] - 1.0) * 0.2)
        score += max(0, ratio_score)
        
        # Percentile component (0-0.3)
        percentile_score = metrics['volume_percentile'] * 0.3
        score += percentile_score
        
        # Trend component (0-0.3)
        if metrics['volume_trend'] == 'increasing':
            trend_score = 0.3
        elif metrics['volume_trend'] == 'stable':
            trend_score = 0.2
        else:
            trend_score = 0.1
        score += trend_score
        
        return min(1.0, score)


class TestVolumeConfirmationFilter:
    """Test suite for volume confirmation filter functionality."""
    
    def test_basic_volume_metrics_calculation(self, epic1_config):
        """Test basic volume metrics calculation."""
        filter_instance = VolumeConfirmationFilter(epic1_config['volume_confirmation'])
        
        # Create test volume data
        volume_data = pd.Series([10000] * 50 + [25000])  # Volume spike at end
        
        metrics = filter_instance.calculate_volume_metrics(volume_data)
        
        # Verify metrics structure
        assert 'avg_volume' in metrics
        assert 'current_volume' in metrics
        assert 'volume_ratio' in metrics
        assert 'volume_percentile' in metrics
        assert 'is_volume_spike' in metrics
        assert 'volume_trend' in metrics
        
        # Check calculations
        assert metrics['current_volume'] == 25000
        assert abs(metrics['avg_volume'] - 10000) < 100  # Should be close to 10000
        assert metrics['volume_ratio'] == 2.5  # 25000 / 10000
        assert metrics['is_volume_spike'] == True  # Above 2.0 threshold
        assert metrics['volume_percentile'] > 0.9  # Should be high percentile
    
    def test_volume_spike_detection(self, epic1_config):
        """Test volume spike detection logic."""
        filter_instance = VolumeConfirmationFilter(epic1_config['volume_confirmation'])
        
        # Test with normal volume
        normal_volume = pd.Series([15000, 16000, 14000, 15500, 15800])
        normal_metrics = filter_instance.calculate_volume_metrics(normal_volume)
        assert not normal_metrics['is_volume_spike']
        
        # Test with volume spike
        spike_volume = pd.Series([15000] * 20 + [35000])  # 2.33x spike
        spike_metrics = filter_instance.calculate_volume_metrics(spike_volume)
        assert spike_metrics['is_volume_spike']
        assert spike_metrics['volume_ratio'] > 2.0
    
    def test_volume_trend_analysis(self, epic1_config):
        """Test volume trend detection."""
        filter_instance = VolumeConfirmationFilter(epic1_config['volume_confirmation'])
        
        # Increasing volume trend
        increasing_volume = pd.Series([10000] * 20 + [15000] * 20)
        inc_metrics = filter_instance.calculate_volume_metrics(increasing_volume)
        assert inc_metrics['volume_trend'] == 'increasing'
        
        # Decreasing volume trend
        decreasing_volume = pd.Series([20000] * 20 + [10000] * 20)
        dec_metrics = filter_instance.calculate_volume_metrics(decreasing_volume)
        assert dec_metrics['volume_trend'] == 'decreasing'
        
        # Stable volume trend
        stable_volume = pd.Series([15000] * 40)
        stable_metrics = filter_instance.calculate_volume_metrics(stable_volume)
        assert stable_metrics['volume_trend'] == 'stable'
    
    def test_signal_volume_validation_buy_signal(self, epic1_config):
        """Test volume validation for buy signals."""
        filter_instance = VolumeConfirmationFilter(epic1_config['volume_confirmation'])
        
        # High volume buy signal (should be confirmed)
        high_volume_data = pd.Series([10000] * 25 + [25000])  # 2.5x spike
        validation = filter_instance.validate_signal_volume(high_volume_data, 'buy')
        
        assert validation['volume_confirmed'] == True
        assert validation['validation_score'] > 0.6
        assert validation['confidence'] > 0.6
        assert len(validation['validation_reasons']) > 0
        
        # Low volume buy signal (should not be confirmed)
        low_volume_data = pd.Series([10000] * 25 + [8000])  # Below average
        low_validation = filter_instance.validate_signal_volume(low_volume_data, 'buy')
        
        assert low_validation['volume_confirmed'] == False
        assert low_validation['validation_score'] < 0.4
        assert low_validation['confidence'] < 0.4
    
    def test_signal_volume_validation_sell_signal(self, epic1_config):
        """Test volume validation for sell signals."""
        filter_instance = VolumeConfirmationFilter(epic1_config['volume_confirmation'])
        
        # High volume sell signal
        high_volume_data = pd.Series([15000] * 20 + [40000])  # Strong volume spike
        validation = filter_instance.validate_signal_volume(high_volume_data, 'sell')
        
        assert validation['volume_confirmed'] == True
        assert validation['validation_score'] > 0.7
        
        # Verify metrics are properly included
        assert 'metrics' in validation
        assert validation['metrics']['volume_ratio'] > 2.5
    
    def test_volume_percentile_calculation(self, epic1_config):
        """Test volume percentile calculation accuracy."""
        filter_instance = VolumeConfirmationFilter(epic1_config['volume_confirmation'])
        
        # Create volume data with known distribution
        base_volumes = [10000] * 40  # 40 periods of 10k volume
        test_volumes = base_volumes + [20000]  # Add volume double the average
        
        volume_data = pd.Series(test_volumes)
        metrics = filter_instance.calculate_volume_metrics(volume_data)
        
        # 20000 should be in high percentile (all 40 base volumes are lower)
        assert metrics['volume_percentile'] > 0.95
        
        # Test with median volume
        median_volumes = base_volumes + [10000]
        median_data = pd.Series(median_volumes)
        median_metrics = filter_instance.calculate_volume_metrics(median_data)
        
        # Should be around 50th percentile
        assert 0.4 <= median_metrics['volume_percentile'] <= 0.6
    
    def test_volume_quality_score_calculation(self, epic1_config):
        """Test volume quality score calculation."""
        filter_instance = VolumeConfirmationFilter(epic1_config['volume_confirmation'])
        
        # High quality volume scenario
        high_quality_volume = pd.Series([10000] * 20 + [15000] * 20 + [30000])
        high_score = filter_instance.get_volume_quality_score(high_quality_volume)
        
        assert high_score > 0.7
        
        # Low quality volume scenario
        low_quality_volume = pd.Series([20000] * 20 + [10000] * 20 + [5000])
        low_score = filter_instance.get_volume_quality_score(low_quality_volume)
        
        assert low_score < 0.4
        
        # Medium quality volume scenario
        medium_quality_volume = pd.Series([15000] * 40 + [20000])
        medium_score = filter_instance.get_volume_quality_score(medium_quality_volume)
        
        assert 0.4 <= medium_score <= 0.7
    
    def test_volume_confirmation_with_different_thresholds(self, epic1_config):
        """Test volume confirmation with different threshold settings."""
        # Strict threshold configuration
        strict_config = epic1_config['volume_confirmation'].copy()
        strict_config['volume_threshold_multiplier'] = 2.5
        strict_config['volume_spike_threshold'] = 3.0
        strict_config['min_volume_percentile'] = 0.7
        
        strict_filter = VolumeConfirmationFilter(strict_config)
        
        # Lenient threshold configuration
        lenient_config = epic1_config['volume_confirmation'].copy()
        lenient_config['volume_threshold_multiplier'] = 1.2
        lenient_config['volume_spike_threshold'] = 1.5
        lenient_config['min_volume_percentile'] = 0.2
        
        lenient_filter = VolumeConfirmationFilter(lenient_config)
        
        # Test with moderate volume increase
        moderate_volume = pd.Series([10000] * 25 + [18000])  # 1.8x increase
        
        strict_validation = strict_filter.validate_signal_volume(moderate_volume)
        lenient_validation = lenient_filter.validate_signal_volume(moderate_volume)
        
        # Strict filter should reject, lenient should accept
        assert not strict_validation['volume_confirmed']
        assert lenient_validation['volume_confirmed']
        assert lenient_validation['validation_score'] > strict_validation['validation_score']
    
    def test_insufficient_data_handling(self, epic1_config):
        """Test handling of insufficient volume data."""
        filter_instance = VolumeConfirmationFilter(epic1_config['volume_confirmation'])
        
        # Very limited data
        limited_volume = pd.Series([15000, 16000, 17000])  # Only 3 periods
        
        metrics = filter_instance.calculate_volume_metrics(limited_volume)
        validation = filter_instance.validate_signal_volume(limited_volume)
        
        # Should handle gracefully
        assert 'avg_volume' in metrics
        assert 'volume_confirmed' in validation
        assert metrics['volume_trend'] == 'stable'  # Default for insufficient data
        
        # Empty data
        empty_volume = pd.Series([])
        empty_metrics = filter_instance.calculate_volume_metrics(empty_volume)
        
        assert empty_metrics['current_volume'] == 0
        assert empty_metrics['volume_ratio'] == 1.0
    
    def test_zero_volume_handling(self, epic1_config):
        """Test handling of zero volume periods."""
        filter_instance = VolumeConfirmationFilter(epic1_config['volume_confirmation'])
        
        # Data with zero volumes
        zero_volume_data = pd.Series([10000, 15000, 0, 0, 20000])
        
        metrics = filter_instance.calculate_volume_metrics(zero_volume_data)
        validation = filter_instance.validate_signal_volume(zero_volume_data)
        
        # Should handle without errors
        assert isinstance(metrics['volume_ratio'], (int, float))
        assert isinstance(validation['validation_score'], (int, float))
        
        # All zero volume data
        all_zero_volume = pd.Series([0] * 25)
        zero_metrics = filter_instance.calculate_volume_metrics(all_zero_volume)
        
        assert zero_metrics['volume_ratio'] == 1.0  # Default when avg is 0
    
    def test_volume_confirmation_edge_cases(self, epic1_config):
        """Test edge cases in volume confirmation."""
        filter_instance = VolumeConfirmationFilter(epic1_config['volume_confirmation'])
        
        # Extreme volume spike
        extreme_spike = pd.Series([5000] * 20 + [100000])  # 20x spike
        extreme_validation = filter_instance.validate_signal_volume(extreme_spike)
        
        assert extreme_validation['volume_confirmed'] == True
        assert extreme_validation['validation_score'] > 0.8
        
        # Negative volume (invalid data)
        with patch('pandas.Series') as mock_series:
            mock_series.return_value = pd.Series([10000, -5000, 15000])
            # Should handle gracefully without crashing
            
        # Very large volume numbers
        large_volume = pd.Series([1000000] * 20 + [2500000])
        large_validation = filter_instance.validate_signal_volume(large_volume)
        
        assert 'volume_confirmed' in large_validation
        assert large_validation['metrics']['volume_ratio'] == 2.5
    
    def test_volume_filter_performance(self, epic1_config, low_volume_market_data):
        """Test performance of volume filter calculations."""
        import time
        
        filter_instance = VolumeConfirmationFilter(epic1_config['volume_confirmation'])
        
        # Large dataset
        large_volume_data = low_volume_market_data['volume']
        
        # Performance test
        start_time = time.time()
        iterations = 1000
        
        for _ in range(iterations):
            metrics = filter_instance.calculate_volume_metrics(large_volume_data)
            validation = filter_instance.validate_signal_volume(large_volume_data)
        
        elapsed_time = time.time() - start_time
        avg_time = elapsed_time / iterations
        
        # Should be fast (< 1ms per calculation)
        assert avg_time < 0.001, f"Volume filter too slow: {avg_time:.4f}s per calculation"
    
    @pytest.mark.parametrize("volume_scenario", [
        "low_consistent",
        "high_consistent", 
        "volatile_spikes",
        "decreasing_trend",
        "increasing_trend"
    ])
    def test_volume_scenarios(self, epic1_config, volume_scenario):
        """Test various volume scenarios."""
        filter_instance = VolumeConfirmationFilter(epic1_config['volume_confirmation'])
        
        # Generate scenario-specific data
        if volume_scenario == "low_consistent":
            volume_data = pd.Series([5000] * 30)
        elif volume_scenario == "high_consistent":
            volume_data = pd.Series([50000] * 30)
        elif volume_scenario == "volatile_spikes":
            base_volume = [10000] * 25
            spikes = [30000, 5000, 35000, 8000, 40000]
            volume_data = pd.Series(base_volume + spikes)
        elif volume_scenario == "decreasing_trend":
            volume_data = pd.Series(list(range(50000, 10000, -1000)))
        elif volume_scenario == "increasing_trend":
            volume_data = pd.Series(list(range(10000, 50000, 1000)))
        
        metrics = filter_instance.calculate_volume_metrics(volume_data)
        validation = filter_instance.validate_signal_volume(volume_data)
        quality_score = filter_instance.get_volume_quality_score(volume_data)
        
        # All scenarios should return valid results
        assert isinstance(metrics['volume_ratio'], (int, float))
        assert isinstance(validation['validation_score'], (int, float))
        assert 0.0 <= quality_score <= 1.0
        
        # Scenario-specific assertions
        if volume_scenario == "volatile_spikes":
            assert metrics['volume_ratio'] > 1.5  # Should detect spikes
        elif volume_scenario == "increasing_trend":
            assert metrics['volume_trend'] == 'increasing'
        elif volume_scenario == "decreasing_trend":
            assert metrics['volume_trend'] == 'decreasing'