"""
Comprehensive pytest fixtures and configuration for trading bot tests.
Provides mock APIs, test data, and shared test utilities.
"""

import pytest
import pandas as pd
import numpy as np
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Any, Optional
import os
import sys
import sqlite3
from contextlib import contextmanager
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import project modules
from config.unified_config import TradingConfig
from trading_bot import TradingBot
from strategies.stoch_rsi_strategy import StochRSIStrategy
from strategies.ma_crossover_strategy import MACrossoverStrategy
from services.data_service import TradingDataService
from database.database_manager import DatabaseManager
from risk_management.enhanced_risk_manager import EnhancedRiskManager


# Test Configuration
@pytest.fixture(scope="session")
def test_config():
    """Test configuration with safe default values."""
    config_data = {
        "strategy": "StochRSI",
        "timeframe": "1Min",
        "candle_lookback_period": 100,
        "sleep_time_between_trades": 1,
        "max_trades_active": 3,
        "investment_amount": 10000,
        "trade_capital_percent": 2.0,
        "stop_loss": 5.0,
        "limit_price": 10.0,
        "extended_hours": False,
        "activate_trailing_stop_loss_at": 5.0,
        "indicators": {
            "stochRSI": {
                "enabled": True,
                "rsi_period": 14,
                "stoch_period": 14,
                "d_period": 3,
                "k_period": 3,
                "oversold": 20,
                "overbought": 80
            },
            "ema": {
                "enabled": True,
                "fast_period": 12,
                "slow_period": 26
            }
        },
        "risk_management": {
            "use_atr_position_sizing": True,
            "use_atr_stop_loss": True,
            "atr_period": 14,
            "atr_multiplier": 2.0,
            "max_daily_loss": 0.05,
            "max_position_size": 0.10,
            "max_positions": 5
        }
    }
    return TradingConfig(**config_data)


# Database Fixtures
@pytest.fixture(scope="function")
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_trading.db")
    
    yield db_path
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def db_manager(temp_db):
    """Database manager with temporary database."""
    manager = DatabaseManager(temp_db)
    yield manager
    manager.close()


