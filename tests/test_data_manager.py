"""
Comprehensive unit tests for the UnifiedDataManager.
Tests cover API connection, data fetching and caching, indicator calculations,
thread safety, circuit breakers, and error handling.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import threading
import time
import queue
import json
import tempfile
import os

from services.unified_data_manager import UnifiedDataManager, get_data_manager, cleanup_data_manager
from services.circuit_breaker import CircuitBreakerError


class TestDataManagerInitialization:
    """Test data manager initialization and setup."""
    
    def test_data_manager_initialization(self):
        """Test basic data manager initialization."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            manager = UnifiedDataManager()
            
            assert manager.api is None  # Will be set by initialize_api
            assert manager.stream is None
            assert manager.is_streaming is False
            assert isinstance(manager.data_queue, queue.Queue)
            assert manager.last_update is not None
    
    @patch('services.unified_data_manager.get_database')
    @patch('services.unified_data_manager.cache_manager')
    @patch('services.unified_data_manager.circuit_manager')
    def test_singleton_data_manager(self, mock_circuit, mock_cache, mock_db):
        """Test singleton data manager instance."""
        with patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            manager1 = get_data_manager()
            manager2 = get_data_manager()
            
            assert manager1 is manager2


class TestAPIInitialization:
    """Test Alpaca API initialization."""
    
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
        
        return temp_path
    
    def test_initialize_api_success_json_format(self, mock_auth_file):
        """Test successful API initialization with JSON format auth file."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', create=True) as mock_open, \
             patch('alpaca_trade_api.REST') as mock_rest:
            
            # Mock file content
            with open(mock_auth_file, 'r') as f:
                content = f.read()
            mock_open.return_value.__enter__.return_value.read.return_value = content
            
            # Mock Alpaca API
            mock_api = Mock()
            mock_rest.return_value = mock_api
            
            # Mock account breaker
            manager = UnifiedDataManager()
            manager.account_breaker = Mock()
            manager.account_breaker.call = Mock()
            
            result = manager.initialize_api()
            
            assert result is True
            assert manager.api == mock_api
            mock_rest.assert_called_once_with(
                'test_key_id',
                'test_secret_key', 
                'https://paper-api.alpaca.markets',
                api_version='v2'
            )
        
        # Cleanup
        os.unlink(mock_auth_file)
    
    def test_initialize_api_success_line_format(self):
        """Test successful API initialization with line format auth file."""
        auth_content = "test_key_id\ntest_secret_key\nhttps://paper-api.alpaca.markets"
        
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', create=True) as mock_open, \
             patch('alpaca_trade_api.REST') as mock_rest:
            
            mock_open.return_value.__enter__.return_value.read.return_value = auth_content
            
            # Mock Alpaca API
            mock_api = Mock()
            mock_rest.return_value = mock_api
            
            manager = UnifiedDataManager()
            manager.account_breaker = Mock()
            manager.account_breaker.call = Mock()
            
            result = manager.initialize_api()
            
            assert result is True
            assert manager.api == mock_api
    
    def test_initialize_api_file_not_found(self):
        """Test API initialization when auth file doesn't exist."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('os.path.exists', return_value=False):
            
            manager = UnifiedDataManager()
            result = manager.initialize_api()
            
            assert result is False
            assert manager.api is None
    
    def test_initialize_api_invalid_credentials(self):
        """Test API initialization with invalid credentials."""
        auth_content = "\n\n"  # Empty credentials
        
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', create=True) as mock_open:
            
            mock_open.return_value.__enter__.return_value.read.return_value = auth_content
            
            manager = UnifiedDataManager()
            result = manager.initialize_api()
            
            assert result is False
            assert manager.api is None


