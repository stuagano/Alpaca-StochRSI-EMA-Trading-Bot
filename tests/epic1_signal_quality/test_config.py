"""
Test Configuration for Epic 1 Signal Quality Enhancement

Provides proper configuration objects for testing Epic 1 components.

Author: Testing & Validation System
Version: 1.0.0
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class StochRSIConfig:
    """Configuration for StochRSI indicator."""
    enabled: bool = True
    rsi_length: int = 14
    stoch_length: int = 14
    K: int = 3
    D: int = 3
    lower_band: float = 20
    upper_band: float = 80
    dynamic_bands_enabled: bool = True
    atr_period: int = 14
    atr_sensitivity: float = 2.0
    band_adjustment_factor: float = 1.5
    min_band_width: float = 10
    max_band_width: float = 90


@dataclass
class VolumeConfirmationConfig:
    """Configuration for volume confirmation."""
    enabled: bool = True
    require_volume_confirmation: bool = True
    volume_period: int = 20
    relative_volume_period: int = 50
    volume_confirmation_threshold: float = 1.2
    profile_periods: int = 100
    min_volume_ratio: float = 1.0


@dataclass
class MultiTimeframeConfig:
    """Configuration for multi-timeframe validation."""
    primary_timeframe: str = '5Min'
    confirmation_timeframes: List[str] = None
    signal_alignment_required: bool = True
    min_confirmation_percentage: int = 60
    
    def __post_init__(self):
        if self.confirmation_timeframes is None:
            self.confirmation_timeframes = ['15Min', '1Hour']


@dataclass
class IndicatorsConfig:
    """Configuration for all indicators."""
    stochRSI: StochRSIConfig = None
    
    def __post_init__(self):
        if self.stochRSI is None:
            self.stochRSI = StochRSIConfig()


@dataclass
class Epic1TestConfig:
    """Complete configuration for Epic 1 testing."""
    indicators: IndicatorsConfig = None
    volume_confirmation: VolumeConfirmationConfig = None
    multi_timeframe: MultiTimeframeConfig = None
    candle_lookback_period: int = 50
    
    def __post_init__(self):
        if self.indicators is None:
            self.indicators = IndicatorsConfig()
        if self.volume_confirmation is None:
            self.volume_confirmation = VolumeConfirmationConfig()
        if self.multi_timeframe is None:
            self.multi_timeframe = MultiTimeframeConfig()


def get_epic1_test_config() -> Epic1TestConfig:
    """Get Epic 1 test configuration."""
    return Epic1TestConfig()


def get_mock_config_dict() -> Dict:
    """Get mock configuration as dictionary for compatibility."""
    return {
        'indicators': {
            'stochRSI': {
                'enabled': True,
                'rsi_length': 14,
                'stoch_length': 14,
                'K': 3,
                'D': 3,
                'lower_band': 20,
                'upper_band': 80,
                'dynamic_bands_enabled': True,
                'atr_period': 14,
                'atr_sensitivity': 2.0,
                'band_adjustment_factor': 1.5,
                'min_band_width': 10,
                'max_band_width': 90
            }
        },
        'volume_confirmation': {
            'enabled': True,
            'require_volume_confirmation': True,
            'volume_period': 20,
            'relative_volume_period': 50,
            'volume_confirmation_threshold': 1.2,
            'profile_periods': 100,
            'min_volume_ratio': 1.0
        },
        'multi_timeframe': {
            'primary_timeframe': '5Min',
            'confirmation_timeframes': ['15Min', '1Hour'],
            'signal_alignment_required': True,
            'min_confirmation_percentage': 60
        },
        'candle_lookback_period': 50
    }


# Export main configuration
epic1_test_config = get_epic1_test_config()

__all__ = [
    'Epic1TestConfig',
    'StochRSIConfig',
    'VolumeConfirmationConfig', 
    'MultiTimeframeConfig',
    'IndicatorsConfig',
    'get_epic1_test_config',
    'get_mock_config_dict',
    'epic1_test_config'
]