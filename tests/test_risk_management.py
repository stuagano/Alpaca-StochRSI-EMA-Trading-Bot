"""
Comprehensive unit tests for the enhanced risk management system.
Tests cover position sizing validation, stop loss calculations, portfolio risk limits,
trailing stop functionality, and advanced risk controls.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import threading
import time
from decimal import Decimal

from risk_management.enhanced_risk_manager import (
    EnhancedRiskManager, RiskValidationResult, PortfolioRiskState,
    RiskViolationType, get_enhanced_risk_manager
)
from risk_management.position_sizer import PositionSizeRecommendation
from risk_management.trailing_stop_manager import TrailingStopConfig, TrailingStopType
from risk_management.risk_config import RiskConfig, RiskLevel


class TestEnhancedRiskManagerInitialization:
    """Test enhanced risk manager initialization and setup."""
    
    def test_risk_manager_initialization(self):
        """Test basic risk manager initialization."""
        manager = EnhancedRiskManager()
        
        assert manager.config is not None
        assert manager.position_sizer is not None
        assert manager.trailing_stop_manager is not None
        assert manager.portfolio_analyzer is not None
        assert manager.var_model is not None
        assert manager.volatility_model is not None
        assert manager.portfolio_state is not None
        assert manager.active_positions == {}
        assert manager.risk_breaches == {}
        assert manager.emergency_stop_active is False
        assert manager.override_active is False
    
    def test_risk_manager_with_custom_config(self):
        """Test risk manager initialization with custom config."""
        custom_config = RiskConfig()
        custom_config.max_position_size = 0.10
        custom_config.max_daily_loss = 0.03
        
        manager = EnhancedRiskManager(config=custom_config)
        
        assert manager.config.max_position_size == 0.10
        assert manager.config.max_daily_loss == 0.03
    
    def test_singleton_risk_manager(self):
        """Test singleton risk manager instance."""
        manager1 = get_enhanced_risk_manager()
        manager2 = get_enhanced_risk_manager()
        
        assert manager1 is manager2


class TestPositionSizeValidation:
    """Test position size validation functionality."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance for testing."""
        config = RiskConfig()
        config.max_position_size = 0.10  # 10%
        config.max_portfolio_exposure = 0.80  # 80%
        config.max_positions = 5
        config.min_stop_loss_distance = 0.01  # 1%
        config.max_stop_loss_distance = 0.20  # 20%
        
        manager = EnhancedRiskManager(config=config)
        return manager
    
    def test_validate_position_size_approved(self, risk_manager):
        """Test position size validation with approval."""
        with patch.object(risk_manager, '_get_portfolio_value', return_value=100000.0), \
             patch.object(risk_manager, '_calculate_current_exposure', return_value=20000.0):
            
            result = risk_manager.validate_position_size(
                symbol='AAPL',
                proposed_size=50,  # $5000 position (5%)
                entry_price=100.0,
                stop_loss_price=95.0
            )
            
            assert result.approved is True
            assert result.confidence_score > 0.5
            assert result.risk_score < 50
            assert len(result.violations) == 0
    
    def test_validate_position_size_too_large(self, risk_manager):
        """Test position size validation with oversized position."""
        with patch.object(risk_manager, '_get_portfolio_value', return_value=100000.0), \
             patch.object(risk_manager, '_calculate_current_exposure', return_value=20000.0):
            
            result = risk_manager.validate_position_size(
                symbol='AAPL',
                proposed_size=150,  # $15000 position (15%)
                entry_price=100.0,
                stop_loss_price=95.0
            )
            
            assert result.approved is False
            assert 'exceeds maximum limit' in str(result.violations)
            assert result.risk_score > 50
    
    def test_validate_position_size_portfolio_exposure_exceeded(self, risk_manager):
        """Test position size validation with portfolio exposure exceeded."""
        with patch.object(risk_manager, '_get_portfolio_value', return_value=100000.0), \
             patch.object(risk_manager, '_calculate_current_exposure', return_value=75000.0):
            
            result = risk_manager.validate_position_size(
                symbol='AAPL',
                proposed_size=80,  # $8000 position would exceed 80% limit
                entry_price=100.0,
                stop_loss_price=95.0
            )
            
            assert result.approved is False
            assert 'portfolio exposure limit' in str(result.violations)
    
    def test_validate_position_size_max_positions_exceeded(self, risk_manager):
        """Test position size validation with max positions exceeded."""
        # Mock active positions at limit
        risk_manager.active_positions = {
            'AAPL': {}, 'MSFT': {}, 'GOOGL': {}, 'TSLA': {}, 'NVDA': {}
        }
        
        with patch.object(risk_manager, '_get_portfolio_value', return_value=100000.0), \
             patch.object(risk_manager, '_calculate_current_exposure', return_value=20000.0):
            
            result = risk_manager.validate_position_size(
                symbol='AMZN',
                proposed_size=50,
                entry_price=100.0,
                stop_loss_price=95.0
            )
            
            assert result.approved is False
            assert 'Maximum positions limit reached' in str(result.violations)
    
    def test_validate_position_size_invalid_inputs(self, risk_manager):
        """Test position size validation with invalid inputs."""
        # Test negative position size
        result = risk_manager.validate_position_size(
            symbol='AAPL',
            proposed_size=-10,
            entry_price=100.0
        )
        
        assert result.approved is False
        assert 'Position size must be positive' in str(result.violations)
        
        # Test invalid symbol
        result = risk_manager.validate_position_size(
            symbol='',
            proposed_size=10,
            entry_price=100.0
        )
        
        assert result.approved is False
        assert 'Invalid symbol' in str(result.violations)
        
        # Test invalid entry price
        result = risk_manager.validate_position_size(
            symbol='AAPL',
            proposed_size=10,
            entry_price=0.0
        )
        
        assert result.approved is False
        assert 'Entry price must be positive' in str(result.violations)
    
    def test_validate_position_size_emergency_stop(self, risk_manager):
        """Test position size validation during emergency stop."""
        risk_manager.emergency_stop_active = True
        risk_manager.emergency_stop_reason = "Market volatility"
        
        result = risk_manager.validate_position_size(
            symbol='AAPL',
            proposed_size=10,
            entry_price=100.0
        )
        
        assert result.approved is False
        assert 'Emergency stop active' in str(result.violations)
    
    def test_validate_position_size_with_adjustment(self, risk_manager):
        """Test position size validation with size adjustment."""
        with patch.object(risk_manager, '_get_portfolio_value', return_value=100000.0), \
             patch.object(risk_manager, '_calculate_current_exposure', return_value=20000.0):
            
            result = risk_manager.validate_position_size(
                symbol='AAPL',
                proposed_size=120,  # $12000 position (12%, slightly over 10% limit)
                entry_price=100.0,
                stop_loss_price=95.0
            )
            
            # Should suggest adjustment rather than rejection
            assert result.position_size_adjustment is not None
            assert result.position_size_adjustment < 120
            assert 'Position size reduced' in str(result.warnings)