class TestAccountOperations:
    """Test account-related operations."""
    
    @pytest.fixture
    def data_manager(self):
        """Create a data manager instance for testing."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            manager = UnifiedDataManager()
            manager.api = Mock()
            manager.account_breaker = Mock()
            return manager
    
    def test_get_account_info_success(self, data_manager):
        """Test successful account info retrieval."""
        # Mock account object
        mock_account = Mock()
        mock_account.portfolio_value = 100000.0
        mock_account.cash = 50000.0
        mock_account.buying_power = 200000.0
        mock_account.unrealized_pl = 1500.0
        mock_account.equity = 101500.0
        mock_account.id = 'test_account_id'
        mock_account.status = 'ACTIVE'
        
        data_manager.account_breaker.call.return_value = mock_account
        
        result = data_manager.get_account_info()
        
        assert result['portfolio_value'] == 100000.0
        assert result['cash'] == 50000.0
        assert result['buying_power'] == 200000.0
        assert result['day_pl'] == 1500.0
        assert result['equity'] == 101500.0
        assert result['account_id'] == 'test_account_id'
        assert result['status'] == 'ACTIVE'
    
    def test_get_account_info_alternative_pl_field(self, data_manager):
        """Test account info with alternative P&L field."""
        # Mock account with unrealized_intraday_pl instead of unrealized_pl
        mock_account = Mock()
        mock_account.portfolio_value = 100000.0
        mock_account.cash = 50000.0
        mock_account.buying_power = 200000.0
        mock_account.unrealized_pl = None
        mock_account.unrealized_intraday_pl = 800.0
        mock_account.equity = 100800.0
        mock_account.id = 'test_account_id'
        mock_account.status = 'ACTIVE'
        
        data_manager.account_breaker.call.return_value = mock_account
        
        result = data_manager.get_account_info()
        
        assert result['day_pl'] == 800.0
    
    def test_get_account_info_circuit_breaker_open(self, data_manager):
        """Test account info when circuit breaker is open."""
        data_manager.account_breaker.call.side_effect = CircuitBreakerError("Circuit breaker open")
        
        with pytest.raises(CircuitBreakerError):
            data_manager.get_account_info()
    
    def test_get_account_info_api_not_initialized(self, data_manager):
        """Test account info when API is not initialized."""
        data_manager.api = None
        
        with pytest.raises(Exception, match="Alpaca API not initialized"):
            data_manager.get_account_info()


class TestPositionOperations:
    """Test position-related operations."""
    
    @pytest.fixture
    def data_manager(self):
        """Create a data manager instance for testing."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            manager = UnifiedDataManager()
            manager.api = Mock()
            manager.account_breaker = Mock()
            return manager
    
    def test_get_positions_success(self, data_manager):
        """Test successful positions retrieval."""
        # Mock position objects
        mock_position1 = Mock()
        mock_position1.symbol = 'AAPL'
        mock_position1.qty = 100
        mock_position1.avg_entry_price = 150.0
        mock_position1.current_price = 155.0
        mock_position1.market_value = 15500.0
        mock_position1.unrealized_pl = 500.0
        mock_position1.unrealized_plpc = 0.033
        mock_position1.change_today = 2.5
        
        mock_position2 = Mock()
        mock_position2.symbol = 'MSFT'
        mock_position2.qty = -50  # Short position
        mock_position2.avg_entry_price = 300.0
        mock_position2.current_price = 295.0
        mock_position2.market_value = -14750.0
        mock_position2.unrealized_pl = 250.0
        mock_position2.unrealized_plpc = 0.017
        mock_position2.change_today = None
        
        data_manager.account_breaker.call.return_value = [mock_position1, mock_position2]
        
        result = data_manager.get_positions()
        
        assert len(result) == 2
        
        # Check first position (long)
        pos1 = result[0]
        assert pos1['symbol'] == 'AAPL'
        assert pos1['qty'] == 100
        assert pos1['side'] == 'long'
        assert pos1['unrealized_plpc'] == 3.3  # Converted to percentage
        assert pos1['change_today'] == 2.5
        
        # Check second position (short)
        pos2 = result[1]
        assert pos2['symbol'] == 'MSFT'
        assert pos2['qty'] == -50
        assert pos2['side'] == 'short'
        assert pos2['change_today'] == 0.0  # None converted to 0.0
    
    def test_get_positions_circuit_breaker_open(self, data_manager):
        """Test positions retrieval when circuit breaker is open."""
        data_manager.account_breaker.call.side_effect = CircuitBreakerError("Circuit breaker open")
        
        with pytest.raises(CircuitBreakerError):
            data_manager.get_positions()


