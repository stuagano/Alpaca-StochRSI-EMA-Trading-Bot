"""
Error handling decorators for Flask API routes.

Provides DRY-compliant decorators to eliminate duplicate error handling
patterns across blueprints.
"""

import functools
import logging
import time
from typing import Any, Callable, Optional, Type, Tuple

from flask import current_app, jsonify

logger = logging.getLogger(__name__)


def require_service(service_name: str, error_message: Optional[str] = None):
    """
    Decorator that ensures a service is available before executing the route.

    Eliminates the repeated pattern of:
        service = getattr(current_app, service_name, None)
        if not service:
            return jsonify({'error': 'Service not initialized'}), 503

    Args:
        service_name: Name of the service attribute on current_app
        error_message: Custom error message (optional)

    Usage:
        @bp.route('/data')
        @require_service('pnl_service')
        def get_data(service):
            return jsonify(service.get_data())
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            service = getattr(current_app, service_name, None)
            if not service:
                msg = error_message or f'{service_name} not initialized'
                logger.warning(f"Service unavailable: {service_name}")
                return jsonify({'error': msg}), 503

            # Inject service as first argument
            return f(service, *args, **kwargs)
        return wrapper
    return decorator


def handle_api_errors(
    default_status: int = 500,
    default_message: str = 'Internal server error',
    log_level: str = 'error'
):
    """
    Decorator that provides consistent error handling for API routes.

    Eliminates the repeated try/except pattern in routes.

    Args:
        default_status: Default HTTP status code for errors
        default_message: Default error message
        log_level: Logging level ('error', 'warning', 'info')

    Usage:
        @bp.route('/data')
        @handle_api_errors(default_status=500)
        def get_data():
            return jsonify(risky_operation())
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except ValueError as e:
                logger.warning(f"Validation error in {f.__name__}: {e}")
                return jsonify({'error': str(e)}), 400
            except PermissionError as e:
                logger.warning(f"Permission denied in {f.__name__}: {e}")
                return jsonify({'error': 'Permission denied'}), 403
            except FileNotFoundError as e:
                logger.warning(f"Resource not found in {f.__name__}: {e}")
                return jsonify({'error': 'Resource not found'}), 404
            except Exception as e:
                log_func = getattr(logger, log_level, logger.error)
                log_func(f"Error in {f.__name__}: {e}", exc_info=True)
                return jsonify({'error': default_message}), default_status
        return wrapper
    return decorator


def retry_on_transient(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (ConnectionError, TimeoutError)
):
    """
    Decorator that retries a function on transient errors.

    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        exceptions: Tuple of exception types to retry on

    Usage:
        @retry_on_transient(max_attempts=3)
        def fetch_external_data():
            return requests.get(url).json()
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for "
                            f"{f.__name__}, retrying in {wait_time:.1f}s: {e}"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {f.__name__}: {e}"
                        )

            raise last_exception
        return wrapper
    return decorator


def validate_json_request(*required_fields: str):
    """
    Decorator that validates required fields in JSON request body.

    Args:
        required_fields: Names of required fields

    Usage:
        @bp.route('/create', methods=['POST'])
        @validate_json_request('name', 'value')
        def create_item():
            data = request.get_json()
            # data is guaranteed to have 'name' and 'value'
    """
    from flask import request

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({'error': 'JSON body required'}), 400

            missing = [field for field in required_fields if field not in data]
            if missing:
                return jsonify({
                    'error': f'Missing required fields: {", ".join(missing)}'
                }), 400

            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_auth(f: Callable) -> Callable:
    """
    Decorator that requires authentication for a route.

    Currently a pass-through for development; can be enhanced with
    API key, JWT, or session-based authentication.

    Usage:
        @bp.route('/protected')
        @require_auth
        def protected_route():
            return jsonify({'data': 'secret'})
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # TODO: Implement actual authentication check
        # For now, allow all requests (development mode)
        # In production, check headers, tokens, etc.
        return f(*args, **kwargs)
    return wrapper


# Backward compatibility aliases
handle_errors = handle_api_errors
