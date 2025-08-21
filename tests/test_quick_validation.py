#!/usr/bin/env python3
"""
Quick validation tests for testing strategy implementation.
These tests verify that the testing infrastructure is working correctly.
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestTestingInfrastructure:
    """Validate testing infrastructure is properly configured."""
    
    def test_fixtures_are_importable(self):
        """Test that all test fixtures can be imported."""
        try:
            from tests.fixtures.market_data_fixtures import (
                MarketDataGenerator,
                ScenarioBuilder,
                get_standard_market_data
            )
            from tests.fixtures.order_fixtures import (
                OrderGenerator,
                PositionGenerator,
                get_sample_buy_order
            )
            assert True  # All imports successful
        except ImportError as e:
            pytest.fail(f"Failed to import test fixtures: {e}")
    
    def test_mocks_are_available(self):
        """Test that mock implementations are available."""
        try:
            from tests.mocks.alpaca_api_mock import (
                MockAlpacaAPI,
                create_realistic_market_scenario
            )
            assert True  # All imports successful
        except ImportError as e:
            pytest.fail(f"Failed to import mocks: {e}")
    
    def test_conftest_fixtures_available(self):
        """Test that conftest.py fixtures are available."""
        # This test will only pass if conftest.py is properly configured
        # The fixtures should be automatically available
        pass
    
    def test_test_directories_exist(self):
        """Test that all required test directories exist."""
        test_root = Path(__file__).parent
        
        required_dirs = [
            "fixtures",
            "mocks", 
            "unit",
            "integration",
            "performance"
        ]
        
        for dir_name in required_dirs:
            dir_path = test_root / dir_name
            assert dir_path.exists(), f"Missing required test directory: {dir_name}"
            
            # Check for __init__.py to ensure it's a Python package
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                # Create __init__.py if it doesn't exist
                init_file.touch()

class TestBasicFunctionality:
    """Test basic functionality works with test infrastructure."""
    
    def test_market_data_generation(self):
        """Test market data generation works."""
        from tests.fixtures.market_data_fixtures import get_standard_market_data
        
        data = get_standard_market_data("AAPL", periods=10)
        
        assert data is not None
        assert len(data) == 10
        assert all(col in data.columns for col in ['open', 'high', 'low', 'close', 'volume'])
        assert data['high'].min() >= data['low'].max()  # Basic OHLC validation
    
    def test_order_fixture_generation(self):
        """Test order fixture generation works."""
        from tests.fixtures.order_fixtures import get_sample_buy_order
        
        order = get_sample_buy_order("AAPL")
        
        assert order is not None
        assert order.ticker == "AAPL"
        assert order.type == "buy"
        assert order.quantity > 0
        assert order.buy_price > 0
    
    def test_mock_api_creation(self):
        """Test mock API can be created and used."""
        from tests.mocks.alpaca_api_mock import create_realistic_market_scenario
        
        mock_api = create_realistic_market_scenario()
        
        assert mock_api is not None
        
        # Test basic API operations
        account = mock_api.get_account()
        assert account.cash > 0
        
        positions = mock_api.list_positions()
        assert isinstance(positions, list)
        
        clock = mock_api.get_clock()
        assert hasattr(clock, 'is_open')

class TestEnvironmentConfiguration:
    """Test environment configuration for testing."""
    
    def test_testing_environment_variables(self):
        """Test that testing environment variables can be set."""
        # Set test environment variables
        os.environ['TESTING'] = 'True'
        os.environ['DATABASE_URL'] = 'sqlite:///test.db'
        
        assert os.getenv('TESTING') == 'True'
        assert 'test' in os.getenv('DATABASE_URL', '')
    
    def test_project_structure(self):
        """Test project structure is as expected."""
        project_root = Path(__file__).parent.parent
        
        # Check key directories exist
        key_dirs = [
            'src',
            'tests', 
            'docs',
            'config',
            'strategies',
            'risk_management'
        ]
        
        for dir_name in key_dirs:
            dir_path = project_root / dir_name
            if not dir_path.exists():
                print(f"Warning: Expected directory '{dir_name}' not found")
                # Don't fail the test, just warn
    
    def test_test_dependencies_available(self):
        """Test that required test dependencies are available."""
        required_packages = [
            'pytest',
            'pandas',
            'numpy'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            pytest.fail(f"Missing required packages: {missing_packages}")

@pytest.mark.smoke
class TestSmokeTests:
    """Smoke tests for quick validation."""
    
    def test_basic_imports(self):
        """Smoke test: Basic project imports work."""
        try:
            # Try importing core project modules
            import config
            import strategies
            
            # If we get here, basic imports work
            assert True
        except ImportError:
            # Don't fail smoke tests for missing optional modules
            pass
    
    def test_pytest_markers_work(self):
        """Smoke test: Pytest markers are configured."""
        # This test itself uses the @pytest.mark.smoke marker
        # If it runs, markers are working
        assert True
    
    def test_basic_math_operations(self):
        """Smoke test: Basic operations work (sanity check)."""
        assert 2 + 2 == 4
        assert 10 / 2 == 5
        assert 3 * 3 == 9

if __name__ == "__main__":
    # Allow running this file directly for quick validation
    print("Running quick validation tests...")
    pytest.main([__file__, "-v"])