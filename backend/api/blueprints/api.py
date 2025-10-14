#!/usr/bin/env python3
"""
API Blueprint
Core API endpoints for account, positions, and signals
"""

from flask import Blueprint, jsonify, current_app, request
from backend.api.services.trading_service import TradingService
from backend.api.utils.decorators import handle_errors, require_auth

api_bp = Blueprint('api', __name__)

@api_bp.route('/status')
@handle_errors
def api_status():
    """Get system status"""
    service = current_app.trading_service
    status = service.get_system_status()

    return jsonify({
        'status': 'running',
        'last_update': status.get('last_update'),
        'market_status': status.get('market_status'),
        'services': status.get('services'),
        'trading_mode': current_app.config.TRADING_CONFIG.trading.mode
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
    symbols = request.args.getlist('symbols')

    if not symbols:
        # Get default symbols from config
        symbols = current_app.config.TRADING_CONFIG.trading.symbols

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
    config = current_app.config.TRADING_CONFIG

    return jsonify({
        'symbols': config.trading.symbols,
        'mode': config.trading.mode
    })