class TestPriceOperations:
    """Test price-related operations."""
    
    @pytest.fixture
    def data_manager(self):
        """Create a data manager instance for testing."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            manager = UnifiedDataManager()
            manager.api = Mock()
            manager.quote_breaker = Mock()
            manager.price_cache = Mock()
            manager.db = Mock()
            return manager
    
    def test_get_latest_price_cache_hit(self, data_manager):
        """Test price retrieval with cache hit."""
        data_manager.price_cache.get.return_value = 150.50
        
        result = data_manager.get_latest_price('AAPL')
        
        assert result == 150.50
        data_manager.quote_breaker.call.assert_not_called()
    
    def test_get_latest_price_cache_miss_success(self, data_manager):
        """Test price retrieval with cache miss and successful API call."""
        data_manager.price_cache.get.return_value = None
        
        # Mock quote object
        mock_quote = Mock()
        mock_quote.bid_price = 149.50
        mock_quote.ask_price = 150.50
        
        data_manager.quote_breaker.call.return_value = mock_quote
        
        result = data_manager.get_latest_price('AAPL')
        
        expected_price = (149.50 + 150.50) / 2  # Mid price
        assert result == expected_price
        data_manager.price_cache.set.assert_called_once_with('AAPL', expected_price)
        data_manager.db.store_price_cache.assert_called_once()
    
    def test_get_latest_price_ask_only(self, data_manager):
        """Test price retrieval with only ask price available."""
        data_manager.price_cache.get.return_value = None
        
        # Mock quote with only ask price
        mock_quote = Mock()
        mock_quote.bid_price = 0
        mock_quote.ask_price = 150.50
        
        data_manager.quote_breaker.call.return_value = mock_quote
        
        result = data_manager.get_latest_price('AAPL')
        
        assert result == 150.50
    
    def test_get_latest_price_bid_only(self, data_manager):
        """Test price retrieval with only bid price available."""
        data_manager.price_cache.get.return_value = None
        
        # Mock quote with only bid price
        mock_quote = Mock()
        mock_quote.bid_price = 149.50
        mock_quote.ask_price = 0
        
        data_manager.quote_breaker.call.return_value = mock_quote
        
        result = data_manager.get_latest_price('AAPL')
        
        assert result == 149.50
    
    def test_get_latest_price_invalid_quote(self, data_manager):
        """Test price retrieval with invalid quote data."""
        data_manager.price_cache.get.return_value = None
        
        # Mock quote with no valid prices
        mock_quote = Mock()
        mock_quote.bid_price = 0
        mock_quote.ask_price = 0
        
        data_manager.quote_breaker.call.return_value = mock_quote
        
        result = data_manager.get_latest_price('AAPL')
        
        assert result is None
    
    def test_get_latest_price_crypto_symbol(self, data_manager):
        """Test price retrieval for crypto symbol (should be skipped)."""
        result = data_manager.get_latest_price('BTCUSD')
        
        assert result is None
        data_manager.quote_breaker.call.assert_not_called()
    
    def test_get_latest_price_circuit_breaker_open(self, data_manager):
        """Test price retrieval when circuit breaker is open."""
        data_manager.price_cache.get.return_value = None
        data_manager.quote_breaker.call.side_effect = CircuitBreakerError("Circuit breaker open")
        data_manager.db.get_cached_price.return_value = (149.75, datetime.now())
        
        result = data_manager.get_latest_price('AAPL')
        
        # Should return fallback from persistent cache
        assert result == 149.75
    
    def test_get_latest_price_api_not_initialized(self, data_manager):
        """Test price retrieval when API is not initialized."""
        data_manager.api = None
        
        result = data_manager.get_latest_price('AAPL')
        
        assert result is None


class TestHistoricalDataOperations:
    """Test historical data operations."""
    
    @pytest.fixture
    def data_manager(self):
        """Create a data manager instance for testing."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            manager = UnifiedDataManager()
            manager.api = Mock()
            manager.bars_breaker = Mock()
            manager.db = Mock()
            return manager
    
    @pytest.fixture
    def sample_bars(self):
        """Create sample bar data."""
        bars = []
        for i in range(5):
            bar = Mock()
            bar.o = 100.0 + i
            bar.h = 101.0 + i
            bar.l = 99.0 + i
            bar.c = 100.5 + i
            bar.v = 1000 + i * 100
            bar.t = datetime.now() - timedelta(minutes=5-i)
            bars.append(bar)
        return bars
    
    def test_get_historical_data_database_hit(self, data_manager):
        """Test historical data retrieval with database hit."""
        # Mock database returning sufficient data
        db_data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        })
        data_manager.db.get_historical_data.return_value = db_data
        
        result = data_manager.get_historical_data('AAPL', '1Min', 24, 200)
        
        assert not result.empty
        assert len(result) == 3
        data_manager.bars_breaker.call.assert_not_called()
    
    def test_get_historical_data_api_fallback(self, data_manager, sample_bars):
        """Test historical data retrieval with API fallback."""
        # Mock database returning insufficient data
        data_manager.db.get_historical_data.return_value = pd.DataFrame()
        data_manager.bars_breaker.call.return_value = sample_bars
        
        result = data_manager.get_historical_data('AAPL', '1Min', 24, 200)
        
        assert not result.empty
        assert len(result) == 5
        data_manager.db.store_historical_data.assert_called_once()
    
    def test_get_historical_data_no_data_found(self, data_manager):
        """Test historical data retrieval when no data is found."""
        data_manager.db.get_historical_data.return_value = pd.DataFrame()
        data_manager.bars_breaker.call.return_value = []
        
        result = data_manager.get_historical_data('AAPL', '1Min', 24, 200)
        
        assert result.empty
    
    def test_get_historical_data_crypto_symbol(self, data_manager):
        """Test historical data retrieval for crypto symbol (should be skipped)."""
        result = data_manager.get_historical_data('BTCUSD', '1Min', 24, 200)
        
        assert result.empty
        data_manager.bars_breaker.call.assert_not_called()
    
    def test_get_historical_data_circuit_breaker_open(self, data_manager):
        """Test historical data retrieval when circuit breaker is open."""
        data_manager.db.get_historical_data.return_value = pd.DataFrame()
        data_manager.bars_breaker.call.side_effect = CircuitBreakerError("Circuit breaker open")
        
        result = data_manager.get_historical_data('AAPL', '1Min', 24, 200)
        
        assert result.empty
    
    def test_get_historical_data_api_not_initialized(self, data_manager):
        """Test historical data retrieval when API is not initialized."""
        data_manager.api = None
        
        result = data_manager.get_historical_data('AAPL', '1Min', 24, 200)
        
        assert result.empty


