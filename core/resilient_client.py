"""
Resilient Alpaca Client Wrapper
Wraps Alpaca API calls with retry, circuit breaker, rate limiting, and timeout handling.
"""

import logging
import time
from typing import Any, Optional, List, Dict
from functools import wraps

from core.resilience import (
    retry_with_backoff,
    get_circuit_breaker,
    get_rate_limiter,
    CircuitBreakerConfig,
    RateLimiterConfig,
    TimeoutConfig,
    AlpacaAPIError,
    RateLimitError,
    ConnectionError,
    TimeoutError,
    CircuitOpenError,
    RETRYABLE_EXCEPTIONS,
)

logger = logging.getLogger(__name__)


# Configuration for Alpaca API resilience
ALPACA_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=2,
    timeout=30.0,
    half_open_max_calls=3,
)

ALPACA_RATE_CONFIG = RateLimiterConfig(
    requests_per_second=3.0,  # Alpaca allows 200/min = 3.33/s, we stay under
    burst_size=10,
    wait_for_token=True,
)

ALPACA_TIMEOUT = TimeoutConfig(
    connect_timeout=5.0,
    read_timeout=30.0,
    total_timeout=60.0,
)


def wrap_alpaca_error(func):
    """
    Decorator that converts Alpaca API exceptions to our custom types.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            error_type = type(e).__name__

            # Rate limit errors
            if '429' in error_str or 'rate limit' in error_str:
                raise RateLimitError(str(e))

            # Connection errors
            if any(x in error_type.lower() for x in ['connection', 'timeout', 'network']):
                raise ConnectionError(str(e))

            # Timeout errors
            if 'timeout' in error_str or 'timed out' in error_str:
                raise TimeoutError(str(e))

            # API errors with status codes
            if hasattr(e, 'status_code'):
                status = e.status_code
                retryable = status in {429, 500, 502, 503, 504}
                raise AlpacaAPIError(str(e), status_code=status, retryable=retryable)

            # Re-raise unknown errors
            raise

    return wrapper


class ResilientAlpacaClient:
    """
    Wrapper around Alpaca client that adds resilience features.

    Features:
    - Automatic retry with exponential backoff
    - Circuit breaker to prevent hammering failed API
    - Rate limiting to stay under API limits
    - Request timeout handling
    - Error classification and handling
    """

    def __init__(self, alpaca_client: Any):
        """
        Initialize with an existing Alpaca client.

        Args:
            alpaca_client: The underlying alpaca_trade_api.REST client
        """
        self._client = alpaca_client
        self._circuit_breaker = get_circuit_breaker("alpaca_api", ALPACA_CIRCUIT_CONFIG)
        self._rate_limiter = get_rate_limiter("alpaca_api", ALPACA_RATE_CONFIG)

        logger.info("ResilientAlpacaClient initialized")

    @property
    def client(self) -> Any:
        """Access the underlying client for direct calls if needed."""
        return self._client

    def _resilient_call(self, method_name: str, *args, **kwargs) -> Any:
        """
        Make a resilient API call with all protections.
        """
        # 1. Rate limit
        self._rate_limiter.acquire()

        # 2. Check circuit breaker
        if not self._circuit_breaker.can_execute():
            reset_time = self._circuit_breaker.get_reset_time()
            raise CircuitOpenError("alpaca_api", reset_time)

        # 3. Execute with retry
        @retry_with_backoff(
            max_retries=3,
            base_delay=1.0,
            retryable_exceptions=RETRYABLE_EXCEPTIONS + (AlpacaAPIError,),
        )
        @wrap_alpaca_error
        def execute():
            method = getattr(self._client, method_name)
            return method(*args, **kwargs)

        try:
            result = execute()
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            self._circuit_breaker.record_failure()
            raise

    # ==========================================================================
    # Account Methods
    # ==========================================================================

    def get_account(self) -> Any:
        """Get account information."""
        return self._resilient_call('get_account')

    # ==========================================================================
    # Position Methods
    # ==========================================================================

    def list_positions(self) -> List[Any]:
        """List all open positions."""
        return self._resilient_call('list_positions')

    def get_position(self, symbol: str) -> Any:
        """Get position for a specific symbol."""
        return self._resilient_call('get_position', symbol)

    def close_position(self, symbol: str, qty: Optional[float] = None) -> Any:
        """Close a position."""
        if qty:
            return self._resilient_call('close_position', symbol, qty=qty)
        return self._resilient_call('close_position', symbol)

    def close_all_positions(self, cancel_orders: bool = True) -> List[Any]:
        """Close all positions."""
        return self._resilient_call('close_all_positions', cancel_orders=cancel_orders)

    # ==========================================================================
    # Order Methods
    # ==========================================================================

    def submit_order(
        self,
        symbol: str,
        qty: Optional[float] = None,
        notional: Optional[float] = None,
        side: str = 'buy',
        type: str = 'market',
        time_in_force: str = 'day',
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        extended_hours: bool = False,
        order_class: Optional[str] = None,
        take_profit: Optional[Dict] = None,
        stop_loss: Optional[Dict] = None,
        trail_price: Optional[float] = None,
        trail_percent: Optional[float] = None,
    ) -> Any:
        """Submit a new order."""
        kwargs = {
            'symbol': symbol,
            'side': side,
            'type': type,
            'time_in_force': time_in_force,
        }

        if qty is not None:
            kwargs['qty'] = qty
        if notional is not None:
            kwargs['notional'] = notional
        if limit_price is not None:
            kwargs['limit_price'] = limit_price
        if stop_price is not None:
            kwargs['stop_price'] = stop_price
        if client_order_id is not None:
            kwargs['client_order_id'] = client_order_id
        if extended_hours:
            kwargs['extended_hours'] = extended_hours
        if order_class is not None:
            kwargs['order_class'] = order_class
        if take_profit is not None:
            kwargs['take_profit'] = take_profit
        if stop_loss is not None:
            kwargs['stop_loss'] = stop_loss
        if trail_price is not None:
            kwargs['trail_price'] = trail_price
        if trail_percent is not None:
            kwargs['trail_percent'] = trail_percent

        return self._resilient_call('submit_order', **kwargs)

    def get_order(self, order_id: str, nested: bool = False) -> Any:
        """Get order by ID."""
        return self._resilient_call('get_order', order_id, nested=nested)

    def get_order_by_client_order_id(self, client_order_id: str) -> Any:
        """Get order by client order ID."""
        return self._resilient_call('get_order_by_client_order_id', client_order_id)

    def list_orders(
        self,
        status: str = 'open',
        limit: int = 50,
        after: Optional[str] = None,
        until: Optional[str] = None,
        direction: str = 'desc',
        nested: bool = False,
        symbols: Optional[List[str]] = None,
    ) -> List[Any]:
        """List orders."""
        return self._resilient_call(
            'list_orders',
            status=status,
            limit=limit,
            after=after,
            until=until,
            direction=direction,
            nested=nested,
            symbols=symbols,
        )

    def cancel_order(self, order_id: str) -> None:
        """Cancel an order."""
        return self._resilient_call('cancel_order', order_id)

    def cancel_all_orders(self) -> List[Any]:
        """Cancel all open orders."""
        return self._resilient_call('cancel_all_orders')

    def replace_order(
        self,
        order_id: str,
        qty: Optional[float] = None,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        trail: Optional[float] = None,
        time_in_force: Optional[str] = None,
        client_order_id: Optional[str] = None,
    ) -> Any:
        """Replace/modify an existing order."""
        kwargs = {'order_id': order_id}
        if qty is not None:
            kwargs['qty'] = qty
        if limit_price is not None:
            kwargs['limit_price'] = limit_price
        if stop_price is not None:
            kwargs['stop_price'] = stop_price
        if trail is not None:
            kwargs['trail'] = trail
        if time_in_force is not None:
            kwargs['time_in_force'] = time_in_force
        if client_order_id is not None:
            kwargs['client_order_id'] = client_order_id

        return self._resilient_call('replace_order', **kwargs)

    # ==========================================================================
    # Market Data Methods
    # ==========================================================================

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
        adjustment: str = 'raw',
        feed: str = 'iex',
    ) -> Any:
        """Get historical bars."""
        return self._resilient_call(
            'get_bars',
            symbol,
            timeframe,
            start=start,
            end=end,
            limit=limit,
            adjustment=adjustment,
            feed=feed,
        )

    def get_crypto_bars(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Any:
        """Get crypto bars."""
        return self._resilient_call(
            'get_crypto_bars',
            symbol,
            timeframe,
            start=start,
            end=end,
            limit=limit,
        )

    def get_latest_bar(self, symbol: str) -> Any:
        """Get latest bar for a symbol."""
        return self._resilient_call('get_latest_bar', symbol)

    def get_latest_bars(self, symbols: List[str]) -> Dict[str, Any]:
        """Get latest bars for multiple symbols."""
        return self._resilient_call('get_latest_bars', symbols)

    def get_latest_crypto_bar(self, symbol: str, exchange: str = 'CBSE') -> Any:
        """Get latest crypto bar."""
        return self._resilient_call('get_latest_crypto_bar', symbol, exchange)

    def get_latest_quote(self, symbol: str) -> Any:
        """Get latest quote for a symbol."""
        return self._resilient_call('get_latest_quote', symbol)

    def get_latest_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """Get latest quotes for multiple symbols."""
        return self._resilient_call('get_latest_quotes', symbols)

    def get_latest_trade(self, symbol: str) -> Any:
        """Get latest trade for a symbol."""
        return self._resilient_call('get_latest_trade', symbol)

    def get_latest_trades(self, symbols: List[str]) -> Dict[str, Any]:
        """Get latest trades for multiple symbols."""
        return self._resilient_call('get_latest_trades', symbols)

    # ==========================================================================
    # Clock & Calendar
    # ==========================================================================

    def get_clock(self) -> Any:
        """Get market clock."""
        return self._resilient_call('get_clock')

    def get_calendar(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[Any]:
        """Get market calendar."""
        return self._resilient_call('get_calendar', start=start, end=end)

    # ==========================================================================
    # Assets
    # ==========================================================================

    def get_asset(self, symbol: str) -> Any:
        """Get asset information."""
        return self._resilient_call('get_asset', symbol)

    def list_assets(
        self,
        status: str = 'active',
        asset_class: Optional[str] = None,
    ) -> List[Any]:
        """List assets."""
        return self._resilient_call('list_assets', status=status, asset_class=asset_class)

    # ==========================================================================
    # Status & Health
    # ==========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get resilience status."""
        return {
            'circuit_breaker': self._circuit_breaker.get_status(),
            'rate_limiter': self._rate_limiter.get_status(),
        }

    def is_healthy(self) -> bool:
        """Check if client is healthy."""
        return self._circuit_breaker.state.value != 'open'

    def reset_circuit_breaker(self) -> None:
        """Manually reset circuit breaker (use with caution)."""
        # Force transition to closed
        self._circuit_breaker._failure_count = 0
        self._circuit_breaker._state = self._circuit_breaker._state.__class__.CLOSED
        logger.info("Circuit breaker manually reset")


def create_resilient_client(alpaca_client: Any) -> ResilientAlpacaClient:
    """
    Factory function to create a resilient client wrapper.

    Args:
        alpaca_client: The underlying Alpaca REST client

    Returns:
        ResilientAlpacaClient wrapper
    """
    return ResilientAlpacaClient(alpaca_client)
