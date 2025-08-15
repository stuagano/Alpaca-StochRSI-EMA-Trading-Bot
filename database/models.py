import sqlite3
import pandas as pd
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import os

class DatabaseManager:
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize database and create tables if they don't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Orders table (completed trades)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        time DATETIME NOT NULL,
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
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Open orders table (active positions)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS open_orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        time DATETIME NOT NULL,
                        ticker TEXT NOT NULL,
                        type TEXT NOT NULL,
                        buy_price REAL,
                        quantity REAL NOT NULL,
                        total REAL NOT NULL,
                        acc_balance REAL,
                        target_price REAL,
                        stop_loss_price REAL,
                        activate_trailing_stop_at REAL,
                        current_price REAL,
                        unrealized_pnl REAL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Time and coins table (position tracking)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS position_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        time DATETIME NOT NULL,
                        ticker TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        avg_price REAL NOT NULL,
                        total_value REAL NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Strategy performance table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL,
                        strategy_name TEXT NOT NULL,
                        total_trades INTEGER DEFAULT 0,
                        winning_trades INTEGER DEFAULT 0,
                        losing_trades INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0.0,
                        win_rate REAL DEFAULT 0.0,
                        avg_win REAL DEFAULT 0.0,
                        avg_loss REAL DEFAULT 0.0,
                        max_drawdown REAL DEFAULT 0.0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Market data cache table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS market_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ticker TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        open REAL NOT NULL,
                        high REAL NOT NULL,
                        low REAL NOT NULL,
                        close REAL NOT NULL,
                        volume INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(ticker, timestamp)
                    )
                """)
                
                # System logs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        level TEXT NOT NULL,
                        module TEXT NOT NULL,
                        message TEXT NOT NULL,
                        extra_data TEXT
                    )
                """)
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
    
    def migrate_csv_data(self, orders_csv: str = None, open_orders_csv: str = None, time_coins_csv: str = None):
        """Migrate existing CSV data to database"""
        try:
            if orders_csv and os.path.exists(orders_csv):
                df = pd.read_csv(orders_csv)
                df.to_sql('orders', sqlite3.connect(self.db_path), if_exists='append', index=False)
                self.logger.info(f"Migrated {len(df)} orders from CSV")
            
            if open_orders_csv and os.path.exists(open_orders_csv):
                df = pd.read_csv(open_orders_csv)
                df.to_sql('open_orders', sqlite3.connect(self.db_path), if_exists='append', index=False)
                self.logger.info(f"Migrated {len(df)} open orders from CSV")
                
            if time_coins_csv and os.path.exists(time_coins_csv):
                df = pd.read_csv(time_coins_csv)
                df.to_sql('position_tracking', sqlite3.connect(self.db_path), if_exists='append', index=False)
                self.logger.info(f"Migrated {len(df)} position records from CSV")
                
        except Exception as e:
            self.logger.error(f"CSV migration failed: {e}")
            raise