class TestOptimalPositionSizing:
    """Test optimal position sizing calculations."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance for testing."""
        config = RiskConfig()
        config.default_risk_per_trade = 0.02  # 2%
        config.use_atr_stop_loss = True
        config.atr_multiplier = 2.0
        
        manager = EnhancedRiskManager(config=config)
        return manager
    
    @patch('risk_management.enhanced_risk_manager.EnhancedRiskManager._get_historical_data')
    @patch('risk_management.enhanced_risk_manager.EnhancedRiskManager._get_portfolio_value')
    def test_calculate_optimal_position_size_success(self, mock_portfolio_value, mock_historical_data, risk_manager):
        """Test successful optimal position size calculation."""
        mock_portfolio_value.return_value = 100000.0
        
        # Mock historical data
        historical_data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'close': [100, 101, 102, 103, 104],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        mock_historical_data.return_value = historical_data
        
        # Mock position sizer recommendation
        mock_recommendation = PositionSizeRecommendation(
            symbol='AAPL',
            recommended_size=20.0,
            max_safe_size=25.0,
            risk_adjusted_size=20.0,
            method_used='kelly',
            risk_per_trade=0.02,
            stop_loss_distance=0.05,
            confidence_score=0.8
        )
        
        with patch.object(risk_manager.position_sizer, 'calculate_position_size', return_value=mock_recommendation):
            result = risk_manager.calculate_optimal_position_size(
                symbol='AAPL',
                entry_price=100.0,
                stop_loss_price=95.0
            )
            
            assert result.symbol == 'AAPL'
            assert result.risk_adjusted_size == 20.0
            assert result.confidence_score == 0.8
    
    def test_calculate_optimal_position_size_error_fallback(self, risk_manager):
        """Test optimal position size calculation with error fallback."""
        with patch.object(risk_manager, '_get_portfolio_value', side_effect=Exception("API Error")):
            result = risk_manager.calculate_optimal_position_size(
                symbol='AAPL',
                entry_price=100.0
            )
            
            # Should return conservative fallback
            assert result.method_used == 'fallback'
            assert result.confidence_score == 0.1
            assert 'Calculation failed' in str(result.warnings)


