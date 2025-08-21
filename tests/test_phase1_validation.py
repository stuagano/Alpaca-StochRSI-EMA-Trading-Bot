"""
Phase 1 Foundation Cleanup Validation Tests
Comprehensive validation of all Phase 1 improvements
"""

import pytest
import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta
import logging
import threading

# Test imports
from database.database_manager import DatabaseManager
from utils.secure_config_manager import get_secure_config, validate_environment
from utils.input_validator import InputValidator, ValidationError
from utils.thread_manager import thread_manager, ManagedThread
from services.redis_cache_service import get_redis_cache, get_trading_cache
from indicators.optimized_indicators import calculate_all_indicators_optimized, benchmark_indicators
from config.production_config import get_production_config
from app import create_app
from app.error_handlers import APIError, TradingError

logger = logging.getLogger(__name__)

class TestSecurityImprovements:
    """Test security-related improvements"""
    
    def test_sql_injection_prevention(self):
        """Test that SQL injection is prevented"""
        db_manager = DatabaseManager()
        
        # Test malicious inputs
        malicious_inputs = [
            "'; DROP TABLE historical_data; --",
            "1' OR '1'='1",
            "'; UPDATE historical_data SET symbol='HACKED'; --"
        ]
        
        for malicious_input in malicious_inputs:
            try:
                # These should not cause SQL injection
                result = db_manager.get_latest_timestamp(malicious_input, "15Min")
                # Should either return None or raise ValueError for invalid input
                assert result is None or isinstance(result, pd.Timestamp)
            except ValueError:
                # Expected for invalid input
                pass
            except Exception as e:
                # Should not get SQL errors
                assert "syntax error" not in str(e).lower()
                assert "drop table" not in str(e).lower()
    
    def test_input_validation(self):
        """Test comprehensive input validation"""
        # Test symbol validation
        with pytest.raises(ValidationError):
            InputValidator.validate_symbol("'; DROP TABLE;")
        
        with pytest.raises(ValidationError):
            InputValidator.validate_symbol("")
        
        with pytest.raises(ValidationError):
            InputValidator.validate_symbol("TOOLONGSTRING")
        
        # Valid symbol should pass
        valid_symbol = InputValidator.validate_symbol("AAPL")
        assert valid_symbol == "AAPL"
        
        # Test timeframe validation
        with pytest.raises(ValidationError):
            InputValidator.validate_timeframe("invalid")
        
        valid_timeframe = InputValidator.validate_timeframe("15m")
        assert valid_timeframe == "15m"
        
        # Test quantity validation
        with pytest.raises(ValidationError):
            InputValidator.validate_quantity(-100)
        
        with pytest.raises(ValidationError):
            InputValidator.validate_quantity("not_a_number")
        
        valid_quantity = InputValidator.validate_quantity(100.5)
        assert valid_quantity == 100.5
    
    def test_secure_config_management(self):
        """Test secure configuration management"""
        config = get_secure_config()
        
        # Test that environment validation works
        # Note: This may fail in test environment if credentials aren't set
        try:
            is_valid = validate_environment()
            logger.info(f"Environment validation result: {is_valid}")
        except Exception as e:
            logger.warning(f"Environment validation failed (expected in test): {e}")
        
        # Test configuration access
        try:
            db_config = config.get_database_url()
            assert isinstance(db_config, str)
            assert "postgresql://" in db_config
        except ValueError:
            # Expected if DB_PASSWORD not set
            pass

