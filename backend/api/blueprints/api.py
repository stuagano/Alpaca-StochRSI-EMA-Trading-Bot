#!/usr/bin/env python3
"""
API Blueprint
Core API endpoints for account, positions, and signals
"""

from flask import Blueprint, jsonify, current_app, request
from ..services.trading_service import TradingService
from ..utils.decorators import handle_errors, require_auth

api_bp = Blueprint('api', __name__)

@api_bp.route('/status')
@handle_errors
def api_status():
    """Get system status"""
    cfg = current_app.config['TRADING_CONFIG']
    service = current_app.trading_service

    try:
        status = service.get_system_status()
        services_state = status.get('services', {})
        last_update = status.get('last_update')
        market_status = status.get('market_status')
    except Exception as exc:  # pragma: no cover - defensive fallback
        current_app.logger.error("Status check failed: %s", exc, exc_info=True)
        services_state = {}
        last_update = None
        market_status = 'UNKNOWN'

    return jsonify({
        'status': 'running',
        'last_update': last_update,
        'market_status': market_status,
        'services': services_state,
        'trading_mode': getattr(cfg, 'market_type', 'crypto')
    })

@api_bp.route('/account')
@handle_errors
def api_account():
    """Get account information"""
    service = current_app.trading_service
    account_data = service.get_account_data()
    return jsonify(account_data)

@api_bp.route('/positions')
@handle_errors
def api_positions():
    """Get current crypto positions"""
    service = current_app.trading_service
    positions = service.get_positions()
    return jsonify(positions)

@api_bp.route('/signals')
@handle_errors
def api_signals():
    """Get current trading signals"""
    service = current_app.trading_service
    config = current_app.config['TRADING_CONFIG']
    symbols = request.args.getlist('symbols')

    if not symbols:
        symbols_param = request.args.get('symbols')
        if symbols_param:
            symbols = [symbol.strip() for symbol in symbols_param.split(',') if symbol.strip()]

    if not symbols:
        default_symbols = list(getattr(config, 'symbols', []) or [])
        symbols = default_symbols

    if not symbols:
        current_app.logger.warning("No symbols provided and none configured; returning empty signal list")
        return jsonify([])

    signals = service.calculate_signals(symbols)
    return jsonify(signals)

@api_bp.route('/orders')
@handle_errors
def api_orders():
    """Get recent orders"""
    service = current_app.trading_service
    status = request.args.get('status', 'all')
    limit = int(request.args.get('limit', 50))

    orders = service.get_orders(status=status, limit=limit)
    return jsonify(orders)

@api_bp.route('/symbols')
@handle_errors
def api_symbols():
    """Get tracked symbols"""
    config = current_app.config['TRADING_CONFIG']

    symbols = list(getattr(config, 'symbols', []) or [])
    mode = getattr(config, 'market_type', 'crypto')

    return jsonify({
        'symbols': symbols,
        'mode': mode or 'crypto'
    })