class TestIndicatorCalculations:
    """Test technical indicator calculations."""
    
    @pytest.fixture
    def data_manager(self):
        """Create a data manager instance for testing."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            manager = UnifiedDataManager()
            manager.indicator_cache = Mock()
            return manager
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLC data."""
        return pd.DataFrame({
            'open': [100, 101, 102, 103, 104, 105],
            'high': [101, 102, 103, 104, 105, 106],
            'low': [99, 100, 101, 102, 103, 104],
            'close': [100, 101, 102, 103, 104, 105],
            'volume': [1000, 1100, 1200, 1300, 1400, 1500]
        })
    
    @pytest.fixture
    def indicator_config(self):
        """Create indicator configuration."""
        return {
            'indicators': {
                'EMA': 'True',
                'EMA_params': {'ema_period': 5},
                'stochRSI': 'True',
                'stochRSI_params': {
                    'rsi_length': 5,
                    'stoch_length': 5,
                    'K': 3,
                    'D': 3
                },
                'stoch': 'True',
                'stoch_params': {
                    'K_Length': 5,
                    'smooth_K': 3,
                    'smooth_D': 3
                }
            }
        }
    
    def test_calculate_indicators_cache_hit(self, data_manager, sample_data, indicator_config):
        """Test indicator calculation with cache hit."""
        cached_indicators = {'EMA': 102.5, 'RSI': 55.0}
        data_manager.indicator_cache.get.return_value = cached_indicators
        
        result = data_manager.calculate_indicators(sample_data, indicator_config)
        
        assert result == cached_indicators
    
    def test_calculate_indicators_ema(self, data_manager, sample_data, indicator_config):
        """Test EMA indicator calculation."""
        data_manager.indicator_cache.get.return_value = None
        
        result = data_manager.calculate_indicators(sample_data, indicator_config)
        
        assert 'EMA' in result
        assert isinstance(result['EMA'], float)
        assert result['EMA'] > 0
        data_manager.indicator_cache.set.assert_called_once()
    
    def test_calculate_indicators_stochrsi(self, data_manager, sample_data, indicator_config):
        """Test StochRSI indicator calculation."""
        data_manager.indicator_cache.get.return_value = None
        
        result = data_manager.calculate_indicators(sample_data, indicator_config)
        
        assert 'RSI' in result or len(sample_data) < 5  # May need more data
        if 'StochRSI_K' in result:
            assert isinstance(result['StochRSI_K'], float)
            assert 0 <= result['StochRSI_K'] <= 100
    
    def test_calculate_indicators_stoch(self, data_manager, sample_data, indicator_config):
        """Test Stochastic indicator calculation."""
        data_manager.indicator_cache.get.return_value = None
        
        result = data_manager.calculate_indicators(sample_data, indicator_config)
        
        if 'Stoch_K' in result:
            assert isinstance(result['Stoch_K'], float)
            assert 0 <= result['Stoch_K'] <= 100
    
    def test_calculate_indicators_empty_dataframe(self, data_manager, indicator_config):
        """Test indicator calculation with empty DataFrame."""
        empty_df = pd.DataFrame()
        
        result = data_manager.calculate_indicators(empty_df, indicator_config)
        
        assert result == {}
    
    def test_calculate_indicators_missing_close_column(self, data_manager, indicator_config):
        """Test indicator calculation with missing close column."""
        invalid_df = pd.DataFrame({'open': [100, 101], 'high': [101, 102]})
        
        result = data_manager.calculate_indicators(invalid_df, indicator_config)
        
        assert result == {}
    
    def test_calculate_indicators_series(self, data_manager, sample_data, indicator_config):
        """Test indicator series calculation for charting."""
        result = data_manager.calculate_indicators_series(sample_data, indicator_config)
        
        if 'EMA' in result:
            assert isinstance(result['EMA'], list)
            assert len(result['EMA']) == len(sample_data)


