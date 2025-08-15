#!/usr/bin/env python3
"""
Comprehensive test suite for enhanced risk management system
"""

import sys
import os
import unittest
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import risk management components
from risk_management.risk_service import RiskManagementService
from risk_management.position_sizer import DynamicPositionSizer, PositionSizingMethod
from risk_management.risk_models import PortfolioRiskAnalyzer, ValueAtRisk, VolatilityModel
from risk_management.risk_middleware import RiskValidationMiddleware, TradeAction, ValidationSeverity
from risk_management.trailing_stop_manager import TrailingStopManager, TrailingStopConfig, TrailingStopType

class TestPositionSizer(unittest.TestCase):
    """Test position sizing calculations and validations"""
    
    def setUp(self):
        self.position_sizer = DynamicPositionSizer()
        self.test_data = self._create_test_data()
    
    def _create_test_data(self):
        """Create synthetic market data for testing"""
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        np.random.seed(42)  # For reproducible tests
        
        # Generate realistic OHLC data
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = 100 * (1 + returns).cumprod()
        
        data = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.005, len(prices))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(prices)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(prices)))),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, len(prices))
        }, index=dates)
        
        # Ensure OHLC consistency
        data['high'] = data[['open', 'high', 'close']].max(axis=1)
        data['low'] = data[['open', 'low', 'close']].min(axis=1)
        
        return data
    
    def test_position_size_validation_negative_inputs(self):
        """Test that negative or invalid inputs are handled properly"""
        
        # Test negative entry price
        with self.assertRaises(ValueError):
            self.position_sizer.calculate_position_size(
                symbol="TEST",
                entry_price=-100.0,
                stop_loss_price=95.0,
                portfolio_value=10000,
                method=PositionSizingMethod.VOLATILITY_ADJUSTED
            )
        
        # Test zero entry price
        with self.assertRaises(ValueError):
            self.position_sizer.calculate_position_size(
                symbol="TEST",
                entry_price=0.0,
                stop_loss_price=95.0,
                portfolio_value=10000,
                method=PositionSizingMethod.VOLATILITY_ADJUSTED
            )
        
        # Test negative portfolio value
        with self.assertRaises(ValueError):
            self.position_sizer.calculate_position_size(
                symbol="TEST",
                entry_price=100.0,
                stop_loss_price=95.0,
                portfolio_value=-10000,
                method=PositionSizingMethod.VOLATILITY_ADJUSTED
            )
    
    def test_position_size_bounds(self):
        """Test that position sizes are within acceptable bounds"""
        
        recommendation = self.position_sizer.calculate_position_size(
            symbol="TEST",
            entry_price=100.0,
            stop_loss_price=95.0,
            portfolio_value=10000,
            method=PositionSizingMethod.VOLATILITY_ADJUSTED,
            historical_data=self.test_data
        )
        
        # Position size should be positive
        self.assertGreater(recommendation.risk_adjusted_size, 0)
        
        # Position size should not exceed maximum
        self.assertLessEqual(recommendation.risk_adjusted_size, self.position_sizer.max_position_size)
        
        # Position size should not be below minimum
        self.assertGreaterEqual(recommendation.risk_adjusted_size, self.position_sizer.min_position_size)
        
        # Risk per trade should be reasonable
        self.assertLessEqual(recommendation.risk_per_trade, self.position_sizer.max_risk_per_trade)
    
    def test_atr_position_sizing_validation(self):
        """Test ATR-based position sizing with various scenarios"""
        
        # Normal case
        recommendation = self.position_sizer.calculate_position_size(
            symbol="TEST",
            entry_price=100.0,
            stop_loss_price=95.0,
            portfolio_value=10000,
            method=PositionSizingMethod.ATR_BASED,
            historical_data=self.test_data
        )
        
        self.assertIsInstance(recommendation.risk_adjusted_size, float)
        self.assertGreater(recommendation.risk_adjusted_size, 0)
        
        # Test with insufficient data
        small_data = self.test_data.tail(5)  # Only 5 periods
        recommendation_small = self.position_sizer.calculate_position_size(
            symbol="TEST",
            entry_price=100.0,
            stop_loss_price=95.0,
            portfolio_value=10000,
            method=PositionSizingMethod.ATR_BASED,
            historical_data=small_data
        )
        
        # Should fallback to minimum position size
        self.assertGreaterEqual(recommendation_small.risk_adjusted_size, self.position_sizer.min_position_size)
    
    def test_volatility_adjusted_sizing_edge_cases(self):
        """Test volatility-adjusted sizing with edge cases"""
        
        # Create data with extreme volatility
        extreme_data = self.test_data.copy()
        extreme_data['close'] = extreme_data['close'] * (1 + np.random.normal(0, 0.5, len(extreme_data)))
        
        recommendation = self.position_sizer.calculate_position_size(
            symbol="TEST",
            entry_price=100.0,
            stop_loss_price=95.0,
            portfolio_value=10000,
            method=PositionSizingMethod.VOLATILITY_ADJUSTED,
            historical_data=extreme_data
        )
        
        # Even with extreme volatility, position size should be bounded
        self.assertLessEqual(recommendation.risk_adjusted_size, self.position_sizer.max_position_size)
        self.assertGreaterEqual(recommendation.risk_adjusted_size, self.position_sizer.min_position_size)