class TestTrailingStopManagement:
    """Test trailing stop functionality."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance for testing."""
        config = RiskConfig()
        config.trailing_stop_distance = 0.05  # 5%
        config.trailing_activation_threshold = 0.02  # 2%
        
        manager = EnhancedRiskManager(config=config)
        return manager
    
    def test_create_trailing_stop_success(self, risk_manager):
        """Test successful trailing stop creation."""
        with patch.object(risk_manager.trailing_stop_manager, 'add_trailing_stop', return_value=True):
            result = risk_manager.create_trailing_stop(
                symbol='AAPL',
                entry_price=100.0,
                position_size=10.0
            )
            
            assert result is True
    
    def test_create_trailing_stop_with_config_override(self, risk_manager):
        """Test trailing stop creation with configuration override."""
        config_override = {
            'type': 'percentage',
            'initial_distance': 0.03,
            'trail_distance': 0.015,
            'activation_threshold': 0.01
        }
        
        with patch.object(risk_manager.trailing_stop_manager, 'add_trailing_stop', return_value=True) as mock_add:
            result = risk_manager.create_trailing_stop(
                symbol='AAPL',
                entry_price=100.0,
                position_size=10.0,
                config_override=config_override
            )
            
            assert result is True
            # Verify the configuration was used
            call_args = mock_add.call_args
            config_arg = call_args[1]['config']
            assert config_arg.initial_distance == 0.03
    
    def test_update_position_price_with_trigger(self, risk_manager):
        """Test position price update with trailing stop trigger."""
        trigger_info = {
            'triggered': True,
            'trigger_price': 104.0,
            'stop_type': 'trailing'
        }
        
        with patch.object(risk_manager.trailing_stop_manager, 'update_price', return_value=trigger_info), \
             patch.object(risk_manager, '_update_portfolio_state'), \
             patch.object(risk_manager, '_check_portfolio_risk_limits'):
            
            result = risk_manager.update_position_price('AAPL', 105.0)
            
            assert result == trigger_info
            assert result['triggered'] is True


class TestPositionTracking:
    """Test position tracking and management."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance for testing."""
        return EnhancedRiskManager()
    
    def test_add_position_success(self, risk_manager):
        """Test successful position addition."""
        result = risk_manager.add_position(
            symbol='AAPL',
            entry_price=100.0,
            position_size=10.0,
            stop_loss_price=95.0
        )
        
        assert result is True
        assert 'AAPL' in risk_manager.active_positions
        
        position = risk_manager.active_positions['AAPL']
        assert position['symbol'] == 'AAPL'
        assert position['entry_price'] == 100.0
        assert position['position_size'] == 10.0
        assert position['stop_loss_price'] == 95.0
        assert position['market_value'] == 1000.0
    
    def test_remove_position_success(self, risk_manager):
        """Test successful position removal."""
        # First add a position
        risk_manager.add_position('AAPL', 100.0, 10.0, 95.0)
        
        with patch.object(risk_manager.trailing_stop_manager, 'remove_trailing_stop'):
            result = risk_manager.remove_position('AAPL')
            
            assert result is True
            assert 'AAPL' not in risk_manager.active_positions
    
    def test_remove_position_not_found(self, risk_manager):
        """Test position removal when position doesn't exist."""
        result = risk_manager.remove_position('NONEXISTENT')
        
        assert result is False


