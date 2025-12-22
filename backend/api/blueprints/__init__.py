"""
Flask Blueprints
Modular route organization
"""

from .dashboard import dashboard_bp
from .trading import trading_bp
from .api import api_bp
from .pnl import pnl_bp
from .websocket_events import websocket_bp
from .activity import activity_bp

__all__ = [
    'dashboard_bp',
    'trading_bp',
    'api_bp',
    'pnl_bp',
    'websocket_bp',
    'activity_bp'
]