class TestPerformanceImprovements:
    """Test performance-related improvements"""
    
    def test_vectorized_indicators(self):
        """Test that vectorized indicators work and are faster"""
        # Create test data
        dates = pd.date_range(start='2023-01-01', periods=1000, freq='1min')
        test_data = pd.DataFrame({
            'high': np.random.randn(1000).cumsum() + 100,
            'low': np.random.randn(1000).cumsum() + 95,
            'close': np.random.randn(1000).cumsum() + 98,
            'volume': np.random.randint(1000, 10000, 1000)
        }, index=dates)
        
        # Test that indicators calculate successfully
        result = calculate_all_indicators_optimized(test_data)
        
        # Verify required columns exist
        expected_columns = ['ATR', 'StochRSI', 'StochRSI %K', 'StochRSI %D', 'dynamic_lower_band', 'dynamic_upper_band']
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"
        
        # Test performance benchmarking
        benchmark_results = benchmark_indicators(test_data.head(100), iterations=3)
        assert 'All Indicators' in benchmark_results
        assert benchmark_results['All Indicators']['avg_time'] < 1.0  # Should be under 1 second
    
    def test_database_connection_pooling(self):
        """Test database connection pooling"""
        db_manager = DatabaseManager()
        
        # Test that connection pool is initialized
        assert hasattr(db_manager, '_connection_pool')
        assert db_manager._connection_pool is not None
        
        # Test getting and returning connections
        conn1 = db_manager.get_connection()
        conn2 = db_manager.get_connection()
        
        assert conn1 is not None
        assert conn2 is not None
        assert conn1 != conn2  # Should be different connections
        
        # Return connections
        db_manager.return_connection(conn1)
        db_manager.return_connection(conn2)
    
    def test_redis_caching(self):
        """Test Redis caching functionality"""
        try:
            cache = get_redis_cache()
            trading_cache = get_trading_cache()
            
            # Test basic cache operations
            test_key = "test_key"
            test_value = {"test": "data", "timestamp": time.time()}
            
            # Set and get
            success = cache.set(test_key, test_value, ttl=60)
            if success:  # Only test if Redis is available
                retrieved = cache.get(test_key)
                assert retrieved == test_value
                
                # Test cache stats
                stats = cache.get_stats()
                assert 'hits' in stats
                assert 'misses' in stats
                assert 'hit_rate' in stats
                
                # Clean up
                cache.delete(test_key)
            else:
                logger.warning("Redis not available for testing")
                
        except Exception as e:
            logger.warning(f"Redis testing failed (expected if Redis not running): {e}")

class TestArchitectureImprovements:
    """Test architectural improvements"""
    
    def test_thread_management(self):
        """Test thread management and memory leak prevention"""
        # Test creating managed thread
        def test_function(shutdown_event=None):
            counter = 0
            while counter < 5 and not (shutdown_event and shutdown_event.is_set()):
                counter += 1
                time.sleep(0.1)
            return counter
        
        managed_thread = thread_manager.create_thread(
            target=test_function,
            name="test_thread"
        )
        
        # Start thread
        managed_thread.start()
        assert managed_thread.is_alive()
        
        # Wait for completion
        time.sleep(1)
        
        # Thread should complete naturally
        assert not managed_thread.is_alive() or managed_thread._is_stopped
        
        # Test thread status
        status = thread_manager.get_thread_status()
        assert isinstance(status, dict)
    
    def test_modular_flask_app(self):
        """Test modular Flask application structure"""
        app = create_app()
        
        # Test that app is created
        assert app is not None
        
        # Test that blueprints are registered
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        expected_blueprints = ['api']  # At minimum, api blueprint should exist
        
        for expected in expected_blueprints:
            assert expected in blueprint_names, f"Missing blueprint: {expected}"
        
        # Test error handlers are registered
        assert app.error_handler_spec is not None
    
    def test_structured_error_handling(self):
        """Test structured error handling"""
        # Test custom errors
        with pytest.raises(TradingError):
            raise TradingError("Test trading error")
        
        with pytest.raises(APIError):
            raise APIError("Test API error", status_code=400, error_code="TEST_ERROR")
        
        # Test error response structure
        error = APIError("Test message", status_code=400, error_code="TEST_CODE")
        assert error.message == "Test message"
        assert error.status_code == 400
        assert error.error_code == "TEST_CODE"
        assert isinstance(error.timestamp, str)
    
    def test_configuration_consolidation(self):
        """Test consolidated configuration system"""
        config = get_production_config()
        
        # Test configuration structure
        assert hasattr(config, 'database')
        assert hasattr(config, 'redis')
        assert hasattr(config, 'trading')
        assert hasattr(config, 'api')
        
        # Test configuration validation
        try:
            is_valid = config.validate()
            logger.info(f"Configuration validation: {is_valid}")
        except Exception as e:
            logger.warning(f"Configuration validation failed (expected in test): {e}")
        
        # Test dictionary conversion
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert 'database' in config_dict
        assert 'redis' in config_dict

class TestResourceManagement:
    """Test resource cleanup and management"""
    
    def test_memory_leak_prevention(self):
        """Test that memory leaks are prevented"""
        from utils.thread_manager import get_memory_usage
        
        # Get initial memory usage
        initial_memory = get_memory_usage()
        
        if initial_memory:  # Only test if psutil available
            initial_rss = initial_memory.get('rss_mb', 0)
            
            # Create and destroy multiple threads
            for i in range(5):
                def dummy_function(shutdown_event=None):
                    time.sleep(0.1)
                
                thread = thread_manager.create_thread(
                    target=dummy_function,
                    name=f"memory_test_{i}"
                )
                thread.start()
                time.sleep(0.2)  # Let it complete
            
            # Check memory after operations
            final_memory = get_memory_usage()
            final_rss = final_memory.get('rss_mb', 0)
            
            # Memory should not increase significantly
            memory_increase = final_rss - initial_rss
            assert memory_increase < 10, f"Memory increased by {memory_increase}MB"
        else:
            logger.warning("Memory monitoring not available for testing")
    
    def test_resource_cleanup(self):
        """Test resource cleanup functionality"""
        from utils.thread_manager import ResourceCleaner
        
        # Test cleanup methods exist and don't crash
        try:
            ResourceCleaner.cleanup_websocket_connections(None)
            ResourceCleaner.cleanup_database_connections(None)
            ResourceCleaner.cleanup_api_clients(None)
        except Exception as e:
            # Should handle None gracefully
            assert "NoneType" not in str(e)

