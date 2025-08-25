#!/usr/bin/env python3
"""
Centralized Debug Configuration Management
==========================================

This module provides consistent debug configuration across all components
of the trading bot system.
"""

import os
import logging
from typing import Dict, Any, Optional
from enum import Enum

class DebugLevel(Enum):
    """Debug levels for different environments"""
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    DEBUG = "debug"

class DebugConfig:
    """Centralized debug configuration management"""
    
    def __init__(self):
        self._environment = os.getenv('TRADING_BOT_ENV', 'development').lower()
        self._flask_debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
        self._log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self._debug_port = int(os.getenv('DEBUG_PORT', 5678))
        
    @property
    def environment(self) -> str:
        """Get current environment"""
        return self._environment
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self._environment == DebugLevel.PRODUCTION.value
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self._environment in [DebugLevel.DEVELOPMENT.value, DebugLevel.DEBUG.value]
    
    @property
    def flask_debug(self) -> bool:
        """Get Flask debug setting"""
        # Never enable Flask debug in production
        if self.is_production:
            return False
        return self._flask_debug or self.is_development
    
    @property
    def log_level(self) -> str:
        """Get logging level"""
        if self.is_production:
            return 'WARNING'
        elif self._environment == DebugLevel.STAGING.value:
            return 'INFO'
        else:
            return self._log_level
    
    @property
    def debug_port(self) -> int:
        """Get debug port"""
        return self._debug_port
    
    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask configuration for debug settings"""
        return {
            'DEBUG': self.flask_debug,
            'ENV': 'production' if self.is_production else 'development',
            'TESTING': False,
            # Add other Flask-specific debug configs
            'EXPLAIN_TEMPLATE_LOADING': self.is_development and self.flask_debug,
            'PRESERVE_CONTEXT_ON_EXCEPTION': self.is_development,
            'TRAP_HTTP_EXCEPTIONS': self.is_development,
            'TRAP_BAD_REQUEST_ERRORS': self.is_development,
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        level = getattr(logging, self.log_level, logging.INFO)
        
        # Define formatters
        formatters = {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(levelname)s - %(name)s - %(message)s'
            },
            'json': {
                'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "file": "%(filename)s", "line": %(lineno)d}',
                'datefmt': '%Y-%m-%dT%H:%M:%S'
            }
        }
        
        # Choose formatter based on environment
        if self.is_production:
            formatter = 'json'
        elif self.is_development:
            formatter = 'detailed'
        else:
            formatter = 'simple'
        
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': formatters,
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': self.log_level,
                    'formatter': formatter,
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': self.log_level,
                    'formatter': formatter,
                    'filename': 'logs/trading_bot.log',
                    'maxBytes': 10485760,  # 10MB
                    'backupCount': 5
                }
            },
            'loggers': {
                'trading_bot': {
                    'level': self.log_level,
                    'handlers': ['console', 'file'] if not self.is_production else ['file'],
                    'propagate': False
                },
                'flask': {
                    'level': 'INFO' if self.is_production else self.log_level,
                    'handlers': ['console', 'file'] if not self.is_production else ['file'],
                    'propagate': False
                },
                'alpaca': {
                    'level': 'WARNING' if self.is_production else 'INFO',
                    'handlers': ['console', 'file'] if not self.is_production else ['file'],
                    'propagate': False
                },
                'werkzeug': {
                    'level': 'WARNING',  # Always reduce Werkzeug noise
                    'handlers': ['file'],
                    'propagate': False
                }
            },
            'root': {
                'level': level,
                'handlers': ['console'] if self.is_development else ['file']
            }
        }
    
    def get_microservice_config(self, service_name: str) -> Dict[str, Any]:
        """Get debug configuration for microservices"""
        return {
            'debug': self.is_development,
            'log_level': self.log_level,
            'service_name': service_name,
            'environment': self.environment,
            'enable_profiling': self.is_development,
            'enable_metrics': True,
            'metrics_port': self.debug_port + hash(service_name) % 100,  # Unique port per service
        }
    
    def get_testing_config(self) -> Dict[str, Any]:
        """Get configuration for testing environment"""
        return {
            'TESTING': True,
            'DEBUG': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'LOG_LEVEL': 'DEBUG',
            'PRESERVE_CONTEXT_ON_EXCEPTION': False,
        }
    
    def setup_logging(self, logger_name: Optional[str] = None) -> logging.Logger:
        """Setup logging with current configuration"""
        import logging.config
        import os
        
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Configure logging
        logging.config.dictConfig(self.get_logging_config())
        
        # Return logger
        if logger_name:
            return logging.getLogger(logger_name)
        return logging.getLogger('trading_bot')
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate debug configuration"""
        issues = []
        warnings = []
        
        # Check environment consistency
        if self.is_production and self.flask_debug:
            issues.append("Flask debug is enabled in production environment")
        
        if self.is_production and self.log_level == 'DEBUG':
            warnings.append("Debug logging enabled in production (may impact performance)")
        
        # Check port availability
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', self.debug_port))
        except OSError:
            warnings.append(f"Debug port {self.debug_port} is already in use")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'config': {
                'environment': self.environment,
                'flask_debug': self.flask_debug,
                'log_level': self.log_level,
                'debug_port': self.debug_port,
                'is_production': self.is_production,
                'is_development': self.is_development
            }
        }
    
    def export_environment_vars(self) -> Dict[str, str]:
        """Export configuration as environment variables"""
        return {
            'TRADING_BOT_ENV': self.environment,
            'FLASK_DEBUG': str(self.flask_debug).lower(),
            'LOG_LEVEL': self.log_level,
            'DEBUG_PORT': str(self.debug_port),
            'FLASK_ENV': 'production' if self.is_production else 'development'
        }

# Global instance
debug_config = DebugConfig()

# Backwards compatibility exports
FLASK_DEBUG = debug_config.flask_debug
LOG_LEVEL = debug_config.log_level
DEBUG_PORT = debug_config.debug_port
ENVIRONMENT = debug_config.environment

if __name__ == '__main__':
    # CLI for debug configuration management
    import json
    import sys
    
    def print_help():
        print("Debug Configuration Management")
        print("Commands:")
        print("  status    - Show current debug configuration")
        print("  validate  - Validate current configuration")
        print("  flask     - Get Flask debug configuration")
        print("  logging   - Get logging configuration")
        print("  export    - Export as environment variables")
        print("  test      - Test logging setup")
    
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'status':
        config = debug_config.validate_configuration()['config']
        print(json.dumps(config, indent=2))
    elif command == 'validate':
        result = debug_config.validate_configuration()
        print(json.dumps(result, indent=2))
        if not result['valid']:
            sys.exit(1)
    elif command == 'flask':
        print(json.dumps(debug_config.get_flask_config(), indent=2))
    elif command == 'logging':
        print(json.dumps(debug_config.get_logging_config(), indent=2))
    elif command == 'export':
        for key, value in debug_config.export_environment_vars().items():
            print(f"export {key}={value}")
    elif command == 'test':
        logger = debug_config.setup_logging('test_logger')
        logger.debug("Debug message test")
        logger.info("Info message test")
        logger.warning("Warning message test")
        logger.error("Error message test")
        print("✅ Logging test completed")
    else:
        print(f"Unknown command: {command}")
        print_help()
        sys.exit(1)