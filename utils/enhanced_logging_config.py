#!/usr/bin/env python3
"""
Enhanced Logging Configuration for Professional Trading System
Provides comprehensive logging with file rotation, structured formats, and real-time monitoring
"""

import logging
import logging.handlers
import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class TradingJSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured trading logs"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if they exist
        if hasattr(record, 'symbol'):
            log_entry['symbol'] = record.symbol
        if hasattr(record, 'signal_type'):
            log_entry['signal_type'] = record.signal_type
        if hasattr(record, 'price'):
            log_entry['price'] = record.price
        if hasattr(record, 'epic1_enhanced'):
            log_entry['epic1_enhanced'] = record.epic1_enhanced
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time
        if hasattr(record, 'client_id'):
            log_entry['client_id'] = record.client_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

class TradingConsoleFormatter(logging.Formatter):
    """Enhanced console formatter with colors and emojis"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green  
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    # Emojis for different log types
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨'
    }
    
    def format(self, record):
        # Add color and emoji
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        emoji = self.EMOJIS.get(record.levelname, '📝')
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Build the message
        message = f"{color}{emoji} [{timestamp}] {record.levelname:8} {reset}"
        
        # Add module info
        if hasattr(record, 'symbol'):
            message += f" [{record.symbol}]"
        
        message += f" {record.name}: {record.getMessage()}"
        
        # Add execution time if available
        if hasattr(record, 'execution_time'):
            message += f" {color}({record.execution_time:.3f}s){reset}"
        
        return message

class EnhancedLoggingConfig:
    """Enhanced logging configuration manager"""
    
    def __init__(self, log_dir: str = "logs", app_name: str = "trading_bot"):
        self.log_dir = Path(log_dir)
        self.app_name = app_name
        self.log_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different log types
        (self.log_dir / "trading").mkdir(exist_ok=True)
        (self.log_dir / "websocket").mkdir(exist_ok=True)
        (self.log_dir / "epic1").mkdir(exist_ok=True)
        (self.log_dir / "performance").mkdir(exist_ok=True)
        (self.log_dir / "errors").mkdir(exist_ok=True)
        
        self.setup_logging()
    
    def setup_logging(self):
        """Setup comprehensive logging configuration"""
        
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Set root logger level
        root_logger.setLevel(logging.DEBUG)
        
        # Setup different log handlers
        self.setup_console_handler()
        self.setup_file_handlers()
        self.setup_specialized_loggers()
        
        # Log startup message
        logger = logging.getLogger(__name__)
        logger.info("🚀 Enhanced logging system initialized")
        logger.info(f"📁 Log directory: {self.log_dir.absolute()}")
    
    def setup_console_handler(self):
        """Setup enhanced console logging"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(TradingConsoleFormatter())
        
        # Add to root logger
        logging.getLogger().addHandler(console_handler)
    
    def setup_file_handlers(self):
        """Setup rotating file handlers"""
        
        # Main application log (rotating)
        main_log_file = self.log_dir / f"{self.app_name}.log"
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(TradingJSONFormatter())
        logging.getLogger().addHandler(main_handler)
        
        # Error log (rotating)
        error_log_file = self.log_dir / "errors" / f"{self.app_name}_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(TradingJSONFormatter())
        logging.getLogger().addHandler(error_handler)
        
        # Daily rotating log for trading events
        trading_log_file = self.log_dir / "trading" / f"{self.app_name}_trading.log"
        trading_handler = logging.handlers.TimedRotatingFileHandler(
            trading_log_file,
            when='midnight',
            interval=1,
            backupCount=30,  # Keep 30 days
            encoding='utf-8'
        )
        trading_handler.setLevel(logging.INFO)
        trading_handler.setFormatter(TradingJSONFormatter())
        
        # Add filter for trading events
        trading_handler.addFilter(self.TradingEventFilter())
        logging.getLogger().addHandler(trading_handler)
    
    def setup_specialized_loggers(self):
        """Setup specialized loggers for different components"""
        
        # Epic 1 Logger
        epic1_logger = logging.getLogger('epic1')
        epic1_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "epic1" / "epic1_signals.log",
            maxBytes=5*1024*1024,
            backupCount=3,
            encoding='utf-8'
        )
        epic1_handler.setFormatter(TradingJSONFormatter())
        epic1_logger.addHandler(epic1_handler)
        epic1_logger.setLevel(logging.DEBUG)
        
        # WebSocket Logger
        websocket_logger = logging.getLogger('websocket')
        websocket_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "websocket" / "websocket_events.log",
            maxBytes=5*1024*1024,
            backupCount=3,
            encoding='utf-8'
        )
        websocket_handler.setFormatter(TradingJSONFormatter())
        websocket_logger.addHandler(websocket_handler)
        websocket_logger.setLevel(logging.INFO)
        
        # Performance Logger
        performance_logger = logging.getLogger('performance')
        performance_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "performance" / "performance_metrics.log",
            maxBytes=5*1024*1024,
            backupCount=3,
            encoding='utf-8'
        )
        performance_handler.setFormatter(TradingJSONFormatter())
        performance_logger.addHandler(performance_handler)
        performance_logger.setLevel(logging.INFO)
        
        # Flask Logger
        flask_logger = logging.getLogger('werkzeug')
        flask_logger.setLevel(logging.WARNING)  # Reduce Flask noise
        
        # SocketIO Logger
        socketio_logger = logging.getLogger('socketio')
        socketio_logger.setLevel(logging.WARNING)  # Reduce SocketIO noise
        
        # Set third-party loggers to WARNING to reduce noise
        for logger_name in ['urllib3', 'requests', 'alpaca_trade_api', 'pandas']:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    class TradingEventFilter(logging.Filter):
        """Filter to capture only trading-related events"""
        
        def filter(self, record):
            trading_keywords = [
                'signal', 'trade', 'order', 'position', 'buy', 'sell', 
                'epic1', 'stochrsi', 'volume', 'timeframe', 'price'
            ]
            
            message = record.getMessage().lower()
            return any(keyword in message for keyword in trading_keywords)

