import unittest
import asyncio
import time
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.timeframe.integration_helper import (
    MultiTimeframeIntegrationHelper,
    TradingSignal,
    SignalType,
    ValidationResult,
    ValidationStage,
    validate_signal_data,
    format_validation_response
)

class TestMultiTimeframeValidation(unittest.TestCase):
    """Test multi-timeframe validation system"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = {
            'timeframes': {
                '15m': {'weight': 1.0, 'enabled': True},
                '1h': {'weight': 1.5, 'enabled': True},
                '1d': {'weight': 2.0, 'enabled': True}
            },
            'validation': {
                'consensus_threshold': 0.75,
                'minimum_agreement': 2,
                'signal_strength_threshold': 0.6,
                'timeout_ms': 5000
            },
            'cache': {
                'max_size': 100,
                'ttl_seconds': 60
            }
        }
        
        self.helper = MultiTimeframeIntegrationHelper(self.config)
        
        # Sample trading signal
        self.sample_signal = {
            'symbol': 'AAPL',
            'type': 'BUY',
            'strength': 0.8,
            'timestamp': int(time.time() * 1000),
            'price': 150.25,
            'reason': 'StochRSI oversold signal',
            'indicators': {
                'stochRSI': {'k': 25, 'd': 30, 'signal': 1},
                'ema': {'fast': 148.5, 'slow': 147.2}
            },
            'metadata': {
                'confidence': 0.75,
                'strategies': ['StochRSI', 'EMA']
            }
        }
    
    def test_signal_validation(self):
        """Test basic signal validation."""
        result = self.helper.validate_signal(self.sample_signal)
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertGreater(result.confidence_score, 0)

    def test_invalid_signal_data(self):
        """Test validation with invalid data."""
        invalid_signal = self.sample_signal.copy()
        del invalid_signal['symbol']
        
        with self.assertRaises(ValueError):
            validate_signal_data(invalid_signal)
            
    def test_consensus_logic(self):
        """Test consensus calculation logic."""
        timeframe_signals = {
            '15m': {'trend': 'bullish', 'strength': 0.8},
            '1h': {'trend': 'bullish', 'strength': 0.7},
            '1d': {'trend': 'neutral', 'strength': 0.5}
        }
        
        consensus = self.helper._calculate_consensus(timeframe_signals, 'BUY')
        self.assertGreater(consensus, 0.7)
        self.assertLess(consensus, 1.0)
        
    def test_cache_integration(self):
        """Test caching of validation results."""
        signal_id = self.helper._get_signal_id(self.sample_signal)
        
        # First validation should not be cached
        self.helper.validate_signal(self.sample_signal)
        self.assertFalse(self.helper.cache.has(signal_id))
        
        # After first validation, result should be cached
        self.helper.validate_signal(self.sample_signal)
        self.assertTrue(self.helper.cache.has(signal_id))
        
        # Test cache retrieval
        cached_result = self.helper.cache.get(signal_id)
        self.assertIsInstance(cached_result, ValidationResult)
        
    @patch('src.utils.timeframe.integration_helper.asyncio.run')
    def test_async_data_fetching(self, mock_async_run):
        """Test asynchronous data fetching for timeframes."""
        
        async def mock_fetch(*args, **kwargs):
            return {'trend': 'bullish', 'strength': 0.8}
            
        mock_async_run.return_value = {
            '15m': mock_fetch(),
            '1h': mock_fetch(),
            '1d': mock_fetch()
        }
        
        timeframe_data = self.helper._fetch_all_timeframes_async(self.sample_signal)
        
        self.assertEqual(len(timeframe_data), 3)
        self.assertIn('15m', timeframe_data)
        
if __name__ == '__main__':
    unittest.main()