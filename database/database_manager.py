import psycopg2
import pandas as pd
from datetime import datetime
import os
from psycopg2 import pool
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    _connection_pool = None
    
    def __init__(self, db_url=None):
        if db_url is None:
            db_url = self._get_secure_db_url()
        self.db_url = db_url
        self._init_connection_pool()
        self.create_tables()
    
    def _get_secure_db_url(self):
        """Get database URL from environment variables for security"""
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'tradingbot_dev')
        username = os.getenv('DB_USER', 'tradingbot')
        password = os.getenv('DB_PASSWORD')
        
        if not password:
            raise ValueError("DB_PASSWORD environment variable must be set")
        
        return f'postgresql://{username}:{password}@{host}:{port}/{database}'
    
    def _init_connection_pool(self):
        """Initialize connection pool for better performance and resource management"""
        if DatabaseManager._connection_pool is None:
            try:
                DatabaseManager._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=20,
                    dsn=self.db_url
                )
                logger.info("Database connection pool initialized")
            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                raise
    
    def get_connection(self):
        """Get connection from pool"""
        try:
            return DatabaseManager._connection_pool.getconn()
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
    
    def return_connection(self, conn):
        """Return connection to pool"""
        try:
            DatabaseManager._connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")

    def create_tables(self):
        """Create tables with proper indexes for performance"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # Create historical_data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS historical_data (
                        timestamp TIMESTAMPTZ NOT NULL,
                        symbol TEXT NOT NULL,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        volume INTEGER,
                        timeframe TEXT NOT NULL,
                        CONSTRAINT historical_data_unique UNIQUE (timestamp, symbol, timeframe)
                    );
                ''')
                
                # Create hypertable if TimescaleDB is available
                try:
                    cursor.execute("SELECT create_hypertable('historical_data', 'timestamp', if_not_exists => TRUE);")
                except Exception as e:
                    logger.warning(f"TimescaleDB not available, using regular table: {e}")
                
                # Create performance indexes
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_historical_symbol_timeframe 
                    ON historical_data (symbol, timeframe, timestamp DESC);
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_historical_timestamp 
                    ON historical_data (timestamp DESC);
                ''')
                
                conn.commit()
                logger.info("Database tables and indexes created successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create tables: {e}")
            raise
        finally:
            self.return_connection(conn)

    def store_historical_data(self, symbol, timeframe, df):
        """Store historical data with proper validation and error handling"""
        if df.empty:
            logger.warning(f"Empty dataframe provided for {symbol} {timeframe}")
            return
        
        # Input validation
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Symbol must be a non-empty string")
        if not isinstance(timeframe, str) or not timeframe.strip():
            raise ValueError("Timeframe must be a non-empty string")
        
        conn = self.get_connection()
        try:
            # Prepare data
            df_copy = df.copy()
            df_copy['symbol'] = symbol
            df_copy['timeframe'] = timeframe
            
            # Use parameterized insert for security
            with conn.cursor() as cursor:
                for idx, row in df_copy.iterrows():
                    cursor.execute("""
                        INSERT INTO historical_data 
                        (timestamp, symbol, open, high, low, close, volume, timeframe)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (timestamp, symbol, timeframe) DO NOTHING
                    """, (
                        idx, symbol, row.get('open'), row.get('high'), 
                        row.get('low'), row.get('close'), row.get('volume'), timeframe
                    ))
            
            conn.commit()
            logger.info(f"Stored {len(df_copy)} records for {symbol} {timeframe}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to store historical data for {symbol}: {e}")
            raise
        finally:
            self.return_connection(conn)

    def get_historical_data(self, symbol, timeframe, start_date, end_date):
        """Get historical data with proper validation and error handling"""
        # Input validation
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Symbol must be a non-empty string")
        if not isinstance(timeframe, str) or not timeframe.strip():
            raise ValueError("Timeframe must be a non-empty string")
        
        conn = self.get_connection()
        try:
            query = """
                SELECT timestamp, symbol, open, high, low, close, volume, timeframe 
                FROM historical_data 
                WHERE symbol = %s AND timeframe = %s AND timestamp BETWEEN %s AND %s
                ORDER BY timestamp
            """
            
            df = pd.read_sql_query(
                query, 
                conn, 
                params=(symbol, timeframe, start_date, end_date), 
                index_col='timestamp'
            )
            
            # Drop duplicate columns that might have been created
            df = df.loc[:,~df.columns.duplicated()]
            logger.info(f"Retrieved {len(df)} records for {symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error reading from database for {symbol}: {e}")
            return pd.DataFrame()
        finally:
            self.return_connection(conn)

    def get_latest_timestamp(self, symbol, timeframe):
        """Get latest timestamp with proper validation and parameterized query"""
        # Input validation
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Symbol must be a non-empty string")
        if not isinstance(timeframe, str) or not timeframe.strip():
            raise ValueError("Timeframe must be a non-empty string")
        
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT MAX(timestamp) FROM historical_data WHERE symbol = %s AND timeframe = %s", 
                    (symbol, timeframe)
                )
                result = cursor.fetchone()[0]
                if result:
                    return pd.to_datetime(result)
                return None
        except Exception as e:
            logger.error(f"Error getting latest timestamp for {symbol}: {e}")
            return None
        finally:
            self.return_connection(conn)

    def close(self):
        """Close connection pool"""
        if DatabaseManager._connection_pool:
            DatabaseManager._connection_pool.closeall()
            DatabaseManager._connection_pool = None
            logger.info("Database connection pool closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
