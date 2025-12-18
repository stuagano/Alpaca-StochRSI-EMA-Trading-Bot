#!/usr/bin/env python3
"""
Trading Blueprint
Trading operations and control endpoints
"""

from dataclasses import asdict, is_dataclass

from flask import Blueprint, jsonify, request, current_app

from ..utils.decorators import handle_errors, require_auth
from ..utils.validators import validate_order

trading_bp = Blueprint('trading', __name__)


def _get_trading_service():
    """Get trading service with null-safety check."""
    service = current_app.trading_service
    if not service:
        return None
    return service


def _service_unavailable_response():
    """Standard response when trading service is unavailable."""
    return jsonify({'error': 'Trading service not initialized'}), 503

@trading_bp.route('/start', methods=['POST'])
@handle_errors
@require_auth
def start_trading():
    """Start automated trading"""
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    config = request.get_json(silent=True) or {}

    # Start trading with optional config overrides
    result = service.start_trading(config)

    return jsonify({
        'status': 'started',
        'config': result.get('config'),
        'message': 'Trading bot started successfully'
    })

@trading_bp.route('/stop', methods=['POST'])
@handle_errors
@require_auth
def stop_trading():
    """Stop automated trading"""
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    # Optional: close all positions
    data = request.get_json(silent=True) or {}
    close_positions = data.get('close_positions', False)
    result = service.stop_trading(close_positions=close_positions)

    return jsonify({
        'status': 'stopped',
        'positions_closed': result.get('positions_closed', 0),
        'message': 'Trading bot stopped successfully'
    })

@trading_bp.route('/buy', methods=['POST'])
@handle_errors
@require_auth
@validate_order
def place_buy_order():
    """Place a buy order"""
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    data = request.get_json()

    order = service.place_order({
        'symbol': data['symbol'],
        'qty': data['qty'],
        'side': 'buy',
        'type': data.get('type', 'market'),
        'time_in_force': data.get('time_in_force', 'gtc')
    })

    return jsonify({
        'status': 'submitted',
        'order': order
    })

@trading_bp.route('/sell', methods=['POST'])
@handle_errors
@require_auth
@validate_order
def place_sell_order():
    """Place a sell order"""
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    data = request.get_json()

    order = service.place_order({
        'symbol': data['symbol'],
        'qty': data['qty'],
        'side': 'sell',
        'type': data.get('type', 'market'),
        'time_in_force': data.get('time_in_force', 'gtc')
    })

    return jsonify({
        'status': 'submitted',
        'order': order
    })

@trading_bp.route('/close/<symbol>', methods=['POST'])
@handle_errors
@require_auth
def close_position(symbol):
    """Close a specific position"""
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    result = service.close_position(symbol)

    return jsonify({
        'status': 'closed' if result else 'failed',
        'symbol': symbol,
        'order': result
    })

@trading_bp.route('/close-all', methods=['POST'])
@handle_errors
@require_auth
def close_all_positions():
    """Close all positions"""
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    results = service.close_all_positions()

    return jsonify({
        'status': 'completed',
        'positions_closed': len(results),
        'results': results
    })

@trading_bp.route('/set-multiplier', methods=['POST'])
@handle_errors
def set_multiplier():
    """Set position size multiplier for next trades"""
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    data = request.get_json(silent=True) or {}
    multiplier = data.get('multiplier', 1)

    # Validate multiplier range (1x to 10x)
    if not isinstance(multiplier, (int, float)) or multiplier < 1 or multiplier > 10:
        return jsonify({'error': 'Multiplier must be between 1 and 10'}), 400

    # Store multiplier on trading service
    service.position_multiplier = float(multiplier)

    # Also update on trading bot if running
    if service.trading_bot and hasattr(service.trading_bot, 'position_multiplier'):
        service.trading_bot.position_multiplier = float(multiplier)

    current_app.logger.info(f"Position multiplier set to {multiplier}x")

    return jsonify({
        'status': 'updated',
        'multiplier': multiplier,
        'message': f'Position size multiplier set to {multiplier}x'
    })


@trading_bp.route('/strategy', methods=['GET', 'POST'])
@handle_errors
def strategy_config():
    """Get or update strategy configuration"""
    if request.method == 'GET':
        config = current_app.config['TRADING_CONFIG']
        indicators = getattr(config, 'indicators', None)
        indicator_payload = asdict(indicators) if is_dataclass(indicators) else (indicators or {})

        return jsonify({
            'active_strategy': getattr(config, 'strategy', None),
            'available_strategies': ['stoch_rsi', 'ma_crossover', 'crypto_scalping'],
            'parameters': indicator_payload
        })

    # POST - Update strategy
    service = _get_trading_service()
    if not service:
        return _service_unavailable_response()

    data = request.get_json(silent=True) or {}
    result = service.update_strategy(data.get('strategy'), data.get('parameters')) or {}

    return jsonify({
        'status': 'updated',
        'strategy': result.get('strategy'),
        'parameters': result.get('parameters')
    })
