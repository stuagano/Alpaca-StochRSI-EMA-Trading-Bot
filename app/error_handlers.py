"""
Structured Error Handling System
Provides consistent error responses and logging
"""

from flask import jsonify, request, current_app
from werkzeug.exceptions import HTTPException
import logging
import traceback
from datetime import datetime
from utils.input_validator import ValidationError

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Custom API error with structured response"""
    
    def __init__(self, message, status_code=400, error_code=None, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or f"API_ERROR_{status_code}"
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()

class TradingError(APIError):
    """Trading-specific errors"""
    
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="TRADING_ERROR",
            details=details
        )

class SecurityError(APIError):
    """Security-related errors"""
    
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="SECURITY_ERROR",
            details=details
        )

class ConfigurationError(APIError):
    """Configuration-related errors"""
    
    def __init__(self, message, details=None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="CONFIG_ERROR",
            details=details
        )

def log_error(error, request_info=None):
    """Log error with context information"""
    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': datetime.utcnow().isoformat(),
        'request_info': request_info or {}
    }
    
    if request:
        error_data['request_info'].update({
            'method': request.method,
            'url': request.url,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'content_type': request.headers.get('Content-Type', ''),
        })
    
    # Log with appropriate level based on error type
    if isinstance(error, (ValidationError, TradingError)):
        logger.warning(f"Client error: {error_data}")
    elif isinstance(error, SecurityError):
        logger.error(f"Security error: {error_data}")
    else:
        logger.error(f"Server error: {error_data}", exc_info=True)

def create_error_response(error, include_traceback=False):
    """Create standardized error response"""
    if isinstance(error, APIError):
        response_data = {
            'success': False,
            'error': {
                'code': error.error_code,
                'message': error.message,
                'details': error.details,
                'timestamp': error.timestamp
            }
        }
        status_code = error.status_code
    elif isinstance(error, ValidationError):
        response_data = {
            'success': False,
            'error': {
                'code': 'VALIDATION_ERROR',
                'message': str(error),
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        status_code = 400
    elif isinstance(error, HTTPException):
        response_data = {
            'success': False,
            'error': {
                'code': f'HTTP_{error.code}',
                'message': error.description,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        status_code = error.code
    else:
        # Generic server error
        response_data = {
            'success': False,
            'error': {
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'An unexpected error occurred',
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        status_code = 500
    
    # Include traceback in development mode
    if include_traceback and current_app.debug:
        response_data['error']['traceback'] = traceback.format_exc()
    
    return jsonify(response_data), status_code

def register_error_handlers(app):
    """Register all error handlers with the Flask app"""
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """Handle input validation errors"""
        log_error(error)
        return create_error_response(error)
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handle custom API errors"""
        log_error(error)
        return create_error_response(error)
    
    @app.errorhandler(TradingError)
    def handle_trading_error(error):
        """Handle trading-specific errors"""
        log_error(error)
        return create_error_response(error)
    
    @app.errorhandler(SecurityError)
    def handle_security_error(error):
        """Handle security errors"""
        log_error(error)
        # Don't include sensitive details in security error responses
        sanitized_error = APIError(
            message="Access denied",
            status_code=403,
            error_code="SECURITY_ERROR"
        )
        return create_error_response(sanitized_error)
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors"""
        return jsonify({
            'success': False,
            'error': {
                'code': 'NOT_FOUND',
                'message': 'The requested resource was not found',
                'timestamp': datetime.utcnow().isoformat()
            }
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 Method Not Allowed errors"""
        return jsonify({
            'success': False,
            'error': {
                'code': 'METHOD_NOT_ALLOWED',
                'message': f'Method {request.method} not allowed for this endpoint',
                'allowed_methods': list(error.valid_methods) if hasattr(error, 'valid_methods') else [],
                'timestamp': datetime.utcnow().isoformat()
            }
        }), 405
    
    @app.errorhandler(429)
    def handle_rate_limit(error):
        """Handle rate limiting errors"""
        return jsonify({
            'success': False,
            'error': {
                'code': 'RATE_LIMIT_EXCEEDED',
                'message': 'Rate limit exceeded. Please try again later.',
                'timestamp': datetime.utcnow().isoformat()
            }
        }), 429
    
    @app.errorhandler(500)
    def handle_internal_server_error(error):
        """Handle 500 Internal Server Error"""
        log_error(error)
        return create_error_response(error, include_traceback=app.debug)
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle any unexpected errors"""
        log_error(error)
        return create_error_response(error, include_traceback=app.debug)
    
    # Request validation middleware
    @app.before_request
    def validate_request():
        """Validate incoming requests"""
        try:
            # Validate JSON payload size
            if request.content_length and request.content_length > 10 * 1024 * 1024:  # 10MB limit
                raise ValidationError("Request payload too large")
            
            # Validate Content-Type for POST/PUT requests
            if request.method in ['POST', 'PUT', 'PATCH']:
                if request.content_type and not request.content_type.startswith(('application/json', 'multipart/form-data')):
                    logger.warning(f"Unusual content type: {request.content_type}")
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error in request validation: {e}")
            # Don't block requests for validation errors
    
    # Response headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to responses"""
        try:
            # Security headers
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
            # API response headers
            response.headers['X-API-Version'] = '2.0.0'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            
            return response
        except Exception as e:
            logger.error(f"Error adding security headers: {e}")
            return response

# Utility functions for raising structured errors
def raise_trading_error(message, details=None):
    """Raise a trading error with structured format"""
    raise TradingError(message, details)

def raise_security_error(message, details=None):
    """Raise a security error with structured format"""
    raise SecurityError(message, details)

def raise_config_error(message, details=None):
    """Raise a configuration error with structured format"""
    raise ConfigurationError(message, details)

def validate_and_raise(condition, message, error_type=APIError, **kwargs):
    """Validate condition and raise error if false"""
    if not condition:
        raise error_type(message, **kwargs)