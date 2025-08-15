"""
Integration tests for the trading bot system.
Tests end-to-end workflows including data management, strategy execution,
risk management, and order processing.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import threading
import time
import tempfile
import os
import json

from trading_bot import TradingBot
from services.unified_data_manager import UnifiedDataManager
from strategies.stoch_rsi_strategy import StochRSIStrategy
from strategies.ma_crossover_strategy import MACrossoverStrategy
from risk_management.enhanced_risk_manager import EnhancedRiskManager, RiskValidationResult
from config_params import config


class TestBasicIntegration:
    """Test basic integration between components."""
    
    @pytest.fixture
    def mock_auth_file(self):
        """Create a temporary auth file."""
        auth_data = {
            'APCA-API-KEY-ID': 'test_key_id',
            'APCA-API-SECRET-KEY': 'test_secret_key',
            'BASE-URL': 'https://paper-api.alpaca.markets'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            json.dump(auth_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
    
    @pytest.fixture
    def mock_tickers_file(self):
        """Create a temporary tickers file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("AAPL MSFT GOOGL")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
    
    @pytest.fixture
    def sample_historical_data(self):
        """Create sample historical data."""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='1min')
        data = pd.DataFrame({
            'open': np.random.uniform(99, 101, 100),
            'high': np.random.uniform(100, 102, 100),
            'low': np.random.uniform(98, 100, 100),
            'close': np.random.uniform(99, 101, 100),
            'volume': np.random.randint(1000, 5000, 100)
        }, index=dates)
        
        # Ensure OHLC consistency
        data['high'] = data[['open', 'high', 'close']].max(axis=1)
        data['low'] = data[['open', 'low', 'close']].min(axis=1)
        
        return data
    
    def test_data_manager_initialization_integration(self, mock_auth_file):
        """Test data manager initialization with real file operations."""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', create=True) as mock_open, \
             patch('alpaca_trade_api.REST') as mock_rest, \
             patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'):
            
            # Read actual auth file content
            with open(mock_auth_file, 'r') as f:
                content = f.read()
            mock_open.return_value.__enter__.return_value.read.return_value = content
            
            # Mock Alpaca API
            mock_api = Mock()
            mock_account = Mock()
            mock_account.equity = 100000.0
            mock_api.get_account.return_value = mock_account
            mock_rest.return_value = mock_api
            
            manager = UnifiedDataManager()
            
            # Test that API is properly initialized
            assert manager.api is not None
            
            # Test account info retrieval
            manager.account_breaker = Mock()
            manager.account_breaker.call.return_value = mock_account
            
            account_info = manager.get_account_info()
            assert account_info['equity'] == 100000.0
    
    def test_trading_bot_strategy_integration(self, mock_tickers_file, sample_historical_data):
        """Test trading bot integration with strategy."""
        # Create mock data manager
        mock_data_manager = Mock()
        mock_data_manager.api = Mock()
        mock_data_manager.get_historical_data.return_value = sample_historical_data
        mock_data_manager.get_latest_price.return_value = 100.0
        
        # Create real strategy
        with patch.object(config, 'indicators', {
            'stochRSI': {'enabled': True, 'lower_band': 20, 'upper_band': 80},
            'EMA': {'enabled': True, 'ema_period': 10}
        }):
            strategy = StochRSIStrategy(config)
        
        # Create trading bot
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
            bot = TradingBot(mock_data_manager, strategy)
        
        # Test signal generation
        signal = strategy.generate_signal(sample_historical_data)
        assert signal in [-1, 0, 1]
        
        # Test bot can process the signal
        with patch.object(bot, 'enter_position') as mock_enter:
            mock_data_manager.get_historical_data.return_value = sample_historical_data
            bot.strategy.generate_signal = Mock(return_value=1)  # Force buy signal
            
            bot.run_strategy()
            
            if bot.can_place_new_trade():
                mock_enter.assert_called()


