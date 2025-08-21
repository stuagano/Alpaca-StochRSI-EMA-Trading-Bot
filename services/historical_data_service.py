#!/usr/bin/env python3
"""
Historical Data Service for 24/7 Chart Access
Provides cached historical data when markets are closed
"""

import logging
import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
from pathlib import Path
import threading
from queue import Queue
import alpaca_trade_api as tradeapi

from utils.enhanced_logging_config import get_logger, log_performance_metric, LoggingContext

logger = get_logger(__name__)

class HistoricalDataService:
    """Service for managing historical market data with caching"""
    
    def __init__(self, api_key: str, api_secret: str, base_url: str = None):
        """Initialize the historical data service"""
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url or "https://paper-api.alpaca.markets"
        
        # Initialize Alpaca API
        self.api = tradeapi.REST(
            api_key,
            api_secret,
            base_url,
            api_version='v2'
        )
        
        # Database setup
        self.db_path = Path("database/historical_data.db")
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_database()
        
        # Cache configuration
        self.memory_cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.max_cache_size = 1000  # Maximum cached items
        
        # Background sync
        self.sync_queue = Queue()
        self.sync_thread = None
        self.sync_running = False
        
        logger.info("📊 Historical Data Service initialized")
    
    def init_database(self):
        """Initialize SQLite database for historical data"""
        with LoggingContext(logger, "database_initialization"):
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Create historical data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS historical_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol VARCHAR(10) NOT NULL,
                    timestamp DATETIME NOT NULL,
                    timeframe VARCHAR(10) NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER,
                    vwap REAL,
                    trade_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp, timeframe)
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
                ON historical_data(symbol, timestamp, timeframe)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON historical_data(timestamp)
            ''')
            
            # Create metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_metadata (
                    symbol VARCHAR(10) PRIMARY KEY,
                    last_update DATETIME,
                    earliest_data DATETIME,
                    latest_data DATETIME,
                    total_records INTEGER,
                    timeframes TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("✅ Database initialized successfully")
    
    def fetch_historical_data(
        self, 
        symbol: str, 
        timeframe: str = "1Day",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Fetch historical data from Alpaca API
        
        Args:
            symbol: Stock symbol
            timeframe: Timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
            start: Start datetime
            end: End datetime
            limit: Maximum number of bars
        
        Returns:
            DataFrame with historical data
        """
        with LoggingContext(logger, f"fetch_historical_data_{symbol}_{timeframe}"):
            try:
                # Default date range if not specified
                if end is None:
                    end = datetime.now()
                if start is None:
                    # Default to 30 days of data
                    start = end - timedelta(days=30)
                
                # Convert timeframe to Alpaca format
                alpaca_timeframe = self._convert_timeframe(timeframe)
                
                # Fetch from Alpaca API
                # Format dates properly for Alpaca API
                start_str = start.strftime('%Y-%m-%d')
                end_str = end.strftime('%Y-%m-%d')
                
                bars = self.api.get_bars(
                    symbol,
                    alpaca_timeframe,
                    start=start_str,
                    end=end_str,
                    limit=limit,
                    adjustment='raw'
                ).df
                
                if not bars.empty:
                    # Store in database
                    self._store_historical_data(symbol, timeframe, bars)
                    
                    logger.info(f"✅ Fetched {len(bars)} bars for {symbol} ({timeframe})")
                    log_performance_metric("historical_data_fetched", len(bars), {
                        "symbol": symbol,
                        "timeframe": timeframe
                    })
                    
                return bars
                
            except Exception as e:
                logger.error(f"❌ Error fetching historical data: {e}")
                # Try to load from cache
                return self.load_cached_data(symbol, timeframe, start, end)
    
    def load_cached_data(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load historical data from local cache"""
        
        # Check memory cache first
        cache_key = f"{symbol}_{timeframe}_{start}_{end}"
        if cache_key in self.memory_cache:
            cache_entry = self.memory_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                logger.debug(f"📦 Memory cache hit for {cache_key}")
                return cache_entry['data']
        
        # Load from database
        with LoggingContext(logger, f"load_cached_data_{symbol}"):
            try:
                conn = sqlite3.connect(str(self.db_path))
                
                query = '''
                    SELECT timestamp, open, high, low, close, volume
                    FROM historical_data
                    WHERE symbol = ? AND timeframe = ?
                '''
                params = [symbol, timeframe]
                
                if start:
                    query += ' AND timestamp >= ?'
                    params.append(start.isoformat())
                if end:
                    query += ' AND timestamp <= ?'
                    params.append(end.isoformat())
                
                query += ' ORDER BY timestamp'
                
                df = pd.read_sql_query(query, conn, params=params, parse_dates=['timestamp'])
                conn.close()
                
                if not df.empty:
                    df.set_index('timestamp', inplace=True)
                    
                    # Update memory cache
                    self.memory_cache[cache_key] = {
                        'data': df,
                        'timestamp': time.time()
                    }
                    
                    # Manage cache size
                    if len(self.memory_cache) > self.max_cache_size:
                        # Remove oldest entries
                        oldest_keys = sorted(
                            self.memory_cache.keys(),
                            key=lambda k: self.memory_cache[k]['timestamp']
                        )[:100]
                        for key in oldest_keys:
                            del self.memory_cache[key]
                    
                    logger.info(f"📊 Loaded {len(df)} cached bars for {symbol}")
                    return df
                
                return pd.DataFrame()
                
            except Exception as e:
                logger.error(f"❌ Error loading cached data: {e}")
                return pd.DataFrame()
    
    def _store_historical_data(self, symbol: str, timeframe: str, data: pd.DataFrame):
        """Store historical data in database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            
            # Prepare data for insertion
            records = []
            for timestamp, row in data.iterrows():
                records.append((
                    symbol,
                    timestamp,
                    timeframe,
                    float(row.get('open', 0)),
                    float(row.get('high', 0)),
                    float(row.get('low', 0)),
                    float(row.get('close', 0)),
                    int(row.get('volume', 0)),
                    float(row.get('vwap', 0)),
                    int(row.get('trade_count', 0))
                ))
            
            # Insert or replace data
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT OR REPLACE INTO historical_data 
                (symbol, timestamp, timeframe, open, high, low, close, volume, vwap, trade_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', records)
            
            # Update metadata
            cursor.execute('''
                INSERT OR REPLACE INTO data_metadata 
                (symbol, last_update, earliest_data, latest_data, total_records)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                symbol,
                datetime.now(),
                data.index.min(),
                data.index.max(),
                len(data)
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"💾 Stored {len(records)} records for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error storing historical data: {e}")
    
    def get_hybrid_data(
        self,
        symbol: str,
        timeframe: str = "1Day",
        lookback_days: int = 30,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Get hybrid data - live if available, historical as fallback
        
        Args:
            symbol: Stock symbol
            timeframe: Timeframe
            lookback_days: Days of historical data to fetch
            use_cache: Whether to use cached data
        
        Returns:
            DataFrame with market data
        """
        with LoggingContext(logger, f"get_hybrid_data_{symbol}"):
            try:
                # Check if market is open
                clock = self.api.get_clock()
                is_open = clock.is_open
                
                end = datetime.now()
                start = end - timedelta(days=lookback_days)
                
                if is_open:
                    # Try to fetch fresh data
                    logger.info(f"🟢 Market open - fetching live data for {symbol}")
                    data = self.fetch_historical_data(symbol, timeframe, start, end)
                else:
                    # Use cached data
                    logger.info(f"🔴 Market closed - using cached data for {symbol}")
                    data = self.load_cached_data(symbol, timeframe, start, end)
                    
                    if data.empty and use_cache:
                        # If no cache, try to fetch anyway (will get last available)
                        logger.info(f"📊 No cache found, fetching last available data")
                        data = self.fetch_historical_data(symbol, timeframe, start, end)
                
                return data
                
            except Exception as e:
                logger.error(f"❌ Error getting hybrid data: {e}")
                # Always return cached data as fallback
                return self.load_cached_data(symbol, timeframe, start, end)
    
    def start_background_sync(self, symbols: List[str], timeframes: List[str] = None):
        """Start background data synchronization"""
        if self.sync_running:
            logger.warning("⚠️ Background sync already running")
            return
        
        self.sync_running = True
        self.sync_thread = threading.Thread(
            target=self._background_sync_worker,
            args=(symbols, timeframes or ["1Day", "1Hour", "15Min"]),
            daemon=True
        )
        self.sync_thread.start()
        
        logger.info(f"🔄 Started background sync for {len(symbols)} symbols")
    
    def _background_sync_worker(self, symbols: List[str], timeframes: List[str]):
        """Background worker for data synchronization"""
        while self.sync_running:
            try:
                # Check if market is open
                clock = self.api.get_clock()
                
                if clock.is_open:
                    # Sync data for all symbols
                    for symbol in symbols:
                        for timeframe in timeframes:
                            try:
                                self.fetch_historical_data(
                                    symbol, 
                                    timeframe,
                                    start=datetime.now() - timedelta(days=7),
                                    limit=500
                                )
                                time.sleep(0.5)  # Rate limiting
                            except Exception as e:
                                logger.error(f"Sync error for {symbol}: {e}")
                    
                    # Sleep for 5 minutes before next sync
                    time.sleep(300)
                else:
                    # Market closed, sleep for 30 minutes
                    logger.debug("🌙 Market closed, background sync sleeping")
                    time.sleep(1800)
                    
            except Exception as e:
                logger.error(f"❌ Background sync error: {e}")
                time.sleep(60)
    
    def stop_background_sync(self):
        """Stop background data synchronization"""
        self.sync_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        logger.info("🛑 Background sync stopped")
    
    def _convert_timeframe(self, timeframe: str) -> str:
        """Convert timeframe to Alpaca API format"""
        conversion = {
            "1Min": "1Min",
            "5Min": "5Min", 
            "15Min": "15Min",
            "30Min": "30Min",
            "1Hour": "1Hour",
            "4Hour": "4Hour",
            "1Day": "1Day",
            "1Week": "1Week"
        }
        return conversion.get(timeframe, "1Day")
    
    def get_data_stats(self, symbol: str = None) -> Dict[str, Any]:
        """Get statistics about cached data"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            
            if symbol:
                query = '''
                    SELECT 
                        COUNT(*) as total_records,
                        MIN(timestamp) as earliest,
                        MAX(timestamp) as latest,
                        COUNT(DISTINCT timeframe) as timeframes
                    FROM historical_data
                    WHERE symbol = ?
                '''
                result = conn.execute(query, (symbol,)).fetchone()
            else:
                query = '''
                    SELECT 
                        COUNT(*) as total_records,
                        COUNT(DISTINCT symbol) as symbols,
                        MIN(timestamp) as earliest,
                        MAX(timestamp) as latest
                    FROM historical_data
                '''
                result = conn.execute(query).fetchone()
            
            conn.close()
            
            return {
                'total_records': result[0] if result else 0,
                'symbols': result[1] if not symbol and result else 1,
                'earliest_data': result[2] if symbol and result else result[2],
                'latest_data': result[3] if symbol and result else result[3],
                'cache_size_mb': self.db_path.stat().st_size / 1024 / 1024 if self.db_path.exists() else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting data stats: {e}")
            return {}

# Singleton instance
_historical_service = None

def get_historical_data_service(api_key: str = None, api_secret: str = None) -> HistoricalDataService:
    """Get or create historical data service instance"""
    global _historical_service
    
    if _historical_service is None:
        if not api_key or not api_secret:
            # Try to load from environment
            import os
            api_key = os.getenv('ALPACA_API_KEY')
            api_secret = os.getenv('ALPACA_SECRET_KEY')
        
        _historical_service = HistoricalDataService(api_key, api_secret)
    
    return _historical_service