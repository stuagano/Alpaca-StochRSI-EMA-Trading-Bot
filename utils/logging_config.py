import logging
import logging.config
import logging.handlers
import sys
import time
import os
from typing import Optional, Dict, Any
from contextlib import contextmanager
from pathlib import Path

try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False

try:
    from config.debug_config import debug_config
    HAS_DEBUG_CONFIG = True
except ImportError:
    HAS_DEBUG_CONFIG = False

def setup_logging(force_reconfigure: bool = False):
    """
    Sets up comprehensive logging system with structured output.
    Integrates with debug_config if available.
    """
    if HAS_DEBUG_CONFIG and not force_reconfigure:
        # Use centralized debug configuration
        debug_config.setup_logging()
        return logging.getLogger('trading_bot')
    
    # Fallback logging setup
    logger = logging.getLogger()
    
    # Prevent duplicate logs if already configured
    if logger.hasHandlers() and not force_reconfigure:
        return logger
        
    if logger.hasHandlers():
        logger.handlers.clear()

    # Set appropriate log level
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Create logs directory
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if HAS_JSON_LOGGER:
        console_formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    else:
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'trading_bot.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    if HAS_JSON_LOGGER:
        file_formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(filename)s %(lineno)d %(message)s')
    else:
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger

class PerformanceLogger:
    """Performance logging utility for tracking execution times."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.timings: Dict[str, list] = {}
    
    @contextmanager
    def timer(self, operation: str):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if operation not in self.timings:
                self.timings[operation] = []
            self.timings[operation].append(duration)
            self.logger.debug(f"Operation '{operation}' took {duration:.3f} seconds")
    
    def log_performance(self, operation: str, duration: float, metadata: Optional[Dict[str, Any]] = None):
        """Log performance metrics for an operation."""
        log_data = {
            'operation': operation,
            'duration_seconds': duration,
            'timestamp': time.time()
        }
        if metadata:
            log_data.update(metadata)
        self.logger.info(f"Performance metric: {log_data}")
    
    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        if operation and operation in self.timings:
            timings = self.timings[operation]
            return {
                'operation': operation,
                'count': len(timings),
                'total': sum(timings),
                'average': sum(timings) / len(timings) if timings else 0,
                'min': min(timings) if timings else 0,
                'max': max(timings) if timings else 0
            }
        elif operation is None:
            return {op: self.get_stats(op) for op in self.timings}
        else:
            return {}

logger = setup_logging()
