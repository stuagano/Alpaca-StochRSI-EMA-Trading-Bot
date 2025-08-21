"""
Comprehensive unit tests for TradingBot core functionality.
Tests trading operations, risk management, and position management.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import tempfile
import os

from trading_bot import TradingBot
from tests.mocks.alpaca_api_mock import MockAlpacaAPI, create_mock_alpaca_api


class TestTradingBotInitialization:
    """Test TradingBot initialization and setup."""
    
    def test_bot_initialization(self, mock_data_manager, stoch_rsi_strategy):
        """Test basic bot initialization."""
        bot = TradingBot(mock_data_manager, stoch_rsi_strategy)
        
        assert bot.data_manager == mock_data_manager
        assert bot.strategy == stoch_rsi_strategy
        assert bot.api == mock_data_manager.api
        assert hasattr(bot, 'tickers')
        assert hasattr(bot, 'enhanced_risk_manager')
    
    def test_bot_initialization_with_tickers_file(self, mock_data_manager, stoch_rsi_strategy, temp_directory):
        """Test bot initialization with custom tickers file."""
        # Create temporary tickers file
        auth_dir = os.path.join(temp_directory, "AUTH")
        os.makedirs(auth_dir, exist_ok=True)
        tickers_file = os.path.join(auth_dir, "Tickers.txt")
        
        with open(tickers_file, "w") as f:
            f.write("AAPL TSLA GOOGL MSFT")
        
        # Change working directory temporarily
        original_cwd = os.getcwd()
        os.chdir(temp_directory)
        
        try:
            bot = TradingBot(mock_data_manager, stoch_rsi_strategy)
            assert bot.tickers == ["AAPL", "TSLA", "GOOGL", "MSFT"]
        finally:
            os.chdir(original_cwd)
    
    def test_bot_initialization_missing_tickers_file(self, mock_data_manager, stoch_rsi_strategy, temp_directory):
        """Test bot initialization when tickers file is missing."""
        original_cwd = os.getcwd()
        os.chdir(temp_directory)
        
        try:
            bot = TradingBot(mock_data_manager, stoch_rsi_strategy)
            assert bot.tickers == []
        finally:
            os.chdir(original_cwd)
    
    def test_risk_management_initialization(self, mock_data_manager, stoch_rsi_strategy):
        """Test risk management components initialization."""
        bot = TradingBot(mock_data_manager, stoch_rsi_strategy)
        
        assert hasattr(bot, 'enhanced_risk_manager')
        assert hasattr(bot, 'risk_config')
        assert hasattr(bot, 'enable_enhanced_risk_management')
        assert isinstance(bot.enable_enhanced_risk_management, bool)


class TestTradingBotMarketOperations:
    """Test market-related operations."""
    
    def test_is_market_open_true(self, trading_bot):
        """Test market open detection when market is open."""
        trading_bot.api.get_clock.return_value.is_open = True
        
        assert trading_bot.is_market_open() is True
    
    def test_is_market_open_false(self, trading_bot):
        """Test market open detection when market is closed."""
        trading_bot.api.get_clock.return_value.is_open = False
        
        assert trading_bot.is_market_open() is False
    
    def test_can_place_new_trade_within_limit(self, trading_bot):
        """Test can place trade when within position limits."""
        # Mock 2 open positions (under limit of 3)
        mock_positions = [Mock(), Mock()]
        trading_bot.api.list_positions.return_value = mock_positions
        
        assert trading_bot.can_place_new_trade() is True
    
    def test_can_place_new_trade_at_limit(self, trading_bot):
        """Test can place trade when at position limit."""
        # Mock 3 open positions (at limit)
        mock_positions = [Mock(), Mock(), Mock()]
        trading_bot.api.list_positions.return_value = mock_positions
        
        assert trading_bot.can_place_new_trade() is False
    
    def test_can_place_new_trade_over_limit(self, trading_bot):
        """Test can place trade when over position limit."""
        # Mock 5 open positions (over limit of 3)
        mock_positions = [Mock() for _ in range(5)]
        trading_bot.api.list_positions.return_value = mock_positions
        
        assert trading_bot.can_place_new_trade() is False


class TestTradingBotPositionManagement:
    """Test position entry and management."""
    
    def test_enter_position_successful(self, trading_bot):
        """Test successful position entry."""
        ticker = "AAPL"
        price = 150.0
        
        # Setup mocks
        trading_bot.data_manager.get_latest_price.return_value = price
        trading_bot.enable_enhanced_risk_management = False
        
        # Create sample DataFrame for calculations
        df = pd.DataFrame({
            'close': [148, 149, 150],
            'high': [149, 150, 151],
            'low': [147, 148, 149]
        })
        
        # Mock order submission
        mock_order = Mock()
        mock_order.id = "order_123"
        trading_bot.api.submit_order.return_value = mock_order
        
        # Execute position entry
        trading_bot.enter_position(ticker, df)
        
        # Verify order was submitted
        trading_bot.api.submit_order.assert_called_once()
        call_args = trading_bot.api.submit_order.call_args
        assert call_args[1]['symbol'] == ticker
        assert call_args[1]['side'] == "buy"
        assert call_args[1]['type'] == "market"
    
    def test_enter_position_no_price(self, trading_bot):
        """Test position entry when price is unavailable."""
        ticker = "AAPL"
        trading_bot.data_manager.get_latest_price.return_value = None
        
        df = pd.DataFrame({'close': [150]})
        
        trading_bot.enter_position(ticker, df)
        
        # Should not submit order when price is unavailable
        trading_bot.api.submit_order.assert_not_called()
    
    def test_enter_position_with_enhanced_risk_management(self, trading_bot_with_risk):
        """Test position entry with enhanced risk management."""
        ticker = "AAPL"
        price = 150.0
        
        # Setup mocks
        trading_bot_with_risk.data_manager.get_latest_price.return_value = price
        
        # Mock portfolio value
        trading_bot_with_risk.api.get_account.return_value.equity = 100000.0
        
        # Mock risk manager responses
        optimal_size_mock = Mock()
        optimal_size_mock.risk_adjusted_size = 0.05
        trading_bot_with_risk.enhanced_risk_manager.calculate_optimal_position_size.return_value = optimal_size_mock
        
        validation_result_mock = Mock()
        validation_result_mock.approved = True
        validation_result_mock.violations = []
        validation_result_mock.warnings = []
        validation_result_mock.position_size_adjustment = None
        trading_bot_with_risk.enhanced_risk_manager.validate_position_size.return_value = validation_result_mock
        
        df = pd.DataFrame({'close': [150]})
        
        # Mock order submission
        mock_order = Mock()
        trading_bot_with_risk.api.submit_order.return_value = mock_order
        
        trading_bot_with_risk.enter_position(ticker, df)
        
        # Verify risk management methods were called
        trading_bot_with_risk.enhanced_risk_manager.calculate_optimal_position_size.assert_called_once()
        trading_bot_with_risk.enhanced_risk_manager.validate_position_size.assert_called_once()
        trading_bot_with_risk.api.submit_order.assert_called_once()
    
    def test_enter_position_rejected_by_risk_manager(self, trading_bot_with_risk):
        """Test position entry rejected by risk manager."""
        ticker = "AAPL"
        price = 150.0
        
        trading_bot_with_risk.data_manager.get_latest_price.return_value = price
        trading_bot_with_risk.api.get_account.return_value.equity = 100000.0
        
        # Mock risk manager rejection
        optimal_size_mock = Mock()
        optimal_size_mock.risk_adjusted_size = 0.05
        trading_bot_with_risk.enhanced_risk_manager.calculate_optimal_position_size.return_value = optimal_size_mock
        
        validation_result_mock = Mock()
        validation_result_mock.approved = False
        validation_result_mock.violations = ["Position size too large"]
        trading_bot_with_risk.enhanced_risk_manager.validate_position_size.return_value = validation_result_mock
        
        df = pd.DataFrame({'close': [150]})
        
        trading_bot_with_risk.enter_position(ticker, df)
        
        # Should not submit order when rejected
        trading_bot_with_risk.api.submit_order.assert_not_called()
    
    def test_calculate_position_size_basic(self, trading_bot):
        """Test basic position size calculation."""
        price = 100.0
        df = pd.DataFrame({'close': [100]})
        
        # Should use basic calculation when ATR is disabled
        trading_bot.risk_management_params['use_atr_position_sizing'] = False
        
        size = trading_bot.calculate_position_size(price, df)
        
        # Expected: (10000 * 0.02) / 100 = 2.0 shares
        expected_size = 2.0
        assert abs(size - expected_size) < 0.01
    
    def test_calculate_position_size_with_atr(self, trading_bot):
        """Test position size calculation with ATR."""
        price = 100.0
        
        # Create DataFrame with ATR column
        df = pd.DataFrame({
            'close': [98, 99, 100, 101, 102],
            'ATRr_14': [0, 0, 0, 0, 2.0]  # ATR value of 2.0
        })
        
        trading_bot.risk_management_params['use_atr_position_sizing'] = True
        trading_bot.risk_management_params['atr_period'] = 14
        
        with patch.object(df, 'ta') as mock_ta:
            # Mock ta.atr to add ATR column
            mock_ta.atr.return_value = None  # Side effect handled by setting ATRr_14 column
            
            size = trading_bot.calculate_position_size(price, df)
            
            # Expected: (10000 * 0.02) / 2.0 = 100.0 shares (using ATR as risk per share)
            expected_size = 100.0
            assert abs(size - expected_size) < 0.01
    
    def test_calculate_stop_loss_basic(self, trading_bot):
        """Test basic stop loss calculation."""
        price = 100.0
        df = pd.DataFrame({'close': [100]})
        
        trading_bot.risk_management_params['use_atr_stop_loss'] = False
        
        stop_loss = trading_bot.calculate_stop_loss(price, df)
        
        # Expected: 100 * (1 - 0.05) = 95.0
        expected_stop_loss = 95.0
        assert abs(stop_loss - expected_stop_loss) < 0.01
    
    def test_calculate_stop_loss_with_atr(self, trading_bot):
        """Test stop loss calculation with ATR."""
        price = 100.0
        
        df = pd.DataFrame({
            'close': [98, 99, 100],
            'ATRr_14': [0, 0, 2.0]
        })
        
        trading_bot.risk_management_params['use_atr_stop_loss'] = True
        trading_bot.risk_management_params['atr_period'] = 14
        trading_bot.risk_management_params['atr_multiplier'] = 2.0
        
        with patch.object(df, 'ta') as mock_ta:
            mock_ta.atr.return_value = None
            
            stop_loss = trading_bot.calculate_stop_loss(price, df)
            
            # Expected: 100 - (2.0 * 2.0) = 96.0
            expected_stop_loss = 96.0
            assert abs(stop_loss - expected_stop_loss) < 0.01


class TestTradingBotSellOperations:
    """Test sell operations and position closing."""
    
    def test_sell_successful(self, trading_bot):
        """Test successful sell operation."""
        ticker = "AAPL"
        quantity = 10
        buy_price = 150.0
        highest_price = 155.0
        current_price = 152.0
        
        trading_bot.data_manager.get_latest_price.return_value = current_price
        trading_bot.enable_enhanced_risk_management = False
        
        # Mock order submission
        mock_order = Mock()
        trading_bot.api.submit_order.return_value = mock_order
        
        trading_bot.sell(ticker, quantity, buy_price, highest_price, "target_price")
        
        # Verify sell order was submitted
        trading_bot.api.submit_order.assert_called_once_with(
            ticker, quantity, "sell", "market", "day"
        )
    
    def test_sell_no_price(self, trading_bot):
        """Test sell operation when price is unavailable."""
        ticker = "AAPL"
        trading_bot.data_manager.get_latest_price.return_value = None
        
        trading_bot.sell(ticker, 10, 150.0, 155.0)
        
        # Should not submit order when price unavailable
        trading_bot.api.submit_order.assert_not_called()
    
    def test_sell_with_risk_management(self, trading_bot_with_risk):
        """Test sell operation with enhanced risk management."""
        ticker = "AAPL"
        quantity = 10
        buy_price = 150.0
        
        trading_bot_with_risk.data_manager.get_latest_price.return_value = 152.0
        
        mock_order = Mock()
        trading_bot_with_risk.api.submit_order.return_value = mock_order
        
        trading_bot_with_risk.sell(ticker, quantity, buy_price, 155.0)
        
        # Verify risk manager was called to remove position
        trading_bot_with_risk.enhanced_risk_manager.remove_position.assert_called_once_with(ticker)


class TestTradingBotPositionMonitoring:
    """Test position monitoring and management."""
    
    def test_check_open_positions_no_positions(self, trading_bot):
        """Test checking positions when none exist."""
        trading_bot.api.list_positions.return_value = []
        
        # Should not raise any errors
        trading_bot.check_open_positions()
    
    def test_check_open_positions_with_positions(self, trading_bot):
        """Test checking positions with active positions."""
        # Create mock position
        mock_position = Mock()
        mock_position.symbol = "AAPL"
        mock_position.qty = 10
        mock_position.avg_entry_price = 150.0
        mock_position.client_order_id = "order_123"
        
        trading_bot.api.list_positions.return_value = [mock_position]
        trading_bot.data_manager.get_latest_price.return_value = 152.0
        trading_bot.enable_enhanced_risk_management = False
        
        # Mock order lookup
        mock_order = Mock()
        mock_order.client_order_id = "sl_142.50_tp_165.00"
        trading_bot.api.get_order_by_client_order_id.return_value = mock_order
        
        trading_bot.check_open_positions()
        
        # Should check latest price for position
        trading_bot.data_manager.get_latest_price.assert_called_with("AAPL")
    
    def test_check_positions_trailing_stop_trigger(self, trading_bot_with_risk):
        """Test position monitoring with trailing stop trigger."""
        mock_position = Mock()
        mock_position.symbol = "AAPL"
        mock_position.qty = 10
        mock_position.avg_entry_price = 150.0
        
        trading_bot_with_risk.api.list_positions.return_value = [mock_position]
        trading_bot_with_risk.data_manager.get_latest_price.return_value = 155.0
        
        # Mock trailing stop trigger
        trading_bot_with_risk.enhanced_risk_manager.update_position_price.return_value = "Trailing stop triggered at $154.50"
        
        # Mock sell operation
        trading_bot_with_risk.data_manager.get_latest_price.return_value = 155.0
        mock_order = Mock()
        trading_bot_with_risk.api.submit_order.return_value = mock_order
        
        trading_bot_with_risk.check_open_positions()
        
        # Verify trailing stop update was called
        trading_bot_with_risk.enhanced_risk_manager.update_position_price.assert_called_with("AAPL", 155.0)
    
    def test_check_positions_stop_loss_trigger(self, trading_bot):
        """Test position monitoring with stop loss trigger."""
        mock_position = Mock()
        mock_position.symbol = "AAPL"
        mock_position.qty = 10
        mock_position.avg_entry_price = 150.0
        mock_position.client_order_id = "order_123"
        
        trading_bot.api.list_positions.return_value = [mock_position]
        trading_bot.data_manager.get_latest_price.return_value = 140.0  # Below stop loss
        trading_bot.enable_enhanced_risk_management = False
        
        # Mock order with stop loss
        mock_order = Mock()
        mock_order.client_order_id = "sl_142.50_tp_165.00"
        trading_bot.api.get_order_by_client_order_id.return_value = mock_order
        
        # Mock sell operation
        mock_sell_order = Mock()
        trading_bot.api.submit_order.return_value = mock_sell_order
        
        with patch.object(trading_bot, 'sell') as mock_sell:
            trading_bot.check_open_positions()
            
            # Should trigger sell due to stop loss
            mock_sell.assert_called_once()
            call_args = mock_sell.call_args[1]
            assert call_args['reason'] == "stop_loss"
    
    def test_check_positions_target_price_trigger(self, trading_bot):
        """Test position monitoring with target price trigger."""
        mock_position = Mock()
        mock_position.symbol = "AAPL"
        mock_position.qty = 10
        mock_position.avg_entry_price = 150.0
        mock_position.client_order_id = "order_123"
        
        trading_bot.api.list_positions.return_value = [mock_position]
        trading_bot.data_manager.get_latest_price.return_value = 170.0  # Above target
        trading_bot.enable_enhanced_risk_management = False
        
        # Mock order with target price
        mock_order = Mock()
        mock_order.client_order_id = "sl_142.50_tp_165.00"
        trading_bot.api.get_order_by_client_order_id.return_value = mock_order
        
        with patch.object(trading_bot, 'sell') as mock_sell:
            trading_bot.check_open_positions()
            
            # Should trigger sell due to target price
            mock_sell.assert_called_once()
            call_args = mock_sell.call_args[1]
            assert call_args['reason'] == "target_price"


class TestTradingBotRunStrategy:
    """Test strategy execution loop."""
    
    def test_run_strategy_no_trades_allowed(self, trading_bot):
        """Test strategy execution when no trades allowed."""
        # Mock that max trades reached
        trading_bot.api.list_positions.return_value = [Mock(), Mock(), Mock()]  # 3 positions (at limit)
        
        trading_bot.run_strategy()
        
        # Should not call strategy or place trades
        trading_bot.data_manager.get_historical_data.assert_not_called()
    
    def test_run_strategy_with_signal(self, trading_bot):
        """Test strategy execution with buy signal."""
        trading_bot.tickers = ["AAPL"]
        trading_bot.api.list_positions.return_value = []  # No current positions
        
        # Mock historical data
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='1min'),
            'close': np.random.normal(150, 5, 100)
        })
        trading_bot.data_manager.get_historical_data.return_value = df
        
        # Mock strategy signal
        trading_bot.strategy.generate_signal.return_value = 1  # Buy signal
        
        # Mock latest price
        trading_bot.data_manager.get_latest_price.return_value = 150.0
        
        with patch.object(trading_bot, 'enter_position') as mock_enter:
            trading_bot.run_strategy()
            
            # Should attempt to enter position
            mock_enter.assert_called_once_with("AAPL", df)
    
    def test_run_strategy_no_signal(self, trading_bot):
        """Test strategy execution with no signal."""
        trading_bot.tickers = ["AAPL"]
        trading_bot.api.list_positions.return_value = []
        
        df = pd.DataFrame({'close': [150]})
        trading_bot.data_manager.get_historical_data.return_value = df
        trading_bot.strategy.generate_signal.return_value = 0  # No signal
        
        with patch.object(trading_bot, 'enter_position') as mock_enter:
            trading_bot.run_strategy()
            
            # Should not enter position
            mock_enter.assert_not_called()
    
    def test_run_strategy_empty_dataframe(self, trading_bot):
        """Test strategy execution with empty historical data."""
        trading_bot.tickers = ["AAPL"]
        trading_bot.api.list_positions.return_value = []
        
        # Return empty DataFrame
        trading_bot.data_manager.get_historical_data.return_value = pd.DataFrame()
        
        with patch.object(trading_bot, 'enter_position') as mock_enter:
            trading_bot.run_strategy()
            
            # Should not enter position with empty data
            mock_enter.assert_not_called()


class TestTradingBotRecordKeeping:
    """Test record keeping and CSV operations."""
    
    def test_record_order(self, trading_bot, temp_directory):
        """Test order recording functionality."""
        ticker = "AAPL"
        price = 150.0
        quantity = 10
        
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_directory)
        
        try:
            # Create ORDERS directory
            orders_dir = "ORDERS"
            os.makedirs(orders_dir, exist_ok=True)
            
            # Mock account cash
            trading_bot.api.get_account.return_value.cash = 10000.0
            
            trading_bot.record_order(ticker, price, quantity)
            
            # Check that files were created
            assert os.path.exists("ORDERS/Orders.csv")
            assert os.path.exists("ORDERS/Time and Coins.csv")
            
            # Read and verify order data
            orders_df = pd.read_csv("ORDERS/Orders.csv")
            assert len(orders_df) == 1
            assert orders_df.iloc[0]['Ticker'] == ticker
            assert orders_df.iloc[0]['Buy Price'] == price
            assert orders_df.iloc[0]['Quantity'] == quantity
            
        finally:
            os.chdir(original_cwd)
    
    def test_record_sell(self, trading_bot, temp_directory):
        """Test sell record functionality."""
        ticker = "AAPL"
        quantity = 10
        buy_price = 150.0
        sell_price = 155.0
        highest_price = 157.0
        
        original_cwd = os.getcwd()
        os.chdir(temp_directory)
        
        try:
            os.makedirs("ORDERS", exist_ok=True)
            trading_bot.api.get_account.return_value.cash = 11000.0
            
            trading_bot.record_sell(ticker, quantity, buy_price, sell_price, highest_price)
            
            # Verify sell record
            orders_df = pd.read_csv("ORDERS/Orders.csv")
            assert len(orders_df) == 1
            assert orders_df.iloc[0]['Type'] == 'sell'
            assert orders_df.iloc[0]['Sell Price'] == sell_price
            
        finally:
            os.chdir(original_cwd)


class TestTradingBotRiskDashboard:
    """Test risk dashboard and management features."""
    
    def test_get_risk_dashboard_disabled(self, trading_bot):
        """Test risk dashboard when enhanced risk management is disabled."""
        trading_bot.enable_enhanced_risk_management = False
        
        dashboard = trading_bot.get_risk_dashboard()
        
        assert "message" in dashboard
        assert dashboard["message"] == "Enhanced risk management disabled"
    
    def test_get_risk_dashboard_enabled(self, trading_bot_with_risk):
        """Test risk dashboard when enhanced risk management is enabled."""
        # Mock risk manager responses
        portfolio_summary = {"total_value": 100000, "risk_level": "moderate"}
        validation_stats = {"total_validations": 10, "approved": 8}
        trailing_stops = {"AAPL": {"current_stop": 145.0}}
        
        trading_bot_with_risk.enhanced_risk_manager.get_portfolio_risk_summary.return_value = portfolio_summary
        trading_bot_with_risk.enhanced_risk_manager.get_validation_statistics.return_value = validation_stats
        trading_bot_with_risk.enhanced_risk_manager.trailing_stop_manager.get_all_stops_status.return_value = trailing_stops
        
        # Mock risk config
        trading_bot_with_risk.risk_config.max_daily_loss = 0.05
        trading_bot_with_risk.risk_config.max_position_size = 0.10
        trading_bot_with_risk.risk_config.max_positions = 5
        trading_bot_with_risk.risk_config.get_risk_level.return_value = Mock(value="moderate")
        
        dashboard = trading_bot_with_risk.get_risk_dashboard()
        
        assert "portfolio_summary" in dashboard
        assert "validation_statistics" in dashboard
        assert "trailing_stops" in dashboard
        assert "risk_config" in dashboard
        assert "timestamp" in dashboard
    
    def test_emergency_override_enable(self, trading_bot_with_risk):
        """Test enabling emergency risk override."""
        trading_bot_with_risk.enhanced_risk_manager.enable_emergency_override.return_value = True
        
        result = trading_bot_with_risk.enable_emergency_override("Market crash detected", 120)
        
        assert result is True
        trading_bot_with_risk.enhanced_risk_manager.enable_emergency_override.assert_called_once_with(
            "Market crash detected", 120
        )
    
    def test_emergency_override_disable(self, trading_bot_with_risk):
        """Test disabling emergency risk override."""
        trading_bot_with_risk.enhanced_risk_manager.disable_emergency_override.return_value = True
        
        result = trading_bot_with_risk.disable_emergency_override()
        
        assert result is True
        trading_bot_with_risk.enhanced_risk_manager.disable_emergency_override.assert_called_once()
    
    def test_validate_proposed_trade(self, trading_bot_with_risk):
        """Test proposed trade validation."""
        from risk_management.enhanced_risk_manager import RiskValidationResult
        
        # Mock validation result
        validation_result = RiskValidationResult(
            approved=True,
            confidence_score=0.85,
            risk_score=20.0,
            violations=[],
            warnings=[],
            recommendations=["Trade approved"]
        )
        
        trading_bot_with_risk.enhanced_risk_manager.validate_position_size.return_value = validation_result
        
        # Mock historical data for stop loss calculation
        df = pd.DataFrame({'close': [150]})
        trading_bot_with_risk.data_manager.get_historical_data.return_value = df
        
        result = trading_bot_with_risk.validate_proposed_trade("AAPL", 10, 150.0)
        
        assert result.approved is True
        assert result.confidence_score == 0.85
    
    def test_toggle_risk_management(self, trading_bot):
        """Test toggling enhanced risk management."""
        # Enable risk management
        result = trading_bot.toggle_enhanced_risk_management(True)
        assert result is True
        assert trading_bot.enable_enhanced_risk_management is True
        
        # Disable risk management
        result = trading_bot.toggle_enhanced_risk_management(False)
        assert result is True
        assert trading_bot.enable_enhanced_risk_management is False


class TestTradingBotErrorHandling:
    """Test error handling and edge cases."""
    
    def test_enter_position_api_error(self, trading_bot):
        """Test position entry with API error."""
        ticker = "AAPL"
        trading_bot.data_manager.get_latest_price.return_value = 150.0
        trading_bot.enable_enhanced_risk_management = False
        
        # Mock API error
        trading_bot.api.submit_order.side_effect = Exception("API Error")
        
        df = pd.DataFrame({'close': [150]})
        
        # Should handle error gracefully
        trading_bot.enter_position(ticker, df)
        # No exception should be raised
    
    def test_sell_api_error(self, trading_bot):
        """Test sell operation with API error."""
        trading_bot.data_manager.get_latest_price.return_value = 150.0
        trading_bot.api.submit_order.side_effect = Exception("API Error")
        
        # Should handle error gracefully
        trading_bot.sell("AAPL", 10, 150.0, 155.0)
        # No exception should be raised
    
    def test_check_positions_client_order_id_error(self, trading_bot):
        """Test position checking with malformed client order ID."""
        mock_position = Mock()
        mock_position.symbol = "AAPL"
        mock_position.qty = 10
        mock_position.client_order_id = "order_123"
        
        trading_bot.api.list_positions.return_value = [mock_position]
        trading_bot.data_manager.get_latest_price.return_value = 150.0
        trading_bot.enable_enhanced_risk_management = False
        
        # Mock malformed client order ID
        mock_order = Mock()
        mock_order.client_order_id = "invalid_format"
        trading_bot.api.get_order_by_client_order_id.return_value = mock_order
        
        # Should handle parsing error gracefully
        trading_bot.check_open_positions()
        # No exception should be raised
    
    def test_portfolio_value_error_handling(self, trading_bot):
        """Test portfolio value calculation with API error."""
        trading_bot.api.get_account.side_effect = Exception("API Error")
        
        # Should return default value
        portfolio_value = trading_bot._get_portfolio_value()
        assert portfolio_value == 100000.0  # Default fallback


class TestTradingBotPerformance:
    """Performance tests for trading bot operations."""
    
    @pytest.mark.performance
    def test_run_strategy_performance(self, trading_bot, benchmark):
        """Benchmark strategy execution performance."""
        trading_bot.tickers = ["AAPL", "TSLA", "GOOGL"]
        trading_bot.api.list_positions.return_value = []
        
        # Mock data and signals
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=1000, freq='1min'),
            'close': np.random.normal(150, 5, 1000)
        })
        trading_bot.data_manager.get_historical_data.return_value = df
        trading_bot.strategy.generate_signal.return_value = 0  # No signal to avoid order placement
        
        # Benchmark the strategy execution
        benchmark(trading_bot.run_strategy)
    
    @pytest.mark.performance  
    def test_check_positions_performance(self, trading_bot, benchmark):
        """Benchmark position checking performance."""
        # Create multiple mock positions
        positions = []
        for i in range(10):
            mock_position = Mock()
            mock_position.symbol = f"STOCK{i}"
            mock_position.qty = 10
            mock_position.client_order_id = f"order_{i}"
            positions.append(mock_position)
        
        trading_bot.api.list_positions.return_value = positions
        trading_bot.data_manager.get_latest_price.return_value = 150.0
        trading_bot.enable_enhanced_risk_management = False
        
        # Mock order lookup
        mock_order = Mock()
        mock_order.client_order_id = "sl_142.50_tp_165.00"
        trading_bot.api.get_order_by_client_order_id.return_value = mock_order
        
        # Benchmark position checking
        benchmark(trading_bot.check_open_positions)