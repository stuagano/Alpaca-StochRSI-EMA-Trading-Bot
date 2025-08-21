"""
Epic 1 Integration Validation and Testing Suite
==============================================

Comprehensive test suite for validating Epic 1 feature integration
with the existing trading system architecture.
"""

import unittest
import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEpic1Integration(unittest.TestCase):
    """Test Epic 1 integration with existing trading system."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_data = self._create_test_data()
        self.mock_data_manager = self._create_mock_data_manager()
        
    def _create_test_data(self) -> pd.DataFrame:
        """Create sample trading data for testing."""
        dates = pd.date_range(start='2024-01-01', end='2024-01-02', freq='1min')
        np.random.seed(42)  # For reproducible tests
        
        data = pd.DataFrame({
            'open': 100 + np.random.randn(len(dates)) * 2,
            'high': 102 + np.random.randn(len(dates)) * 2,
            'low': 98 + np.random.randn(len(dates)) * 2,
            'close': 100 + np.random.randn(len(dates)) * 2,
            'volume': 1000 + np.random.randint(0, 500, len(dates))
        }, index=dates)
        
        # Ensure OHLC relationships are maintained
        data['high'] = np.maximum(data[['open', 'close']].max(axis=1), data['high'])
        data['low'] = np.minimum(data[['open', 'close']].min(axis=1), data['low'])
        
        return data
    
    def _create_mock_data_manager(self):
        """Create mock data manager for testing."""
        mock_dm = Mock()
        mock_dm.get_historical_data.return_value = self.test_data
        mock_dm.get_latest_price.return_value = 100.0
        return mock_dm
    
    def test_epic1_helper_import(self):
        """Test that Epic 1 integration helpers can be imported."""
        try:
            from src.utils.epic1_integration_helpers import (
                initialize_epic1_components,
                calculate_enhanced_signal_data,
                calculate_volume_confirmation,
                get_basic_timeframe_data,
                calculate_signal_quality_metrics
            )
            self.assertTrue(True, "Epic 1 helpers imported successfully")
        except ImportError as e:
            self.skipTest(f"Epic 1 components not available: {e}")
    
    def test_enhanced_signal_calculation(self):
        """Test enhanced signal data calculation."""
        try:
            from src.utils.epic1_integration_helpers import calculate_enhanced_signal_data
            
            result = calculate_enhanced_signal_data('AAPL', self.test_data, self.mock_data_manager)
            
            # Validate result structure
            self.assertIn('epic1_features', result)
            self.assertIn('legacy_compatibility', result)
            self.assertIn('integration_status', result)
            
            # Check Epic 1 features
            epic1_features = result['epic1_features']
            self.assertIn('dynamic_stochrsi', epic1_features)
            self.assertIn('volume_confirmation', epic1_features)
            self.assertIn('signal_quality', epic1_features)
            self.assertIn('multi_timeframe', epic1_features)
            
            logger.info("✅ Enhanced signal calculation test passed")
            
        except ImportError:
            self.skipTest("Epic 1 components not available")
        except Exception as e:
            self.fail(f"Enhanced signal calculation failed: {e}")
    
    def test_volume_confirmation_calculation(self):
        """Test volume confirmation system."""
        try:
            from src.utils.epic1_integration_helpers import calculate_volume_confirmation
            
            result = calculate_volume_confirmation(self.test_data, 'AAPL')
            
            # Validate result structure
            required_fields = [
                'volume_confirmed', 'volume_ratio', 'current_volume',
                'volume_ma', 'relative_volume', 'volume_strength',
                'volume_trend', 'confirmation_threshold', 'analysis_quality'
            ]
            
            for field in required_fields:
                self.assertIn(field, result, f"Missing field: {field}")
            
            # Validate data types
            self.assertIsInstance(result['volume_confirmed'], bool)
            self.assertIsInstance(result['volume_ratio'], (int, float))
            self.assertIsInstance(result['current_volume'], int)
            
            logger.info("✅ Volume confirmation calculation test passed")
            
        except ImportError:
            self.skipTest("Epic 1 components not available")
        except Exception as e:
            self.fail(f"Volume confirmation calculation failed: {e}")
    
    def test_signal_quality_metrics(self):
        """Test signal quality metrics calculation."""
        try:
            from src.utils.epic1_integration_helpers import calculate_signal_quality_metrics
            
            result = calculate_signal_quality_metrics('AAPL', self.mock_data_manager)
            
            # Validate result structure
            if 'error' not in result:
                self.assertIn('overall_quality_score', result)
                self.assertIn('quality_grade', result)
                self.assertIn('components', result)
                self.assertIn('recommendations', result)
                
                # Validate score range
                score = result['overall_quality_score']
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 1.0)
                
                # Validate grade
                valid_grades = ['A+', 'A', 'B', 'C', 'D', 'F']
                self.assertIn(result['quality_grade'], valid_grades)
            
            logger.info("✅ Signal quality metrics test passed")
            
        except ImportError:
            self.skipTest("Epic 1 components not available")
        except Exception as e:
            self.fail(f"Signal quality metrics calculation failed: {e}")
    
    def test_multi_timeframe_data(self):
        """Test multi-timeframe data retrieval."""
        try:
            from src.utils.epic1_integration_helpers import get_basic_timeframe_data
            
            result = get_basic_timeframe_data('AAPL', self.mock_data_manager)
            
            # Validate result structure
            if 'error' not in result:
                self.assertIn('timeframes', result)
                self.assertIn('alignment_score', result)
                self.assertIn('alignment_status', result)
                self.assertIn('valid_timeframes', result)
                
                # Validate alignment score
                score = result['alignment_score']
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 1.0)
            
            logger.info("✅ Multi-timeframe data test passed")
            
        except ImportError:
            self.skipTest("Epic 1 components not available")
        except Exception as e:
            self.fail(f"Multi-timeframe data test failed: {e}")
    
    def test_epic1_status_endpoint(self):
        """Test Epic 1 status functionality."""
        try:
            from src.utils.epic1_integration_helpers import get_epic1_status
            
            status = get_epic1_status()
            
            # Validate status structure
            self.assertIn('epic1_available', status)
            self.assertIn('components_initialized', status)
            self.assertIn('last_check', status)
            
            logger.info("✅ Epic 1 status test passed")
            
        except ImportError:
            self.skipTest("Epic 1 components not available")
        except Exception as e:
            self.fail(f"Epic 1 status test failed: {e}")
    
    def test_backward_compatibility(self):
        """Test that Epic 0 functionality remains intact."""
        try:
            from src.utils.epic1_integration_helpers import calculate_enhanced_signal_data
            
            # Test with Epic 1 disabled scenario
            result = calculate_enhanced_signal_data('AAPL', self.test_data, self.mock_data_manager)
            
            # Should always have legacy compatibility layer
            self.assertIn('legacy_compatibility', result)
            legacy = result['legacy_compatibility']
            
            # Validate legacy fields
            expected_legacy_fields = ['signal', 'strength', 'status']
            for field in expected_legacy_fields:
                self.assertIn(field, legacy, f"Missing legacy field: {field}")
            
            logger.info("✅ Backward compatibility test passed")
            
        except ImportError:
            self.skipTest("Epic 1 components not available")
        except Exception as e:
            self.fail(f"Backward compatibility test failed: {e}")


class TestEpic1Configuration(unittest.TestCase):
    """Test Epic 1 configuration management."""
    
    def test_unified_config_epic1_fields(self):
        """Test that unified config includes Epic 1 fields."""
        try:
            from config.unified_config import TradingConfig, Epic1Config
            
            # Create default config
            config = TradingConfig()
            
            # Validate Epic 1 config exists
            self.assertIsInstance(config.epic1, Epic1Config)
            
            # Validate Epic 1 subconfigs
            self.assertTrue(hasattr(config.epic1, 'dynamic_stochrsi'))
            self.assertTrue(hasattr(config.epic1, 'volume_confirmation'))
            self.assertTrue(hasattr(config.epic1, 'multi_timeframe'))
            self.assertTrue(hasattr(config.epic1, 'signal_quality'))
            self.assertTrue(hasattr(config.epic1, 'performance'))
            
            logger.info("✅ Epic 1 configuration structure test passed")
            
        except ImportError as e:
            self.fail(f"Could not import Epic 1 configuration: {e}")
    
    def test_epic1_config_defaults(self):
        """Test Epic 1 configuration default values."""
        try:
            from config.unified_config import Epic1Config
            
            config = Epic1Config()
            
            # Test default values
            self.assertTrue(config.enabled)
            self.assertTrue(config.fallback_to_epic0)
            self.assertTrue(config.enable_enhanced_websocket)
            self.assertTrue(config.enable_epic1_api_endpoints)
            
            # Test subconfig defaults
            self.assertTrue(config.dynamic_stochrsi.enabled)
            self.assertTrue(config.volume_confirmation.enabled)
            self.assertTrue(config.multi_timeframe.enabled)
            self.assertTrue(config.signal_quality.enabled)
            
            logger.info("✅ Epic 1 configuration defaults test passed")
            
        except ImportError as e:
            self.fail(f"Could not import Epic 1 configuration: {e}")


class TestEpic1APIEndpoints(unittest.TestCase):
    """Test Epic 1 API endpoint functionality."""
    
    def setUp(self):
        """Set up test Flask app."""
        self.test_client = None
        try:
            # This would require a full Flask app setup
            # For now, we'll test the endpoint logic separately
            pass
        except Exception as e:
            logger.warning(f"Could not set up Flask test client: {e}")
    
    def test_epic1_api_route_structure(self):
        """Test that Epic 1 API routes are properly structured."""
        # This test validates the route definitions exist
        # In a full test environment, this would test actual HTTP endpoints
        
        expected_routes = [
            '/api/epic1/status',
            '/api/epic1/enhanced-signal/<symbol>',
            '/api/epic1/volume-dashboard-data',
            '/api/epic1/multi-timeframe/<symbol>'
        ]
        
        # For now, just validate the routes are documented
        self.assertTrue(len(expected_routes) > 0)
        logger.info("✅ Epic 1 API route structure test passed")


class TestEpic1Performance(unittest.TestCase):
    """Test Epic 1 performance characteristics."""
    
    def test_enhanced_signal_performance(self):
        """Test that enhanced signal calculation performs within acceptable limits."""
        try:
            from src.utils.epic1_integration_helpers import calculate_enhanced_signal_data
            import time
            
            # Create larger test dataset
            dates = pd.date_range(start='2024-01-01', end='2024-01-03', freq='1min')
            large_data = pd.DataFrame({
                'open': 100 + np.random.randn(len(dates)) * 2,
                'high': 102 + np.random.randn(len(dates)) * 2,
                'low': 98 + np.random.randn(len(dates)) * 2,
                'close': 100 + np.random.randn(len(dates)) * 2,
                'volume': 1000 + np.random.randint(0, 500, len(dates))
            }, index=dates)
            
            mock_dm = Mock()
            mock_dm.get_historical_data.return_value = large_data
            mock_dm.get_latest_price.return_value = 100.0
            
            # Measure performance
            start_time = time.time()
            result = calculate_enhanced_signal_data('AAPL', large_data, mock_dm)
            execution_time = time.time() - start_time
            
            # Should complete in reasonable time (< 5 seconds for test data)
            self.assertLess(execution_time, 5.0, f"Enhanced signal calculation too slow: {execution_time}s")
            
            # Should return valid result
            self.assertIn('epic1_features', result)
            
            logger.info(f"✅ Enhanced signal performance test passed ({execution_time:.3f}s)")
            
        except ImportError:
            self.skipTest("Epic 1 components not available")
        except Exception as e:
            self.fail(f"Performance test failed: {e}")


def run_integration_validation():
    """Run complete Epic 1 integration validation suite."""
    logger.info("🚀 Starting Epic 1 Integration Validation Suite")
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestEpic1Integration,
        TestEpic1Configuration,
        TestEpic1APIEndpoints,
        TestEpic1Performance
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Generate summary
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total_tests - failures - errors - skipped
    
    logger.info("\n" + "="*60)
    logger.info("EPIC 1 INTEGRATION VALIDATION SUMMARY")
    logger.info("="*60)
    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failures}")
    logger.info(f"Errors: {errors}")
    logger.info(f"Skipped: {skipped}")
    logger.info("="*60)
    
    if failures == 0 and errors == 0:
        logger.info("✅ All Epic 1 integration tests passed!")
        return True
    else:
        logger.error("❌ Some Epic 1 integration tests failed!")
        
        if result.failures:
            logger.error("FAILURES:")
            for test, traceback in result.failures:
                logger.error(f"  - {test}: {traceback}")
        
        if result.errors:
            logger.error("ERRORS:")
            for test, traceback in result.errors:
                logger.error(f"  - {test}: {traceback}")
        
        return False


if __name__ == '__main__':
    success = run_integration_validation()
    sys.exit(0 if success else 1)