@pytest.fixture(scope="function")
def test_database(temp_db):
    """Pre-populated test database with sample data."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Create and populate orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            ticker TEXT NOT NULL,
            type TEXT NOT NULL,
            buy_price REAL,
            sell_price REAL,
            highest_price REAL,
            quantity REAL NOT NULL,
            total REAL NOT NULL,
            acc_balance REAL,
            target_price REAL,
            stop_loss_price REAL,
            activate_trailing_stop_at REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sample orders data
    sample_orders = [
        ('2024-01-01 10:00:00', 'AAPL', 'buy', 150.00, None, 150.00, 10, 1500.00, 10000.00, 165.00, 142.50, 157.50),
        ('2024-01-01 11:00:00', 'AAPL', 'sell', 150.00, 160.00, 162.00, 10, 1600.00, 10100.00, None, None, None),
        ('2024-01-02 10:00:00', 'TSLA', 'buy', 200.00, None, 200.00, 5, 1000.00, 10100.00, 220.00, 190.00, 210.00),
    ]
    
    cursor.executemany('''
        INSERT INTO orders (time, ticker, type, buy_price, sell_price, highest_price, 
                           quantity, total, acc_balance, target_price, stop_loss_price, 
                           activate_trailing_stop_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_orders)
    
    # Create market_data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            open_price REAL NOT NULL,
            high_price REAL NOT NULL,
            low_price REAL NOT NULL,
            close_price REAL NOT NULL,
            volume INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    
    yield temp_db


# Mock API Fixtures
@pytest.fixture(scope="function")
def mock_alpaca_api():
    """Comprehensive mock Alpaca API for testing."""
    mock_api = Mock()
    
    # Mock account
    mock_account = Mock()
    mock_account.cash = 10000.0
    mock_account.equity = 12000.0
    mock_account.buying_power = 40000.0
    mock_api.get_account.return_value = mock_account
    
    # Mock clock
    mock_clock = Mock()
    mock_clock.is_open = True
    mock_clock.timestamp = datetime.now()
    mock_api.get_clock.return_value = mock_clock
    
    # Mock positions
    mock_position = Mock()
    mock_position.symbol = "AAPL"
    mock_position.qty = 10
    mock_position.avg_entry_price = 150.00
    mock_position.market_value = 1520.00
    mock_position.unrealized_pl = 20.00
    mock_position.client_order_id = "sl_142.50_tp_165.00"
    mock_api.list_positions.return_value = [mock_position]
    
    # Mock orders
    mock_order = Mock()
    mock_order.id = "order_123"
    mock_order.symbol = "AAPL"
    mock_order.qty = 10
    mock_order.side = "buy"
    mock_order.order_type = "market"
    mock_order.status = "filled"
    mock_order.filled_avg_price = 150.00
    mock_order.client_order_id = "sl_142.50_tp_165.00"
    
    mock_api.submit_order.return_value = mock_order
    mock_api.get_order_by_client_order_id.return_value = mock_order
    
    # Mock bars data
    mock_api.get_bars = Mock()
    
    return mock_api


@pytest.fixture(scope="function")
def mock_data_manager(mock_alpaca_api):
    """Mock data manager with Alpaca API."""
    manager = Mock()
    manager.api = mock_alpaca_api
    
    # Mock historical data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    base_price = 150.0
    
    historical_data = pd.DataFrame({
        'timestamp': dates,
        'open': base_price + np.random.randn(100) * 2,
        'high': base_price + np.random.randn(100) * 2 + 1,
        'low': base_price + np.random.randn(100) * 2 - 1,
        'close': base_price + np.random.randn(100) * 2,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    manager.get_historical_data.return_value = historical_data
    manager.get_latest_price.return_value = 152.50
    
    return manager


# Market Data Fixtures
@pytest.fixture(scope="function")
def sample_market_data():
    """Generate realistic market data for testing."""
    np.random.seed(42)  # For reproducible tests
    
    periods = 100
    dates = pd.date_range(start='2024-01-01 09:30:00', periods=periods, freq='1min')
    
    # Generate realistic OHLCV data
    base_price = 150.0
    returns = np.random.normal(0, 0.001, periods)  # 0.1% volatility
    
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Create OHLC from close prices
    opens = prices[:-1] + [prices[-1]]
    closes = prices
    
    highs = [max(o, c) + abs(np.random.normal(0, 0.002)) * c for o, c in zip(opens, closes)]
    lows = [min(o, c) - abs(np.random.normal(0, 0.002)) * c for o, c in zip(opens, closes)]
    volumes = np.random.randint(1000, 50000, periods)
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })


@pytest.fixture(scope="function")
def sample_ohlcv_data():
    """Sample OHLCV data with technical indicators."""
    df = sample_market_data()
    
    # Add technical indicators
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Moving averages
    df['EMA_12'] = df['close'].ewm(span=12).mean()
    df['EMA_26'] = df['close'].ewm(span=26).mean()
    
    # Volume indicators
    df['VWAP'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
    
    return df


# Strategy Fixtures
@pytest.fixture(scope="function")
def stoch_rsi_strategy(test_config):
    """StochRSI strategy instance for testing."""
    return StochRSIStrategy(test_config)


@pytest.fixture(scope="function")
def ma_crossover_strategy(test_config):
    """MA Crossover strategy instance for testing."""
    return MACrossoverStrategy(test_config)


# Trading Bot Fixtures
@pytest.fixture(scope="function")
def trading_bot(mock_data_manager, stoch_rsi_strategy):
    """Trading bot instance with mocked dependencies."""
    bot = TradingBot(mock_data_manager, stoch_rsi_strategy)
    bot.enable_enhanced_risk_management = False  # Disable for unit tests
    return bot


@pytest.fixture(scope="function")
def trading_bot_with_risk(mock_data_manager, stoch_rsi_strategy):
    """Trading bot with enhanced risk management enabled."""
    bot = TradingBot(mock_data_manager, stoch_rsi_strategy)
    bot.enable_enhanced_risk_management = True
    return bot


# Risk Management Fixtures
@pytest.fixture(scope="function")
def mock_risk_manager():
    """Mock enhanced risk manager."""
    risk_manager = Mock(spec=EnhancedRiskManager)
    
    # Mock risk validation result
    from risk_management.enhanced_risk_manager import RiskValidationResult
    
    validation_result = RiskValidationResult(
        approved=True,
        confidence_score=0.85,
        risk_score=25.0,
        position_size_adjustment=None,
        violations=[],
        warnings=[],
        recommendations=["Position size within acceptable range"]
    )
    
    risk_manager.validate_position_size.return_value = validation_result
    risk_manager.calculate_optimal_position_size.return_value = Mock(
        risk_adjusted_size=0.05,
        confidence_score=0.85
    )
    
    return risk_manager


# Async Fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# File System Fixtures
@pytest.fixture(scope="function")
def temp_directory():
    """Temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture(scope="function")
