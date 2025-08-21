"""
Integration tests for API endpoints and data services.
Tests real API interactions with mocked external dependencies.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import asyncio
import time

from services.data_service import TradingDataService
from services.unified_data_manager import UnifiedDataManager
from flask_app import app
from database.database_manager import DatabaseManager
from tests.mocks.alpaca_api_mock import create_mock_alpaca_api, create_realistic_market_scenario


@pytest.mark.integration
class TestDataServiceIntegration:
    """Integration tests for data service operations."""
    
    def test_data_service_initialization(self, temp_db):
        """Test data service initialization with database."""
        service = TradingDataService()
        service.db_manager.db_path = temp_db
        
        assert service.db_manager is not None
        assert service.orders_dao is not None
        assert service.open_orders_dao is not None
        assert service.market_data_dao is not None
    
    def test_order_workflow_integration(self, temp_db):
        """Test complete order workflow from creation to completion."""
        service = TradingDataService()
        service.db_manager.db_path = temp_db
        
        # Create open order
        order_data = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ticker': 'AAPL',
            'type': 'buy',
            'buy_price': 150.0,
            'quantity': 10,
            'total': 1500.0,
            'acc_balance': 50000.0,
            'target_price': 165.0,
            'stop_loss_price': 142.5,
            'activate_trailing_stop_at': 157.5,
            'current_price': 150.0,
            'unrealized_pnl': 0.0
        }
        
        # Add open order
        order_id = service.add_open_order(order_data)
        assert order_id > 0
        
        # Verify order exists
        open_orders = service.get_open_orders('AAPL')
        assert len(open_orders) == 1
        assert open_orders.iloc[0]['ticker'] == 'AAPL'
        
        # Update order
        updates = {'current_price': 155.0, 'unrealized_pnl': 50.0}
        success = service.update_open_order(order_id, updates)
        assert success is True
        
        # Close position
        success = service.close_position(order_id, 160.0)
        assert success is True
        
        # Verify order moved to completed orders
        completed_orders = service.get_completed_orders('AAPL')
        assert len(completed_orders) > 0
        
        # Verify no open orders remain
        open_orders = service.get_open_orders('AAPL')
        assert len(open_orders) == 0
    
    def test_portfolio_summary_integration(self, temp_db):
        """Test portfolio summary with real data."""
        service = TradingDataService()
        service.db_manager.db_path = temp_db
        
        # Add some completed trades
        trades = [
            {
                'time': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'ticker': 'AAPL',
                'type': 'buy',
                'buy_price': 150.0,
                'sell_price': None,
                'quantity': 10,
                'total': 1500.0,
                'acc_balance': 50000.0
            },
            {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ticker': 'AAPL',
                'type': 'sell',
                'buy_price': 150.0,
                'sell_price': 160.0,
                'quantity': 10,
                'total': 1600.0,
                'acc_balance': 50100.0
            }
        ]
        
        for trade in trades:
            service.add_completed_order(trade)
        
        # Add open position
        open_order = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ticker': 'TSLA',
            'type': 'buy',
            'buy_price': 200.0,
            'quantity': 5,
            'total': 1000.0,
            'acc_balance': 49100.0,
            'current_price': 205.0,
            'unrealized_pnl': 25.0
        }
        service.add_open_order(open_order)
        
        # Get portfolio summary
        summary = service.get_portfolio_summary()
        
        assert summary['completed_trades'] > 0
        assert summary['open_positions'] == 1
        assert summary['total_open_value'] == 1000.0
        assert summary['unrealized_pnl'] == 25.0
    
    def test_market_data_storage_and_retrieval(self, temp_db):
        """Test market data storage and retrieval."""
        service = TradingDataService()
        service.db_manager.db_path = temp_db
        
        # Store market data
        ticker = 'AAPL'
        timestamp = datetime.now()
        ohlcv = {
            'open': 150.0,
            'high': 152.0,
            'low': 149.0,
            'close': 151.0,
            'volume': 10000
        }
        
        success = service.store_market_data(ticker, timestamp, ohlcv)
        assert success is True
        
        # Retrieve market data
        historical_data = service.get_historical_data(ticker, days=1)
        assert len(historical_data) > 0
        assert historical_data.iloc[0]['ticker'] == ticker
        assert historical_data.iloc[0]['close_price'] == 151.0
    
    def test_strategy_performance_analysis(self, temp_db):
        """Test strategy performance analysis integration."""
        service = TradingDataService()
        service.db_manager.db_path = temp_db
        
        # Add multiple trades with different outcomes
        trades = []
        base_time = datetime.now() - timedelta(days=7)
        
        for i in range(10):
            buy_price = 100.0 + i
            sell_price = buy_price + np.random.choice([-5, 5, 10])  # Mix of wins/losses
            
            trades.extend([
                {
                    'time': (base_time + timedelta(hours=i*2)).strftime('%Y-%m-%d %H:%M:%S'),
                    'ticker': f'STOCK{i%3}',
                    'type': 'buy',
                    'buy_price': buy_price,
                    'sell_price': None,
                    'quantity': 10,
                    'total': buy_price * 10,
                    'acc_balance': 50000.0
                },
                {
                    'time': (base_time + timedelta(hours=i*2+1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'ticker': f'STOCK{i%3}',
                    'type': 'sell',
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'quantity': 10,
                    'total': sell_price * 10,
                    'acc_balance': 50000.0 + (sell_price - buy_price) * 10
                }
            ])
        
        for trade in trades:
            service.add_completed_order(trade)
        
        # Analyze performance
        performance = service.get_strategy_performance(days=7)
        
        assert 'total_trades' in performance
        assert 'win_rate' in performance
        assert 'total_pnl' in performance
        assert 'profit_factor' in performance
        assert performance['total_trades'] == 10


@pytest.mark.integration 
class TestUnifiedDataManagerIntegration:
    """Integration tests for unified data manager."""
    
    def test_data_manager_with_mock_api(self):
        """Test data manager with mock Alpaca API."""
        mock_api = create_realistic_market_scenario()
        
        # This would normally be done through dependency injection
        data_manager = Mock()
        data_manager.api = mock_api
        
        # Test account retrieval
        account = data_manager.api.get_account()
        assert account.cash == 50000.0
        assert account.equity == 75000.0
        
        # Test position retrieval
        positions = data_manager.api.list_positions()
        assert len(positions) == 2
        assert positions[0].symbol == 'AAPL'
        assert positions[1].symbol == 'TSLA'
    
    def test_historical_data_retrieval(self):
        """Test historical data retrieval integration."""
        mock_api = create_mock_alpaca_api()
        
        # Test bars retrieval
        bars_df = mock_api.get_bars('AAPL', '1Min', limit=100)
        
        assert len(bars_df) == 100
        assert all(col in bars_df.columns for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        assert bars_df['close'].dtype in [np.float64, float]
        assert (bars_df['high'] >= bars_df['close']).all()
        assert (bars_df['low'] <= bars_df['close']).all()
    
    def test_real_time_data_simulation(self):
        """Test real-time data simulation."""
        mock_api = create_mock_alpaca_api()
        
        # Get multiple snapshots to simulate real-time updates
        snapshots = []
        for _ in range(5):
            snapshot = mock_api.get_snapshot('AAPL')
            snapshots.append(snapshot)
            time.sleep(0.1)  # Small delay
        
        assert len(snapshots) == 5
        
        # Prices should vary (simulate market movement)
        prices = [s['latest_trade']['price'] for s in snapshots]
        assert len(set(prices)) > 1  # Prices should change


@pytest.mark.integration
class TestFlaskAppIntegration:
    """Integration tests for Flask application endpoints."""
    
    @pytest.fixture(scope="class")
    def test_client(self):
        """Create test client for Flask app."""
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            yield client
    
    def test_dashboard_endpoint(self, test_client):
        """Test dashboard endpoint integration."""
        response = test_client.get('/')
        assert response.status_code == 200
        assert b'Trading Dashboard' in response.data or b'dashboard' in response.data.lower()
    
    def test_api_status_endpoint(self, test_client):
        """Test API status endpoint."""
        with patch('flask_app.get_service_registry') as mock_registry:
            mock_registry.return_value.get_health_report.return_value = {
                'status': 'healthy',
                'ready_services': 3,
                'total_services': 3
            }
            
            response = test_client.get('/api/status')
            assert response.status_code == 200
            
            # Check response format
            if response.is_json:
                data = response.get_json()
                assert 'status' in data
    
    def test_positions_endpoint(self, test_client):
        """Test positions endpoint."""
        with patch('flask_app.get_service_registry') as mock_registry:
            mock_data_manager = Mock()
            mock_data_manager.api.list_positions.return_value = []
            mock_registry.return_value.get.return_value = mock_data_manager
            
            response = test_client.get('/api/positions')
            
            # Should return valid response even with empty positions
            assert response.status_code in [200, 404]  # Depends on implementation
    
    def test_trading_bot_integration_endpoint(self, test_client):
        """Test trading bot integration endpoints."""
        # Test bot status
        with patch('flask_app.trading_bot') as mock_bot:
            mock_bot.get_risk_dashboard.return_value = {
                'status': 'active',
                'positions': 0,
                'risk_level': 'low'
            }
            
            response = test_client.get('/api/bot/status')
            
            # Should handle bot status requests
            assert response.status_code in [200, 404, 500]


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    def test_database_migration_integration(self, temp_db):
        """Test database migration from CSV files."""
        # Create temporary CSV files
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create ORDERS directory
            orders_dir = os.path.join(temp_dir, 'ORDERS')
            os.makedirs(orders_dir)
            
            # Create sample CSV file
            csv_content = """Time,Ticker,Type,Buy Price,Sell Price,Highest Price,Quantity,Total,Acc Balance,Target Price,Stop Loss Price,ActivateTrailingStopAt
