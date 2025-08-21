"""
Comprehensive mock implementation of Alpaca API for testing.
Provides realistic behavior for all trading operations.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass
from enum import Enum
import uuid
import time


class OrderStatus(Enum):
    """Order status enumeration."""
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    DONE_FOR_DAY = "done_for_day"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REPLACED = "replaced"
    PENDING_CANCEL = "pending_cancel"
    PENDING_REPLACE = "pending_replace"
    ACCEPTED = "accepted"
    PENDING_NEW = "pending_new"
    ACCEPTED_FOR_BIDDING = "accepted_for_bidding"
    STOPPED = "stopped"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    CALCULATED = "calculated"


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class TimeInForce(Enum):
    """Time in force enumeration."""
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"
    EXT = "ext"


@dataclass
class MockAccount:
    """Mock account object."""
    id: str
    account_number: str
    status: str
    currency: str
    cash: float
    portfolio_value: float
    equity: float
    last_equity: float
    buying_power: float
    initial_margin: float
    maintenance_margin: float
    sma: float
    day_trade_count: int
    daytrade_buying_power: float
    regt_buying_power: float
    created_at: datetime
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', str(uuid.uuid4()))
        self.account_number = kwargs.get('account_number', '123456789')
        self.status = kwargs.get('status', 'ACTIVE')
        self.currency = kwargs.get('currency', 'USD')
        self.cash = kwargs.get('cash', 100000.0)
        self.portfolio_value = kwargs.get('portfolio_value', 100000.0)
        self.equity = kwargs.get('equity', 100000.0)
        self.last_equity = kwargs.get('last_equity', 100000.0)
        self.buying_power = kwargs.get('buying_power', 400000.0)
        self.initial_margin = kwargs.get('initial_margin', 0.0)
        self.maintenance_margin = kwargs.get('maintenance_margin', 0.0)
        self.sma = kwargs.get('sma', 0.0)
        self.day_trade_count = kwargs.get('day_trade_count', 0)
        self.daytrade_buying_power = kwargs.get('daytrade_buying_power', 400000.0)
        self.regt_buying_power = kwargs.get('regt_buying_power', 200000.0)
        self.created_at = kwargs.get('created_at', datetime.now())


@dataclass
class MockClock:
    """Mock market clock object."""
    timestamp: datetime
    is_open: bool
    next_open: datetime
    next_close: datetime
    
    def __init__(self, **kwargs):
        now = datetime.now()
        self.timestamp = kwargs.get('timestamp', now)
        
        # Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
        current_hour = now.hour
        current_weekday = now.weekday()
        
        # Default to market open during weekdays 9:30-16:00
        self.is_open = kwargs.get('is_open', 
            current_weekday < 5 and 9.5 <= current_hour < 16)
        
        # Calculate next open/close
        if self.is_open:
            self.next_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
            self.next_open = None
        else:
            if current_weekday >= 5 or current_hour >= 16:
                # Weekend or after hours - next open is Monday 9:30
                days_ahead = 7 - current_weekday if current_weekday >= 5 else 1
                self.next_open = (now + timedelta(days=days_ahead)).replace(
                    hour=9, minute=30, second=0, microsecond=0)
            else:
                # Before market open
                self.next_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            self.next_close = None


@dataclass
class MockPosition:
    """Mock position object."""
    asset_id: str
    symbol: str
    exchange: str
    asset_class: str
    avg_entry_price: float
    qty: float
    side: str
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_plpc: float
    unrealized_intraday_pl: float
    unrealized_intraday_plpc: float
    current_price: float
    lastday_price: float
    change_today: float
    client_order_id: Optional[str] = None
    
    def __init__(self, **kwargs):
        self.asset_id = kwargs.get('asset_id', str(uuid.uuid4()))
        self.symbol = kwargs.get('symbol', 'AAPL')
        self.exchange = kwargs.get('exchange', 'NASDAQ')
        self.asset_class = kwargs.get('asset_class', 'us_equity')
        self.qty = kwargs.get('qty', 10)
        self.avg_entry_price = kwargs.get('avg_entry_price', 150.0)
        self.side = "long" if self.qty > 0 else "short"
        self.current_price = kwargs.get('current_price', 152.0)
        self.market_value = self.qty * self.current_price
        self.cost_basis = self.qty * self.avg_entry_price
        self.unrealized_pl = self.market_value - self.cost_basis
        self.unrealized_plpc = (self.unrealized_pl / self.cost_basis) * 100
        self.unrealized_intraday_pl = kwargs.get('unrealized_intraday_pl', 0.0)
        self.unrealized_intraday_plpc = kwargs.get('unrealized_intraday_plpc', 0.0)
        self.lastday_price = kwargs.get('lastday_price', 151.0)
        self.change_today = ((self.current_price - self.lastday_price) / self.lastday_price) * 100
        self.client_order_id = kwargs.get('client_order_id')


@dataclass
class MockOrder:
    """Mock order object."""
    id: str
    client_order_id: str
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime
    filled_at: Optional[datetime]
    expired_at: Optional[datetime]
    canceled_at: Optional[datetime]
    failed_at: Optional[datetime]
    asset_id: str
    symbol: str
    asset_class: str
    qty: float
    filled_qty: float
    type: str
    side: str
    time_in_force: str
    limit_price: Optional[float]
    stop_price: Optional[float]
    status: str
    extended_hours: bool
    legs: Optional[List[Any]]
    trail_price: Optional[float]
    trail_percent: Optional[float]
    hwm: Optional[float]
    filled_avg_price: Optional[float]
    
    def __init__(self, **kwargs):
        now = datetime.now()
        self.id = kwargs.get('id', str(uuid.uuid4()))
        self.client_order_id = kwargs.get('client_order_id', f"order_{int(time.time())}")
        self.created_at = kwargs.get('created_at', now)
        self.updated_at = kwargs.get('updated_at', now)
        self.submitted_at = kwargs.get('submitted_at', now)
        self.filled_at = kwargs.get('filled_at')
        self.expired_at = kwargs.get('expired_at')
        self.canceled_at = kwargs.get('canceled_at')
        self.failed_at = kwargs.get('failed_at')
        self.asset_id = kwargs.get('asset_id', str(uuid.uuid4()))
        self.symbol = kwargs.get('symbol', 'AAPL')
        self.asset_class = kwargs.get('asset_class', 'us_equity')
        self.qty = kwargs.get('qty', 10)
        self.filled_qty = kwargs.get('filled_qty', 0)
        self.type = kwargs.get('type', 'market')
        self.side = kwargs.get('side', 'buy')
        self.time_in_force = kwargs.get('time_in_force', 'day')
        self.limit_price = kwargs.get('limit_price')
        self.stop_price = kwargs.get('stop_price')
        self.status = kwargs.get('status', 'new')
        self.extended_hours = kwargs.get('extended_hours', False)
        self.legs = kwargs.get('legs')
        self.trail_price = kwargs.get('trail_price')
        self.trail_percent = kwargs.get('trail_percent')
        self.hwm = kwargs.get('hwm')
        self.filled_avg_price = kwargs.get('filled_avg_price')


class MockAlpacaAPI:
    """
    Comprehensive mock of Alpaca Trading API.
    Simulates realistic trading behavior for testing.
    """
    
    def __init__(self, **kwargs):
        """Initialize mock API with default values."""
        self.base_url = kwargs.get('base_url', 'https://paper-api.alpaca.markets')
        self.api_key = kwargs.get('api_key', 'test_key')
        self.secret_key = kwargs.get('secret_key', 'test_secret')
        
        # Internal state
        self._account = MockAccount(**kwargs.get('account', {}))
        self._positions = {}
        self._orders = {}
        self._order_counter = 0
        self._market_data = {}
        self._is_market_open = kwargs.get('market_open', True)
        
        # Price simulation
        self._price_data = self._generate_initial_prices()
        
        # Initialize with some default positions if specified
        default_positions = kwargs.get('positions', [])
        for pos_data in default_positions:
            position = MockPosition(**pos_data)
            self._positions[position.symbol] = position
    
    def _generate_initial_prices(self) -> Dict[str, float]:
        """Generate initial price data for common symbols."""
        symbols = ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN', 'META', 'NVDA', 'SPY', 'QQQ']
        base_prices = [150.0, 200.0, 2500.0, 300.0, 3000.0, 250.0, 400.0, 420.0, 350.0]
        
        return dict(zip(symbols, base_prices))
    
    def _simulate_price_movement(self, symbol: str, volatility: float = 0.01) -> float:
        """Simulate realistic price movement."""
        if symbol not in self._price_data:
            self._price_data[symbol] = 100.0
        
        current_price = self._price_data[symbol]
        change = np.random.normal(0, volatility)
        new_price = current_price * (1 + change)
        self._price_data[symbol] = max(new_price, 0.01)  # Prevent negative prices
        
        return self._price_data[symbol]
    
    def get_account(self) -> MockAccount:
        """Get account information."""
        # Update account values based on positions
        total_market_value = sum(pos.market_value for pos in self._positions.values())
        self._account.equity = self._account.cash + total_market_value
        self._account.portfolio_value = self._account.equity
        
        return self._account
    
    def get_clock(self) -> MockClock:
        """Get market clock information."""
        return MockClock(is_open=self._is_market_open)
    
    def list_positions(self) -> List[MockPosition]:
        """List all open positions."""
        # Update position prices
        for symbol, position in self._positions.items():
            new_price = self._simulate_price_movement(symbol)
            position.current_price = new_price
            position.market_value = position.qty * new_price
            position.unrealized_pl = position.market_value - position.cost_basis
            position.unrealized_plpc = (position.unrealized_pl / position.cost_basis) * 100
        
        return list(self._positions.values())
    
    def get_position(self, symbol: str) -> Optional[MockPosition]:
        """Get position for a specific symbol."""
        return self._positions.get(symbol)
    
    def submit_order(self, symbol: str, qty: float, side: str, type: str = "market", 
                    time_in_force: str = "day", limit_price: Optional[float] = None,
                    stop_price: Optional[float] = None, client_order_id: Optional[str] = None,
                    extended_hours: bool = False, **kwargs) -> MockOrder:
        """Submit a new order."""
        self._order_counter += 1
        
        # Generate order ID and client order ID
        order_id = f"order_{self._order_counter}_{int(time.time())}"
        if not client_order_id:
            client_order_id = f"client_order_{self._order_counter}"
        
        # Create order
        order = MockOrder(
            id=order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            qty=qty,
            side=side,
            type=type,
            time_in_force=time_in_force,
            limit_price=limit_price,
            stop_price=stop_price,
            extended_hours=extended_hours,
            status=OrderStatus.NEW.value
        )
        
        # Store order
        self._orders[order_id] = order
        
        # Simulate order execution for market orders
        if type == "market" and self._is_market_open:
            self._execute_order(order)
        
        return order
    
    def _execute_order(self, order: MockOrder) -> None:
        """Simulate order execution."""
        current_price = self._simulate_price_movement(order.symbol)
        
        # Add some slippage for market orders
        if order.type == "market":
            slippage = np.random.normal(0, 0.001)  # 0.1% slippage
            execution_price = current_price * (1 + slippage)
        else:
            execution_price = order.limit_price or current_price
        
        # Update order
        order.status = OrderStatus.FILLED.value
        order.filled_qty = order.qty
        order.filled_avg_price = execution_price
        order.filled_at = datetime.now()
        order.updated_at = datetime.now()
        
        # Update positions
        if order.side == "buy":
            self._add_to_position(order.symbol, order.qty, execution_price, order.client_order_id)
            # Deduct cash
            self._account.cash -= order.qty * execution_price
        elif order.side == "sell":
            self._reduce_position(order.symbol, order.qty, execution_price)
            # Add cash
            self._account.cash += order.qty * execution_price
    
    def _add_to_position(self, symbol: str, qty: float, price: float, client_order_id: str) -> None:
        """Add to or create a position."""
        if symbol in self._positions:
            position = self._positions[symbol]
            # Calculate new average price
            total_cost = (position.qty * position.avg_entry_price) + (qty * price)
            total_qty = position.qty + qty
            position.avg_entry_price = total_cost / total_qty
            position.qty = total_qty
            position.cost_basis = total_cost
        else:
            # Create new position
            self._positions[symbol] = MockPosition(
                symbol=symbol,
                qty=qty,
                avg_entry_price=price,
                current_price=price,
                client_order_id=client_order_id
            )
    
    def _reduce_position(self, symbol: str, qty: float, price: float) -> None:
        """Reduce or close a position."""
        if symbol in self._positions:
            position = self._positions[symbol]
            if qty >= position.qty:
                # Close entire position
                del self._positions[symbol]
            else:
                # Partial close
                position.qty -= qty
                position.cost_basis = position.qty * position.avg_entry_price
    
    def get_order(self, order_id: str) -> Optional[MockOrder]:
        """Get order by ID."""
        return self._orders.get(order_id)
    
    def get_order_by_client_order_id(self, client_order_id: str) -> Optional[MockOrder]:
        """Get order by client order ID."""
        for order in self._orders.values():
            if order.client_order_id == client_order_id:
                return order
        return None
    
    def list_orders(self, status: str = "all", limit: int = 500, 
                   after: Optional[datetime] = None, until: Optional[datetime] = None,
                   direction: str = "desc", nested: bool = True, 
                   symbols: Optional[str] = None) -> List[MockOrder]:
        """List orders with optional filtering."""
        orders = list(self._orders.values())
        
        # Filter by status
        if status != "all":
            orders = [o for o in orders if o.status == status]
        
        # Filter by symbols
        if symbols:
            symbol_list = symbols.split(',') if isinstance(symbols, str) else symbols
            orders = [o for o in orders if o.symbol in symbol_list]
        
        # Filter by date range
        if after:
            orders = [o for o in orders if o.created_at >= after]
        if until:
            orders = [o for o in orders if o.created_at <= until]
        
        # Sort by creation time
        orders.sort(key=lambda x: x.created_at, reverse=(direction == "desc"))
        
        # Apply limit
        return orders[:limit]
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if order_id in self._orders:
            order = self._orders[order_id]
            if order.status in [OrderStatus.NEW.value, OrderStatus.PARTIALLY_FILLED.value]:
                order.status = OrderStatus.CANCELED.value
                order.canceled_at = datetime.now()
                order.updated_at = datetime.now()
                return True
        return False
    
    def cancel_all_orders(self) -> List[str]:
        """Cancel all open orders."""
        canceled_orders = []
        for order_id, order in self._orders.items():
            if order.status in [OrderStatus.NEW.value, OrderStatus.PARTIALLY_FILLED.value]:
                if self.cancel_order(order_id):
                    canceled_orders.append(order_id)
        return canceled_orders
    
    def get_bars(self, symbol: str, timeframe: str = "1Min", start: Optional[datetime] = None,
                end: Optional[datetime] = None, limit: int = 1000, **kwargs) -> pd.DataFrame:
        """Get historical bar data."""
        # Generate realistic OHLCV data
        if not start:
            start = datetime.now() - timedelta(days=30)
        if not end:
            end = datetime.now()
        
        # Create date range based on timeframe
        if timeframe == "1Min":
            freq = "1min"
        elif timeframe == "5Min":
            freq = "5min"
        elif timeframe == "15Min":
            freq = "15min"
        elif timeframe == "1Hour":
            freq = "1H"
        elif timeframe == "1Day":
            freq = "1D"
        else:
            freq = "1min"
        
        dates = pd.date_range(start=start, end=end, freq=freq)[:limit]
        
        # Generate price data
        base_price = self._price_data.get(symbol, 100.0)
        np.random.seed(hash(symbol) % 2**32)  # Deterministic but different per symbol
        
        prices = [base_price]
        for _ in range(len(dates) - 1):
            change = np.random.normal(0, 0.01)  # 1% volatility
            prices.append(max(prices[-1] * (1 + change), 0.01))
        
        # Create OHLC data
        ohlc_data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.005)))
            low = price * (1 - abs(np.random.normal(0, 0.005)))
            ohlc_data.append({
                'timestamp': dates[i],
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': np.random.randint(1000, 100000)
            })
        
        return pd.DataFrame(ohlc_data)
    
    def get_latest_bar(self, symbol: str) -> Dict[str, Any]:
        """Get the latest bar for a symbol."""
        current_price = self._simulate_price_movement(symbol)
        
        return {
            'timestamp': datetime.now(),
            'open': current_price * 0.999,
            'high': current_price * 1.002,
            'low': current_price * 0.998,
            'close': current_price,
            'volume': np.random.randint(1000, 10000)
        }
    
    def get_snapshot(self, symbol: str) -> Dict[str, Any]:
        """Get market snapshot for a symbol."""
        current_price = self._simulate_price_movement(symbol)
        
        return {
            'symbol': symbol,
            'latest_quote': {
                'bid': current_price * 0.999,
                'ask': current_price * 1.001,
                'bid_size': np.random.randint(100, 1000),
                'ask_size': np.random.randint(100, 1000),
                'timestamp': datetime.now()
            },
            'latest_trade': {
                'price': current_price,
                'size': np.random.randint(100, 1000),
                'timestamp': datetime.now()
            },
            'minute_bar': self.get_latest_bar(symbol),
            'daily_bar': self.get_latest_bar(symbol),
            'prev_daily_bar': {
                'open': current_price * 0.995,
                'high': current_price * 1.005,
                'low': current_price * 0.99,
                'close': current_price * 0.998,
                'volume': np.random.randint(100000, 1000000)
            }
        }
    
    # Utility methods for testing
    def set_market_open(self, is_open: bool) -> None:
        """Set market open status."""
        self._is_market_open = is_open
    
    def set_account_cash(self, cash: float) -> None:
        """Set account cash balance."""
        self._account.cash = cash
    
    def set_symbol_price(self, symbol: str, price: float) -> None:
        """Set current price for a symbol."""
        self._price_data[symbol] = price
    
    def add_test_position(self, symbol: str, qty: float, avg_price: float) -> None:
        """Add a test position."""
        self._positions[symbol] = MockPosition(
            symbol=symbol,
            qty=qty,
            avg_entry_price=avg_price,
            current_price=avg_price
        )
    
    def clear_all_positions(self) -> None:
        """Clear all positions."""
        self._positions.clear()
    
    def clear_all_orders(self) -> None:
        """Clear all orders."""
        self._orders.clear()
        self._order_counter = 0
    
    def get_order_count(self) -> int:
        """Get total number of orders."""
        return len(self._orders)
    
    def get_position_count(self) -> int:
        """Get total number of positions."""
        return len(self._positions)


def create_mock_alpaca_api(**kwargs) -> MockAlpacaAPI:
    """Factory function to create mock Alpaca API."""
    return MockAlpacaAPI(**kwargs)


def create_realistic_market_scenario() -> MockAlpacaAPI:
    """Create a realistic market scenario for testing."""
    api = MockAlpacaAPI(
        market_open=True,
        account={
            'cash': 50000.0,
            'equity': 75000.0,
            'buying_power': 200000.0
        },
        positions=[
            {
                'symbol': 'AAPL',
                'qty': 100,
                'avg_entry_price': 150.0,
                'current_price': 152.0
            },
            {
                'symbol': 'TSLA', 
                'qty': 50,
                'avg_entry_price': 200.0,
                'current_price': 195.0
            }
        ]
    )
    return api


def create_empty_account_scenario() -> MockAlpacaAPI:
    """Create scenario with empty account for testing new trades."""
    return MockAlpacaAPI(
        market_open=True,
        account={
            'cash': 100000.0,
            'equity': 100000.0,
            'buying_power': 400000.0
        }
    )


def create_market_closed_scenario() -> MockAlpacaAPI:
    """Create scenario with market closed."""
    return MockAlpacaAPI(
        market_open=False,
        account={
            'cash': 50000.0,
            'equity': 50000.0,
            'buying_power': 200000.0
        }
    )