# Logging utility functions
def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)

def log_trading_event(logger: logging.Logger, event_type: str, symbol: str, 
                     data: Dict[str, Any], execution_time: Optional[float] = None):
    """Log a trading event with structured data"""
    extra = {
        'symbol': symbol,
        'signal_type': event_type,
        **data
    }
    
    if execution_time is not None:
        extra['execution_time'] = execution_time
    
    logger.info(f"Trading event: {event_type} for {symbol}", extra=extra)

def log_epic1_signal(symbol: str, signal_data: Dict[str, Any]):
    """Log Epic 1 enhanced signal data"""
    logger = logging.getLogger('epic1')
    
    extra = {
        'symbol': symbol,
        'epic1_enhanced': True,
        'signal_type': signal_data.get('signal', 'UNKNOWN'),
        'confidence': signal_data.get('confidence', 0),
        'price': signal_data.get('price', 0)
    }
    
    logger.info(f"Epic 1 signal generated for {symbol}: {signal_data.get('signal', 'UNKNOWN')}", extra=extra)

def log_websocket_event(event_type: str, client_id: str, data: Dict[str, Any]):
    """Log WebSocket events"""
    logger = logging.getLogger('websocket')
    
    extra = {
        'client_id': client_id,
        'event_type': event_type,
        **data
    }
    
    logger.info(f"WebSocket {event_type}: {client_id}", extra=extra)

def log_performance_metric(metric_name: str, value: float, context: Dict[str, Any] = None):
    """Log performance metrics"""
    logger = logging.getLogger('performance')
    
    extra = {
        'metric_name': metric_name,
        'metric_value': value,
        **(context or {})
    }
    
    logger.info(f"Performance metric: {metric_name} = {value}", extra=extra)

# Performance timing decorator
def log_execution_time(logger_name: str = None):
    """Decorator to log function execution time"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name or func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.debug(
                    f"Function {func.__name__} executed successfully",
                    extra={'execution_time': execution_time}
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"Function {func.__name__} failed: {str(e)}",
                    extra={'execution_time': execution_time},
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator

# Context manager for logging blocks
class LoggingContext:
    """Context manager for logging code blocks with timing"""
    
    def __init__(self, logger: logging.Logger, operation: str, **extra_data):
        self.logger = logger
        self.operation = operation
        self.extra_data = extra_data
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}", extra=self.extra_data)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - self.start_time
        
        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation}",
                extra={**self.extra_data, 'execution_time': execution_time}
            )
        else:
            self.logger.error(
                f"Failed {self.operation}: {str(exc_val)}",
                extra={**self.extra_data, 'execution_time': execution_time},
                exc_info=True
            )

# Initialize logging when module is imported
def initialize_logging():
    """Initialize the enhanced logging system"""
    global _logging_config
    if '_logging_config' not in globals():
        _logging_config = EnhancedLoggingConfig()
    return _logging_config

# Auto-initialize when imported
_logging_config = initialize_logging()

# Export commonly used functions
__all__ = [
    'get_logger',
    'log_trading_event', 
    'log_epic1_signal',
    'log_websocket_event',
    'log_performance_metric',
    'log_execution_time',
    'LoggingContext',
    'TradingJSONFormatter',
    'TradingConsoleFormatter',
    'EnhancedLoggingConfig'
]