import logging
import pandas as pd
from datetime import datetime, timedelta
import alpaca_trade_api as tradeapi

logger = logging.getLogger(__name__)

class AlpacaDataService:
    """
    Production-ready data service using the legacy alpaca_trade_api.
    """
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://paper-api.alpaca.markets"):
        self.api = tradeapi.REST(api_key, secret_key, base_url)
        logger.info("AlpacaDataService (Legacy) initialized.")

    def get_market_data(self, symbol: str, lookback_minutes: int = 50) -> pd.DataFrame:
        """
        Fetch historical bars for a symbol using legacy REST API.
        """
        try:
            # Normalize symbol
            normalized_symbol = symbol
            if '/' not in normalized_symbol and normalized_symbol.endswith('USD'):
                normalized_symbol = f"{normalized_symbol[:-3]}/USD"

            end = datetime.now().replace(microsecond=0)
            start = end - timedelta(minutes=lookback_minutes + 15)

            # Format as RFC3339 (Alpaca requires this format without microseconds)
            start_str = start.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end.strftime('%Y-%m-%dT%H:%M:%SZ')

            # Using legacy get_crypto_bars (or get_bars for newer REST versions)
            # alpaca-trade-api handles the crypto specific endpoint
            bars = self.api.get_crypto_bars(
                normalized_symbol,
                tradeapi.rest.TimeFrame.Minute,
                start=start_str,
                end=end_str
            ).df
            
            if bars.empty:
                logger.warning(f"No bars returned for {normalized_symbol}")
                return pd.DataFrame()
            
            # Legacy df usually has timestamp as index and columns: open, high, low, close, volume
            df = bars[['open', 'high', 'low', 'close', 'volume']].copy()
            df['symbol'] = symbol
            
            return df

        except Exception as e:
            logger.error(f"Error fetching legacy market data for {symbol}: {e}")
            return pd.DataFrame()