class TestDataStreaming:
    """Test real-time data streaming functionality."""
    
    @pytest.fixture
    def data_manager(self):
        """Create a data manager instance for testing."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            manager = UnifiedDataManager()
            manager.api = Mock()
            return manager
    
    def test_start_data_stream_success(self, data_manager):
        """Test successful data stream start."""
        tickers = ['AAPL', 'MSFT']
        
        with patch.object(data_manager, 'get_latest_price', return_value=150.0):
            result = data_manager.start_data_stream(tickers, update_interval=0.1)
            
            assert result is True
            assert data_manager.is_streaming is True
            assert data_manager.update_thread is not None
            
            # Wait a moment for thread to start
            time.sleep(0.05)
            
            # Stop streaming
            data_manager.stop_data_stream()
    
    def test_start_data_stream_already_running(self, data_manager):
        """Test starting data stream when already running."""
        data_manager.is_streaming = True
        
        result = data_manager.start_data_stream(['AAPL'])
        
        assert result is True
    
    def test_start_data_stream_no_api(self, data_manager):
        """Test starting data stream without API."""
        data_manager.api = None
        
        result = data_manager.start_data_stream(['AAPL'])
        
        assert result is False
    
    def test_start_data_stream_no_tickers(self, data_manager):
        """Test starting data stream without tickers."""
        result = data_manager.start_data_stream([])
        
        assert result is False
    
    def test_stop_data_stream(self, data_manager):
        """Test stopping data stream."""
        # Start stream first
        with patch.object(data_manager, 'get_latest_price', return_value=150.0):
            data_manager.start_data_stream(['AAPL'], update_interval=0.1)
            
            # Stop stream
            data_manager.stop_data_stream()
            
            assert data_manager.is_streaming is False


class TestCacheOperations:
    """Test caching operations."""
    
    @pytest.fixture
    def data_manager(self):
        """Create a data manager instance for testing."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            manager = UnifiedDataManager()
            manager.price_cache = Mock()
            manager.indicator_cache = Mock()
            return manager
    
    def test_get_cache_stats(self, data_manager):
        """Test cache statistics retrieval."""
        data_manager.price_cache.get_stats.return_value = {
            'hits': 100, 'misses': 20, 'size': 500
        }
        data_manager.indicator_cache.get_stats.return_value = {
            'hits': 50, 'misses': 10, 'size': 100
        }
        
        with patch('services.unified_data_manager.circuit_manager') as mock_circuit:
            mock_circuit.get_status.return_value = {'breakers': 3, 'open': 0}
            
            stats = data_manager.get_cache_stats()
            
            assert 'price_cache' in stats
            assert 'indicator_cache' in stats
            assert 'circuit_breakers' in stats
    
    def test_get_system_health(self, data_manager):
        """Test system health information retrieval."""
        data_manager.api = Mock()
        data_manager.is_streaming = True
        data_manager.db = Mock()
        data_manager.db.get_database_stats.return_value = {'connections': 5}
        
        with patch('services.unified_data_manager.circuit_manager') as mock_circuit:
            mock_circuit.get_status.return_value = {'breakers': 3, 'open': 0}
            
            health = data_manager.get_system_health()
            
            assert health['api_initialized'] is True
            assert health['streaming'] is True
            assert 'last_update' in health
            assert 'cache_stats' in health
            assert 'database_stats' in health
            assert 'circuit_breakers' in health


