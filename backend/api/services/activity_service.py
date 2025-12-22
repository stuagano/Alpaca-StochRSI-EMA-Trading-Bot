"""
Bot Activity Service
Tracks and stores bot decision-making activity for dashboard display
Uses file-based persistence for cross-process communication
"""

import json
import logging
import os
import threading
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Shared file path for activity data
ACTIVITY_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'activity_feed.json')

@dataclass
class ActivityEntry:
    """Single activity log entry"""
    timestamp: str
    type: str  # 'scan', 'signal', 'decision', 'trade', 'info', 'warning'
    symbol: Optional[str]
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'type': self.type,
            'symbol': self.symbol,
            'message': self.message,
            'details': self.details or {}
        }


class ActivityService:
    """
    Singleton service to track bot activity.
    Thread-safe ring buffer for recent activity entries.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_entries: int = 200):
        if self._initialized:
            return

        self._max_entries = max_entries
        self._activity_log: deque = deque(maxlen=max_entries)
        self._signal_cache: Dict[str, Dict] = {}  # Latest signal per symbol
        self._scanner_stats: Dict[str, Any] = {
            'symbols_tracked': 0,
            'last_scan': None,
            'signals_generated': 0,
            'signals_rejected': 0,
            'total_scans': 0,
            'avg_confidence': 0.0,
            'confidence_sum': 0.0,
            'confidence_count': 0
        }
        self._lock = threading.RLock()
        self._initialized = True

        # Ensure data directory exists
        os.makedirs(os.path.dirname(ACTIVITY_FILE), exist_ok=True)

        # Load persisted data
        self._load_from_file()
        logger.info("ActivityService initialized")

    def _load_from_file(self):
        """Load activity data from persistent file"""
        try:
            if os.path.exists(ACTIVITY_FILE):
                with open(ACTIVITY_FILE, 'r') as f:
                    data = json.load(f)
                    # Load activity log
                    for entry_dict in data.get('activity', [])[-self._max_entries:]:
                        entry = ActivityEntry(**entry_dict)
                        self._activity_log.append(entry)
                    # Load signal cache
                    self._signal_cache = data.get('signals', {})
                    # Load scanner stats
                    self._scanner_stats.update(data.get('scanner', {}))
        except Exception as e:
            logger.warning(f"Could not load activity file: {e}")

    def _save_to_file(self):
        """Save activity data to persistent file"""
        try:
            data = {
                'activity': [e.to_dict() for e in self._activity_log],
                'signals': self._signal_cache,
                'scanner': self._scanner_stats,
                'updated': datetime.now().isoformat()
            }
            with open(ACTIVITY_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save activity file: {e}")

    def log_activity(self,
                     activity_type: str,
                     message: str,
                     symbol: Optional[str] = None,
                     details: Optional[Dict] = None):
        """Log an activity entry"""
        with self._lock:
            entry = ActivityEntry(
                timestamp=datetime.now().isoformat(),
                type=activity_type,
                symbol=symbol,
                message=message,
                details=details
            )
            self._activity_log.append(entry)
            self._save_to_file()

    def log_scan_start(self, symbols_count: int):
        """Log start of a scan cycle"""
        with self._lock:
            self._scanner_stats['symbols_tracked'] = symbols_count
            self._scanner_stats['last_scan'] = datetime.now().isoformat()
            self._scanner_stats['total_scans'] += 1
            self._save_to_file()

        self.log_activity(
            'scan',
            f"Scanning {symbols_count} symbols for opportunities",
            details={'symbols_count': symbols_count}
        )

    def log_scan_complete(self, signals_found: int, signals_rejected: int):
        """Log completion of scan cycle"""
        with self._lock:
            self._scanner_stats['signals_generated'] = signals_found
            self._scanner_stats['signals_rejected'] = signals_rejected
            self._save_to_file()

        if signals_found > 0:
            self.log_activity(
                'scan',
                f"Scan complete: {signals_found} signals found, {signals_rejected} rejected",
                details={'found': signals_found, 'rejected': signals_rejected}
            )

    def log_signal(self, symbol: str, action: str, confidence: float,
                   price: float, reason: str, accepted: bool = True):
        """Log a signal evaluation"""
        with self._lock:
            # Update confidence stats
            self._scanner_stats['confidence_sum'] += confidence
            self._scanner_stats['confidence_count'] += 1
            self._scanner_stats['avg_confidence'] = (
                self._scanner_stats['confidence_sum'] /
                self._scanner_stats['confidence_count']
            )

            # Cache latest signal per symbol
            self._signal_cache[symbol] = {
                'action': action,
                'confidence': confidence,
                'price': price,
                'reason': reason,
                'accepted': accepted,
                'timestamp': datetime.now().isoformat()
            }
            self._save_to_file()

        status = "ACCEPTED" if accepted else "REJECTED"
        emoji = "✅" if accepted else "❌"

        self.log_activity(
            'signal',
            f"{emoji} {symbol}: {action.upper()} signal ({confidence:.0%}) - {status}",
            symbol=symbol,
            details={
                'action': action,
                'confidence': confidence,
                'price': price,
                'reason': reason,
                'accepted': accepted
            }
        )

    def log_decision(self, symbol: str, decision: str, reason: str,
                     details: Optional[Dict] = None):
        """Log a trading decision"""
        self.log_activity(
            'decision',
            f"{symbol}: {decision} - {reason}",
            symbol=symbol,
            details=details
        )

    def log_trade(self, symbol: str, side: str, qty: float, price: float,
                  pnl: Optional[float] = None, reason: str = ""):
        """Log an executed trade"""
        emoji = "🟢" if side.lower() == 'buy' else "🔴"
        pnl_str = f" P&L: ${pnl:.2f}" if pnl is not None else ""

        self.log_activity(
            'trade',
            f"{emoji} {side.upper()} {qty:.6f} {symbol} @ ${price:.4f}{pnl_str}",
            symbol=symbol,
            details={
                'side': side,
                'qty': qty,
                'price': price,
                'pnl': pnl,
                'reason': reason
            }
        )

    def log_position_update(self, symbol: str, entry_price: float,
                            current_price: float, pnl_pct: float,
                            stop_price: float, target_price: float):
        """Log position monitoring update"""
        emoji = "📈" if pnl_pct > 0 else "📉"
        self.log_activity(
            'info',
            f"{emoji} {symbol}: {pnl_pct:.2%} | Stop: ${stop_price:.4f} | Target: ${target_price:.4f}",
            symbol=symbol,
            details={
                'entry_price': entry_price,
                'current_price': current_price,
                'pnl_pct': pnl_pct,
                'stop_price': stop_price,
                'target_price': target_price
            }
        )

    def log_rejection(self, symbol: str, reason: str, details: Optional[Dict] = None):
        """Log why a potential trade was rejected"""
        self.log_activity(
            'warning',
            f"⚠️ {symbol}: Entry rejected - {reason}",
            symbol=symbol,
            details=details
        )

    def get_recent_activity(self, limit: int = 50) -> List[Dict]:
        """Get recent activity entries"""
        with self._lock:
            # Reload from file to get data from other processes
            self._reload_from_file()
            entries = list(self._activity_log)
            # Return most recent first
            return [e.to_dict() for e in reversed(entries)][:limit]

    def get_signal_cache(self) -> Dict[str, Dict]:
        """Get cached signals for all symbols"""
        with self._lock:
            # Reload from file to get data from other processes
            self._reload_from_file()
            return dict(self._signal_cache)

    def get_scanner_stats(self) -> Dict[str, Any]:
        """Get scanner statistics"""
        with self._lock:
            # Reload from file to get data from other processes
            self._reload_from_file()
            return dict(self._scanner_stats)

    def _reload_from_file(self):
        """Reload activity data from file without clearing existing in-memory data"""
        try:
            if os.path.exists(ACTIVITY_FILE):
                with open(ACTIVITY_FILE, 'r') as f:
                    data = json.load(f)
                    # Reload activity log
                    self._activity_log.clear()
                    for entry_dict in data.get('activity', [])[-self._max_entries:]:
                        entry = ActivityEntry(**entry_dict)
                        self._activity_log.append(entry)
                    # Reload signal cache
                    self._signal_cache = data.get('signals', {})
                    # Reload scanner stats
                    loaded_stats = data.get('scanner', {})
                    self._scanner_stats.update(loaded_stats)
        except Exception as e:
            logger.debug(f"Could not reload activity file: {e}")

    def clear_activity(self):
        """Clear all activity (for testing)"""
        with self._lock:
            self._activity_log.clear()
            self._signal_cache.clear()


# Singleton instance
_activity_service: Optional[ActivityService] = None

def get_activity_service() -> ActivityService:
    """Get or create the activity service singleton"""
    global _activity_service
    if _activity_service is None:
        _activity_service = ActivityService()
    return _activity_service