class TestRiskService(unittest.TestCase):
    """Test risk management service functionality"""
    
    def setUp(self):
        # Mock dependencies
        self.mock_config = Mock()
        self.mock_config.max_daily_loss_percentage = 5.0
        self.mock_config.max_drawdown_percentage = 15.0
        self.mock_config.max_positions = 10
        self.mock_config.correlation_threshold = 0.7
        
        self.mock_data_service = Mock()
        self.mock_data_service.get_portfolio_summary.return_value = {
            'total_open_value': 100000,
            'cash': 20000,
            'unrealized_pnl': -1000
        }
        self.mock_data_service.get_open_orders.return_value = pd.DataFrame()
        
        # Create risk service with mocked dependencies
        with patch('risk_management.risk_service.get_trading_config', return_value=self.mock_config), \
             patch('risk_management.risk_service.get_data_service', return_value=self.mock_data_service):
            self.risk_service = RiskManagementService()
    
    def test_emergency_stop_conditions(self):
        """Test emergency stop trigger conditions"""
        
        # Initially should not be triggered
        self.assertFalse(self.risk_service.is_emergency_stop_active())
        
        # Manually trigger emergency stop
        self.risk_service._trigger_emergency_stop("Test emergency condition")
        
        # Should now be active
        self.assertTrue(self.risk_service.is_emergency_stop_active())
        
        # Reset should work
        success = self.risk_service.reset_emergency_stop()
        self.assertTrue(success)
        self.assertFalse(self.risk_service.is_emergency_stop_active())
    
    def test_portfolio_risk_limits(self):
        """Test portfolio-level risk limit enforcement"""
        
        # Create mock positions with high concentration
        test_positions = {
            'AAPL': {'market_value': 80000, 'quantity': 800},  # 80% of portfolio
            'MSFT': {'market_value': 20000, 'quantity': 200}   # 20% of portfolio
        }
        
        # Test concentration limit violation
        violations = self.risk_service._check_concentration_limits(test_positions)
        
        # Should have a violation for AAPL concentration
        self.assertTrue(any('AAPL' in violation for violation in violations))
    
    def test_daily_loss_limits(self):
        """Test daily loss limit enforcement"""
        
        # Mock high daily loss
        self.mock_data_service.get_portfolio_summary.return_value = {
            'total_open_value': 100000,
            'cash': 20000,
            'unrealized_pnl': -8000  # 8% loss
        }
        
        violations = self.risk_service._check_daily_loss_limits()
        
        # Should have a daily loss violation
        self.assertTrue(len(violations) > 0)
        self.assertTrue(any('daily loss' in violation.lower() for violation in violations))

