"""
Unified Data Manager with connection pooling, circuit breaker, and memory management.
This replaces both realtime_manager.py and realtime_manager_flask.py.
"""
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import alpaca_trade_api as alpaca
import threading
import time
import queue
import ta
import logging
from typing import Dict, List, Optional, Any, Tuple
from alpaca_trade_api.stream import Stream

from .database_abstraction import get_database
from .memory_cache import cache_manager
from .circuit_breaker import circuit_manager, CircuitBreakerError

logger = logging.getLogger(__name__)


class UnifiedDataManager:
    """
    Unified data manager with comprehensive features:
    - Thread-safe database operations with connection pooling
    - Memory-managed price cache with TTL
    - Circuit breaker pattern for API failure resilience
    - Real-time streaming with proper resource management
    - Comprehensive error handling and logging
    """
    
    def __init__(self):
        self.api: Optional[alpaca.REST] = None
        self.stream: Optional[Stream] = None
        self.is_streaming = False
        self.data_queue = queue.Queue()
        self.last_update = datetime.now()
        self.update_thread: Optional[threading.Thread] = None
        self.stream_thread: Optional[threading.Thread] = None
        
        # Initialize services
        self.db = get_database()
        self.price_cache = cache_manager.get_cache(
            'price_cache',
            max_size=10000,
            default_ttl=10.0,  # 10 second TTL for prices
            cleanup_interval=30.0
        )
        self.indicator_cache = cache_manager.get_cache(
            'indicator_cache',
            max_size=1000,
            default_ttl=30.0,  # 30 second TTL for indicators
            cleanup_interval=60.0
        )
        
        # Circuit breakers for different API endpoints
        self.quote_breaker = circuit_manager.get_breaker(
            'alpaca_quotes',
            failure_threshold=5,
            recovery_timeout=60
        )
        self.bars_breaker = circuit_manager.get_breaker(
            'alpaca_bars',
            failure_threshold=3,
            recovery_timeout=120
        )
        self.account_breaker = circuit_manager.get_breaker(
            'alpaca_account',
            failure_threshold=5,
            recovery_timeout=60
        )
        
        # Initialize API
        self.initialize_api()
    
    def initialize_api(self) -> bool:
        """Initialize Alpaca API connection with proper error handling."""
        try:
            # Try to get credentials from environment variables first
            api_key = os.getenv('APCA_API_KEY_ID')
            secret_key = os.getenv('APCA_API_SECRET_KEY')
            base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
            
            # If not in environment, fallback to AUTH file
            if not api_key or not secret_key:
                if not os.path.exists('AUTH/authAlpaca.txt'):
                    raise FileNotFoundError("No API credentials found in environment or AUTH/authAlpaca.txt")
                
                with open('AUTH/authAlpaca.txt', 'r') as f:
                    content = f.read().strip()
                
                # Parse credentials (JSON or line format)
                try:
                    auth_data = json.loads(content)
                    api_key = auth_data.get('APCA-API-KEY-ID', '').strip()
                    secret_key = auth_data.get('APCA-API-SECRET-KEY', '').strip()
                    base_url = auth_data.get('BASE-URL', 'https://paper-api.alpaca.markets').strip()
                except json.JSONDecodeError:
                    lines = content.split('\n')
                    if len(lines) < 2:
                        raise ValueError("Invalid authAlpaca.txt format")
                    api_key = lines[0].strip()
                    secret_key = lines[1].strip()
                base_url = lines[2].strip() if len(lines) > 2 else 'https://paper-api.alpaca.markets'
            
            if not api_key or not secret_key:
                raise ValueError("API key and secret key cannot be empty")
            
            # Clean base URL
            base_url = base_url.rstrip('/').rstrip('/v2')
            
            self.api = alpaca.REST(api_key, secret_key, base_url, api_version='v2')
            
            # Test connection with circuit breaker
            self.account_breaker.call(self.api.get_account)
            
            logger.info(f"Alpaca API initialized successfully - {base_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca API: {e}")
            self.api = None
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information with circuit breaker protection."""
        if not self.api:
            raise Exception("Alpaca API not initialized")
        
        try:
            account = self.account_breaker.call(self.api.get_account)
            
            # Handle different account object attributes safely
            day_pl = 0
            if hasattr(account, 'unrealized_pl') and account.unrealized_pl:
                day_pl = float(account.unrealized_pl)
            elif hasattr(account, 'unrealized_intraday_pl') and account.unrealized_intraday_pl:
                day_pl = float(account.unrealized_intraday_pl)
            
            return {
                'portfolio_value': float(account.portfolio_value),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'day_pl': day_pl,
                'equity': float(account.equity),
                'account_id': account.id,
                'status': account.status
            }
            
        except CircuitBreakerError:
            logger.warning("Account info circuit breaker is open")
            raise
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            raise
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get positions with circuit breaker protection."""
        if not self.api:
            raise Exception("Alpaca API not initialized")
        
        try:
            positions = self.account_breaker.call(self.api.list_positions)
            
            result = []
            for pos in positions:
                result.append({
                    'symbol': pos.symbol,
                    'qty': int(pos.qty),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price),
                    'market_value': float(pos.market_value),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc) * 100,
                    'change_today': float(pos.change_today) if pos.change_today else 0.0,
                    'side': 'long' if int(pos.qty) > 0 else 'short'
                })
            
            return result
            
        except CircuitBreakerError:
            logger.warning("Positions circuit breaker is open")
            raise
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price with caching and circuit breaker protection."""
        if not self.api:
            logger.warning("Alpaca API not initialized")
            return None
        
        # Check cache first
        cached_price = self.price_cache.get(symbol)
        if cached_price is not None:
            return cached_price
        
        # Skip crypto symbols for paper trading
        if symbol.endswith('USD') and len(symbol) > 4:
            logger.debug(f"Skipping crypto symbol {symbol}")
            return None
        
        try:
            quote = self.quote_breaker.call(self.api.get_latest_quote, symbol)
            
            if not quote:
                logger.warning(f"No quote data for {symbol}")
                return None
            
            # Calculate mid price
            bid_price = float(quote.bid_price) if quote.bid_price else 0
            ask_price = float(quote.ask_price) if quote.ask_price else 0
            
            if bid_price > 0 and ask_price > 0:
                price = (bid_price + ask_price) / 2
            elif ask_price > 0:
                price = ask_price
            elif bid_price > 0:
                price = bid_price
            else:
                logger.warning(f"Invalid quote data for {symbol}")
                return None
            
            # Cache the result
            self.price_cache.set(symbol, price)
            
            # Store in persistent cache
            try:
                self.db.store_price_cache(symbol, price, datetime.now())
            except Exception as e:
                logger.debug(f"Failed to store price cache: {e}")
            
            return price
            
        except CircuitBreakerError:
            logger.warning(f"Quote circuit breaker is open for {symbol}")
            # Try to get from persistent cache as fallback
            cached = self.db.get_cached_price(symbol, max_age_seconds=300)  # 5 minute fallback
            if cached:
                price, timestamp = cached
                logger.info(f"Using fallback cached price for {symbol}: {price}")
                return price
            return None
            
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def get_historical_data(
        self,
        symbol: str,
        timeframe: str = '1Min',
        start_hours_ago: int = 24,
        limit: int = 200
    ) -> pd.DataFrame:
        """Get historical data with database caching and circuit breaker protection."""
        if not self.api:
            logger.warning("Alpaca API not initialized")
            return pd.DataFrame()
        
        # Skip crypto symbols
        if symbol.endswith('USD') and len(symbol) > 4:
            logger.debug(f"Skipping crypto symbol {symbol}")
            return pd.DataFrame()
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=start_hours_ago)
        
        # Try database first
        try:
            db_data = self.db.get_historical_data(symbol, timeframe, start_time, end_time, limit)
            if not db_data.empty and len(db_data) >= min(limit, 50):  # Accept if we have enough data
                logger.debug(f"Retrieved {len(db_data)} bars from database for {symbol}")
                return db_data.tail(limit)
        except Exception as e:
            logger.debug(f"Database retrieval failed for {symbol}: {e}")
        
        # Fetch from API with circuit breaker
        try:
            tf_map = {
                '1Min': '1Min', '5Min': '5Min', '15Min': '15Min',
                '1Hour': '1Hour', '1Day': '1Day'
            }
            alpaca_tf = tf_map.get(timeframe, '1Min')
            
            # Try different time ranges if no data found
            time_ranges = [start_hours_ago, 48, 72, 168]  # Expand search range
            
            for hours_ago in time_ranges:
                try:
                    search_start = end_time - timedelta(hours=hours_ago)
                    start_str = search_start.strftime('%Y-%m-%dT%H:%M:%SZ')
                    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                    
                    bars = self.bars_breaker.call(
                        self.api.get_bars,
                        symbol,
                        alpaca_tf,
                        start=start_str,
                        end=end_str,
                        limit=limit
                    )
                    
                    if bars and len(bars) > 0:
                        # Convert to DataFrame
                        data = []
                        for bar in bars:
                            data.append({
                                'open': float(bar.o),
                                'high': float(bar.h),
                                'low': float(bar.l),
                                'close': float(bar.c),
                                'volume': int(bar.v),
                                'timestamp': bar.t
                            })
                        
                        if data:
                            df = pd.DataFrame(data)
                            df.set_index('timestamp', inplace=True)
                            
                            # Store in database for future use
                            try:
                                self.db.store_historical_data(symbol, timeframe, df)
                            except Exception as e:
                                logger.debug(f"Failed to store historical data: {e}")
                            
                            logger.debug(f"Fetched {len(df)} bars from API for {symbol}")
                            return df
                    
                    logger.debug(f"No data for {symbol} in {hours_ago}h range, expanding search...")
                    
                except Exception as e:
                    logger.debug(f"API fetch failed for {symbol} ({hours_ago}h): {e}")
                    continue
            
            logger.warning(f"No historical data found for {symbol}")
            return pd.DataFrame()
            
        except CircuitBreakerError:
            logger.warning(f"Bars circuit breaker is open for {symbol}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame, config: Dict) -> Dict[str, Any]:
        """Calculate technical indicators with caching."""
        if df.empty or 'close' not in df.columns:
            return {}
        
        # Create cache key
        cache_key = f"{hash(df.index[-1].isoformat())}_{hash(str(config))}"
        cached_indicators = self.indicator_cache.get(cache_key)
        if cached_indicators is not None:
            return cached_indicators
        
        indicators = {}
        
        try:
            # EMA
            if config['indicators'].get('EMA') == "True":
                ema_period = config['indicators']['EMA_params']['ema_period']
                if len(df) >= ema_period:
                    ema = ta.trend.ema_indicator(df['close'], window=ema_period)
                    if not ema.empty and not pd.isna(ema.iloc[-1]):
                        indicators['EMA'] = float(ema.iloc[-1])
            
            # StochRSI
            if config['indicators'].get('stochRSI') == "True":
                params = config['indicators']['stochRSI_params']
                rsi_length = params['rsi_length']
                stoch_length = params['stoch_length']
                k_smooth = params['K']
                d_smooth = params['D']
                
                min_length = max(rsi_length, stoch_length, k_smooth, d_smooth)
                if len(df) >= min_length:
                    # Calculate RSI
                    rsi = ta.momentum.rsi(df['close'], window=rsi_length)
                    if not rsi.empty and not pd.isna(rsi.iloc[-1]):
                        indicators['RSI'] = float(rsi.iloc[-1])
                    
                    # Calculate StochRSI
                    stoch_rsi_k = ta.momentum.stochrsi_k(
                        df['close'], window=stoch_length, smooth1=k_smooth, smooth2=d_smooth
                    )
                    stoch_rsi_d = ta.momentum.stochrsi_d(
                        df['close'], window=stoch_length, smooth1=k_smooth, smooth2=d_smooth
                    )
                    
                    if not stoch_rsi_k.empty and not pd.isna(stoch_rsi_k.iloc[-1]):
                        indicators['StochRSI_K'] = float(stoch_rsi_k.iloc[-1]) * 100
                    if not stoch_rsi_d.empty and not pd.isna(stoch_rsi_d.iloc[-1]):
                        indicators['StochRSI_D'] = float(stoch_rsi_d.iloc[-1]) * 100
            
            # Stochastic
            if config['indicators'].get('stoch') == "True":
                params = config['indicators']['stoch_params']
                k_length = params['K_Length']
                smooth_k = params['smooth_K']
                smooth_d = params['smooth_D']
                
                if len(df) >= k_length and all(col in df.columns for col in ['high', 'low']):
                    stoch_k = ta.momentum.stoch(
                        df['high'], df['low'], df['close'],
                        window=k_length, smooth_window=smooth_k
                    )
                    stoch_d = ta.momentum.stoch_signal(
                        df['high'], df['low'], df['close'],
                        window=k_length, smooth_window=smooth_d
                    )
                    
                    if not stoch_k.empty and not pd.isna(stoch_k.iloc[-1]):
                        indicators['Stoch_K'] = float(stoch_k.iloc[-1])
                    if not stoch_d.empty and not pd.isna(stoch_d.iloc[-1]):
                        indicators['Stoch_D'] = float(stoch_d.iloc[-1])
            
            # Cache the results
            self.indicator_cache.set(cache_key, indicators)
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
        
        return indicators
    
    def calculate_indicators_series(self, df: pd.DataFrame, config: Dict) -> Dict[str, List]:
        """Calculate indicator series for charting."""
        if df.empty or 'close' not in df.columns:
            return {}
        
        indicators = {}
        
        try:
            # EMA series
            if config['indicators'].get('EMA') == "True":
                ema_period = config['indicators']['EMA_params']['ema_period']
                if len(df) >= ema_period:
                    ema = ta.trend.ema_indicator(df['close'], window=ema_period)
                    indicators['EMA'] = ema.fillna(method='ffill').tolist()
            
            # StochRSI series
            if config['indicators'].get('stochRSI') == "True":
                params = config['indicators']['stochRSI_params']
                rsi_length = params['rsi_length']
                stoch_length = params['stoch_length']
                k_smooth = params['K']
                d_smooth = params['D']
                
                min_length = max(rsi_length, stoch_length, k_smooth, d_smooth)
                if len(df) >= min_length:
                    rsi = ta.momentum.rsi(df['close'], window=rsi_length)
                    indicators['RSI'] = rsi.fillna(method='ffill').tolist()
                    
                    stoch_rsi_k = ta.momentum.stochrsi_k(
                        df['close'], window=stoch_length, smooth1=k_smooth, smooth2=d_smooth
                    )
                    stoch_rsi_d = ta.momentum.stochrsi_d(
                        df['close'], window=stoch_length, smooth1=k_smooth, smooth2=d_smooth
                    )
                    
                    indicators['StochRSI_K'] = (stoch_rsi_k * 100).fillna(method='ffill').tolist()
                    indicators['StochRSI_D'] = (stoch_rsi_d * 100).fillna(method='ffill').tolist()
            
            # Stochastic series
            if config['indicators'].get('stoch') == "True":
                params = config['indicators']['stoch_params']
                k_length = params['K_Length']
                smooth_k = params['smooth_K']
                smooth_d = params['smooth_D']
                
                if len(df) >= k_length and all(col in df.columns for col in ['high', 'low']):
                    stoch_k = ta.momentum.stoch(
                        df['high'], df['low'], df['close'],
                        window=k_length, smooth_window=smooth_k
                    )
                    stoch_d = ta.momentum.stoch_signal(
                        df['high'], df['low'], df['close'],
                        window=k_length, smooth_window=smooth_d
                    )
                    
                    indicators['Stoch_K'] = stoch_k.fillna(method='ffill').tolist()
                    indicators['Stoch_D'] = stoch_d.fillna(method='ffill').tolist()
        
        except Exception as e:
            logger.error(f"Error calculating indicator series: {e}")
        
        return indicators
    
    def start_data_stream(self, tickers: List[str], update_interval: float = 5.0) -> bool:
        """Start real-time data streaming with proper resource management."""
        if self.is_streaming:
            logger.warning("Data stream already running")
            return True
        
        if not self.api or not tickers:
            logger.error("Cannot start stream: API not initialized or no tickers provided")
            return False
        
        self.is_streaming = True
        logger.info(f"Starting data stream for {len(tickers)} tickers")
        
        def stream_worker():
            """Background worker for data updates."""
            consecutive_failures = 0
            max_failures = 10
            
            while self.is_streaming:
                try:
                    start_time = time.time()
                    
                    # Update prices
                    for ticker in tickers:
                        if not self.is_streaming:
                            break
                        
                        try:
                            price = self.get_latest_price(ticker)
                            if price:
                                logger.debug(f"Updated price for {ticker}: {price}")
                        except Exception as e:
                            logger.debug(f"Failed to update price for {ticker}: {e}")
                    
                    # Update account info (less frequently)
                    if int(time.time()) % 30 == 0:  # Every 30 seconds
                        try:
                            account_info = self.get_account_info()
                            logger.debug("Updated account info")
                        except Exception as e:
                            logger.debug(f"Failed to update account info: {e}")
                    
                    self.last_update = datetime.now()
                    consecutive_failures = 0
                    
                    # Dynamic sleep based on processing time
                    processing_time = time.time() - start_time
                    sleep_time = max(0.1, update_interval - processing_time)
                    time.sleep(sleep_time)
                    
                except Exception as e:
                    consecutive_failures += 1
                    logger.error(f"Stream worker error ({consecutive_failures}/{max_failures}): {e}")
                    
                    if consecutive_failures >= max_failures:
                        logger.error("Too many consecutive failures, stopping stream")
                        self.is_streaming = False
                        break
                    
                    time.sleep(min(consecutive_failures * 2, 30))  # Exponential backoff
            
            logger.info("Data stream worker stopped")
        
        # Start worker thread
        self.update_thread = threading.Thread(
            target=stream_worker,
            daemon=True,
            name="DataStreamWorker"
        )
        self.update_thread.start()
        
        return True
    
    def stop_data_stream(self) -> None:
        """Stop data streaming and clean up resources."""
        if not self.is_streaming:
            return
        
        logger.info("Stopping data stream...")
        self.is_streaming = False
        
        # Wait for threads to finish
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=10)
        
        if self.stream_thread and self.stream_thread.is_alive():
            if self.stream:
                self.stream.stop()
            self.stream_thread.join(timeout=10)
        
        logger.info("Data stream stopped")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'price_cache': self.price_cache.get_stats(),
            'indicator_cache': self.indicator_cache.get_stats(),
            'circuit_breakers': circuit_manager.get_status()
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health information."""
        return {
            'api_initialized': self.api is not None,
            'streaming': self.is_streaming,
            'last_update': self.last_update.isoformat(),
            'cache_stats': self.get_cache_stats(),
            'database_stats': self.db.get_database_stats(),
            'circuit_breakers': circuit_manager.get_status()
        }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Starting data manager cleanup...")
        
        self.stop_data_stream()
        
        # Reset circuit breakers
        circuit_manager.reset_all()
        
        # Shutdown caches
        cache_manager.shutdown_all()
        
        # Close database connections
        self.db.close()
        
        logger.info("Data manager cleanup complete")


# Singleton instance
_data_manager_instance: Optional[UnifiedDataManager] = None
_instance_lock = threading.RLock()


def get_data_manager() -> UnifiedDataManager:
    """Get singleton instance of UnifiedDataManager."""
    global _data_manager_instance
    
    with _instance_lock:
        if _data_manager_instance is None:
            _data_manager_instance = UnifiedDataManager()
        return _data_manager_instance


def cleanup_data_manager() -> None:
    """Clean up singleton data manager."""
    global _data_manager_instance
    
    with _instance_lock:
        if _data_manager_instance is not None:
            _data_manager_instance.cleanup()
            _data_manager_instance = None