class OrdersDAO:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def add_order(self, order_data: Dict[str, Any]) -> int:
        """Add a new completed order"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO orders (time, ticker, type, buy_price, sell_price, highest_price, 
                                      quantity, total, acc_balance, target_price, stop_loss_price, 
                                      activate_trailing_stop_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_data.get('time'),
                    order_data.get('ticker'),
                    order_data.get('type'),
                    order_data.get('buy_price'),
                    order_data.get('sell_price'),
                    order_data.get('highest_price'),
                    order_data.get('quantity'),
                    order_data.get('total'),
                    order_data.get('acc_balance'),
                    order_data.get('target_price'),
                    order_data.get('stop_loss_price'),
                    order_data.get('activate_trailing_stop_at')
                ))
                order_id = cursor.lastrowid
                conn.commit()
                self.logger.info(f"Added order {order_id} for {order_data.get('ticker')}")
                return order_id
        except Exception as e:
            self.logger.error(f"Failed to add order: {e}")
            raise
    
    def get_orders(self, ticker: str = None, limit: int = None) -> pd.DataFrame:
        """Get orders, optionally filtered by ticker"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                query = "SELECT * FROM orders"
                params = []
                
                if ticker:
                    query += " WHERE ticker = ?"
                    params.append(ticker)
                
                query += " ORDER BY time DESC"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            self.logger.error(f"Failed to get orders: {e}")
            return pd.DataFrame()
    
    def get_performance_metrics(self, start_date: str = None, end_date: str = None) -> Dict[str, float]:
        """Calculate performance metrics for completed orders"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                query = """
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN sell_price > buy_price THEN 1 ELSE 0 END) as winning_trades,
                        AVG(CASE WHEN sell_price > buy_price THEN (sell_price - buy_price) * quantity ELSE 0 END) as avg_win,
                        AVG(CASE WHEN sell_price < buy_price THEN (buy_price - sell_price) * quantity ELSE 0 END) as avg_loss,
                        SUM((sell_price - buy_price) * quantity) as total_pnl
                    FROM orders 
                    WHERE sell_price IS NOT NULL
                """
                params = []
                
                if start_date:
                    query += " AND time >= ?"
                    params.append(start_date)
                if end_date:
                    query += " AND time <= ?"
                    params.append(end_date)
                
                result = pd.read_sql_query(query, conn, params=params).iloc[0]
                
                win_rate = (result['winning_trades'] / result['total_trades']) * 100 if result['total_trades'] > 0 else 0
                
                return {
                    'total_trades': result['total_trades'],
                    'winning_trades': result['winning_trades'],
                    'win_rate': win_rate,
                    'avg_win': result['avg_win'] or 0,
                    'avg_loss': result['avg_loss'] or 0,
                    'total_pnl': result['total_pnl'] or 0
                }
        except Exception as e:
            self.logger.error(f"Failed to calculate performance metrics: {e}")
            return {}

class OpenOrdersDAO:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def add_open_order(self, order_data: Dict[str, Any]) -> int:
        """Add a new open order"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO open_orders (time, ticker, type, buy_price, quantity, total, 
                                           acc_balance, target_price, stop_loss_price, 
                                           activate_trailing_stop_at, current_price, unrealized_pnl)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_data.get('time'),
                    order_data.get('ticker'),
                    order_data.get('type'),
                    order_data.get('buy_price'),
                    order_data.get('quantity'),
                    order_data.get('total'),
                    order_data.get('acc_balance'),
                    order_data.get('target_price'),
                    order_data.get('stop_loss_price'),
                    order_data.get('activate_trailing_stop_at'),
                    order_data.get('current_price'),
                    order_data.get('unrealized_pnl', 0)
                ))
                order_id = cursor.lastrowid
                conn.commit()
                self.logger.info(f"Added open order {order_id} for {order_data.get('ticker')}")
                return order_id
        except Exception as e:
            self.logger.error(f"Failed to add open order: {e}")
            raise
    
    def get_open_orders(self, ticker: str = None) -> pd.DataFrame:
        """Get all open orders"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                query = "SELECT * FROM open_orders"
                params = []
                
                if ticker:
                    query += " WHERE ticker = ?"
                    params.append(ticker)
                
                query += " ORDER BY time DESC"
                
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            self.logger.error(f"Failed to get open orders: {e}")
            return pd.DataFrame()
    
    def update_open_order(self, order_id: int, updates: Dict[str, Any]) -> bool:
        """Update an open order"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
                values = list(updates.values()) + [order_id]
                
                cursor.execute(f"""
                    UPDATE open_orders 
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, values)
                
                conn.commit()
                self.logger.info(f"Updated open order {order_id}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to update open order {order_id}: {e}")
            return False
    
    def close_order(self, order_id: int, sell_price: float) -> bool:
        """Move an open order to completed orders"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # Get the open order
                open_order = pd.read_sql_query(
                    "SELECT * FROM open_orders WHERE id = ?", 
                    conn, params=[order_id]
                )
                
                if open_order.empty:
                    return False
                
                order = open_order.iloc[0]
                
                # Add to completed orders
                cursor.execute("""
                    INSERT INTO orders (time, ticker, type, buy_price, sell_price, highest_price,
                                      quantity, total, acc_balance, target_price, stop_loss_price,
                                      activate_trailing_stop_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    order['ticker'],
                    'sell',
                    order['buy_price'],
                    sell_price,
                    order.get('highest_price', sell_price),
                    order['quantity'],
                    order['quantity'] * sell_price,
                    order.get('acc_balance'),
                    order.get('target_price'),
                    order.get('stop_loss_price'),
                    order.get('activate_trailing_stop_at')
                ))
                
                # Remove from open orders
                cursor.execute("DELETE FROM open_orders WHERE id = ?", [order_id])
                
                conn.commit()
                self.logger.info(f"Closed order {order_id} at price {sell_price}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to close order {order_id}: {e}")
            return False

class MarketDataDAO:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def store_market_data(self, ticker: str, timestamp: datetime, ohlcv: Dict[str, float]) -> bool:
        """Store market data"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO market_data (ticker, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticker,
                    timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    ohlcv['open'],
                    ohlcv['high'],
                    ohlcv['low'],
                    ohlcv['close'],
                    ohlcv.get('volume', 0)
                ))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to store market data for {ticker}: {e}")
            return False
    
    def get_market_data(self, ticker: str, start_time: datetime = None, limit: int = 1000) -> pd.DataFrame:
        """Get historical market data"""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                query = "SELECT * FROM market_data WHERE ticker = ?"
                params = [ticker]
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time.strftime('%Y-%m-%d %H:%M:%S'))
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                return pd.read_sql_query(query, conn, params=params)
        except Exception as e:
            self.logger.error(f"Failed to get market data for {ticker}: {e}")
            return pd.DataFrame()