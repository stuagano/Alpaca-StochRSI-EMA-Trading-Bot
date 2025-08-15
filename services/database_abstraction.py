"""
Thread-safe database abstraction layer with connection pooling.
"""
import sqlite3
import threading
import time
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import pandas as pd
from queue import Queue, Empty

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """
    Thread-safe SQLite connection pool.
    
    SQLite has limitations with concurrent access, so we use a pool
    of connections with proper locking and WAL mode for better concurrency.
    """
    
    def __init__(
        self,
        db_path: str,
        max_connections: int = 10,
        timeout: float = 30.0,
        check_same_thread: bool = False
    ):
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self.check_same_thread = check_same_thread
        
        self._pool = Queue(maxsize=max_connections)
        self._created_connections = 0
        self._lock = threading.RLock()
        self._closed = False
        
        # Initialize database with WAL mode for better concurrency
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database with optimal settings."""
        try:
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=self.check_same_thread,
                timeout=self.timeout
            )
            
            # Enable WAL mode for better concurrency
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=10000')
            conn.execute('PRAGMA temp_store=MEMORY')
            conn.execute('PRAGMA mmap_size=268435456')  # 256MB
            
            conn.close()
            logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=self.check_same_thread,
            timeout=self.timeout
        )
        
        # Configure connection
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute('PRAGMA foreign_keys=ON')
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Usage:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                # ... use connection
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        conn = None
        start_time = time.time()
        
        try:
            # Try to get existing connection from pool
            try:
                conn = self._pool.get_nowait()
            except Empty:
                # Create new connection if pool is empty and under limit
                with self._lock:
                    if self._created_connections < self.max_connections:
                        conn = self._create_connection()
                        self._created_connections += 1
                        logger.debug(f"Created new connection ({self._created_connections}/{self.max_connections})")
                    else:
                        # Wait for available connection
                        conn = self._pool.get(timeout=self.timeout)
            
            # Test connection
            conn.execute('SELECT 1')
            
            yield conn
            
        except Exception as e:
            # If connection failed, don't return it to pool
            if conn:
                try:
                    conn.close()
                except:
                    pass
                with self._lock:
                    self._created_connections -= 1
            raise e
            
        finally:
            # Return connection to pool if still valid
            if conn and not self._closed:
                try:
                    # Test if connection is still valid
                    conn.execute('SELECT 1')
                    self._pool.put_nowait(conn)
                except:
                    # Connection is broken, close it
                    try:
                        conn.close()
                    except:
                        pass
                    with self._lock:
                        self._created_connections -= 1
    
    def close_all(self):
        """Close all connections in the pool."""
        self._closed = True
        
        # Close all pooled connections
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
        
        with self._lock:
            self._created_connections = 0
        
        logger.info("All database connections closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        with self._lock:
            return {
                'db_path': self.db_path,
                'max_connections': self.max_connections,
                'created_connections': self._created_connections,
                'available_connections': self._pool.qsize(),
                'timeout': self.timeout,
                'closed': self._closed
            }


class DatabaseAbstraction:
    """
    High-level database abstraction with connection pooling and error handling.
    """
    
    def __init__(
        self,
        db_path: str = 'database/trading_data.db',
        max_connections: int = 10,
        timeout: float = 30.0
    ):
        self.db_path = db_path
        self.pool = DatabaseConnectionPool(
            db_path=db_path,
            max_connections=max_connections,
            timeout=timeout
        )
        
        # Create tables
        self._create_tables()
    
    def _create_tables(self):
        """Create necessary database tables."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Historical data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS historical_data (
                    timestamp DATETIME,
                    symbol TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    timeframe TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (timestamp, symbol, timeframe)
                )
            ''')
            
            # Price cache table for persistence
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_cache (
                    symbol TEXT PRIMARY KEY,
                    price REAL,
                    timestamp DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Trading signals table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    symbol TEXT,
                    signal_type TEXT,
                    price REAL,
                    indicators JSON,
                    confidence REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # System metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    metric_name TEXT,
                    metric_value REAL,
                    metadata JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_historical_symbol_timeframe 
                ON historical_data (symbol, timeframe)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_historical_timestamp 
                ON historical_data (timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp 
                ON trading_signals (symbol, timestamp)
            ''')
            
            conn.commit()
            logger.info("Database tables created/verified")
    
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch: str = 'none'
    ) -> Optional[Union[List[sqlite3.Row], sqlite3.Row, int]]:
        """
        Execute a database query with proper error handling.
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: 'none', 'one', 'all', or 'rowcount'
            
        Returns:
            Query results based on fetch parameter
        """
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch == 'one':
                return cursor.fetchone()
            elif fetch == 'all':
                return cursor.fetchall()
            elif fetch == 'rowcount':
                return cursor.rowcount
            else:
                conn.commit()
                return None
    
    def store_historical_data(self, symbol: str, timeframe: str, df: pd.DataFrame) -> None:
        """Store historical data efficiently."""
        if df.empty:
            return
        
        try:
            # Prepare data
            df_copy = df.copy()
            df_copy['symbol'] = symbol
            df_copy['timeframe'] = timeframe
            
            # Use pandas to_sql with conflict resolution
            with self.pool.get_connection() as conn:
                df_copy.to_sql(
                    'historical_data',
                    conn,
                    if_exists='append',
                    index=True,
                    index_label='timestamp',
                    method='multi'
                )
                conn.commit()
                
            logger.debug(f"Stored {len(df)} historical data points for {symbol}")
            
        except Exception as e:
            logger.error(f"Error storing historical data for {symbol}: {e}")
            raise
    
    def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Get historical data with proper error handling."""
        try:
            query = '''
                SELECT timestamp, open, high, low, close, volume
                FROM historical_data 
                WHERE symbol = ? AND timeframe = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            '''
            params = (symbol, timeframe, start_date, end_date)
            
            if limit:
                query += ' LIMIT ?'
                params = params + (limit,)
            
            with self.pool.get_connection() as conn:
                df = pd.read_sql_query(
                    query,
                    conn,
                    params=params,
                    index_col='timestamp',
                    parse_dates=['timestamp']
                )
                
            return df
            
        except Exception as e:
            logger.error(f"Error retrieving historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_latest_timestamp(self, symbol: str, timeframe: str) -> Optional[datetime]:
        """Get the latest timestamp for a symbol/timeframe."""
        try:
            query = '''
                SELECT MAX(timestamp) as latest_timestamp
                FROM historical_data 
                WHERE symbol = ? AND timeframe = ?
            '''
            
            row = self.execute_query(query, (symbol, timeframe), fetch='one')
            
            if row and row['latest_timestamp']:
                return pd.to_datetime(row['latest_timestamp'])
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest timestamp for {symbol}: {e}")
            return None
    
    def store_price_cache(self, symbol: str, price: float, timestamp: datetime) -> None:
        """Store price in persistent cache."""
        try:
            query = '''
                INSERT OR REPLACE INTO price_cache (symbol, price, timestamp, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            '''
            self.execute_query(query, (symbol, price, timestamp))
            
        except Exception as e:
            logger.error(f"Error storing price cache for {symbol}: {e}")
    
    def get_cached_price(self, symbol: str, max_age_seconds: int = 60) -> Optional[Tuple[float, datetime]]:
        """Get cached price if not too old."""
        try:
            query = '''
                SELECT price, timestamp
                FROM price_cache
                WHERE symbol = ? AND (julianday('now') - julianday(timestamp)) * 86400 < ?
            '''
            
            row = self.execute_query(query, (symbol, max_age_seconds), fetch='one')
            
            if row:
                return row['price'], pd.to_datetime(row['timestamp'])
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached price for {symbol}: {e}")
            return None
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Clean up old data to prevent database bloat."""
        try:
            cutoff_date = datetime.now() - pd.Timedelta(days=days_to_keep)
            
            # Clean historical data
            query = 'DELETE FROM historical_data WHERE timestamp < ?'
            result = self.execute_query(query, (cutoff_date,), fetch='rowcount')
            
            # Clean old price cache
            cache_query = 'DELETE FROM price_cache WHERE timestamp < ?'
            cache_result = self.execute_query(cache_query, (cutoff_date,), fetch='rowcount')
            
            total_deleted = (result or 0) + (cache_result or 0)
            
            if total_deleted > 0:
                logger.info(f"Cleaned up {total_deleted} old database records")
            
            return total_deleted
            
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            return 0
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get table sizes
                stats = {}
                tables = ['historical_data', 'price_cache', 'trading_signals', 'system_metrics']
                
                for table in tables:
                    cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
                    count = cursor.fetchone()[0]
                    stats[f'{table}_count'] = count
                
                # Get database file size
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                db_size = cursor.fetchone()[0]
                stats['database_size_bytes'] = db_size
                stats['database_size_mb'] = round(db_size / (1024 * 1024), 2)
                
                # Get connection pool stats
                stats.update(self.pool.get_stats())
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def close(self):
        """Close database connections."""
        self.pool.close_all()
        logger.info("Database connections closed")


# Global database instance
_db_instance = None
_db_lock = threading.RLock()


def get_database() -> DatabaseAbstraction:
    """Get singleton database instance."""
    global _db_instance
    
    with _db_lock:
        if _db_instance is None:
            _db_instance = DatabaseAbstraction()
        return _db_instance


def close_database():
    """Close global database instance."""
    global _db_instance
    
    with _db_lock:
        if _db_instance is not None:
            _db_instance.close()
            _db_instance = None