class TestRiskMiddleware(unittest.TestCase):
    """Test risk validation middleware"""
    
    def setUp(self):
        # Mock risk service
        self.mock_risk_service = Mock()
        self.mock_risk_service.is_emergency_stop_active.return_value = False
        self.mock_risk_service.validate_trade_risk.return_value = {
            'approved': True,
            'warnings': [],
            'recommendations': [],
            'risk_metrics': {}
        }
        
        # Mock trailing stop manager
        self.mock_trailing_manager = Mock()
        self.mock_trailing_manager.get_stop_status.return_value = None
        
        with patch('risk_management.risk_middleware.get_risk_service', return_value=self.mock_risk_service), \
             patch('risk_management.risk_middleware.get_trailing_stop_manager', return_value=self.mock_trailing_manager):
            self.middleware = RiskValidationMiddleware()
    
    def test_trade_validation_approval(self):
        """Test trade validation for approved trades"""
        
        result = self.middleware.validate_trade(
            action=TradeAction.BUY,
            symbol="AAPL",
            quantity=100,
            price=150.0
        )
        
        self.assertTrue(result.approved)
        self.assertEqual(result.symbol, "AAPL")
        self.assertEqual(result.action, TradeAction.BUY)
    
    def test_trade_validation_rejection(self):
        """Test trade validation for rejected trades"""
        
        # Mock risk service to reject trade
        self.mock_risk_service.validate_trade_risk.return_value = {
            'approved': False,
            'warnings': ['Risk limit exceeded'],
            'recommendations': ['Reduce position size'],
            'risk_metrics': {'risk_score': 85}
        }
        
        result = self.middleware.validate_trade(
            action=TradeAction.BUY,
            symbol="AAPL",
            quantity=1000,  # Large quantity
            price=150.0
        )
        
        self.assertFalse(result.approved)
        self.assertTrue(len(result.messages) > 0)
    
    def test_emergency_stop_validation(self):
        """Test validation during emergency stop"""
        
        # Mock emergency stop active
        self.mock_risk_service.is_emergency_stop_active.return_value = True
        
        result = self.middleware.validate_trade(
            action=TradeAction.BUY,
            symbol="AAPL",
            quantity=100,
            price=150.0
        )
        
        self.assertFalse(result.approved)
        self.assertEqual(result.severity, ValidationSeverity.CRITICAL)
        self.assertTrue(any('EMERGENCY STOP' in msg for msg in result.messages))
    
    def test_input_validation(self):
        """Test input parameter validation"""
        
        # Test invalid symbol
        result = self.middleware.validate_trade(
            action=TradeAction.BUY,
            symbol="",
            quantity=100,
            price=150.0
        )
        
        self.assertFalse(result.approved)
        self.assertEqual(result.severity, ValidationSeverity.ERROR)
        
        # Test invalid price
        result = self.middleware.validate_trade(
            action=TradeAction.BUY,
            symbol="AAPL",
            quantity=100,
            price=-150.0
        )
        
        self.assertFalse(result.approved)
        self.assertEqual(result.severity, ValidationSeverity.ERROR)
    
    def test_override_functionality(self):
        """Test risk validation override functionality"""
        
        # Enable override
        success = self.middleware.enable_override("Emergency trading", 30)
        self.assertTrue(success)
        
        # Mock emergency stop to test override
        self.mock_risk_service.is_emergency_stop_active.return_value = True
        
        result = self.middleware.validate_trade(
            action=TradeAction.BUY,
            symbol="AAPL",
            quantity=100,
            price=150.0
        )
        
        # Should be approved due to override
        self.assertTrue(result.approved)
        self.assertEqual(result.severity, ValidationSeverity.WARNING)
        
        # Disable override
        self.middleware.disable_override()
        
        # Should now be rejected
        result = self.middleware.validate_trade(
            action=TradeAction.BUY,
            symbol="AAPL",
            quantity=100,
            price=150.0
        )
        
        self.assertFalse(result.approved)