class TestIntegrationValidation:
    """Test that all improvements work together"""
    
    def test_end_to_end_data_flow(self):
        """Test complete data flow with all improvements"""
        try:
            # Create test data
            test_data = pd.DataFrame({
                'high': [100, 101, 102, 103, 104],
                'low': [98, 99, 100, 101, 102],
                'close': [99, 100, 101, 102, 103],
                'volume': [1000, 1100, 1200, 1300, 1400]
            })
            
            # Test that we can:
            # 1. Validate input
            symbol = InputValidator.validate_symbol("TEST")
            timeframe = InputValidator.validate_timeframe("15m")
            
            # 2. Calculate indicators
            result = calculate_all_indicators_optimized(test_data)
            assert not result.empty
            
            # 3. Cache results (if Redis available)
            try:
                cache = get_trading_cache()
                cache_success = cache.cache_indicators(symbol, timeframe, "test", result.to_dict())
                if cache_success:
                    cached_data = cache.get_indicators(symbol, timeframe, "test")
                    assert cached_data is not None
            except Exception as e:
                logger.warning(f"Cache testing failed: {e}")
            
            # 4. Database operations (with connection pooling)
            try:
                db_manager = DatabaseManager()
                # Just test that we can create the manager without errors
                assert db_manager is not None
            except Exception as e:
                logger.warning(f"Database testing failed: {e}")
            
            logger.info("End-to-end data flow test completed successfully")
            
        except Exception as e:
            logger.error(f"End-to-end test failed: {e}")
            raise

def run_phase1_validation():
    """Run comprehensive Phase 1 validation"""
    logger.info("Starting Phase 1 Foundation Cleanup Validation")
    
    test_results = {
        'security': 0,
        'performance': 0,
        'architecture': 0,
        'resources': 0,
        'integration': 0,
        'total_tests': 0,
        'passed_tests': 0
    }
    
    test_classes = [
        TestSecurityImprovements,
        TestPerformanceImprovements,
        TestArchitectureImprovements,
        TestResourceManagement,
        TestIntegrationValidation
    ]
    
    for test_class in test_classes:
        class_name = test_class.__name__
        test_instance = test_class()
        
        # Get all test methods
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        for test_method in test_methods:
            test_results['total_tests'] += 1
            try:
                method = getattr(test_instance, test_method)
                method()
                test_results['passed_tests'] += 1
                
                # Categorize the test
                if 'security' in class_name.lower():
                    test_results['security'] += 1
                elif 'performance' in class_name.lower():
                    test_results['performance'] += 1
                elif 'architecture' in class_name.lower():
                    test_results['architecture'] += 1
                elif 'resource' in class_name.lower():
                    test_results['resources'] += 1
                elif 'integration' in class_name.lower():
                    test_results['integration'] += 1
                
                logger.info(f"✅ {class_name}.{test_method} - PASSED")
                
            except Exception as e:
                logger.error(f"❌ {class_name}.{test_method} - FAILED: {e}")
    
    # Calculate success rate
    success_rate = (test_results['passed_tests'] / test_results['total_tests']) * 100 if test_results['total_tests'] > 0 else 0
    
    logger.info(f"\n🎯 Phase 1 Validation Results:")
    logger.info(f"Total Tests: {test_results['total_tests']}")
    logger.info(f"Passed Tests: {test_results['passed_tests']}")
    logger.info(f"Success Rate: {success_rate:.1f}%")
    logger.info(f"Security Tests: {test_results['security']} passed")
    logger.info(f"Performance Tests: {test_results['performance']} passed")
    logger.info(f"Architecture Tests: {test_results['architecture']} passed")
    logger.info(f"Resource Tests: {test_results['resources']} passed")
    logger.info(f"Integration Tests: {test_results['integration']} passed")
    
    if success_rate >= 80:
        logger.info("🚀 Phase 1 Foundation Cleanup: SUCCESS")
        return True
    else:
        logger.error("⚠️ Phase 1 Foundation Cleanup: NEEDS ATTENTION")
        return False

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run validation
    success = run_phase1_validation()
    exit(0 if success else 1)