def mock_file_system(temp_directory):
    """Mock file system with test files."""
    # Create AUTH directory and files
    auth_dir = os.path.join(temp_directory, "AUTH")
    os.makedirs(auth_dir)
    
    # Create Tickers.txt
    with open(os.path.join(auth_dir, "Tickers.txt"), "w") as f:
        f.write("AAPL TSLA GOOGL MSFT AMZN")
    
    # Create ORDERS directory
    orders_dir = os.path.join(temp_directory, "ORDERS")
    os.makedirs(orders_dir)
    
    return temp_directory


# Performance Testing Fixtures
@pytest.fixture(scope="function")
def performance_timer():
    """Timer fixture for performance testing."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.perf_counter()
        
        def stop(self):
            self.end_time = time.perf_counter()
            return self.end_time - self.start_time
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Logging Fixtures
@pytest.fixture(scope="function")
def capture_logs():
    """Capture logs during testing."""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    
    yield log_capture
    
    # Cleanup
    root_logger.removeHandler(handler)


# Parameterized Test Data
@pytest.fixture(params=["AAPL", "TSLA", "GOOGL", "MSFT"])
def test_ticker(request):
    """Parameterized ticker symbols for testing."""
    return request.param


@pytest.fixture(params=["1Min", "5Min", "15Min", "1Hour"])
def test_timeframe(request):
    """Parameterized timeframes for testing."""
    return request.param


@pytest.fixture(params=[
    {"rsi_period": 14, "oversold": 20, "overbought": 80},
    {"rsi_period": 21, "oversold": 30, "overbought": 70},
    {"rsi_period": 7, "oversold": 15, "overbought": 85}
])
def test_indicator_params(request):
    """Parameterized indicator parameters."""
    return request.param


# Cleanup and Utilities
@pytest.fixture(autouse=True)
def cleanup_files():
    """Automatically cleanup test files after each test."""
    yield
    
    # Clean up any test files that might have been created
    test_files = [
        "test_orders.csv",
        "test_positions.csv", 
        "test_config.json",
        "test_trading.db"
    ]
    
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)


@contextmanager
def not_raises(exception):
    """Context manager to assert that an exception is NOT raised."""
    try:
        yield
    except exception:
        raise pytest.fail(f"DID RAISE {exception}")


# Helper Functions
def create_mock_bar_data(symbol: str, start_date: str, periods: int = 100):
    """Create mock bar data for testing."""
    dates = pd.date_range(start=start_date, periods=periods, freq='1min')
    base_price = {"AAPL": 150.0, "TSLA": 200.0, "GOOGL": 2500.0}.get(symbol, 100.0)
    
    np.random.seed(hash(symbol) % 2**32)  # Deterministic but different per symbol
    
    prices = [base_price]
    for _ in range(periods - 1):
        change = np.random.normal(0, 0.01)  # 1% volatility
        prices.append(prices[-1] * (1 + change))
    
    return pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        'close': prices,
        'volume': np.random.randint(1000, 100000, periods)
    })


# Integration Test Fixtures
@pytest.fixture(scope="function")
def integration_test_setup(temp_db, test_config):
    """Setup for integration tests with real components."""
    
    # Create data service with temporary database
    data_service = TradingDataService()
    data_service.db_manager.db_path = temp_db
    
    # Create strategy
    strategy = StochRSIStrategy(test_config)
    
    # Mock the Alpaca API
    with patch('trading_bot.TradingBot.__init__') as mock_init:
        mock_init.return_value = None
        bot = TradingBot.__new__(TradingBot)
        bot.data_manager = mock_data_manager(mock_alpaca_api())
        bot.strategy = strategy
        bot.api = bot.data_manager.api
        bot.tickers = ["AAPL", "TSLA"]
        bot.enable_enhanced_risk_management = False
        
        yield {
            'bot': bot,
            'data_service': data_service,
            'strategy': strategy,
            'config': test_config
        }


# Test session configuration
def pytest_configure(config):
    """Configure pytest session."""
    # Create reports directory
    reports_dir = "tests/reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    # Set up test logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add automatic markers."""
    for item in items:
        # Add slow marker for tests taking longer than 5 seconds
        if "slow" not in [marker.name for marker in item.iter_markers()]:
            if hasattr(item, 'function') and getattr(item.function, '__name__', '').startswith('test_performance'):
                item.add_marker(pytest.mark.slow)
        
        # Add integration marker for integration tests
        if "integration" not in [marker.name for marker in item.iter_markers()]:
            if "integration" in str(item.fspath).lower():
                item.add_marker(pytest.mark.integration)


# Session fixtures for one-time setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment at session start."""
    # Ensure test directories exist
    test_dirs = ["tests/reports", "tests/fixtures", "tests/data"]
    for dir_path in test_dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    yield
    
    # Session cleanup
    print("\nTest session completed.")