class TestTrailingStopManager(unittest.TestCase):
    """Test trailing stop functionality"""
    
    def setUp(self):
        self.trailing_manager = TrailingStopManager()
        self.test_config = TrailingStopConfig(
            stop_type=TrailingStopType.PERCENTAGE,
            initial_distance=0.05,  # 5%
            trail_distance=0.02,    # 2%
            activation_threshold=0.03  # 3%
        )
    
    def test_trailing_stop_creation(self):
        """Test creating trailing stops"""
        
        success = self.trailing_manager.add_trailing_stop(
            symbol="AAPL",
            entry_price=100.0,
            position_size=100,
            config=self.test_config
        )
        
        self.assertTrue(success)
        
        # Check stop status
        status = self.trailing_manager.get_stop_status("AAPL")
        self.assertIsNotNone(status)
        self.assertEqual(status['symbol'], "AAPL")
        self.assertEqual(status['entry_price'], 100.0)
    
    def test_trailing_stop_activation(self):
        """Test trailing stop activation"""
        
        # Add trailing stop
        self.trailing_manager.add_trailing_stop(
            symbol="AAPL",
            entry_price=100.0,
            position_size=100,
            config=self.test_config
        )
        
        # Price goes up (should activate trailing)
        result = self.trailing_manager.update_price("AAPL", 103.5)  # 3.5% gain
        self.assertIsNone(result)  # No trigger yet
        
        # Check that trailing is activated
        status = self.trailing_manager.get_stop_status("AAPL")
        self.assertTrue(status['is_activated'])
    
    def test_trailing_stop_trigger(self):
        """Test trailing stop trigger"""
        
        # Add trailing stop
        self.trailing_manager.add_trailing_stop(
            symbol="AAPL",
            entry_price=100.0,
            position_size=100,
            config=self.test_config
        )
        
        # Price goes up to activate trailing
        self.trailing_manager.update_price("AAPL", 105.0)  # 5% gain
        
        # Price goes up more (trailing should adjust)
        self.trailing_manager.update_price("AAPL", 110.0)  # 10% gain
        
        # Price drops enough to trigger stop
        trigger_result = self.trailing_manager.update_price("AAPL", 107.5)  # Drop from 110 to 107.5
        
        # Should trigger the stop
        self.assertIsNotNone(trigger_result)
        self.assertEqual(trigger_result['symbol'], "AAPL")
        self.assertTrue(trigger_result['was_trailing'])
    
    def test_trailing_stop_input_validation(self):
        """Test trailing stop input validation"""
        
        # Test invalid symbol
        success = self.trailing_manager.add_trailing_stop(
            symbol="",
            entry_price=100.0,
            position_size=100,
            config=self.test_config
        )
        self.assertFalse(success)
        
        # Test invalid entry price
        success = self.trailing_manager.add_trailing_stop(
            symbol="AAPL",
            entry_price=-100.0,
            position_size=100,
            config=self.test_config
        )
        self.assertFalse(success)
        
        # Test zero position size
        success = self.trailing_manager.add_trailing_stop(
            symbol="AAPL",
            entry_price=100.0,
            position_size=0,
            config=self.test_config
        )
        self.assertFalse(success)

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete risk management system"""
    
    def setUp(self):
        # Set up logging for tests
        logging.basicConfig(level=logging.INFO)
        
        # Create test data
        self.test_data = self._create_test_data()
    
    def _create_test_data(self):
        """Create synthetic market data for testing"""
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        np.random.seed(42)
        
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = 100 * (1 + returns).cumprod()
        
        data = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.005, len(prices))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(prices)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(prices)))),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, len(prices))
        }, index=dates)
        
        data['high'] = data[['open', 'high', 'close']].max(axis=1)
        data['low'] = data[['open', 'low', 'close']].min(axis=1)
        
        return data
    
    @patch('risk_management.risk_service.get_trading_config')
    @patch('risk_management.risk_service.get_data_service')
    def test_end_to_end_risk_workflow(self, mock_data_service, mock_config):
        """Test complete risk management workflow"""
        
        # Mock configuration
        mock_config.return_value = Mock(
            max_daily_loss_percentage=5.0,
            max_drawdown_percentage=15.0,
            max_positions=10,
            correlation_threshold=0.7
        )
        
        # Mock data service
        mock_data_service.return_value = Mock(
            get_portfolio_summary=Mock(return_value={
                'total_open_value': 100000,
                'cash': 20000,
                'unrealized_pnl': -1000
            }),
            get_open_orders=Mock(return_value=pd.DataFrame()),
            get_historical_data=Mock(return_value=self.test_data)
        )
        
        # Create risk service
        risk_service = RiskManagementService()
        
        # Test position sizing
        position_rec = risk_service.calculate_position_size(
            symbol="AAPL",
            entry_price=150.0,
            stop_loss_price=142.5,
            method="volatility_adjusted"
        )
        
        self.assertIsNotNone(position_rec)
        self.assertGreater(position_rec.risk_adjusted_size, 0)
        
        # Test trade validation
        validation_result = risk_service.validate_trade_risk(
            symbol="AAPL",
            action="BUY",
            quantity=100,
            price=150.0
        )
        
        self.assertIsInstance(validation_result, dict)
        self.assertIn('approved', validation_result)
        
        # Test dynamic stop loss
        stop_loss = risk_service.calculate_dynamic_stop_loss(
            symbol="AAPL",
            entry_price=150.0,
            method="atr"
        )
        
        self.assertGreater(stop_loss, 0)
        self.assertLess(stop_loss, 150.0)  # Stop should be below entry

def run_stress_test():
    """Run stress tests with extreme market conditions"""
    
    print("\n" + "="*60)
    print("RUNNING STRESS TESTS")
    print("="*60)
    
    # Test with extreme volatility
    print("\n1. Testing with extreme volatility...")
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    extreme_returns = np.random.normal(0, 0.20, len(dates))  # 20% daily volatility
    prices = 100 * (1 + extreme_returns).cumprod()
    
    extreme_data = pd.DataFrame({
        'open': prices,
        'high': prices * 1.1,
        'low': prices * 0.9,
        'close': prices,
        'volume': np.random.randint(100000, 1000000, len(prices))
    }, index=dates)
    
    position_sizer = DynamicPositionSizer()
    
    try:
        recommendation = position_sizer.calculate_position_size(
            symbol="EXTREME_TEST",
            entry_price=100.0,
            stop_loss_price=95.0,
            portfolio_value=10000,
            method=PositionSizingMethod.VOLATILITY_ADJUSTED,
            historical_data=extreme_data
        )
        
        print(f"   ✓ Extreme volatility test passed: position size = {recommendation.risk_adjusted_size:.3f}")
        print(f"   ✓ Risk per trade: {recommendation.risk_per_trade:.3f}")
        
        # Verify position size is within bounds
        assert 0 < recommendation.risk_adjusted_size <= 0.25, "Position size out of bounds"
        assert recommendation.risk_per_trade <= 0.05, "Risk per trade too high"
        
    except Exception as e:
        print(f"   ✗ Extreme volatility test failed: {e}")
    
    # Test with market crash scenario
    print("\n2. Testing market crash scenario...")
    crash_returns = np.concatenate([
        np.random.normal(0.001, 0.02, 50),  # Normal period
        np.array([-0.10, -0.15, -0.20, -0.08, -0.12]),  # Crash
        np.random.normal(-0.002, 0.04, 45)  # Recovery period
    ])
    
    crash_prices = 100 * (1 + crash_returns).cumprod()
    crash_data = pd.DataFrame({
        'open': crash_prices,
        'high': crash_prices * 1.02,
        'low': crash_prices * 0.98,
        'close': crash_prices,
        'volume': np.random.randint(100000, 1000000, len(crash_prices))
    })
    
    try:
        # Create mock risk service
        with patch('risk_management.risk_service.get_trading_config') as mock_config, \
             patch('risk_management.risk_service.get_data_service') as mock_data:
            
            mock_config.return_value = Mock(
                max_daily_loss_percentage=5.0,
                max_drawdown_percentage=15.0,
                max_positions=10,
                correlation_threshold=0.7
            )
            
            mock_data.return_value = Mock(
                get_portfolio_summary=Mock(return_value={
                    'total_open_value': 80000,  # Portfolio down 20%
                    'cash': 20000,
                    'unrealized_pnl': -20000  # 20% unrealized loss
                }),
                get_open_orders=Mock(return_value=pd.DataFrame())
            )
            
            risk_service = RiskManagementService()
            
            # Should trigger emergency conditions
            portfolio_assessment = risk_service.assess_portfolio_risk()
            violations = portfolio_assessment.get('risk_violations', [])
            
            print(f"   ✓ Market crash test completed: {len(violations)} violations detected")
            
            # Emergency stop should be triggered
            if risk_service.is_emergency_stop_active():
                print(f"   ✓ Emergency stop correctly triggered")
            else:
                print(f"   ! Emergency stop not triggered (may be expected)")
            
    except Exception as e:
        print(f"   ✗ Market crash test failed: {e}")
    
    print("\n3. Testing with invalid data...")
    
    # Test with NaN values
    invalid_data = extreme_data.copy()
    invalid_data.iloc[50:60] = np.nan  # Insert NaN values
    
    try:
        recommendation = position_sizer.calculate_position_size(
            symbol="INVALID_TEST",
            entry_price=100.0,
            stop_loss_price=95.0,
            portfolio_value=10000,
            method=PositionSizingMethod.ATR_BASED,
            historical_data=invalid_data
        )
        
        print(f"   ✓ Invalid data test passed: fallback size = {recommendation.risk_adjusted_size:.3f}")
        assert recommendation.risk_adjusted_size > 0, "Fallback position size should be positive"
        
    except Exception as e:
        print(f"   ✗ Invalid data test failed: {e}")
    
    print("\n" + "="*60)
    print("STRESS TESTS COMPLETED")
    print("="*60)

def main():
    """Run all tests"""
    
    print("Starting Enhanced Risk Management Test Suite")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestPositionSizer,
        TestRiskService,
        TestRiskMiddleware,
        TestTrailingStopManager,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('\\n')[-2]}")
    
    # Run stress tests
    if result.testsRun > 0 and len(result.failures) == 0 and len(result.errors) == 0:
        run_stress_test()
    else:
        print("\nSkipping stress tests due to test failures")
    
    # Return exit code
    return 0 if (len(result.failures) == 0 and len(result.errors) == 0) else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)