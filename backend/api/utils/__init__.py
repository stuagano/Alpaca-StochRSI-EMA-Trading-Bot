"""
Utils Module
Utility functions for Flask application
"""

from .decorators import (
    require_service,
    handle_api_errors,
    retry_on_transient,
    validate_json_request,
    require_auth,
    handle_errors,  # Backward compatibility alias
)
from .responses import (
    success_response,
    error_response,
    service_unavailable,
    validation_error,
    not_found,
    paginated_response,
)
from .validators import validate_order, validate_symbol
from .error_handlers import register_error_handlers

__all__ = [
    # Decorators
    'require_service',
    'handle_api_errors',
    'retry_on_transient',
    'validate_json_request',
    'require_auth',
    'handle_errors',  # Backward compatibility
    # Response builders
    'success_response',
    'error_response',
    'service_unavailable',
    'validation_error',
    'not_found',
    'paginated_response',
    # Validators
    'validate_order',
    'validate_symbol',
    'register_error_handlers',
]