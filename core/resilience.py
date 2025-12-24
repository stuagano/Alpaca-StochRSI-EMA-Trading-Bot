"""
Resilience Utilities for Trading Bot
Provides retry logic, circuit breakers, rate limiting, and timeout handling.
"""

import time
import threading
import logging
from functools import wraps
from typing import Callable, Any, Optional, Tuple, Type, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exceptions
# =============================================================================

class TradingBotException(Exception):
    """Base exception for all trading bot errors."""
    pass


class AlpacaAPIError(TradingBotException):
    """Error from Alpaca API."""
    def __init__(self, message: str, status_code: Optional[int] = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class RateLimitError(AlpacaAPIError):
    """Rate limit exceeded - always retryable."""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(message, status_code=429, retryable=True)
        self.retry_after = retry_after or 60


class ConnectionError(TradingBotException):
    """Network connection error - usually retryable."""
    def __init__(self, message: str = "Connection failed"):
        super().__init__(message)
        self.retryable = True


class TimeoutError(TradingBotException):
    """Request timeout - usually retryable."""
    def __init__(self, message: str = "Request timed out"):
        super().__init__(message)
        self.retryable = True


class DataError(TradingBotException):
    """Error with data quality or availability."""
    pass


class InsufficientDataError(DataError):
    """Not enough data for calculations."""
    pass


class ConfigurationError(TradingBotException):
    """Configuration validation error."""
    pass


class ServiceNotFoundError(TradingBotException):
    """Service not found in registry."""
    pass


class CircuitOpenError(TradingBotException):
    """Circuit breaker is open, request rejected."""
    def __init__(self, service_name: str, reset_time: datetime):
        super().__init__(f"Circuit breaker open for {service_name}, resets at {reset_time}")
        self.service_name = service_name
        self.reset_time = reset_time


class PositionSyncError(TradingBotException):
    """Error synchronizing positions with broker."""
    pass


# =============================================================================
# Retry Decorator with Exponential Backoff
# =============================================================================

# Default retryable exceptions
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    RateLimitError,
    ConnectionError,
    TimeoutError,
)

# HTTP status codes that should trigger retry
RETRYABLE_STATUS_CODES: Set[int] = {429, 500, 502, 503, 504}


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        jitter: Add random jitter to prevent thundering herd
        retryable_exceptions: Tuple of exception types to retry
        on_retry: Optional callback called on each retry (exception, attempt_number)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt >= max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    # Add jitter (±25%)
                    if jitter:
                        import random
                        delay = delay * (0.75 + random.random() * 0.5)

                    # Check for retry_after header (rate limits)
                    if hasattr(e, 'retry_after') and e.retry_after:
                        delay = max(delay, e.retry_after)

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    if on_retry:
                        on_retry(e, attempt + 1)

                    time.sleep(delay)
                except Exception as e:
                    # Non-retryable exception
                    logger.error(f"{func.__name__} failed with non-retryable error: {e}")
                    raise

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


# Async version
def async_retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS,
):
    """Async version of retry_with_backoff."""
    import asyncio

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt >= max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise

                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    if jitter:
                        import random
                        delay = delay * (0.75 + random.random() * 0.5)

                    if hasattr(e, 'retry_after') and e.retry_after:
                        delay = max(delay, e.retry_after)

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    await asyncio.sleep(delay)
                except Exception as e:
                    logger.error(f"{func.__name__} failed with non-retryable error: {e}")
                    raise

            if last_exception:
                raise last_exception

        return wrapper
    return decorator


# =============================================================================
# Circuit Breaker
# =============================================================================

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 2          # Successes in half-open to close
    timeout: float = 30.0               # Seconds before half-open
    half_open_max_calls: int = 3        # Max calls in half-open state


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service failing, requests rejected immediately
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._lock = threading.RLock()

        logger.info(f"CircuitBreaker '{name}' initialized in CLOSED state")

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._check_state_transition()
            return self._state

    def _check_state_transition(self) -> None:
        """Check if state should transition based on timeout."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed >= self.config.timeout:
                    self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0
        elif new_state == CircuitState.OPEN:
            self._last_failure_time = datetime.now()

        logger.info(f"CircuitBreaker '{self.name}': {old_state.value} -> {new_state.value}")

    def can_execute(self) -> bool:
        """Check if request can be executed."""
        with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.CLOSED:
                return True
            elif self._state == CircuitState.OPEN:
                return False
            else:  # HALF_OPEN
                return self._half_open_calls < self.config.half_open_max_calls

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def get_reset_time(self) -> Optional[datetime]:
        """Get the time when circuit will transition to half-open."""
        with self._lock:
            if self._state == CircuitState.OPEN and self._last_failure_time:
                return self._last_failure_time + timedelta(seconds=self.config.timeout)
            return None

    def __call__(self, func: Callable) -> Callable:
        """Use as decorator."""
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not self.can_execute():
                reset_time = self.get_reset_time()
                raise CircuitOpenError(self.name, reset_time)

            if self._state == CircuitState.HALF_OPEN:
                with self._lock:
                    self._half_open_calls += 1

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise

        return wrapper

    def get_status(self) -> dict:
        """Get circuit breaker status."""
        with self._lock:
            return {
                'name': self.name,
                'state': self._state.value,
                'failure_count': self._failure_count,
                'success_count': self._success_count,
                'reset_time': self.get_reset_time().isoformat() if self.get_reset_time() else None,
            }


# Global circuit breakers registry
_circuit_breakers: dict[str, CircuitBreaker] = {}
_cb_lock = threading.Lock()


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    with _cb_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, config)
        return _circuit_breakers[name]


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator to wrap function with circuit breaker."""
    def decorator(func: Callable) -> Callable:
        cb = get_circuit_breaker(name, config)
        return cb(func)
    return decorator


