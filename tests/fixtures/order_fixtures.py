"""
Order and position fixtures for testing trading operations.
Provides realistic order data and trading scenarios.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json


@dataclass
class OrderFixture:
    """Order fixture data structure."""
    id: Optional[str] = None
    time: str = ""
    ticker: str = ""
    type: str = ""  # buy/sell
    buy_price: Optional[float] = None
    sell_price: Optional[float] = None
    highest_price: Optional[float] = None
    quantity: float = 0
    total: float = 0
    acc_balance: float = 0
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    activate_trailing_stop_at: Optional[float] = None
    client_order_id: Optional[str] = None
    status: str = "filled"
    fees: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PositionFixture:
    """Position fixture data structure."""
    symbol: str = ""
    qty: float = 0
    avg_entry_price: float = 0
    current_price: float = 0
    market_value: float = 0
    unrealized_pl: float = 0
    unrealized_plpc: float = 0
    cost_basis: float = 0
    side: str = "long"
    client_order_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class OrderGenerator:
    """Generate realistic order data for testing."""
    
    def __init__(self, seed: int = 42):
        """Initialize with random seed."""
        np.random.seed(seed)
        self.order_counter = 0
    
    def generate_buy_order(self, 
                          ticker: str = "AAPL",
                          price: float = 150.0,
                          quantity: float = 10,
                          account_balance: float = 50000.0,
                          timestamp: Optional[datetime] = None) -> OrderFixture:
        """Generate a buy order fixture."""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.order_counter += 1
        
        # Calculate derived values
        total = price * quantity
        stop_loss_price = price * 0.95  # 5% stop loss
        target_price = price * 1.10     # 10% target
        trailing_stop_at = price * 1.05 # 5% for trailing stop activation
        
        return OrderFixture(
            id=f"order_{self.order_counter}",
            time=timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            ticker=ticker,
            type="buy",
            buy_price=price,
            sell_price=None,
            highest_price=price,
            quantity=quantity,
            total=total,
            acc_balance=account_balance - total,
            target_price=target_price,
            stop_loss_price=stop_loss_price,
            activate_trailing_stop_at=trailing_stop_at,
            client_order_id=f"sl_{stop_loss_price:.2f}_tp_{target_price:.2f}",
            status="filled",
            fees=1.0  # $1 commission
        )
    
    def generate_sell_order(self,
                           buy_order: OrderFixture,
                           sell_price: float,
                           reason: str = "target_price",
                           timestamp: Optional[datetime] = None) -> OrderFixture:
        """Generate a sell order from a buy order."""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.order_counter += 1
        
        # Calculate P&L
        total = sell_price * buy_order.quantity
        pnl = (sell_price - buy_order.buy_price) * buy_order.quantity
        
        return OrderFixture(
            id=f"order_{self.order_counter}",
            time=timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            ticker=buy_order.ticker,
            type="sell",
            buy_price=buy_order.buy_price,
            sell_price=sell_price,
            highest_price=max(buy_order.highest_price or buy_order.buy_price, sell_price),
            quantity=buy_order.quantity,
            total=total,
            acc_balance=buy_order.acc_balance + total,
            target_price=None,
            stop_loss_price=None,
            activate_trailing_stop_at=None,
            client_order_id=f"sell_{reason}_{buy_order.ticker}",
            status="filled",
            fees=1.0
        )
    
    def generate_trading_session(self,
                                tickers: List[str],
                                num_trades: int = 10,
                                start_balance: float = 100000.0,
                                start_date: Optional[datetime] = None) -> List[OrderFixture]:
        """Generate a complete trading session with multiple orders."""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=1)
        
        orders = []
        current_balance = start_balance
        current_time = start_date
        open_positions = {}
        
        for i in range(num_trades):
            # Randomly choose to open new position or close existing
            if open_positions and np.random.random() < 0.4:
                # Close existing position (40% chance)
                ticker = np.random.choice(list(open_positions.keys()))
                buy_order = open_positions[ticker]
                
                # Random sell price around current price
                price_change = np.random.normal(0, 0.02)  # 2% volatility
                sell_price = buy_order.buy_price * (1 + price_change)
                
                # Determine sell reason
                if sell_price >= buy_order.target_price:
                    reason = "target_price"
                elif sell_price <= buy_order.stop_loss_price:
                    reason = "stop_loss"
                else:
                    reason = "manual"
                
                sell_order = self.generate_sell_order(
                    buy_order, sell_price, reason, current_time
                )
                orders.append(sell_order)
                current_balance = sell_order.acc_balance
                del open_positions[ticker]
                
            else:
                # Open new position
                ticker = np.random.choice(tickers)
                if ticker not in open_positions:  # Don't double up
                    # Random price and quantity
                    base_price = {"AAPL": 150, "TSLA": 200, "GOOGL": 2500, "MSFT": 300}.get(ticker, 100)
                    price = base_price * (1 + np.random.normal(0, 0.05))
                    
                    # Position size based on account balance (1-5%)
                    position_value = current_balance * np.random.uniform(0.01, 0.05)
                    quantity = int(position_value / price)
                    
                    if quantity > 0 and current_balance > position_value:
                        buy_order = self.generate_buy_order(
                            ticker, price, quantity, current_balance, current_time
                        )
                        orders.append(buy_order)
                        current_balance = buy_order.acc_balance
                        open_positions[ticker] = buy_order
            
            # Advance time
            current_time += timedelta(minutes=np.random.randint(30, 120))
        
        return orders
    
    def generate_profitable_trade_sequence(self, 
                                         ticker: str = "AAPL",
                                         num_trades: int = 5) -> List[OrderFixture]:
        """Generate a sequence of profitable trades."""
        orders = []
        current_balance = 50000.0
        base_price = 150.0
        
        for i in range(num_trades):
            # Each trade is profitable
            buy_price = base_price * (1 + np.random.uniform(-0.02, 0.02))
            sell_price = buy_price * (1 + np.random.uniform(0.05, 0.15))  # 5-15% profit
            
            quantity = 10
            timestamp = datetime.now() - timedelta(hours=num_trades-i)
            
            buy_order = self.generate_buy_order(
                ticker, buy_price, quantity, current_balance, timestamp
            )
            orders.append(buy_order)
            
            sell_order = self.generate_sell_order(
                buy_order, sell_price, "target_price", 
                timestamp + timedelta(minutes=30)
            )
            orders.append(sell_order)
            
            current_balance = sell_order.acc_balance
            base_price = sell_price  # Trending up
        
        return orders
    
    def generate_losing_trade_sequence(self,
                                     ticker: str = "AAPL", 
                                     num_trades: int = 5) -> List[OrderFixture]:
        """Generate a sequence of losing trades."""
        orders = []
        current_balance = 50000.0
        base_price = 150.0
        
        for i in range(num_trades):
            # Each trade is a loss
            buy_price = base_price * (1 + np.random.uniform(-0.02, 0.02))
            sell_price = buy_price * (1 - np.random.uniform(0.03, 0.08))  # 3-8% loss
            
            quantity = 10
            timestamp = datetime.now() - timedelta(hours=num_trades-i)
            
            buy_order = self.generate_buy_order(
                ticker, buy_price, quantity, current_balance, timestamp
            )
            orders.append(buy_order)
            
            sell_order = self.generate_sell_order(
                buy_order, sell_price, "stop_loss",
                timestamp + timedelta(minutes=30)
            )
            orders.append(sell_order)
            
            current_balance = sell_order.acc_balance
            base_price = sell_price  # Trending down
        
        return orders


class PositionGenerator:
    """Generate realistic position data for testing."""
    
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
    
    def generate_position(self,
                         symbol: str = "AAPL",
                         entry_price: float = 150.0,
                         quantity: float = 10,
                         current_price: Optional[float] = None) -> PositionFixture:
        """Generate a position fixture."""
        if current_price is None:
            # Random price movement
            price_change = np.random.normal(0, 0.02)  # 2% volatility
            current_price = entry_price * (1 + price_change)
        
        market_value = current_price * quantity
        cost_basis = entry_price * quantity
        unrealized_pl = market_value - cost_basis
        unrealized_plpc = (unrealized_pl / cost_basis) * 100 if cost_basis > 0 else 0
        
        return PositionFixture(
            symbol=symbol,
            qty=quantity,
            avg_entry_price=entry_price,
            current_price=current_price,
            market_value=market_value,
            unrealized_pl=unrealized_pl,
            unrealized_plpc=unrealized_plpc,
            cost_basis=cost_basis,
            side="long" if quantity > 0 else "short",
            client_order_id=f"pos_{symbol}_{int(entry_price)}"
        )
    
    def generate_portfolio(self,
                          symbols: List[str],
                          total_value: float = 100000.0) -> List[PositionFixture]:
        """Generate a diversified portfolio of positions."""
        positions = []
        
        for symbol in symbols:
            # Allocate random portion of portfolio to each symbol
            allocation = np.random.uniform(0.1, 0.3)  # 10-30% per position
            position_value = total_value * allocation
            
            # Random entry price
            base_price = {"AAPL": 150, "TSLA": 200, "GOOGL": 2500, "MSFT": 300}.get(symbol, 100)
            entry_price = base_price * (1 + np.random.uniform(-0.1, 0.1))
            
            quantity = position_value / entry_price
            
            position = self.generate_position(symbol, entry_price, quantity)
            positions.append(position)
        
        return positions
    
    def generate_winning_positions(self, symbols: List[str]) -> List[PositionFixture]:
        """Generate positions that are currently profitable."""
        positions = []
        
        for symbol in symbols:
            base_price = {"AAPL": 150, "TSLA": 200, "GOOGL": 2500, "MSFT": 300}.get(symbol, 100)
            entry_price = base_price
            current_price = entry_price * (1 + np.random.uniform(0.05, 0.20))  # 5-20% gains
            
            position = self.generate_position(symbol, entry_price, 10, current_price)
            positions.append(position)
        
        return positions
    
    def generate_losing_positions(self, symbols: List[str]) -> List[PositionFixture]:
        """Generate positions that are currently at a loss."""
        positions = []
        
        for symbol in symbols:
            base_price = {"AAPL": 150, "TSLA": 200, "GOOGL": 2500, "MSFT": 300}.get(symbol, 100)
            entry_price = base_price
            current_price = entry_price * (1 - np.random.uniform(0.05, 0.15))  # 5-15% losses
            
            position = self.generate_position(symbol, entry_price, 10, current_price)
            positions.append(position)
        
        return positions


class ScenarioFixtures:
    """Pre-built trading scenarios for testing."""
    
    def __init__(self):
        self.order_gen = OrderGenerator()
        self.position_gen = PositionGenerator()
    
    def day_trader_scenario(self) -> Dict[str, Any]:
        """Day trading scenario with multiple quick trades."""
        tickers = ["AAPL", "TSLA", "MSFT"]
        orders = []
        
        # Generate rapid buy/sell cycles
        for ticker in tickers:
            for i in range(3):  # 3 trades per ticker
                timestamp = datetime.now() - timedelta(hours=6-i*2)
                
                buy_order = self.order_gen.generate_buy_order(
                    ticker=ticker,
                    price=150 + i*5,
                    quantity=5,
                    timestamp=timestamp
                )
                orders.append(buy_order)
                
                # Quick sell (day trading)
                sell_price = buy_order.buy_price * (1 + np.random.uniform(-0.02, 0.03))
                sell_order = self.order_gen.generate_sell_order(
                    buy_order, sell_price, "manual",
                    timestamp + timedelta(minutes=30)
                )
                orders.append(sell_order)
        
        return {
            "name": "Day Trader",
            "description": "Multiple quick trades with small profits/losses",
            "orders": orders,
            "positions": [],
            "total_trades": len(orders) // 2,
            "strategy": "day_trading"
        }
    
    def swing_trader_scenario(self) -> Dict[str, Any]:
        """Swing trading scenario with longer holds."""
        tickers = ["AAPL", "GOOGL"]
        orders = []
        positions = []
        
        # Some completed swing trades
        for ticker in tickers:
            buy_order = self.order_gen.generate_buy_order(
                ticker=ticker,
                price=150 if ticker == "AAPL" else 2500,
                quantity=10,
                timestamp=datetime.now() - timedelta(days=5)
            )
            orders.append(buy_order)
            
            # Swing trade exit after several days
            sell_price = buy_order.buy_price * 1.08  # 8% gain
            sell_order = self.order_gen.generate_sell_order(
                buy_order, sell_price, "target_price",
                datetime.now() - timedelta(days=1)
            )
            orders.append(sell_order)
        
        # Current open positions
        for ticker in ["TSLA", "MSFT"]:
            position = self.position_gen.generate_position(
                symbol=ticker,
                entry_price=200 if ticker == "TSLA" else 300,
                quantity=15
            )
            positions.append(position)
        
        return {
            "name": "Swing Trader",
            "description": "Longer-term trades with larger position sizes",
            "orders": orders,
            "positions": positions,
            "total_trades": len(orders) // 2,
            "strategy": "swing_trading"
        }
    
    def risk_management_scenario(self) -> Dict[str, Any]:
        """Scenario focused on risk management edge cases."""
        orders = []
        
        # Mix of stop losses and target hits
        scenarios = [
            ("AAPL", 150, "stop_loss", -0.05),
            ("TSLA", 200, "target_price", 0.12),
            ("GOOGL", 2500, "stop_loss", -0.08),
            ("MSFT", 300, "target_price", 0.15)
        ]
        
        for ticker, buy_price, exit_reason, change in scenarios:
            timestamp = datetime.now() - timedelta(hours=len(orders))
            
            buy_order = self.order_gen.generate_buy_order(
                ticker=ticker,
                price=buy_price,
                quantity=10,
                timestamp=timestamp
            )
            orders.append(buy_order)
            
            sell_price = buy_price * (1 + change)
            sell_order = self.order_gen.generate_sell_order(
                buy_order, sell_price, exit_reason,
                timestamp + timedelta(hours=2)
            )
            orders.append(sell_order)
        
        return {
            "name": "Risk Management",
            "description": "Trades demonstrating risk management rules",
            "orders": orders,
            "positions": [],
            "total_trades": len(orders) // 2,
            "strategy": "risk_managed"
        }
    
    def portfolio_diversification_scenario(self) -> Dict[str, Any]:
        """Well-diversified portfolio scenario."""
        symbols = ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN", "META"]
        
        # Generate diversified positions
        positions = self.position_gen.generate_portfolio(symbols, 200000)
        
        # Some recent trading history
        orders = self.order_gen.generate_trading_session(
            symbols[:3], num_trades=8, start_balance=150000
        )
        
        return {
            "name": "Diversified Portfolio",
            "description": "Well-diversified portfolio with multiple positions",
            "orders": orders,
            "positions": positions,
            "total_trades": len(orders) // 2,
            "strategy": "diversified"
        }


def create_csv_fixtures(output_dir: str = "tests/fixtures/data"):
    """Create CSV files with test data fixtures."""
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    scenarios = ScenarioFixtures()
    
    # Generate all scenarios
    all_scenarios = [
        scenarios.day_trader_scenario(),
        scenarios.swing_trader_scenario(),
        scenarios.risk_management_scenario(),
        scenarios.portfolio_diversification_scenario()
    ]
    
    for scenario in all_scenarios:
        # Create orders CSV
        if scenario["orders"]:
            orders_df = pd.DataFrame([order.to_dict() for order in scenario["orders"]])
            orders_df.to_csv(
                os.path.join(output_dir, f"{scenario['name'].lower().replace(' ', '_')}_orders.csv"),
                index=False
            )
        
        # Create positions CSV
        if scenario["positions"]:
            positions_df = pd.DataFrame([pos.to_dict() for pos in scenario["positions"]])
            positions_df.to_csv(
                os.path.join(output_dir, f"{scenario['name'].lower().replace(' ', '_')}_positions.csv"),
                index=False
            )
        
        # Create scenario metadata
        metadata = {
            "name": scenario["name"],
            "description": scenario["description"],
            "total_trades": scenario["total_trades"],
            "strategy": scenario["strategy"],
            "created_at": datetime.now().isoformat()
        }
        
        with open(os.path.join(output_dir, f"{scenario['name'].lower().replace(' ', '_')}_metadata.json"), 'w') as f:
            json.dump(metadata, f, indent=2)


# Quick access functions
def get_sample_buy_order(ticker: str = "AAPL") -> OrderFixture:
    """Get a sample buy order."""
    gen = OrderGenerator()
    return gen.generate_buy_order(ticker=ticker)


def get_sample_sell_order(ticker: str = "AAPL") -> OrderFixture:
    """Get a sample sell order."""
    gen = OrderGenerator()
    buy_order = gen.generate_buy_order(ticker=ticker)
    return gen.generate_sell_order(buy_order, buy_order.buy_price * 1.05)


def get_sample_position(symbol: str = "AAPL") -> PositionFixture:
    """Get a sample position."""
    gen = PositionGenerator()
    return gen.generate_position(symbol=symbol)


def get_profitable_trades(count: int = 5) -> List[OrderFixture]:
    """Get profitable trade sequence."""
    gen = OrderGenerator()
    return gen.generate_profitable_trade_sequence(num_trades=count)


def get_losing_trades(count: int = 5) -> List[OrderFixture]:
    """Get losing trade sequence."""
    gen = OrderGenerator()
    return gen.generate_losing_trade_sequence(num_trades=count)


# Export commonly used fixtures
__all__ = [
    'OrderFixture',
    'PositionFixture', 
    'OrderGenerator',
    'PositionGenerator',
    'ScenarioFixtures',
    'create_csv_fixtures',
    'get_sample_buy_order',
    'get_sample_sell_order',
    'get_sample_position',
    'get_profitable_trades',
    'get_losing_trades'
]