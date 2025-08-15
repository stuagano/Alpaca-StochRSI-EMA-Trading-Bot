"""
Comprehensive unit tests for the TradingBot class.
Tests cover initialization, position management, order execution, risk calculations, and more.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import os
import tempfile
import csv

from trading_bot import TradingBot
from risk_management.enhanced_risk_manager import RiskValidationResult, PositionSizeRecommendation
from config_params import config


class TestTradingBotInitialization:
    """Test trading bot initialization and setup."""
    
    @pytest.fixture
    def mock_data_manager(self):
        """Create a mock data manager."""
        manager = Mock()
        manager.api = Mock()
        manager.get_latest_price.return_value = 100.0
        manager.get_historical_data.return_value = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        })
        return manager
    
    @pytest.fixture
    def mock_strategy(self):
        """Create a mock strategy."""
        strategy = Mock()
        strategy.generate_signal.return_value = 1  # Buy signal
        return strategy
    
    @pytest.fixture
    def mock_tickers_file(self):
        """Create a temporary tickers file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("AAPL\nMSFT\nGOOGL\n")
            temp_path = f.name
        
        # Mock the AUTH/Tickers.txt path
        original_path = 'AUTH/Tickers.txt'
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "AAPL MSFT GOOGL"
            yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
    
    def test_trading_bot_initialization(self, mock_data_manager, mock_strategy):
        """Test basic trading bot initialization."""
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL', 'MSFT']):
            bot = TradingBot(mock_data_manager, mock_strategy)
            
            assert bot.data_manager == mock_data_manager
            assert bot.strategy == mock_strategy
            assert bot.api == mock_data_manager.api
            assert bot.tickers == ['AAPL', 'MSFT']
            assert bot.orders_file == 'ORDERS/Orders.csv'
            assert bot.time_and_coins_file == 'ORDERS/Time and Coins.csv'
            assert bot.enable_enhanced_risk_management is True
    
    def test_load_tickers_success(self, mock_data_manager, mock_strategy):
        """Test successful ticker loading."""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "AAPL MSFT GOOGL"
            
            bot = TradingBot(mock_data_manager, mock_strategy)
            tickers = bot.load_tickers()
            
            assert tickers == ['AAPL', 'MSFT', 'GOOGL']
    
    def test_load_tickers_file_not_found(self, mock_data_manager, mock_strategy):
        """Test ticker loading when file doesn't exist."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            bot = TradingBot(mock_data_manager, mock_strategy)
            tickers = bot.load_tickers()
            
            assert tickers == []
    
    def test_load_tickers_permission_error(self, mock_data_manager, mock_strategy):
        """Test ticker loading with permission error."""
        with patch('builtins.open', side_effect=PermissionError):
            bot = TradingBot(mock_data_manager, mock_strategy)
            tickers = bot.load_tickers()
            
            assert tickers == []


class TestMarketOperations:
    """Test market-related operations."""
    
    @pytest.fixture
    def bot(self):
        """Create a trading bot instance for testing."""
        mock_data_manager = Mock()
        mock_strategy = Mock()
        
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
            bot = TradingBot(mock_data_manager, mock_strategy)
            return bot
    
    def test_is_market_open_true(self, bot):
        """Test market open check when market is open."""
        mock_clock = Mock()
        mock_clock.is_open = True
        bot.api.get_clock.return_value = mock_clock
        
        assert bot.is_market_open() is True
    
    def test_is_market_open_false(self, bot):
        """Test market open check when market is closed."""
        mock_clock = Mock()
        mock_clock.is_open = False
        bot.api.get_clock.return_value = mock_clock
        
        assert bot.is_market_open() is False
    
    def test_can_place_new_trade_under_limit(self, bot):
        """Test trade placement when under position limit."""
        bot.api.list_positions.return_value = [Mock(), Mock()]  # 2 positions
        
        with patch.object(config, 'max_trades_active', 5):
            assert bot.can_place_new_trade() is True
    
    def test_can_place_new_trade_at_limit(self, bot):
        """Test trade placement when at position limit."""
        bot.api.list_positions.return_value = [Mock() for _ in range(5)]  # 5 positions
        
        with patch.object(config, 'max_trades_active', 5):
            assert bot.can_place_new_trade() is False


class TestPositionSizing:
    """Test position sizing calculations."""
    
    @pytest.fixture
    def bot(self):
        """Create a trading bot instance for testing."""
        mock_data_manager = Mock()
        mock_strategy = Mock()
        
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
            bot = TradingBot(mock_data_manager, mock_strategy)
            return bot
    
    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame for testing."""
        return pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'close': [100, 101, 102, 103, 104],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
    
    def test_calculate_position_size_basic(self, bot, sample_df):
        """Test basic position size calculation."""
        price = 100.0
        
        with patch.object(config, 'investment_amount', 10000), \
             patch.object(config, 'trade_capital_percent', 10):
            
            size = bot.calculate_position_size(price, sample_df)
            expected_size = (10000 * 0.10) / 100.0  # 10 shares
            
            assert size == expected_size
    
    def test_calculate_position_size_with_atr(self, bot, sample_df):
        """Test position size calculation with ATR."""
        price = 100.0
        bot.risk_management_params = {
            'use_atr_position_sizing': True,
            'atr_period': 14
        }
        
        # Mock ATR calculation
        with patch.object(sample_df, 'ta') as mock_ta, \
             patch.object(config, 'investment_amount', 10000), \
             patch.object(config, 'trade_capital_percent', 10):
            
            # Create a mock ATR column
            sample_df['ATRr_14'] = [2.0, 2.1, 2.2, 2.3, 2.4]
            
            size = bot.calculate_position_size(price, sample_df)
            
            # With ATR, size should be risk_amount / atr_value
            risk_amount = 10000 * 0.10
            atr_value = 2.4  # Last ATR value
            expected_size = risk_amount / atr_value
            
            assert size == expected_size
    
    def test_calculate_stop_loss_percentage(self, bot, sample_df):
        """Test percentage-based stop loss calculation."""
        price = 100.0
        bot.risk_management_params = {'use_atr_stop_loss': False}
        
        with patch.object(config, 'stop_loss', 5.0):  # 5% stop loss
            stop_price = bot.calculate_stop_loss(price, sample_df)
            expected_stop = 100.0 * (1 - 0.05)  # 95.0
            
            assert stop_price == expected_stop
    
    def test_calculate_stop_loss_with_atr(self, bot, sample_df):
        """Test ATR-based stop loss calculation."""
        price = 100.0
        bot.risk_management_params = {
            'use_atr_stop_loss': True,
            'atr_period': 14,
            'atr_multiplier': 2.0
        }
        
        # Mock ATR calculation
        sample_df['ATRr_14'] = [2.0, 2.1, 2.2, 2.3, 2.4]
        
        stop_price = bot.calculate_stop_loss(price, sample_df)
        expected_stop = 100.0 - (2.4 * 2.0)  # 95.2
        
        assert stop_price == expected_stop


