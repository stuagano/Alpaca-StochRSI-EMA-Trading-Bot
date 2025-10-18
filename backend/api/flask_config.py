#!/usr/bin/env python3
"""
Flask Configuration Management
Integrates with the unified configuration system
"""

import os
from pathlib import Path

from config.unified_config import get_config

class Config:
    """Base configuration"""
    # Get unified config
    TRADING_CONFIG = get_config()

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'

    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API settings
    JSON_SORT_KEYS = False

    # CORS settings
    CORS_HEADERS = 'Content-Type'

    # SocketIO settings
    SOCKETIO_ASYNC_MODE = 'threading'

    # Static files
    STATIC_FOLDER = str(Path(__file__).resolve().parents[2] / 'frontend')

    @property
    def ALPACA_CONFIG(self):
        """Get Alpaca configuration from unified config"""
        return {
            'api_key': self.TRADING_CONFIG.api.alpaca_key_id,
            'secret_key': self.TRADING_CONFIG.api.alpaca_secret_key,
            'base_url': self.TRADING_CONFIG.api.base_url
        }

    @property
    def DATABASE_URI(self):
        """Get database URI from unified config"""
        return f"sqlite:///{self.TRADING_CONFIG.database.path}"

    @property
    def LOG_LEVEL(self):
        """Get log level from unified config"""
        return self.TRADING_CONFIG.logging.level

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

    # Development-specific settings
    TEMPLATES_AUTO_RELOAD = True

    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

    # Production security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Production performance
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year

    # Production logging
    LOG_LEVEL = 'INFO'

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True

    # Test database
    DATABASE_URI = 'sqlite:///:memory:'

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

    # Test logging
    LOG_LEVEL = 'DEBUG'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
