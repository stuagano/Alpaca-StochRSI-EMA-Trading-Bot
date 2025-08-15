import logging
import sys
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager
from pythonjsonlogger import jsonlogger

def setup_logging():
    """
    Sets up a standardized JSON logger.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate logs if already configured
    if logger.hasHandlers():
        logger.handlers.clear()

    logHandler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)

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
