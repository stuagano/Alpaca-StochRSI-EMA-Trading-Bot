#!/usr/bin/env python3
"""
Decorators
Custom decorators for Flask routes
"""

import logging
from functools import wraps
from flask import jsonify, request, current_app

logger = logging.getLogger(__name__)

def handle_errors(f):
    """
    Error handling decorator for routes

    Catches exceptions and returns standardized error responses
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.error(f"Value error in {f.__name__}: {e}")
            return jsonify({
                'error': 'Invalid input',
                'message': str(e)
            }), 400
        except KeyError as e:
            logger.error(f"Key error in {f.__name__}: {e}")
            return jsonify({
                'error': 'Missing required field',
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {e}")
            return jsonify({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred'
            }), 500

    return decorated_function

def require_auth(f):
    """
    Authentication decorator

    Ensures request is authenticated before allowing access
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Simple API key authentication
        api_key = request.headers.get('X-API-Key')
        expected_key = current_app.config.get('API_KEY')

        # If no key is configured, bypass authentication (dev mode)
        if not expected_key:
             return f(*args, **kwargs)

        if not api_key:
            return jsonify({'error': 'Authentication required'}), 401
            
        if api_key != expected_key:
            return jsonify({'error': 'Invalid API key'}), 401

        return f(*args, **kwargs)

    return decorated_function

def rate_limit(max_calls=60, time_window=60):
    """
    Rate limiting decorator

    Args:
        max_calls: Maximum number of calls allowed
        time_window: Time window in seconds
    """
    def decorator(f):
        # Simple in-memory rate limiting
        # In production, use Redis or similar
        call_times = []

        @wraps(f)
        def decorated_function(*args, **kwargs):
            import time
            now = time.time()

            # Remove old calls outside the time window
            nonlocal call_times
            call_times = [t for t in call_times if now - t < time_window]

            if len(call_times) >= max_calls:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {max_calls} requests per {time_window} seconds'
                }), 429

            call_times.append(now)
            return f(*args, **kwargs)

        return decorated_function
    return decorator

def cache_response(duration=300):
    """
    Response caching decorator

    Args:
        duration: Cache duration in seconds
    """
    def decorator(f):
        cache = {}

        @wraps(f)
        def decorated_function(*args, **kwargs):
            import time
            import hashlib
            import json

            # Create cache key from function name and arguments
            key_data = f"{f.__name__}:{args}:{kwargs}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Check cache
            if cache_key in cache:
                cached_data, cached_time = cache[cache_key]
                if time.time() - cached_time < duration:
                    return cached_data

            # Call function and cache result
            result = f(*args, **kwargs)
            cache[cache_key] = (result, time.time())

            return result

        return decorated_function
    return decorator