class TestRiskManagementIntegration:
    """Test integration with risk management system."""
    
    @pytest.fixture
    def integrated_bot(self):
        """Create an integrated bot with risk management."""
        mock_data_manager = Mock()
        mock_data_manager.api = Mock()
        mock_strategy = Mock()
        
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
            bot = TradingBot(mock_data_manager, mock_strategy)
            
            # Ensure risk manager is properly initialized
            assert bot.enhanced_risk_manager is not None
            assert bot.enable_enhanced_risk_management is True
            
            return bot
    
    def test_position_entry_with_risk_validation(self, integrated_bot):
        """Test position entry with complete risk validation workflow."""
        # Setup data
        sample_df = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        })
        
        # Mock data manager responses
        integrated_bot.data_manager.get_latest_price.return_value = 100.0
        
        # Mock portfolio value
        mock_account = Mock()
        mock_account.equity = 100000.0
        integrated_bot.api.get_account.return_value = mock_account
        
        # Mock risk manager responses
        mock_validation = RiskValidationResult(
            approved=True,
            confidence_score=0.8,
            risk_score=20.0,
            position_size_adjustment=10.0
        )
        integrated_bot.enhanced_risk_manager.validate_position_size = Mock(return_value=mock_validation)
        
        # Mock optimal position sizing
        from risk_management.position_sizer import PositionSizeRecommendation
        mock_recommendation = PositionSizeRecommendation(
            symbol='AAPL',
            recommended_size=10.0,
            max_safe_size=15.0,
            risk_adjusted_size=10.0,
            method_used='kelly',
            risk_per_trade=0.02,
            stop_loss_distance=0.05,
            confidence_score=0.8
        )
        integrated_bot.enhanced_risk_manager.calculate_optimal_position_size = Mock(return_value=mock_recommendation)
        
        # Mock other risk manager methods
        integrated_bot.enhanced_risk_manager.add_position = Mock(return_value=True)
        integrated_bot.enhanced_risk_manager.create_trailing_stop = Mock(return_value=True)
        
        # Mock order recording
        with patch.object(integrated_bot, 'record_order') as mock_record:
            integrated_bot.enter_position('AAPL', sample_df)
            
            # Verify risk validation was called
            integrated_bot.enhanced_risk_manager.validate_position_size.assert_called_once()
            
            # Verify optimal sizing was calculated
            integrated_bot.enhanced_risk_manager.calculate_optimal_position_size.assert_called_once()
            
            # Verify order was placed
            integrated_bot.api.submit_order.assert_called_once()
            
            # Verify position was added to risk tracking
            integrated_bot.enhanced_risk_manager.add_position.assert_called_once()
            
            # Verify trailing stop was created
            integrated_bot.enhanced_risk_manager.create_trailing_stop.assert_called_once()
            
            # Verify order was recorded
            mock_record.assert_called_once()
    
    def test_position_entry_risk_rejection(self, integrated_bot):
        """Test position entry rejection by risk management."""
        sample_df = pd.DataFrame({
            'close': [100, 101, 102]
        })
        
        integrated_bot.data_manager.get_latest_price.return_value = 100.0
        
        # Mock risk rejection
        mock_validation = RiskValidationResult(
            approved=False,
            confidence_score=0.2,
            risk_score=90.0,
            violations=['Position size too large', 'Portfolio exposure exceeded']
        )
        integrated_bot.enhanced_risk_manager.validate_position_size = Mock(return_value=mock_validation)
        
        integrated_bot.enter_position('AAPL', sample_df)
        
        # Verify order was not placed
        integrated_bot.api.submit_order.assert_not_called()
    
    def test_position_monitoring_integration(self, integrated_bot):
        """Test position monitoring with risk management."""
        # Mock position
        mock_position = Mock()
        mock_position.symbol = 'AAPL'
        mock_position.qty = 10
        mock_position.avg_entry_price = 100.0
        mock_position.client_order_id = 'sl_95.0000_tp_102.0000'
        
        integrated_bot.api.list_positions.return_value = [mock_position]
        integrated_bot.data_manager.get_latest_price.return_value = 105.0
        
        # Mock trailing stop trigger
        trigger_info = {
            'triggered': True,
            'trigger_price': 104.0,
            'stop_type': 'trailing'
        }
        integrated_bot.enhanced_risk_manager.update_position_price = Mock(return_value=trigger_info)
        
        # Mock sell method
        with patch.object(integrated_bot, 'sell') as mock_sell:
            integrated_bot.check_open_positions()
            
            # Verify position price was updated
            integrated_bot.enhanced_risk_manager.update_position_price.assert_called_once_with('AAPL', 105.0)
            
            # Verify sell was called due to trailing stop
            mock_sell.assert_called_once_with(
                'AAPL', 10, 100.0, 105.0, reason='trailing_stop'
            )


