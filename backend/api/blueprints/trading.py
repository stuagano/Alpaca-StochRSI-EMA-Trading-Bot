#!/usr/bin/env python3
"""
Trading Blueprint
Trading operations and control endpoints
"""

from dataclasses import asdict, is_dataclass

from flask import Blueprint, jsonify, request, current_app

from ..utils.decorators import handle_api_errors, require_auth, require_service
from ..utils.validators import validate_order

trading_bp = Blueprint('trading', __name__)


@trading_bp.route('/start', methods=['POST'])
@handle_api_errors()
@require_auth
@require_service('trading_service', 'Trading service not initialized')
def start_trading(service):
    """Start automated trading"""
    config = request.get_json(silent=True) or {}

    # Start trading with optional config overrides
    result = service.start_trading(config)

    return jsonify({
        'status': 'started',
        'config': result.get('config'),
        'message': 'Trading bot started successfully'
    })

@trading_bp.route('/stop', methods=['POST'])
@handle_api_errors()
@require_auth
@require_service('trading_service', 'Trading service not initialized')
def stop_trading(service):
    """Stop automated trading"""
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
@handle_api_errors()
@require_auth
@validate_order
@require_service('trading_service', 'Trading service not initialized')
def place_buy_order(service):
    """Place a buy order"""
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
@handle_api_errors()
@require_auth
@validate_order
@require_service('trading_service', 'Trading service not initialized')
def place_sell_order(service):
    """Place a sell order"""
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
@handle_api_errors()
@require_auth
@require_service('trading_service', 'Trading service not initialized')
def close_position(service, symbol):
    """Close a specific position"""
    result = service.close_position(symbol)

    return jsonify({
        'status': 'closed' if result else 'failed',
        'symbol': symbol,
        'order': result
    })

@trading_bp.route('/close-all', methods=['POST'])
@handle_api_errors()
@require_auth
@require_service('trading_service', 'Trading service not initialized')
def close_all_positions(service):
    """Close all positions"""
    results = service.close_all_positions()

    return jsonify({
        'status': 'completed',
        'positions_closed': len(results),
        'results': results
    })

@trading_bp.route('/set-multiplier', methods=['POST'])
@handle_api_errors()
@require_service('trading_service', 'Trading service not initialized')
def set_multiplier(service):
    """Set position size multiplier for next trades"""
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


@trading_bp.route('/strategy', methods=['GET'])
@handle_api_errors()
def get_strategy_config():
    """Get strategy configuration"""
    config = current_app.config['TRADING_CONFIG']
    indicators = getattr(config, 'indicators', None)
    indicator_payload = asdict(indicators) if is_dataclass(indicators) else (indicators or {})

    return jsonify({
        'active_strategy': getattr(config, 'strategy', None),
        'available_strategies': ['stoch_rsi', 'ma_crossover', 'crypto_scalping'],
        'parameters': indicator_payload
    })


@trading_bp.route('/strategy', methods=['POST'])
@handle_api_errors()
@require_service('trading_service', 'Trading service not initialized')
def update_strategy_config(service):
    """Update strategy configuration"""
    data = request.get_json(silent=True) or {}
    result = service.update_strategy(data.get('strategy'), data.get('parameters')) or {}

    return jsonify({
        'status': 'updated',
        'strategy': result.get('strategy'),
        'parameters': result.get('parameters')
    })