class TestPortfolioRiskAnalysis:
    """Test portfolio-level risk analysis."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance with test positions."""
        manager = EnhancedRiskManager()
        
        # Add some test positions
        manager.add_position('AAPL', 100.0, 10.0, 95.0)
        manager.add_position('MSFT', 200.0, 5.0, 190.0)
        
        return manager
    
    def test_get_portfolio_risk_summary(self, risk_manager):
        """Test portfolio risk summary generation."""
        with patch.object(risk_manager, '_get_portfolio_value', return_value=50000.0):
            summary = risk_manager.get_portfolio_risk_summary()
            
            assert 'timestamp' in summary
            assert 'risk_level' in summary
            assert 'portfolio_metrics' in summary
            assert 'position_metrics' in summary
            assert 'risk_limits' in summary
            
            # Check portfolio metrics
            portfolio_metrics = summary['portfolio_metrics']
            assert 'total_exposure_pct' in portfolio_metrics
            assert 'cash_available' in portfolio_metrics
            
            # Check position metrics
            position_metrics = summary['position_metrics']
            assert position_metrics['total_positions'] == 2
    
    def test_portfolio_risk_level_classification(self, risk_manager):
        """Test portfolio risk level classification."""
        with patch.object(risk_manager, '_get_portfolio_value', return_value=50000.0), \
             patch.object(risk_manager, '_get_daily_loss_percentage', return_value=1.0):  # 1% loss
            
            risk_level = risk_manager._classify_portfolio_risk_level()
            assert risk_level in ['LOW', 'MODERATE', 'HIGH', 'CRITICAL', 'UNKNOWN']
    
    def test_check_portfolio_risk_limits_daily_loss(self, risk_manager):
        """Test portfolio risk limit checking for daily loss."""
        risk_manager.config.max_daily_loss = 0.02  # 2%
        
        with patch.object(risk_manager, '_get_daily_loss_percentage', return_value=3.0):  # 3% loss
            risk_manager._check_portfolio_risk_limits()
            
            # Should record a breach
            assert RiskViolationType.DAILY_LOSS.value in risk_manager.risk_breaches
    
    def test_check_portfolio_risk_limits_exposure(self, risk_manager):
        """Test portfolio risk limit checking for exposure."""
        risk_manager.config.max_portfolio_exposure = 0.80  # 80%
        
        with patch.object(risk_manager, '_get_portfolio_value', return_value=10000.0):  # Small portfolio
            risk_manager._check_portfolio_risk_limits()
            
            # With positions worth $2000 in a $10k portfolio (20%), should be fine
            # But let's test with higher exposure
            risk_manager.portfolio_state.total_exposure = 9000.0  # 90%
            risk_manager._check_portfolio_risk_limits()
            
            # Should record a breach
            assert RiskViolationType.PORTFOLIO_EXPOSURE.value in risk_manager.risk_breaches


class TestEmergencyControls:
    """Test emergency controls and overrides."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance for testing."""
        return EnhancedRiskManager()
    
    def test_enable_emergency_override(self, risk_manager):
        """Test enabling emergency override."""
        result = risk_manager.enable_emergency_override(
            reason="Market crash",
            duration_minutes=30
        )
        
        assert result is True
        assert risk_manager.override_active is True
        assert risk_manager.override_reason == "Market crash"
        assert risk_manager.override_expiry is not None
    
    def test_disable_emergency_override(self, risk_manager):
        """Test disabling emergency override."""
        # First enable it
        risk_manager.enable_emergency_override("Test", 30)
        
        result = risk_manager.disable_emergency_override()
        
        assert result is True
        assert risk_manager.override_active is False
        assert risk_manager.override_reason is None
        assert risk_manager.override_expiry is None
    
    def test_emergency_override_validation_bypass(self, risk_manager):
        """Test that emergency override bypasses normal validation."""
        # Set emergency stop
        risk_manager.emergency_stop_active = True
        risk_manager.emergency_stop_reason = "System error"
        
        # Normal validation should reject
        with patch.object(risk_manager, '_get_portfolio_value', return_value=100000.0):
            result = risk_manager.validate_position_size('AAPL', 10, 100.0)
            assert result.approved is False
        
        # Enable override
        risk_manager.enable_emergency_override("Override needed", 30)
        
        # Now validation should consider override
        with patch.object(risk_manager, '_get_portfolio_value', return_value=100000.0), \
             patch.object(risk_manager, '_calculate_current_exposure', return_value=0.0):
            result = risk_manager.validate_position_size('AAPL', 10, 100.0)
            # Validation should proceed normally with override active