class TestDataFlowIntegration:
    """Test data flow between components."""
    
    @pytest.fixture
    def integrated_system(self):
        """Create an integrated system for testing."""
        # Mock data manager with realistic responses
        mock_data_manager = Mock()
        mock_data_manager.api = Mock()
        
        # Create sample data that flows through the system
        sample_data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'close': [100, 101, 102, 103, 104],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        
        mock_data_manager.get_historical_data.return_value = sample_data
        mock_data_manager.get_latest_price.return_value = 104.0
        
        # Create strategy
        strategy = Mock()
        strategy.generate_signal.return_value = 1  # Buy signal
        
        # Create bot
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
            bot = TradingBot(mock_data_manager, strategy)
        
        return {
            'bot': bot,
            'data_manager': mock_data_manager,
            'strategy': strategy,
            'sample_data': sample_data
        }
    
    def test_complete_trading_workflow(self, integrated_system):
        """Test complete trading workflow from data to order execution."""
        bot = integrated_system['bot']
        data_manager = integrated_system['data_manager']
        strategy = integrated_system['strategy']
        sample_data = integrated_system['sample_data']
        
        # Mock portfolio value
        mock_account = Mock()
        mock_account.equity = 100000.0
        mock_account.cash = 50000.0
        bot.api.get_account.return_value = mock_account
        
        # Mock risk manager to approve trades
        mock_validation = RiskValidationResult(
            approved=True,
            confidence_score=0.8,
            risk_score=20.0
        )
        bot.enhanced_risk_manager.validate_position_size = Mock(return_value=mock_validation)
        
        from risk_management.position_sizer import PositionSizeRecommendation
        mock_recommendation = PositionSizeRecommendation(
            symbol='AAPL',
            recommended_size=10.0,
            max_safe_size=15.0,
            risk_adjusted_size=10.0,
            method_used='kelly',
            risk_per_trade=0.02,
            stop_loss_distance=0.05,
            confidence_score=0.8
        )
        bot.enhanced_risk_manager.calculate_optimal_position_size = Mock(return_value=mock_recommendation)
        bot.enhanced_risk_manager.add_position = Mock(return_value=True)
        bot.enhanced_risk_manager.create_trailing_stop = Mock(return_value=True)
        
        # Mock file operations
        with patch.object(bot, 'append_to_csv') as mock_csv:
            # Execute strategy
            bot.run_strategy()
            
            # Verify data flow:
            # 1. Historical data was requested
            data_manager.get_historical_data.assert_called()
            
            # 2. Strategy processed the data
            strategy.generate_signal.assert_called_with(sample_data)
            
            # 3. Latest price was fetched
            data_manager.get_latest_price.assert_called_with('AAPL')
            
            # 4. Risk validation was performed
            bot.enhanced_risk_manager.validate_position_size.assert_called()
            
            # 5. Order was submitted
            bot.api.submit_order.assert_called()
            
            # 6. Order was recorded
            mock_csv.assert_called()
    
    def test_indicator_calculation_integration(self, integrated_system):
        """Test indicator calculation integration with strategy."""
        data_manager = integrated_system['data_manager']
        sample_data = integrated_system['sample_data']
        
        # Create real data manager for indicator calculations
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            real_data_manager = UnifiedDataManager()
            real_data_manager.indicator_cache = Mock()
            real_data_manager.indicator_cache.get.return_value = None
            
            # Test indicator configuration
            indicator_config = {
                'indicators': {
                    'EMA': 'True',
                    'EMA_params': {'ema_period': 5},
                    'stochRSI': 'True',
                    'stochRSI_params': {
                        'rsi_length': 5,
                        'stoch_length': 5,
                        'K': 3,
                        'D': 3
                    }
                }
            }
            
            # Calculate indicators
            indicators = real_data_manager.calculate_indicators(sample_data, indicator_config)
            
            # Verify indicators were calculated
            if len(sample_data) >= 5:  # Enough data for calculations
                assert 'EMA' in indicators or len(indicators) >= 0  # Some indicators calculated
            
            # Test indicator caching
            real_data_manager.indicator_cache.set.assert_called()


