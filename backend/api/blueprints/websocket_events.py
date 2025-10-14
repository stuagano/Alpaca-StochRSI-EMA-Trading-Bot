#!/usr/bin/env python3
"""
WebSocket Blueprint
Real-time communication using SocketIO
Consolidated from realtime_dashboard.py
"""

from flask import Blueprint
from flask_socketio import emit, join_room, leave_room
import logging

logger = logging.getLogger(__name__)

websocket_bp = Blueprint('websocket', __name__)

def register_socketio_handlers(socketio):
    """Register SocketIO event handlers"""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info("Client connected")
        emit('connection_status', {'status': 'connected'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info("Client disconnected")

    @socketio.on('subscribe')
    def handle_subscribe(data):
        """Subscribe to real-time updates"""
        room = data.get('room', 'default')
        join_room(room)
        emit('subscribed', {'room': room, 'status': 'success'})

    @socketio.on('unsubscribe')
    def handle_unsubscribe(data):
        """Unsubscribe from real-time updates"""
        room = data.get('room', 'default')
        leave_room(room)
        emit('unsubscribed', {'room': room, 'status': 'success'})

    @socketio.on('request_update')
    def handle_update_request(data):
        """Handle manual update request"""
        from flask import current_app

        update_type = data.get('type', 'all')

        if update_type in ['positions', 'all']:
            service = current_app.trading_service
            positions = service.get_positions()
            emit('positions_update', positions)

        if update_type in ['pnl', 'all']:
            pnl_service = current_app.pnl_service
            pnl_data = pnl_service.get_current_pnl()
            emit('pnl_update', pnl_data)

        if update_type in ['signals', 'all']:
            service = current_app.trading_service
            signals = service.calculate_signals()
            emit('signals_update', signals)

def emit_position_update(position_data):
    """Emit position update to all connected clients"""
    from backend.api import socketio
    socketio.emit('position_update', position_data, room='default')

def emit_pnl_update(pnl_data):
    """Emit P&L update to all connected clients"""
    from backend.api import socketio
    socketio.emit('pnl_update', pnl_data, room='default')

def emit_trade_update(trade_data):
    """Emit trade update to all connected clients"""
    from backend.api import socketio
    socketio.emit('trade_update', trade_data, room='default')

def emit_signal_update(signal_data):
    """Emit signal update to all connected clients"""
    from backend.api import socketio
    socketio.emit('signal_update', signal_data, room='default')