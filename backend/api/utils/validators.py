#!/usr/bin/env python3
"""
Validators
Input validation for API endpoints
"""

from functools import wraps
from flask import request, jsonify

def validate_order(f):
    """Validate order parameters"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Required fields
        required = ['symbol', 'qty']
        for field in required:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Validate quantity
        try:
            qty = float(data['qty'])
            if qty <= 0:
                return jsonify({'error': 'Quantity must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid quantity'}), 400

        # Validate order type if provided
        if 'type' in data:
            valid_types = ['market', 'limit', 'stop', 'stop_limit']
            if data['type'] not in valid_types:
                return jsonify({'error': f'Invalid order type. Must be one of: {valid_types}'}), 400

        # Validate time in force if provided
        if 'time_in_force' in data:
            valid_tif = ['day', 'gtc', 'ioc', 'fok']
            if data['time_in_force'] not in valid_tif:
                return jsonify({'error': f'Invalid time_in_force. Must be one of: {valid_tif}'}), 400

        return f(*args, **kwargs)

    return decorated_function

def validate_symbol(f):
    """Validate symbol parameter"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        symbol = kwargs.get('symbol') or request.args.get('symbol')

        if not symbol:
            return jsonify({'error': 'Symbol is required'}), 400

        # Basic symbol validation
        if not symbol.isalnum():
            return jsonify({'error': 'Invalid symbol format'}), 400

        if len(symbol) < 1 or len(symbol) > 12:
            return jsonify({'error': 'Symbol length must be between 1 and 12 characters'}), 400

        return f(*args, **kwargs)

    return decorated_function

def validate_timeframe(f):
    """Validate timeframe parameter"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        timeframe = request.args.get('timeframe', '1Day')

        valid_timeframes = [
            '1Min', '5Min', '15Min', '30Min',
            '1Hour', '4Hour',
            '1Day', '1Week', '1Month'
        ]

        if timeframe not in valid_timeframes:
            return jsonify({
                'error': f'Invalid timeframe. Must be one of: {valid_timeframes}'
            }), 400

        return f(*args, **kwargs)

    return decorated_function