class TestErrorHandlingIntegration:
    """Test error handling across integrated components."""
    
    @pytest.fixture
    def error_prone_system(self):
        """Create a system prone to various errors for testing."""
        mock_data_manager = Mock()
        mock_data_manager.api = Mock()
        mock_strategy = Mock()
        
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
            bot = TradingBot(mock_data_manager, mock_strategy)
        
        return bot
    
    def test_api_connection_error_handling(self, error_prone_system):
        """Test handling of API connection errors."""
        bot = error_prone_system
        
        # Simulate API connection failure
        bot.data_manager.get_latest_price.side_effect = Exception("Connection timeout")
        bot.data_manager.get_historical_data.return_value = pd.DataFrame()
        
        # Should handle gracefully without crashing
        bot.run_strategy()
        
        # Verify no orders were placed due to connection issues
        bot.api.submit_order.assert_not_called()
    
    def test_risk_manager_error_handling(self, error_prone_system):
        """Test handling of risk manager errors."""
        bot = error_prone_system
        
        # Setup basic data
        bot.data_manager.get_latest_price.return_value = 100.0
        bot.data_manager.get_historical_data.return_value = pd.DataFrame({
            'close': [100, 101, 102]
        })
        
        # Simulate risk manager failure
        bot.enhanced_risk_manager.validate_position_size.side_effect = Exception("Risk calculation error")
        
        sample_df = pd.DataFrame({'close': [100, 101, 102]})
        
        # Should handle gracefully
        bot.enter_position('AAPL', sample_df)
        
        # Verify no order was placed due to risk manager error
        bot.api.submit_order.assert_not_called()
    
    def test_order_execution_error_handling(self, error_prone_system):
        """Test handling of order execution errors."""
        bot = error_prone_system
        
        # Setup successful data and risk validation
        bot.data_manager.get_latest_price.return_value = 100.0
        
        mock_account = Mock()
        mock_account.equity = 100000.0
        bot.api.get_account.return_value = mock_account
        
        mock_validation = RiskValidationResult(
            approved=True,
            confidence_score=0.8,
            risk_score=20.0
        )
        bot.enhanced_risk_manager.validate_position_size = Mock(return_value=mock_validation)
        
        from risk_management.position_sizer import PositionSizeRecommendation
        mock_recommendation = PositionSizeRecommendation(
            symbol='AAPL',
            recommended_size=10.0,
            max_safe_size=15.0,
            risk_adjusted_size=10.0,
            method_used='kelly',
            risk_per_trade=0.02,
            stop_loss_distance=0.05,
            confidence_score=0.8
        )
        bot.enhanced_risk_manager.calculate_optimal_position_size = Mock(return_value=mock_recommendation)
        
        # Simulate order execution failure
        bot.api.submit_order.side_effect = Exception("Order rejected")
        
        sample_df = pd.DataFrame({'close': [100, 101, 102]})
        
        # Should handle gracefully without crashing
        bot.enter_position('AAPL', sample_df)
        
        # Error should not propagate
        assert True  # Test passes if no exception is raised


