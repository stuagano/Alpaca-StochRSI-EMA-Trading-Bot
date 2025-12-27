#!/usr/bin/env python3
"""
WebSocket Blueprint
Real-time communication using SocketIO
Enhanced with comprehensive event broadcasting
"""

from flask import Blueprint
from flask_socketio import emit, join_room, leave_room
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

websocket_bp = Blueprint("websocket", __name__)


def register_socketio_handlers(socketio):
    """Register SocketIO event handlers"""

    @socketio.on("connect")
    def handle_connect():
        """Handle client connection"""
        logger.info("Client connected")
        emit(
            "connection_status",
            {"status": "connected", "timestamp": datetime.now().isoformat()},
        )

        # Auto-subscribe to default rooms
        join_room("default")
        join_room("positions")
        join_room("pnl")
        join_room("signals")
        join_room("activity")

        # Send initial data
        send_initial_data()

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info("Client disconnected")

    @socketio.on("subscribe")
    def handle_subscribe(data):
        """Subscribe to real-time updates"""
        room = data.get("room", "default")
        join_room(room)
        emit("subscribed", {"room": room, "status": "success"})

    @socketio.on("unsubscribe")
    def handle_unsubscribe(data):
        """Unsubscribe from real-time updates"""
        room = data.get("room", "default")
        leave_room(room)
        emit("unsubscribed", {"room": room, "status": "success"})

    @socketio.on("request_update")
    def handle_update_request(data):
        """Handle manual update request"""
        from flask import current_app

        update_type = data.get("type", "all")

        try:
            if update_type in ["positions", "all"]:
                service = getattr(current_app, "trading_service", None)
                if service:
                    positions = service.get_positions()
                    emit("positions_update", positions)

            if update_type in ["pnl", "all"]:
                pnl_service = getattr(current_app, "pnl_service", None)
                if pnl_service:
                    pnl_data = pnl_service.get_current_pnl()
                    emit("pnl_update", pnl_data)

            if update_type in ["signals", "all"]:
                service = getattr(current_app, "trading_service", None)
                if service:
                    signals = service.calculate_signals()
                    emit("signals_update", signals)

            if update_type in ["bot_status", "all"]:
                service = getattr(current_app, "trading_service", None)
                if service:
                    status = service.get_bot_status()
                    emit("bot_status_update", status)

        except Exception as e:
            logger.error(f"Error handling update request: {e}")
            emit("error", {"message": f"Update failed: {str(e)}"})

    def send_initial_data():
        """Send initial data to newly connected client"""
        from flask import current_app

        try:
            # Send bot status and related data
            service = getattr(current_app, "trading_service", None)
            if service:
                try:
                    status = service.get_bot_status()
                    emit("bot_status_update", status)

                    positions = service.get_positions()
                    emit("positions_update", positions)

                    signals = service.calculate_signals()
                    emit("signals_update", signals)
                except Exception as e:
                    logger.error(f"Error sending trading data: {e}")

            # Send P&L data
            pnl_service = getattr(current_app, "pnl_service", None)
            if pnl_service:
                try:
                    pnl_data = pnl_service.get_current_pnl()
                    emit("pnl_update", pnl_data)
                except Exception as e:
                    logger.error(f"Error sending P&L data: {e}")

            # Send recent activity
            activity_service = getattr(current_app, "activity_service", None)
            if activity_service:
                try:
                    activity = activity_service.get_recent_activity(limit=10)
                    emit("activity_update", activity)
                except Exception as e:
                    logger.error(f"Error sending activity data: {e}")

        except Exception as e:
            logger.error(f"Error in send_initial_data: {e}")


# Enhanced broadcasting functions
def emit_position_update(position_data):
    """Emit position update to all connected clients"""
    from .. import socketio

    socketio.emit(
        "position_update",
        {"data": position_data, "timestamp": datetime.now().isoformat()},
    )


def emit_pnl_update(pnl_data):
    """Emit P&L update to all connected clients"""
    from .. import socketio

    socketio.emit(
        "pnl_update", {"data": pnl_data, "timestamp": datetime.now().isoformat()}
    )


def emit_trade_update(trade_data):
    """Emit trade update to all connected clients"""
    from .. import socketio

    socketio.emit(
        "trade_update", {"data": trade_data, "timestamp": datetime.now().isoformat()}
    )


def emit_signal_update(signal_data):
    """Emit signal update to all connected clients"""
    from .. import socketio

    socketio.emit(
        "signal_update", {"data": signal_data, "timestamp": datetime.now().isoformat()}
    )


def emit_bot_status_update(status_data):
    """Emit bot status update to all connected clients"""
    from .. import socketio

    socketio.emit(
        "bot_status_update",
        {"data": status_data, "timestamp": datetime.now().isoformat()},
    )


def emit_activity_update(activity_data):
    """Emit activity update to all connected clients"""
    from .. import socketio

    socketio.emit(
        "activity_update",
        {"data": activity_data, "timestamp": datetime.now().isoformat()},
    )


def emit_error_update(error_data):
    """Emit error update to all connected clients"""
    from .. import socketio

    socketio.emit(
        "error_update", {"data": error_data, "timestamp": datetime.now().isoformat()}
    )


def broadcast_to_all(event_name, data):
    """Broadcast an event to all connected clients"""
    from .. import socketio

    socketio.emit(event_name, {"data": data, "timestamp": datetime.now().isoformat()})