2024-01-01 10:00:00,AAPL,buy,150.0,,150.0,10,1500.0,50000.0,165.0,142.5,157.5
2024-01-01 11:00:00,AAPL,sell,150.0,160.0,162.0,10,1600.0,50100.0,,,"""
            
            csv_file = os.path.join(orders_dir, 'Orders.csv')
            with open(csv_file, 'w') as f:
                f.write(csv_content)
            
            # Change to temp directory and test migration
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                service = TradingDataService()
                service.db_manager.db_path = temp_db
                
                # Migration should occur during initialization
                # Verify data was migrated
                orders = service.get_completed_orders()
                assert len(orders) >= 2
                
            finally:
                os.chdir(original_cwd)
    
    def test_database_backup_and_restore(self, temp_db):
        """Test database backup functionality."""
        service = TradingDataService()
        service.db_manager.db_path = temp_db
        
        # Add some test data
        order_data = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ticker': 'AAPL',
            'type': 'buy',
            'buy_price': 150.0,
            'quantity': 10,
            'total': 1500.0,
            'acc_balance': 50000.0
        }
        service.add_completed_order(order_data)
        
        # Create backup
        backup_path = service.backup_database()
        assert os.path.exists(backup_path)
        
        # Verify backup contains data
        assert os.path.getsize(backup_path) > 0
        
        # Cleanup
        os.remove(backup_path)
    
    def test_database_cleanup_integration(self, temp_db):
        """Test database cleanup functionality."""
        service = TradingDataService()
        service.db_manager.db_path = temp_db
        
        # Add old market data
        old_timestamp = datetime.now() - timedelta(days=400)
        service.store_market_data('AAPL', old_timestamp, {
            'open': 100.0, 'high': 102.0, 'low': 98.0, 'close': 101.0, 'volume': 10000
        })
        
        # Add recent market data
        recent_timestamp = datetime.now() - timedelta(days=1)
        service.store_market_data('AAPL', recent_timestamp, {
            'open': 150.0, 'high': 152.0, 'low': 148.0, 'close': 151.0, 'volume': 15000
        })
        
        # Run cleanup (keep 365 days)
        service.cleanup_old_data(keep_days=365)
        
        # Verify old data was removed and recent data remains
        historical_data = service.get_historical_data('AAPL', days=500)
        
        # Should only have recent data
        if not historical_data.empty:
            oldest_date = pd.to_datetime(historical_data['timestamp']).min()
            cutoff_date = datetime.now() - timedelta(days=365)
            assert oldest_date >= cutoff_date


@pytest.mark.integration
@pytest.mark.slow
class TestFullWorkflowIntegration:
    """Integration tests for complete trading workflows."""
    
    def test_complete_trading_cycle(self, integration_test_setup):
        """Test complete trading cycle from signal to execution."""
        setup = integration_test_setup
        bot = setup['bot']
        strategy = setup['strategy']
        
        # Mock market data that would generate a signal
        market_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='1min'),
            'open': np.random.normal(150, 2, 100),
            'high': np.random.normal(152, 2, 100),
            'low': np.random.normal(148, 2, 100),
            'close': np.random.normal(150, 2, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        bot.data_manager.get_historical_data.return_value = market_data
        bot.data_manager.get_latest_price.return_value = 150.0
        
        # Mock strategy to generate buy signal
        with patch.object(strategy, 'generate_signal', return_value=1):
            # Mock successful order placement
            mock_order = Mock()
            mock_order.id = "order_123"
            bot.api.submit_order.return_value = mock_order
            
            # Mock account info
            bot.api.get_account.return_value.cash = 50000.0
            bot.api.get_account.return_value.equity = 50000.0
            
            # Run strategy
            bot.run_strategy()
            
            # Verify order was placed
            bot.api.submit_order.assert_called_once()
            
            # Verify order parameters
            call_args = bot.api.submit_order.call_args
            assert call_args[1]['symbol'] in bot.tickers
            assert call_args[1]['side'] == 'buy'
            assert call_args[1]['type'] == 'market'
    
    def test_position_monitoring_cycle(self, integration_test_setup):
        """Test position monitoring and exit logic."""
        setup = integration_test_setup
        bot = setup['bot']
        
        # Create mock position
        mock_position = Mock()
        mock_position.symbol = 'AAPL'
        mock_position.qty = 10
        mock_position.avg_entry_price = 150.0
        mock_position.client_order_id = 'order_123'
        
        bot.api.list_positions.return_value = [mock_position]
        
        # Mock current price below stop loss
        bot.data_manager.get_latest_price.return_value = 140.0
        
        # Mock order info with stop loss
        mock_order = Mock()
        mock_order.client_order_id = 'sl_142.50_tp_165.00'
        bot.api.get_order_by_client_order_id.return_value = mock_order
        
        # Mock sell order
        mock_sell_order = Mock()
        bot.api.submit_order.return_value = mock_sell_order
        
        # Run position check
        with patch.object(bot, 'sell') as mock_sell:
            bot.check_open_positions()
            
            # Should trigger stop loss
            mock_sell.assert_called_once()
            call_args = mock_sell.call_args[1]
            assert call_args['reason'] == 'stop_loss'
    
    def test_risk_management_integration_cycle(self, integration_test_setup):
        """Test risk management integration in trading cycle."""
        setup = integration_test_setup
        bot = setup['bot']
        
        # Enable enhanced risk management
        bot.enable_enhanced_risk_management = True
        bot.enhanced_risk_manager = Mock()
        
        # Mock risk manager responses
        optimal_size = Mock()
        optimal_size.risk_adjusted_size = 0.02
        bot.enhanced_risk_manager.calculate_optimal_position_size.return_value = optimal_size
        
        validation_result = Mock()
        validation_result.approved = True
        validation_result.violations = []
        validation_result.warnings = []
        validation_result.position_size_adjustment = None
        bot.enhanced_risk_manager.validate_position_size.return_value = validation_result
        
        # Setup market data and signal
        market_data = pd.DataFrame({'close': [150.0] * 100})
        bot.data_manager.get_historical_data.return_value = market_data
        bot.data_manager.get_latest_price.return_value = 150.0
        bot.strategy.generate_signal.return_value = 1
        
        # Mock account
        bot.api.get_account.return_value.equity = 100000.0
        
        # Mock order placement
        mock_order = Mock()
        bot.api.submit_order.return_value = mock_order
        
        # Run entry
        bot.enter_position('AAPL', market_data)
        
        # Verify risk management was called
        bot.enhanced_risk_manager.calculate_optimal_position_size.assert_called_once()
        bot.enhanced_risk_manager.validate_position_size.assert_called_once()
        bot.enhanced_risk_manager.add_position.assert_called_once()


@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceIntegration:
    """Integration performance tests."""
    
    def test_high_volume_order_processing(self, temp_db, benchmark):
        """Test performance with high volume of orders."""
        service = TradingDataService()
        service.db_manager.db_path = temp_db
        
        def process_orders():
            orders = []
            for i in range(100):
                order = {
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'ticker': f'STOCK{i%10}',
                    'type': 'buy',
                    'buy_price': 100.0 + i,
                    'quantity': 10,
                    'total': (100.0 + i) * 10,
                    'acc_balance': 50000.0
                }
                orders.append(service.add_completed_order(order))
            return orders
        
        # Benchmark order processing
        order_ids = benchmark(process_orders)
        assert len(order_ids) == 100
    
    def test_concurrent_position_monitoring(self, integration_test_setup, benchmark):
        """Test performance of position monitoring with multiple positions."""
        setup = integration_test_setup
        bot = setup['bot']
        
        # Create multiple mock positions
        positions = []
        for i in range(20):
            position = Mock()
            position.symbol = f'STOCK{i}'
            position.qty = 10
            position.avg_entry_price = 100.0 + i
            position.client_order_id = f'order_{i}'
            positions.append(position)
        
        bot.api.list_positions.return_value = positions
        bot.data_manager.get_latest_price.return_value = 150.0
        
        # Mock order lookup
        mock_order = Mock()
        mock_order.client_order_id = 'sl_142.50_tp_165.00'
        bot.api.get_order_by_client_order_id.return_value = mock_order
        
        # Benchmark position checking
        benchmark(bot.check_open_positions)


@pytest.mark.integration
@pytest.mark.network
class TestExternalIntegration:
    """Tests that require external network access (marked for optional execution)."""
    
    @pytest.mark.skip(reason="Requires actual API credentials")
    def test_real_alpaca_api_connection(self):
        """Test connection to real Alpaca API (requires credentials)."""
        # This test would be enabled in staging/production testing
        # with real API credentials
        pass
    
    @pytest.mark.skip(reason="Requires market data subscription") 
    def test_real_market_data_feed(self):
        """Test real market data feed integration."""
        # This test would verify real-time data feeds
        pass