# =============================================================================
# Rate Limiter (Token Bucket)
# =============================================================================

@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter."""
    requests_per_second: float = 3.0    # Token refill rate
    burst_size: int = 10                # Maximum tokens (burst capacity)
    wait_for_token: bool = True         # Wait for token or raise immediately


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter.

    Allows burst traffic up to burst_size, then limits to requests_per_second.
    """

    def __init__(self, config: Optional[RateLimiterConfig] = None):
        self.config = config or RateLimiterConfig()

        self._tokens = float(self.config.burst_size)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

        logger.debug(
            f"RateLimiter initialized: {self.config.requests_per_second}/s, "
            f"burst={self.config.burst_size}"
        )

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.config.requests_per_second
        self._tokens = min(self._tokens + tokens_to_add, self.config.burst_size)
        self._last_refill = now

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire a token, blocking if necessary.

        Args:
            timeout: Maximum time to wait for token (None = use config default)

        Returns:
            True if token acquired, False if timeout

        Raises:
            RateLimitError: If wait_for_token is False and no token available
        """
        start_time = time.monotonic()
        max_wait = timeout if timeout is not None else (10.0 if self.config.wait_for_token else 0)

        while True:
            with self._lock:
                self._refill()

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True

            # Check timeout
            elapsed = time.monotonic() - start_time
            if elapsed >= max_wait:
                if not self.config.wait_for_token:
                    raise RateLimitError("Rate limit exceeded, no token available")
                return False

            # Calculate wait time for next token
            with self._lock:
                wait_time = (1.0 - self._tokens) / self.config.requests_per_second

            # Don't wait longer than remaining timeout
            wait_time = min(wait_time, max_wait - elapsed, 0.1)

            if wait_time > 0:
                time.sleep(wait_time)

    def get_status(self) -> dict:
        """Get rate limiter status."""
        with self._lock:
            self._refill()
            return {
                'available_tokens': self._tokens,
                'burst_size': self.config.burst_size,
                'requests_per_second': self.config.requests_per_second,
            }


# Global rate limiters registry
_rate_limiters: dict[str, TokenBucketRateLimiter] = {}
_rl_lock = threading.Lock()


def get_rate_limiter(name: str, config: Optional[RateLimiterConfig] = None) -> TokenBucketRateLimiter:
    """Get or create a rate limiter by name."""
    with _rl_lock:
        if name not in _rate_limiters:
            _rate_limiters[name] = TokenBucketRateLimiter(config)
        return _rate_limiters[name]


def rate_limited(name: str, config: Optional[RateLimiterConfig] = None):
    """Decorator to apply rate limiting to a function."""
    def decorator(func: Callable) -> Callable:
        limiter = get_rate_limiter(name, config)

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            limiter.acquire()
            return func(*args, **kwargs)

        return wrapper
    return decorator


# =============================================================================
# Timeout Utilities
# =============================================================================

@dataclass
class TimeoutConfig:
    """Configuration for request timeouts."""
    connect_timeout: float = 5.0        # Connection timeout in seconds
    read_timeout: float = 30.0          # Read timeout in seconds
    total_timeout: float = 60.0         # Total request timeout

    def as_tuple(self) -> Tuple[float, float]:
        """Return as (connect, read) tuple for requests library."""
        return (self.connect_timeout, self.read_timeout)


# Default timeout configuration
DEFAULT_TIMEOUT = TimeoutConfig()


def with_timeout(timeout: Optional[TimeoutConfig] = None):
    """
    Decorator to enforce timeout on synchronous functions.

    Note: This uses threading and may not interrupt all operations.
    For proper timeout support, use async/await with asyncio.timeout().
    """
    timeout_config = timeout or DEFAULT_TIMEOUT

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=timeout_config.total_timeout)

            if thread.is_alive():
                raise TimeoutError(
                    f"{func.__name__} timed out after {timeout_config.total_timeout}s"
                )

            if exception[0]:
                raise exception[0]

            return result[0]

        return wrapper
    return decorator


# =============================================================================
# Combined Resilience Decorator
# =============================================================================

def resilient(
    circuit_breaker_name: Optional[str] = None,
    rate_limiter_name: Optional[str] = None,
    max_retries: int = 3,
    timeout: Optional[TimeoutConfig] = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS,
):
    """
    Combined resilience decorator that applies:
    1. Rate limiting (if configured)
    2. Circuit breaker (if configured)
    3. Retry with exponential backoff
    4. Timeout (if configured)

    Example:
        @resilient(
            circuit_breaker_name="alpaca_api",
            rate_limiter_name="alpaca_api",
            max_retries=3,
        )
        def call_alpaca_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Build decorator chain from inside out
        wrapped = func

        # 1. Apply retry (innermost)
        wrapped = retry_with_backoff(
            max_retries=max_retries,
            retryable_exceptions=retryable_exceptions,
        )(wrapped)

        # 2. Apply circuit breaker
        if circuit_breaker_name:
            cb = get_circuit_breaker(circuit_breaker_name)
            wrapped = cb(wrapped)

        # 3. Apply rate limiter (outermost, applied first)
        if rate_limiter_name:
            wrapped = rate_limited(rate_limiter_name)(wrapped)

        # 4. Apply timeout
        if timeout:
            wrapped = with_timeout(timeout)(wrapped)

        return wrapped
    return decorator


# =============================================================================
# Health Check Utilities
# =============================================================================

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Health check result."""
    service: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    details: dict = field(default_factory=dict)


def get_resilience_status() -> dict:
    """Get status of all resilience components."""
    return {
        'circuit_breakers': {
            name: cb.get_status() for name, cb in _circuit_breakers.items()
        },
        'rate_limiters': {
            name: rl.get_status() for name, rl in _rate_limiters.items()
        },
    }