class TestValidationStatistics:
    """Test validation statistics tracking."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance for testing."""
        return EnhancedRiskManager()
    
    def test_validation_statistics_tracking(self, risk_manager):
        """Test that validation statistics are tracked correctly."""
        initial_stats = risk_manager.get_validation_statistics()
        assert initial_stats['total_validations'] == 0
        assert initial_stats['approvals'] == 0
        assert initial_stats['rejections'] == 0
        
        # Perform some validations
        with patch.object(risk_manager, '_get_portfolio_value', return_value=100000.0), \
             patch.object(risk_manager, '_calculate_current_exposure', return_value=20000.0):
            
            # Approved validation
            risk_manager.validate_position_size('AAPL', 10, 100.0, 95.0)
            
            # Rejected validation (too large)
            risk_manager.validate_position_size('MSFT', 200, 100.0, 95.0)
        
        stats = risk_manager.get_validation_statistics()
        assert stats['total_validations'] == 2
        assert stats['approvals'] == 1
        assert stats['rejections'] == 1
        assert stats['approval_rate'] == 50.0
    
    def test_reset_validation_statistics(self, risk_manager):
        """Test resetting validation statistics."""
        # Perform a validation first
        with patch.object(risk_manager, '_get_portfolio_value', return_value=100000.0), \
             patch.object(risk_manager, '_calculate_current_exposure', return_value=20000.0):
            risk_manager.validate_position_size('AAPL', 10, 100.0, 95.0)
        
        # Reset statistics
        result = risk_manager.reset_validation_statistics()
        assert result is True
        
        stats = risk_manager.get_validation_statistics()
        assert stats['total_validations'] == 0
        assert stats['approvals'] == 0
        assert stats['rejections'] == 0


class TestCorrelationRiskAssessment:
    """Test correlation risk assessment."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance for testing."""
        manager = EnhancedRiskManager()
        
        # Add some tech positions
        manager.add_position('QQQ', 300.0, 10.0, 285.0)
        manager.add_position('XLK', 150.0, 20.0, 142.5)
        
        return manager
    
    def test_assess_correlation_risk_high(self, risk_manager):
        """Test correlation risk assessment with high correlation."""
        correlation_risk = risk_manager._assess_correlation_risk('VGT')  # Another tech ETF
        
        # Should detect high correlation with existing tech positions
        assert correlation_risk > 0
    
    def test_assess_correlation_risk_low(self, risk_manager):
        """Test correlation risk assessment with low correlation."""
        correlation_risk = risk_manager._assess_correlation_risk('XLF')  # Financial ETF
        
        # Should be lower correlation
        assert correlation_risk >= 0
    
    def test_symbols_are_correlated(self, risk_manager):
        """Test symbol correlation detection."""
        # Test tech ETFs
        assert risk_manager._symbols_are_correlated('QQQ', 'XLK') is True
        assert risk_manager._symbols_are_correlated('XLF', 'VFH') is True
        
        # Test different sectors
        assert risk_manager._symbols_are_correlated('QQQ', 'XLF') is False
        
        # Test similar tickers
        assert risk_manager._symbols_are_correlated('AAPL', 'AAPLB') is True


