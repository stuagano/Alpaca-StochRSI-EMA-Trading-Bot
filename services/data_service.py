import os
import pandas as pd
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from database.models import DatabaseManager, OrdersDAO, OpenOrdersDAO, MarketDataDAO
from config.config_manager import get_database_config, get_trading_config
from utils.logging_config import PerformanceLogger

class TradingDataService:
    """
    Unified data service that replaces CSV operations with database operations
    """
    
    def __init__(self):
        self.logger = logging.getLogger('database')
        self.perf_logger = PerformanceLogger(self.logger)
        
        # Get configuration
        db_config = get_database_config()
        
        # Initialize database components
        self.db_manager = DatabaseManager(db_config.db_path)
        self.orders_dao = OrdersDAO(self.db_manager)
        self.open_orders_dao = OpenOrdersDAO(self.db_manager)
        self.market_data_dao = MarketDataDAO(self.db_manager)
        
        # Migrate CSV data if it exists
        self._migrate_existing_csv_data()
        
        self.logger.info("Trading Data Service initialized successfully")
    
    def _migrate_existing_csv_data(self):
        """Migrate existing CSV files to database"""
        try:
            csv_files = {
                'orders': 'ORDERS/Orders.csv',
                'open_orders': 'ORDERS/Open Orders.csv',
                'time_coins': 'ORDERS/Time and Coins.csv'
            }
            
            migration_needed = any(os.path.exists(f) for f in csv_files.values())
            
            if migration_needed:
                self.logger.info("Migrating existing CSV data to database...")
                
                # Check if database already has data to avoid duplicates
                existing_orders = self.orders_dao.get_orders(limit=1)
                if not existing_orders.empty:
                    self.logger.info("Database already contains data, skipping migration")
                    return
                
                # Migrate each CSV file
                for data_type, csv_file in csv_files.items():
                    if os.path.exists(csv_file):
                        df = pd.read_csv(csv_file)
                        if not df.empty:
                            self._migrate_csv_data_type(data_type, df)
                
                self.logger.info("CSV migration completed successfully")
                
        except Exception as e:
            self.logger.error(f"CSV migration failed: {e}")
    
    def _migrate_csv_data_type(self, data_type: str, df: pd.DataFrame):
        """Migrate specific CSV data type to database"""
        try:
            if data_type == 'orders':
                for _, row in df.iterrows():
                    order_data = {
                        'time': row.get('Time'),
                        'ticker': row.get('Ticker'),
                        'type': row.get('Type'),
                        'buy_price': row.get('Buy Price'),
                        'sell_price': row.get('Sell Price'),
                        'highest_price': row.get('Highest Price'),
                        'quantity': row.get('Quantity'),
                        'total': row.get('Total'),
                        'acc_balance': row.get('Acc Balance'),
                        'target_price': row.get('Target Price'),
                        'stop_loss_price': row.get('Stop Loss Price'),
                        'activate_trailing_stop_at': row.get('ActivateTrailingStopAt')
                    }
                    self.orders_dao.add_order(order_data)
            
            elif data_type == 'open_orders':
                for _, row in df.iterrows():
                    order_data = {
                        'time': row.get('Time'),
                        'ticker': row.get('Ticker'),
                        'type': row.get('Type'),
                        'buy_price': row.get('Buy Price'),
                        'quantity': row.get('Quantity'),
                        'total': row.get('Total'),
                        'acc_balance': row.get('Acc Balance'),
                        'target_price': row.get('Target Price'),
                        'stop_loss_price': row.get('Stop Loss Price'),
                        'activate_trailing_stop_at': row.get('ActivateTrailingStopAt'),
                        'current_price': row.get('Current Price', 0),
                        'unrealized_pnl': row.get('Unrealized PnL', 0)
                    }
                    self.open_orders_dao.add_open_order(order_data)
                    
            self.logger.info(f"Migrated {len(df)} records of type {data_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to migrate {data_type} data: {e}")
    
    # Order Management Methods (replacing CSV operations)
    
    def add_completed_order(self, order_data: Dict[str, Any]) -> int:
        """Add a completed order to the database"""
        start_time = datetime.now()
        try:
            order_id = self.orders_dao.add_order(order_data)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self.perf_logger.log_trade_execution(
                ticker=order_data.get('ticker'),
                action=order_data.get('type'),
                price=order_data.get('sell_price', order_data.get('buy_price')),
                quantity=order_data.get('quantity'),
                execution_time=execution_time,
                order_id=order_id
            )
            
            return order_id
            
        except Exception as e:
            self.logger.error(f"Failed to add completed order: {e}")
            raise
    
    def get_completed_orders(self, ticker: str = None, days: int = None) -> pd.DataFrame:
        """Get completed orders with optional filtering"""
        try:
            if days:
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                orders = self.orders_dao.get_orders(ticker=ticker)
                if not orders.empty:
                    orders = orders[orders['time'] >= start_date]
                return orders
            else:
                return self.orders_dao.get_orders(ticker=ticker)
                
        except Exception as e:
            self.logger.error(f"Failed to get completed orders: {e}")
            return pd.DataFrame()
    
    def add_open_order(self, order_data: Dict[str, Any]) -> int:
        """Add a new open order"""
        try:
            return self.open_orders_dao.add_open_order(order_data)
        except Exception as e:
            self.logger.error(f"Failed to add open order: {e}")
            raise
    
    def get_open_orders(self, ticker: str = None) -> pd.DataFrame:
        """Get all open orders"""
        try:
            return self.open_orders_dao.get_open_orders(ticker=ticker)
        except Exception as e:
            self.logger.error(f"Failed to get open orders: {e}")
            return pd.DataFrame()
    
    def update_open_order(self, order_id: int, updates: Dict[str, Any]) -> bool:
        """Update an open order"""
        try:
            updates['updated_at'] = datetime.now()
            return self.open_orders_dao.update_open_order(order_id, updates)
        except Exception as e:
            self.logger.error(f"Failed to update open order {order_id}: {e}")
            return False
    
    def close_position(self, order_id: int, sell_price: float) -> bool:
        """Close an open position"""
        start_time = datetime.now()
        try:
            result = self.open_orders_dao.close_order(order_id, sell_price)
            
            if result:
                execution_time = (datetime.now() - start_time).total_seconds()
                self.logger.info(f"Position closed: Order {order_id} at ${sell_price:.4f} "
                               f"(execution_time: {execution_time:.3f}s)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to close position {order_id}: {e}")
            return False
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio performance summary"""
        try:
            # Get performance metrics from completed orders
            performance = self.orders_dao.get_performance_metrics()
            
            # Get current open positions
            open_orders = self.get_open_orders()
            
            # Calculate current portfolio metrics
            total_open_value = open_orders['total'].sum() if not open_orders.empty else 0
            unrealized_pnl = open_orders['unrealized_pnl'].sum() if not open_orders.empty else 0
            
            summary = {
                'completed_trades': performance.get('total_trades', 0),
                'win_rate': performance.get('win_rate', 0),
                'total_realized_pnl': performance.get('total_pnl', 0),
                'avg_win': performance.get('avg_win', 0),
                'avg_loss': performance.get('avg_loss', 0),
                'open_positions': len(open_orders),
                'total_open_value': total_open_value,
                'unrealized_pnl': unrealized_pnl,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Log portfolio update
            self.perf_logger.log_portfolio_update(
                total_value=total_open_value,
                pnl=performance.get('total_pnl', 0),
                positions=len(open_orders),
                cash=0  # Would need to get from Alpaca API
            )
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get portfolio summary: {e}")
            return {}
    
    # Market Data Methods
    
    def store_market_data(self, ticker: str, timestamp: datetime, ohlcv: Dict[str, float]) -> bool:
        """Store market data for backtesting and analysis"""
        try:
            return self.market_data_dao.store_market_data(ticker, timestamp, ohlcv)
        except Exception as e:
            self.logger.error(f"Failed to store market data for {ticker}: {e}")
            return False
    
    def get_historical_data(self, ticker: str, days: int = 30) -> pd.DataFrame:
        """Get historical market data"""
        try:
            start_time = datetime.now() - timedelta(days=days)
            return self.market_data_dao.get_market_data(ticker, start_time)
        except Exception as e:
            self.logger.error(f"Failed to get historical data for {ticker}: {e}")
            return pd.DataFrame()
    
    # Analytics and Reporting Methods
    
    def get_strategy_performance(self, strategy_name: str = None, days: int = 30) -> Dict[str, Any]:
        """Get detailed strategy performance analysis"""
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Get orders for the period
            orders = self.orders_dao.get_orders()
            if not orders.empty:
                orders = orders[orders['time'] >= start_date]
            
            if orders.empty:
                return {'error': 'No trades found for the specified period'}
            
            # Calculate detailed metrics
            winning_trades = orders[orders['sell_price'] > orders['buy_price']]
            losing_trades = orders[orders['sell_price'] <= orders['buy_price']]
            
            total_trades = len(orders)
            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            
            win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
            
            # Calculate PnL
            orders['pnl'] = (orders['sell_price'] - orders['buy_price']) * orders['quantity']
            total_pnl = orders['pnl'].sum()
            
            # Calculate drawdown
            orders['cumulative_pnl'] = orders['pnl'].cumsum()
            running_max = orders['cumulative_pnl'].expanding().max()
            drawdown = ((orders['cumulative_pnl'] - running_max) / running_max * 100).fillna(0)
            max_drawdown = abs(drawdown.min())
            
            # Average metrics
            avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
            avg_loss = abs(losing_trades['pnl'].mean()) if not losing_trades.empty else 0
            
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
            
            return {
                'period_days': days,
                'total_trades': total_trades,
                'winning_trades': win_count,
                'losing_trades': loss_count,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'profit_factor': round(profit_factor, 2),
                'max_drawdown': round(max_drawdown, 2),
                'best_trade': round(orders['pnl'].max(), 2),
                'worst_trade': round(orders['pnl'].min(), 2),
                'strategy_name': strategy_name or 'Current Strategy',
                'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get strategy performance: {e}")
            return {'error': str(e)}
    
    def get_trading_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get recent trading statistics"""
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Recent completed orders
            recent_orders = self.orders_dao.get_orders()
            if not recent_orders.empty:
                recent_orders = recent_orders[recent_orders['time'] >= start_date]
            
            # Current open orders
            open_orders = self.get_open_orders()
            
            # Calculate statistics
            stats = {
                'period_days': days,
                'completed_trades': len(recent_orders),
                'active_positions': len(open_orders),
                'total_volume_traded': recent_orders['total'].sum() if not recent_orders.empty else 0,
                'most_traded_ticker': recent_orders['ticker'].mode().iloc[0] if not recent_orders.empty else 'N/A',
                'avg_trade_size': recent_orders['total'].mean() if not recent_orders.empty else 0,
                'last_trade_time': recent_orders['time'].max() if not recent_orders.empty else 'N/A'
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get trading statistics: {e}")
            return {}
    
    def backup_database(self, backup_path: str = None) -> str:
        """Create database backup"""
        try:
            if backup_path is None:
                backup_dir = "backups"
                os.makedirs(backup_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = os.path.join(backup_dir, f'trading_bot_backup_{timestamp}.db')
            
            # Simple file copy for SQLite
            import shutil
            shutil.copy2(self.db_manager.db_path, backup_path)
            
            self.logger.info(f"Database backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            raise
    
    def cleanup_old_data(self, keep_days: int = 365):
        """Clean up old data to maintain database size"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=keep_days)).strftime('%Y-%m-%d')
            
            import sqlite3
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                
                # Clean up old market data
                cursor.execute("DELETE FROM market_data WHERE timestamp < ?", [cutoff_date])
                market_deleted = cursor.rowcount
                
                # Clean up old system logs
                cursor.execute("DELETE FROM system_logs WHERE timestamp < ?", [cutoff_date])
                logs_deleted = cursor.rowcount
                
                conn.commit()
                
                self.logger.info(f"Cleanup completed: {market_deleted} market data records, "
                               f"{logs_deleted} log records deleted (older than {keep_days} days)")
                
        except Exception as e:
            self.logger.error(f"Database cleanup failed: {e}")

# Global data service instance
_data_service = None

def get_data_service() -> TradingDataService:
    """Get singleton data service instance"""
    global _data_service
    if _data_service is None:
        _data_service = TradingDataService()
    return _data_service