class TestThreadSafety:
    """Test thread safety of data manager operations."""
    
    @pytest.fixture
    def data_manager(self):
        """Create a data manager instance for testing."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            manager = UnifiedDataManager()
            manager.api = Mock()
            manager.quote_breaker = Mock()
            manager.price_cache = Mock()
            manager.db = Mock()
            return manager
    
    def test_concurrent_price_requests(self, data_manager):
        """Test concurrent price requests."""
        # Setup mocks
        data_manager.price_cache.get.return_value = None
        mock_quote = Mock()
        mock_quote.bid_price = 149.50
        mock_quote.ask_price = 150.50
        data_manager.quote_breaker.call.return_value = mock_quote
        
        results = []
        errors = []
        
        def get_price(symbol):
            try:
                price = data_manager.get_latest_price(symbol)
                results.append(price)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=get_price, args=(f'STOCK{i}',))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0
        assert len(results) == 10
        assert all(price == 150.0 for price in results)  # Mid price
    
    def test_concurrent_indicator_calculations(self, data_manager):
        """Test concurrent indicator calculations."""
        data_manager.indicator_cache = Mock()
        data_manager.indicator_cache.get.return_value = None
        
        sample_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105]
        })
        
        config = {
            'indicators': {
                'EMA': 'True',
                'EMA_params': {'ema_period': 3}
            }
        }
        
        results = []
        errors = []
        
        def calculate_indicators():
            try:
                indicators = data_manager.calculate_indicators(sample_data, config)
                results.append(indicators)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=calculate_indicators)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0
        assert len(results) == 5


class TestErrorHandling:
    """Test error handling in various scenarios."""
    
    @pytest.fixture
    def data_manager(self):
        """Create a data manager instance for testing."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            manager = UnifiedDataManager()
            manager.api = Mock()
            manager.quote_breaker = Mock()
            manager.bars_breaker = Mock()
            manager.account_breaker = Mock()
            manager.price_cache = Mock()
            manager.db = Mock()
            return manager
    
    def test_get_latest_price_api_error(self, data_manager):
        """Test price retrieval with API error."""
        data_manager.price_cache.get.return_value = None
        data_manager.quote_breaker.call.side_effect = Exception("API Error")
        
        result = data_manager.get_latest_price('AAPL')
        
        assert result is None
    
    def test_get_historical_data_api_error(self, data_manager):
        """Test historical data retrieval with API error."""
        data_manager.db.get_historical_data.return_value = pd.DataFrame()
        data_manager.bars_breaker.call.side_effect = Exception("API Error")
        
        result = data_manager.get_historical_data('AAPL')
        
        assert result.empty
    
    def test_calculate_indicators_error(self, data_manager):
        """Test indicator calculation with error."""
        data_manager.indicator_cache.get.return_value = None
        
        # Create data that might cause calculation errors
        invalid_data = pd.DataFrame({
            'close': [np.nan, np.inf, -np.inf, 100, 101]
        })
        
        config = {
            'indicators': {
                'EMA': 'True',
                'EMA_params': {'ema_period': 3}
            }
        }
        
        # Should not raise exception
        result = data_manager.calculate_indicators(invalid_data, config)
        
        # Result might be empty or have some indicators
        assert isinstance(result, dict)
    
    def test_stream_worker_error_handling(self, data_manager):
        """Test stream worker error handling."""
        data_manager.get_latest_price = Mock(side_effect=Exception("Price error"))
        
        # Should handle errors gracefully
        with patch.object(data_manager, 'get_latest_price', side_effect=Exception("Price error")):
            result = data_manager.start_data_stream(['AAPL'], update_interval=0.01)
            
            assert result is True
            
            # Wait for potential errors to occur
            time.sleep(0.05)
            
            # Stop streaming
            data_manager.stop_data_stream()


class TestCleanup:
    """Test cleanup operations."""
    
    def test_cleanup_data_manager(self):
        """Test data manager cleanup."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager') as mock_cache, \
             patch('services.unified_data_manager.circuit_manager') as mock_circuit, \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            manager = UnifiedDataManager()
            manager.db = Mock()
            
            # Mock cleanup methods
            mock_cache.shutdown_all = Mock()
            mock_circuit.reset_all = Mock()
            
            manager.cleanup()
            
            mock_cache.shutdown_all.assert_called_once()
            mock_circuit.reset_all.assert_called_once()
            manager.db.close.assert_called_once()
    
    def test_cleanup_data_manager_singleton(self):
        """Test singleton data manager cleanup."""
        with patch('services.unified_data_manager.get_database'), \
             patch('services.unified_data_manager.cache_manager'), \
             patch('services.unified_data_manager.circuit_manager'), \
             patch('services.unified_data_manager.UnifiedDataManager.initialize_api', return_value=True):
            
            # Get singleton instance
            manager = get_data_manager()
            
            # Cleanup singleton
            with patch.object(manager, 'cleanup') as mock_cleanup:
                cleanup_data_manager()
                mock_cleanup.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__])