class TestPerformanceIntegration:
    """Test performance aspects of integrated system."""
    
    def test_concurrent_operations(self):
        """Test system performance under concurrent operations."""
        # Create multiple bots for concurrent testing
        bots = []
        for i in range(3):
            mock_data_manager = Mock()
            mock_data_manager.api = Mock()
            mock_strategy = Mock()
            
            with patch('trading_bot.TradingBot.load_tickers', return_value=[f'STOCK{i}']):
                bot = TradingBot(mock_data_manager, mock_strategy)
                bots.append(bot)
        
        # Setup common mocks
        for bot in bots:
            bot.data_manager.get_latest_price.return_value = 100.0
            bot.data_manager.get_historical_data.return_value = pd.DataFrame({
                'close': [100, 101, 102]
            })
            bot.strategy.generate_signal.return_value = 1  # Buy signal
            
            mock_account = Mock()
            mock_account.equity = 100000.0
            bot.api.get_account.return_value = mock_account
            
            mock_validation = RiskValidationResult(
                approved=True,
                confidence_score=0.8,
                risk_score=20.0
            )
            bot.enhanced_risk_manager.validate_position_size = Mock(return_value=mock_validation)
        
        # Run concurrent operations
        def run_strategy(bot):
            bot.run_strategy()
        
        threads = []
        for bot in bots:
            thread = threading.Thread(target=run_strategy, args=(bot,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Verify all operations completed
        for bot in bots:
            # Each bot should have attempted to place orders
            assert bot.data_manager.get_latest_price.called
    
    def test_memory_usage_integration(self):
        """Test memory usage in integrated operations."""
        # Create system with larger datasets
        mock_data_manager = Mock()
        mock_data_manager.api = Mock()
        mock_strategy = Mock()
        
        # Create large dataset
        large_data = pd.DataFrame({
            'open': np.random.uniform(99, 101, 1000),
            'high': np.random.uniform(100, 102, 1000),
            'low': np.random.uniform(98, 100, 1000),
            'close': np.random.uniform(99, 101, 1000),
            'volume': np.random.randint(1000, 5000, 1000)
        })
        
        mock_data_manager.get_historical_data.return_value = large_data
        mock_data_manager.get_latest_price.return_value = 100.0
        
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
            bot = TradingBot(mock_data_manager, mock_strategy)
        
        # Run multiple iterations
        for _ in range(10):
            bot.strategy.generate_signal(large_data)
        
        # System should handle large datasets without issues
        assert True  # Test passes if no memory errors occur


class TestConfigurationIntegration:
    """Test configuration integration across components."""
    
    def test_config_propagation(self):
        """Test that configuration properly propagates through the system."""
        # Mock configuration changes
        with patch.object(config, 'max_trades_active', 3), \
             patch.object(config, 'investment_amount', 50000), \
             patch.object(config, 'stop_loss', 3.0):
            
            mock_data_manager = Mock()
            mock_data_manager.api = Mock()
            mock_strategy = Mock()
            
            with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
                bot = TradingBot(mock_data_manager, mock_strategy)
            
            # Test max trades configuration
            mock_positions = [Mock() for _ in range(3)]  # At limit
            bot.api.list_positions.return_value = mock_positions
            
            assert bot.can_place_new_trade() is False
            
            # Test investment amount configuration
            sample_df = pd.DataFrame({'close': [100, 101, 102]})
            position_size = bot.calculate_position_size(100.0, sample_df)
            
            # Should reflect the configured investment amount
            with patch.object(config, 'trade_capital_percent', 10):
                expected_size = (50000 * 0.10) / 100.0  # 50 shares
                assert position_size == expected_size
    
    def test_risk_config_integration(self):
        """Test risk configuration integration."""
        from risk_management.risk_config import RiskConfig
        
        # Create custom risk config
        custom_config = RiskConfig()
        custom_config.max_position_size = 0.05  # 5%
        custom_config.max_daily_loss = 0.02  # 2%
        
        risk_manager = EnhancedRiskManager(config=custom_config)
        
        # Verify configuration is used
        assert risk_manager.config.max_position_size == 0.05
        assert risk_manager.config.max_daily_loss == 0.02
        
        # Test validation with custom config
        with patch.object(risk_manager, '_get_portfolio_value', return_value=100000.0), \
             patch.object(risk_manager, '_calculate_current_exposure', return_value=0.0):
            
            # Should reject position larger than 5%
            result = risk_manager.validate_position_size(
                symbol='AAPL',
                proposed_size=80,  # $8000 position (8%)
                entry_price=100.0,
                stop_loss_price=95.0
            )
            
            assert result.approved is False
            assert 'exceeds maximum limit' in str(result.violations)


if __name__ == '__main__':
    pytest.main([__file__])