class TestOrderManagement:
    """Test order placement and management."""
    
    @pytest.fixture
    def bot(self):
        """Create a trading bot instance for testing."""
        mock_data_manager = Mock()
        mock_strategy = Mock()
        
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
            bot = TradingBot(mock_data_manager, mock_strategy)
            bot.enhanced_risk_manager = Mock()
            return bot
    
    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame for testing."""
        return pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        })
    
    @patch('trading_bot.TradingBot.record_order')
    @patch('trading_bot.TradingBot._get_portfolio_value')
    def test_enter_position_success(self, mock_portfolio_value, mock_record_order, bot, sample_df):
        """Test successful position entry."""
        mock_portfolio_value.return_value = 100000.0
        bot.data_manager.get_latest_price.return_value = 100.0
        
        # Mock enhanced risk manager
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
        bot.enhanced_risk_manager.calculate_optimal_position_size.return_value = mock_recommendation
        
        mock_validation = RiskValidationResult(
            approved=True,
            confidence_score=0.8,
            risk_score=20.0
        )
        bot.enhanced_risk_manager.validate_position_size.return_value = mock_validation
        
        with patch.object(config, 'extended_hours', False), \
             patch.object(config, 'limit_price', 1.0):
            
            bot.enter_position('AAPL', sample_df)
            
            # Verify API call
            bot.api.submit_order.assert_called_once()
            call_args = bot.api.submit_order.call_args
            
            assert call_args[1]['symbol'] == 'AAPL'
            assert call_args[1]['side'] == 'buy'
            assert call_args[1]['type'] == 'market'
            assert call_args[1]['time_in_force'] == 'day'
            
            # Verify order recording
            mock_record_order.assert_called_once_with('AAPL', 100.0, 10.0)
    
    def test_enter_position_no_price(self, bot, sample_df):
        """Test position entry when price is unavailable."""
        bot.data_manager.get_latest_price.return_value = None
        
        bot.enter_position('AAPL', sample_df)
        
        # Should not place order
        bot.api.submit_order.assert_not_called()
    
    def test_enter_position_risk_rejected(self, bot, sample_df):
        """Test position entry when risk validation rejects."""
        bot.data_manager.get_latest_price.return_value = 100.0
        
        mock_validation = RiskValidationResult(
            approved=False,
            confidence_score=0.2,
            risk_score=80.0,
            violations=['Position size too large']
        )
        bot.enhanced_risk_manager.validate_position_size.return_value = mock_validation
        
        bot.enter_position('AAPL', sample_df)
        
        # Should not place order
        bot.api.submit_order.assert_not_called()
    
    @patch('trading_bot.TradingBot.record_sell')
    def test_sell_position_success(self, mock_record_sell, bot):
        """Test successful position sale."""
        bot.data_manager.get_latest_price.return_value = 105.0
        
        bot.sell('AAPL', 10, 100.0, 106.0, 'target_price')
        
        # Verify API call
        bot.api.submit_order.assert_called_once_with('AAPL', 10, 'sell', 'market', 'day')
        
        # Verify sell recording
        mock_record_sell.assert_called_once_with('AAPL', 10, 100.0, 105.0, 106.0)
    
    def test_sell_position_no_price(self, bot):
        """Test position sale when price is unavailable."""
        bot.data_manager.get_latest_price.return_value = None
        
        bot.sell('AAPL', 10, 100.0, 106.0, 'manual')
        
        # Should not place sell order
        bot.api.submit_order.assert_not_called()


class TestOrderRecording:
    """Test order recording functionality."""
    
    @pytest.fixture
    def bot(self):
        """Create a trading bot instance for testing."""
        mock_data_manager = Mock()
        mock_strategy = Mock()
        
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
            bot = TradingBot(mock_data_manager, mock_strategy)
            return bot
    
    @patch('trading_bot.TradingBot.append_to_csv')
    def test_record_order(self, mock_append_csv, bot):
        """Test order recording."""
        mock_account = Mock()
        mock_account.cash = 50000.0
        bot.api.get_account.return_value = mock_account
        
        with patch.object(config, 'stop_loss', 5.0), \
             patch.object(config, 'limit_price', 2.0), \
             patch.object(config, 'activate_trailing_stop_loss_at', 1.0):
            
            bot.record_order('AAPL', 100.0, 10)
            
            # Verify CSV append calls
            assert mock_append_csv.call_count == 2  # Orders file and time/coins file
            
            # Check order data structure
            orders_call = mock_append_csv.call_args_list[0]
            order_data = orders_call[0][1]  # Second argument (data)
            
            assert order_data['Ticker'] == 'AAPL'
            assert order_data['Type'] == 'buy'
            assert order_data['Buy Price'] == 100.0
            assert order_data['Quantity'] == 10
            assert order_data['Total'] == 1000.0
            assert order_data['Target Price'] == 102.0  # 100 * 1.02
            assert order_data['Stop Loss Price'] == 95.0  # 100 * 0.95
    
    @patch('trading_bot.TradingBot.append_to_csv')
    def test_record_sell(self, mock_append_csv, bot):
        """Test sell order recording."""
        mock_account = Mock()
        mock_account.cash = 51000.0
        bot.api.get_account.return_value = mock_account
        
        bot.record_sell('AAPL', 10, 100.0, 105.0, 106.0)
        
        # Verify CSV append call
        mock_append_csv.assert_called_once()
        
        # Check sell data structure
        sell_data = mock_append_csv.call_args[0][1]  # Second argument (data)
        
        assert sell_data['Ticker'] == 'AAPL'
        assert sell_data['Type'] == 'sell'
        assert sell_data['Buy Price'] == 100.0
        assert sell_data['Sell Price'] == 105.0
        assert sell_data['Highest Price'] == 106.0
        assert sell_data['Quantity'] == 10
        assert sell_data['Total'] == 1050.0
    
    def test_append_to_csv_new_file(self, bot):
        """Test CSV append to new file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_path = temp_file.name
        
        try:
            os.unlink(temp_path)  # Remove the file to test creation
        except FileNotFoundError:
            pass
        
        test_data = {'col1': 'value1', 'col2': 'value2'}
        bot.append_to_csv(temp_path, test_data)
        
        # Verify file was created and contains header
        with open(temp_path, 'r') as f:
            content = f.read()
            assert 'col1,col2' in content
            assert 'value1,value2' in content
        
        # Cleanup
        os.unlink(temp_path)
    
    def test_append_to_csv_existing_file(self, bot):
        """Test CSV append to existing file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
            temp_file.write('col1,col2\nexisting1,existing2\n')
            temp_path = temp_file.name
        
        test_data = {'col1': 'value1', 'col2': 'value2'}
        bot.append_to_csv(temp_path, test_data)
        
        # Verify file contains both old and new data
        with open(temp_path, 'r') as f:
            content = f.read()
            assert 'existing1,existing2' in content
            assert 'value1,value2' in content
            # Header should only appear once
            assert content.count('col1,col2') == 1
        
        # Cleanup
        os.unlink(temp_path)


class TestPositionMonitoring:
    """Test position monitoring and exit logic."""
    
    @pytest.fixture
    def bot(self):
        """Create a trading bot instance for testing."""
        mock_data_manager = Mock()
        mock_strategy = Mock()
        
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
            bot = TradingBot(mock_data_manager, mock_strategy)
            bot.enhanced_risk_manager = Mock()
            return bot
    
    @patch('trading_bot.TradingBot.sell')
    def test_check_open_positions_trailing_stop(self, mock_sell, bot):
        """Test position checking with trailing stop trigger."""
        # Mock position
        mock_position = Mock()
        mock_position.symbol = 'AAPL'
        mock_position.qty = 10
        mock_position.avg_entry_price = 100.0
        mock_position.client_order_id = 'sl_95.0000_tp_102.0000'
        
        bot.api.list_positions.return_value = [mock_position]
        bot.data_manager.get_latest_price.return_value = 105.0
        
        # Mock trailing stop trigger
        trigger_info = {
            'triggered': True,
            'trigger_price': 104.0,
            'stop_type': 'trailing'
        }
        bot.enhanced_risk_manager.update_position_price.return_value = trigger_info
        
        bot.check_open_positions()
        
        # Verify sell was called due to trailing stop
        mock_sell.assert_called_once_with(
            'AAPL', 10, 100.0, 105.0, reason='trailing_stop'
        )
    
    @patch('trading_bot.TradingBot.sell')
    def test_check_open_positions_stop_loss(self, mock_sell, bot):
        """Test position checking with stop loss trigger."""
        # Mock position
        mock_position = Mock()
        mock_position.symbol = 'AAPL'
        mock_position.qty = 10
        mock_position.avg_entry_price = 100.0
        mock_position.client_order_id = 'sl_95.0000_tp_102.0000'
        
        # Mock order lookup
        mock_order = Mock()
        mock_order.client_order_id = 'sl_95.0000_tp_102.0000'
        
        bot.api.list_positions.return_value = [mock_position]
        bot.api.get_order_by_client_order_id.return_value = mock_order
        bot.data_manager.get_latest_price.return_value = 94.0  # Below stop loss
        bot.enhanced_risk_manager.update_position_price.return_value = None
        
        bot.check_open_positions()
        
        # Verify sell was called due to stop loss
        mock_sell.assert_called_once_with(
            'AAPL', 10, 100.0, 94.0, reason='stop_loss'
        )
    
    @patch('trading_bot.TradingBot.sell')
    def test_check_open_positions_target_price(self, mock_sell, bot):
        """Test position checking with target price trigger."""
        # Mock position
        mock_position = Mock()
        mock_position.symbol = 'AAPL'
        mock_position.qty = 10
        mock_position.avg_entry_price = 100.0
        mock_position.client_order_id = 'sl_95.0000_tp_102.0000'
        
        # Mock order lookup
        mock_order = Mock()
        mock_order.client_order_id = 'sl_95.0000_tp_102.0000'
        
        bot.api.list_positions.return_value = [mock_position]
        bot.api.get_order_by_client_order_id.return_value = mock_order
        bot.data_manager.get_latest_price.return_value = 103.0  # Above target
        bot.enhanced_risk_manager.update_position_price.return_value = None
        
        bot.check_open_positions()
        
        # Verify sell was called due to target price
        mock_sell.assert_called_once_with(
            'AAPL', 10, 100.0, 103.0, reason='target_price'
        )


class TestRiskManagementIntegration:
    """Test integration with risk management system."""
    
    @pytest.fixture
    def bot(self):
        """Create a trading bot instance for testing."""
        mock_data_manager = Mock()
        mock_strategy = Mock()
        
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
            bot = TradingBot(mock_data_manager, mock_strategy)
            return bot
    
    def test_get_portfolio_value_success(self, bot):
        """Test portfolio value retrieval."""
        mock_account = Mock()
        mock_account.equity = 100000.0
        bot.api.get_account.return_value = mock_account
        
        value = bot._get_portfolio_value()
        assert value == 100000.0
    
    def test_get_portfolio_value_error(self, bot):
        """Test portfolio value retrieval with error."""
        bot.api.get_account.side_effect = Exception("API Error")
        
        value = bot._get_portfolio_value()
        assert value == 100000.0  # Default fallback
    
    def test_toggle_enhanced_risk_management(self, bot):
        """Test toggling enhanced risk management."""
        # Enable
        result = bot.toggle_enhanced_risk_management(True)
        assert result is True
        assert bot.enable_enhanced_risk_management is True
        
        # Disable
        result = bot.toggle_enhanced_risk_management(False)
        assert result is True
        assert bot.enable_enhanced_risk_management is False
    
    def test_validate_proposed_trade_enabled(self, bot):
        """Test trade validation with enhanced risk management enabled."""
        bot.enable_enhanced_risk_management = True
        bot.enhanced_risk_manager = Mock()
        
        mock_validation = RiskValidationResult(
            approved=True,
            confidence_score=0.8,
            risk_score=20.0
        )
        bot.enhanced_risk_manager.validate_position_size.return_value = mock_validation
        bot.data_manager.get_historical_data.return_value = pd.DataFrame({
            'close': [100, 101, 102]
        })
        
        result = bot.validate_proposed_trade('AAPL', 10.0, 100.0)
        
        assert result.approved is True
        assert result.confidence_score == 0.8
        assert result.risk_score == 20.0
    
    def test_validate_proposed_trade_disabled(self, bot):
        """Test trade validation with enhanced risk management disabled."""
        bot.enable_enhanced_risk_management = False
        
        result = bot.validate_proposed_trade('AAPL', 10.0, 100.0)
        
        assert result.approved is True
        assert result.confidence_score == 1.0
        assert result.risk_score == 0.0
        assert 'Enhanced risk management disabled' in result.recommendations


class TestStrategyExecution:
    """Test strategy execution and signal handling."""
    
    @pytest.fixture
    def bot(self):
        """Create a trading bot instance for testing."""
        mock_data_manager = Mock()
        mock_strategy = Mock()
        
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL', 'MSFT']):
            bot = TradingBot(mock_data_manager, mock_strategy)
            return bot
    
    @patch('trading_bot.TradingBot.enter_position')
    @patch('trading_bot.TradingBot.can_place_new_trade')
    def test_run_strategy_with_signals(self, mock_can_trade, mock_enter_position, bot):
        """Test strategy execution with buy signals."""
        mock_can_trade.return_value = True
        bot.strategy.generate_signal.return_value = 1  # Buy signal
        
        # Mock historical data
        sample_df = pd.DataFrame({
            'open': [100, 101],
            'high': [101, 102],
            'low': [99, 100],
            'close': [100, 101],
            'volume': [1000, 1100]
        })
        bot.data_manager.get_historical_data.return_value = sample_df
        
        bot.run_strategy()
        
        # Should attempt to enter positions for both tickers
        assert mock_enter_position.call_count == 2
        mock_enter_position.assert_any_call('AAPL', sample_df)
        mock_enter_position.assert_any_call('MSFT', sample_df)
    
    @patch('trading_bot.TradingBot.enter_position')
    @patch('trading_bot.TradingBot.can_place_new_trade')
    def test_run_strategy_no_signals(self, mock_can_trade, mock_enter_position, bot):
        """Test strategy execution with no signals."""
        mock_can_trade.return_value = True
        bot.strategy.generate_signal.return_value = 0  # No signal
        
        # Mock historical data
        sample_df = pd.DataFrame({
            'open': [100, 101],
            'high': [101, 102],
            'low': [99, 100],
            'close': [100, 101],
            'volume': [1000, 1100]
        })
        bot.data_manager.get_historical_data.return_value = sample_df
        
        bot.run_strategy()
        
        # Should not enter any positions
        mock_enter_position.assert_not_called()
    
    @patch('trading_bot.TradingBot.enter_position')
    @patch('trading_bot.TradingBot.can_place_new_trade')
    def test_run_strategy_max_trades_reached(self, mock_can_trade, mock_enter_position, bot):
        """Test strategy execution when max trades reached."""
        mock_can_trade.return_value = False
        
        bot.run_strategy()
        
        # Should not attempt to enter any positions
        mock_enter_position.assert_not_called()
        bot.data_manager.get_historical_data.assert_not_called()


class TestErrorHandling:
    """Test error handling in various scenarios."""
    
    @pytest.fixture
    def bot(self):
        """Create a trading bot instance for testing."""
        mock_data_manager = Mock()
        mock_strategy = Mock()
        
        with patch('trading_bot.TradingBot.load_tickers', return_value=['AAPL']):
            bot = TradingBot(mock_data_manager, mock_strategy)
            return bot
    
    def test_enter_position_api_error(self, bot):
        """Test position entry with API error."""
        bot.data_manager.get_latest_price.return_value = 100.0
        bot.api.submit_order.side_effect = Exception("API Error")
        bot.enhanced_risk_manager = Mock()
        
        # Mock risk validation to pass
        mock_validation = RiskValidationResult(approved=True, confidence_score=0.8, risk_score=20.0)
        bot.enhanced_risk_manager.validate_position_size.return_value = mock_validation
        
        sample_df = pd.DataFrame({'close': [100, 101, 102]})
        
        # Should not raise exception
        bot.enter_position('AAPL', sample_df)
    
    def test_sell_position_api_error(self, bot):
        """Test position sale with API error."""
        bot.data_manager.get_latest_price.return_value = 105.0
        bot.api.submit_order.side_effect = Exception("API Error")
        
        # Should not raise exception
        bot.sell('AAPL', 10, 100.0, 106.0, 'manual')
    
    def test_check_positions_parse_error(self, bot):
        """Test position checking with order ID parse error."""
        # Mock position with invalid client_order_id
        mock_position = Mock()
        mock_position.symbol = 'AAPL'
        mock_position.qty = 10
        mock_position.avg_entry_price = 100.0
        mock_position.client_order_id = 'invalid_format'
        
        bot.api.list_positions.return_value = [mock_position]
        bot.api.get_order_by_client_order_id.side_effect = Exception("Parse error")
        bot.data_manager.get_latest_price.return_value = 105.0
        bot.enhanced_risk_manager = Mock()
        bot.enhanced_risk_manager.update_position_price.return_value = None
        
        # Should not raise exception
        bot.check_open_positions()


if __name__ == '__main__':
    pytest.main([__file__])