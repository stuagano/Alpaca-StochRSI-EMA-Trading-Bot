# Database package
"""Database management and models for the trading bot."""

try:
    from .database_manager import DatabaseManager
    from .models import *
    __all__ = ['DatabaseManager']
except ImportError:
    # psycopg2 or other database dependencies not installed
    DatabaseManager = None
    __all__ = []
