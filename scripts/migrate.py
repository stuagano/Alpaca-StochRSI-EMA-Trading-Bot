#!/usr/bin/env python3
"""
Database Migration Script for Alpaca Trading Bot
This script handles database migrations and data synchronization between SQLite and PostgreSQL
"""

import os
import sys
import sqlite3
import psycopg2
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the parent directory to sys.path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from config.unified_config import get_config
from utils.logging_config import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Handles database migrations and data synchronization"""
    
    def __init__(self):
        self.config = get_config()
        self.sqlite_path = os.environ.get('SQLITE_DB_PATH', '/app/data/trading_data.db')
        self.postgres_url = os.environ.get('DATABASE_URL', 'postgresql://tradingbot:tradingpass@postgres:5432/tradingbot_dev')
        
    def connect_sqlite(self) -> sqlite3.Connection:
        """Connect to SQLite database"""
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            logger.info(f"Connected to SQLite database: {self.sqlite_path}")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            raise
    
    def connect_postgres(self) -> psycopg2.extensions.connection:
        """Connect to PostgreSQL database"""
        try:
            conn = psycopg2.connect(self.postgres_url)
            conn.autocommit = True
            logger.info("Connected to PostgreSQL database")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def create_sqlite_tables(self, conn: sqlite3.Connection):
        """Create SQLite tables if they don't exist"""
        try:
            cursor = conn.cursor()
            
            # Market data table (simplified for SQLite)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    open_price REAL NOT NULL,
                    high_price REAL NOT NULL,
                    low_price REAL NOT NULL,
                    close_price REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timeframe, timestamp)
                )
            """)
            
            # Trading signals table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    strength REAL,
                    indicators TEXT,
                    timestamp DATETIME NOT NULL,
                    processed BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    qty REAL NOT NULL,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    limit_price REAL,
                    filled_avg_price REAL,
                    submitted_at DATETIME,
                    filled_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Positions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    qty REAL NOT NULL,
                    side TEXT NOT NULL,
                    market_value REAL,
                    cost_basis REAL,
                    unrealized_pl REAL,
                    avg_entry_price REAL,
                    current_price REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Strategy performance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    period_start DATETIME NOT NULL,
                    period_end DATETIME NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    total_return REAL DEFAULT 0,
                    win_rate REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("SQLite tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create SQLite tables: {e}")
            raise
    
    def migrate_sqlite_to_postgres(self) -> bool:
        """Migrate data from SQLite to PostgreSQL"""
        try:
            sqlite_conn = self.connect_sqlite()
            postgres_conn = self.connect_postgres()
            
            logger.info("Starting SQLite to PostgreSQL migration...")
            
            # Tables to migrate
            tables = [
                'market_data',
                'trading_signals', 
                'orders',
                'positions',
                'strategy_performance'
            ]
            
            for table in tables:
                try:
                    # Read data from SQLite
                    df = pd.read_sql_query(f"SELECT * FROM {table}", sqlite_conn)
                    
                    if df.empty:
                        logger.info(f"No data to migrate for table: {table}")
                        continue
                    
                    # Prepare data for PostgreSQL
                    if table == 'trading_signals' and 'indicators' in df.columns:
                        # Handle JSON column for PostgreSQL
                        df['indicators'] = df['indicators'].fillna('{}')
                    
                    # Insert into PostgreSQL using pandas
                    with postgres_conn.cursor() as cursor:
                        # Use COPY for better performance
                        from io import StringIO
                        output = StringIO()
                        df.to_csv(output, sep='\t', header=False, index=False, na_rep='\\N')
                        output.seek(0)
                        
                        # Map table to schema
                        schema_table = f"trading.{table}" if table in ['market_data', 'trading_signals', 'orders', 'positions', 'strategy_performance'] else table
                        
                        cursor.copy_from(
                            output, 
                            schema_table, 
                            columns=df.columns.tolist(),
                            sep='\t',
                            null='\\N'
                        )
                        
                    logger.info(f"Migrated {len(df)} rows from {table}")
                    
                except Exception as e:
                    logger.warning(f"Failed to migrate table {table}: {e}")
                    continue
            
            sqlite_conn.close()
            postgres_conn.close()
            
            logger.info("SQLite to PostgreSQL migration completed")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
    
    def sync_postgres_to_sqlite(self) -> bool:
        """Sync recent data from PostgreSQL back to SQLite"""
        try:
            sqlite_conn = self.connect_sqlite()
            postgres_conn = self.connect_postgres()
            
            logger.info("Starting PostgreSQL to SQLite sync...")
            
            # Sync recent market data (last 24 hours)
            with postgres_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT symbol, timeframe, timestamp, open_price, high_price, 
                           low_price, close_price, volume
                    FROM trading.market_data 
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                    ORDER BY timestamp DESC
                """)
                
                market_data = cursor.fetchall()
                
                if market_data:
                    sqlite_cursor = sqlite_conn.cursor()
                    for row in market_data:
                        try:
                            sqlite_cursor.execute("""
                                INSERT OR REPLACE INTO market_data 
                                (symbol, timeframe, timestamp, open_price, high_price, 
                                 low_price, close_price, volume)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, row)
                        except Exception as e:
                            logger.debug(f"Skipping duplicate market data: {e}")
                    
                    sqlite_conn.commit()
                    logger.info(f"Synced {len(market_data)} market data records")
            
            # Sync recent trading signals
            with postgres_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT symbol, strategy, signal_type, strength, 
                           indicators::text, timestamp, processed
                    FROM trading.trading_signals 
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                    ORDER BY timestamp DESC
                """)
                
                signals = cursor.fetchall()
                
                if signals:
                    sqlite_cursor = sqlite_conn.cursor()
                    for row in signals:
                        try:
                            sqlite_cursor.execute("""
                                INSERT OR REPLACE INTO trading_signals 
                                (symbol, strategy, signal_type, strength, 
                                 indicators, timestamp, processed)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, row)
                        except Exception as e:
                            logger.debug(f"Skipping duplicate signal: {e}")
                    
                    sqlite_conn.commit()
                    logger.info(f"Synced {len(signals)} trading signals")
            
            sqlite_conn.close()
            postgres_conn.close()
            
            logger.info("PostgreSQL to SQLite sync completed")
            return True
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return False
    
    def backup_sqlite(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of the SQLite database"""
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"/app/data/backup_trading_data_{timestamp}.db"
            
            # Ensure backup directory exists
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Copy database
            import shutil
            shutil.copy2(self.sqlite_path, backup_path)
            
            logger.info(f"SQLite backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise
    
    def verify_migration(self) -> Dict[str, Any]:
        """Verify data integrity after migration"""
        try:
            sqlite_conn = self.connect_sqlite()
            postgres_conn = self.connect_postgres()
            
            verification_results = {}
            
            # Check row counts
            tables = ['market_data', 'trading_signals', 'orders', 'positions']
            
            for table in tables:
                try:
                    # SQLite count
                    sqlite_cursor = sqlite_conn.cursor()
                    sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    sqlite_count = sqlite_cursor.fetchone()[0]
                    
                    # PostgreSQL count
                    with postgres_conn.cursor() as postgres_cursor:
                        postgres_cursor.execute(f"SELECT COUNT(*) FROM trading.{table}")
                        postgres_count = postgres_cursor.fetchone()[0]
                    
                    verification_results[table] = {
                        'sqlite_count': sqlite_count,
                        'postgres_count': postgres_count,
                        'match': sqlite_count == postgres_count
                    }
                    
                except Exception as e:
                    verification_results[table] = {
                        'error': str(e)
                    }
            
            sqlite_conn.close()
            postgres_conn.close()
            
            logger.info("Migration verification completed")
            return verification_results
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {'error': str(e)}

def main():
    """Main migration script"""
    migrator = DatabaseMigrator()
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Database Migration Script')
    parser.add_argument('--action', choices=['migrate', 'sync', 'backup', 'verify', 'init'], 
                       default='migrate', help='Action to perform')
    parser.add_argument('--backup-path', help='Path for backup file')
    
    args = parser.parse_args()
    
    try:
        if args.action == 'init':
            # Initialize SQLite tables
            sqlite_conn = migrator.connect_sqlite()
            migrator.create_sqlite_tables(sqlite_conn)
            sqlite_conn.close()
            logger.info("SQLite database initialized")
            
        elif args.action == 'migrate':
            # Create backup first
            backup_path = migrator.backup_sqlite(args.backup_path)
            logger.info(f"Backup created at: {backup_path}")
            
            # Perform migration
            success = migrator.migrate_sqlite_to_postgres()
            if success:
                logger.info("Migration completed successfully")
                
                # Verify migration
                results = migrator.verify_migration()
                logger.info(f"Verification results: {results}")
            else:
                logger.error("Migration failed")
                sys.exit(1)
                
        elif args.action == 'sync':
            success = migrator.sync_postgres_to_sqlite()
            if success:
                logger.info("Sync completed successfully")
            else:
                logger.error("Sync failed")
                sys.exit(1)
                
        elif args.action == 'backup':
            backup_path = migrator.backup_sqlite(args.backup_path)
            logger.info(f"Backup completed: {backup_path}")
            
        elif args.action == 'verify':
            results = migrator.verify_migration()
            logger.info(f"Verification results: {results}")
            
            # Print summary
            all_match = all(
                result.get('match', False) for result in results.values() 
                if 'error' not in result
            )
            
            if all_match:
                logger.info("✅ All tables verified successfully")
            else:
                logger.warning("⚠️  Some tables have mismatched counts")
                for table, result in results.items():
                    if 'error' in result:
                        logger.error(f"{table}: {result['error']}")
                    elif not result.get('match', False):
                        logger.warning(f"{table}: SQLite={result['sqlite_count']}, PostgreSQL={result['postgres_count']}")
                        
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()