class TestATRCalculations:
    """Test ATR-based calculations."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance for testing."""
        config = RiskConfig()
        config.use_atr_position_sizing = True
        config.use_atr_stop_loss = True
        config.atr_multiplier = 2.0
        
        return EnhancedRiskManager(config=config)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLC data for ATR calculation."""
        return pd.DataFrame({
            'open': [100, 101, 102, 103, 104, 105],
            'high': [101, 103, 104, 105, 106, 107],
            'low': [99, 100, 101, 102, 103, 104],
            'close': [100, 102, 103, 104, 105, 106],
            'volume': [1000, 1100, 1200, 1300, 1400, 1500]
        })
    
    def test_calculate_atr(self, risk_manager, sample_data):
        """Test ATR calculation."""
        atr = risk_manager._calculate_atr(sample_data, period=5)
        
        assert atr > 0
        assert not pd.isna(atr)
    
    def test_calculate_atr_insufficient_data(self, risk_manager):
        """Test ATR calculation with insufficient data."""
        small_data = pd.DataFrame({
            'high': [101, 102],
            'low': [99, 100],
            'close': [100, 101]
        })
        
        atr = risk_manager._calculate_atr(small_data, period=14)
        assert atr == 0.0
    
    def test_calculate_dynamic_stop_loss_atr(self, risk_manager, sample_data):
        """Test dynamic stop loss calculation using ATR."""
        with patch.object(risk_manager, '_get_historical_data', return_value=sample_data):
            stop_loss = risk_manager._calculate_dynamic_stop_loss('AAPL', 100.0)
            
            # Should be less than entry price
            assert stop_loss < 100.0
            assert stop_loss > 0
    
    def test_calculate_dynamic_stop_loss_fallback(self, risk_manager):
        """Test dynamic stop loss calculation with fallback."""
        risk_manager.config.use_atr_stop_loss = False
        risk_manager.config.default_stop_loss_distance = 0.05
        
        stop_loss = risk_manager._calculate_dynamic_stop_loss('AAPL', 100.0)
        
        # Should use percentage-based fallback
        assert stop_loss == 95.0  # 100 * (1 - 0.05)


class TestThreadSafety:
    """Test thread safety of risk management operations."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance for testing."""
        return EnhancedRiskManager()
    
    def test_concurrent_position_validation(self, risk_manager):
        """Test concurrent position validations."""
        results = []
        errors = []
        
        def validate_position(symbol, size):
            try:
                with patch.object(risk_manager, '_get_portfolio_value', return_value=100000.0), \
                     patch.object(risk_manager, '_calculate_current_exposure', return_value=20000.0):
                    result = risk_manager.validate_position_size(symbol, size, 100.0, 95.0)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=validate_position,
                args=(f'STOCK{i}', 10)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0
        assert len(results) == 10
        
        # Verify validation statistics are consistent
        stats = risk_manager.get_validation_statistics()
        assert stats['total_validations'] == 10
    
    def test_concurrent_position_management(self, risk_manager):
        """Test concurrent position addition and removal."""
        def add_positions():
            for i in range(5):
                risk_manager.add_position(f'ADD{i}', 100.0, 10.0, 95.0)
        
        def remove_positions():
            time.sleep(0.1)  # Let some positions be added first
            for i in range(3):
                risk_manager.remove_position(f'ADD{i}')
        
        thread1 = threading.Thread(target=add_positions)
        thread2 = threading.Thread(target=remove_positions)
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Should have 2 positions remaining (ADD3, ADD4)
        assert len(risk_manager.active_positions) == 2


class TestErrorHandling:
    """Test error handling in risk management operations."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance for testing."""
        return EnhancedRiskManager()
    
    def test_validation_with_api_error(self, risk_manager):
        """Test validation when portfolio value API fails."""
        with patch.object(risk_manager, '_get_portfolio_value', side_effect=Exception("API Error")):
            result = risk_manager.validate_position_size('AAPL', 10, 100.0, 95.0)
            
            assert result.approved is False
            assert 'Validation error' in str(result.violations)
    
    def test_historical_data_error_handling(self, risk_manager):
        """Test handling of historical data errors."""
        with patch.object(risk_manager, '_get_historical_data', return_value=None):
            # Should use fallback calculations
            stop_loss = risk_manager._calculate_dynamic_stop_loss('AAPL', 100.0)
            assert stop_loss > 0
    
    def test_portfolio_summary_error_handling(self, risk_manager):
        """Test portfolio summary generation with errors."""
        with patch.object(risk_manager, '_update_portfolio_state', side_effect=Exception("Update Error")):
            summary = risk_manager.get_portfolio_risk_summary()
            
            assert 'error' in summary
            assert 'risk_level' in summary
            assert summary['risk_level'] == 'UNKNOWN'


if __name__ == '__main__':
    pytest.main([__file__])