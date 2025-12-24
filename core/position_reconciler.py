"""
Position Reconciliation Service
Syncs local position state with Alpaca API to prevent drift.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ReconciliationStatus(Enum):
    """Status of a reconciliation check."""
    SYNCED = "synced"
    DRIFT_DETECTED = "drift_detected"
    MISSING_LOCAL = "missing_local"
    MISSING_REMOTE = "missing_remote"
    QUANTITY_MISMATCH = "quantity_mismatch"
    ERROR = "error"


@dataclass
class PositionDrift:
    """Represents a drift between local and remote position state."""
    symbol: str
    status: ReconciliationStatus
    local_qty: Optional[float] = None
    remote_qty: Optional[float] = None
    local_cost: Optional[float] = None
    remote_cost: Optional[float] = None
    detected_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class ReconciliationResult:
    """Result of a full reconciliation run."""
    timestamp: datetime
    success: bool
    positions_checked: int
    drifts_detected: int
    drifts_resolved: int
    errors: List[str] = field(default_factory=list)
    drifts: List[PositionDrift] = field(default_factory=list)
    duration_ms: float = 0


class PositionReconciler:
    """
    Reconciles local position state with Alpaca API.

    Features:
    - Periodic automatic reconciliation
    - Drift detection and reporting
    - Automatic resolution for simple cases
    - Manual resolution workflow for complex cases
    """

    def __init__(
        self,
        alpaca_client: Any,
        local_position_manager: Any,
        reconcile_interval: int = 60,
        auto_resolve: bool = True,
    ):
        """
        Initialize the reconciler.

        Args:
            alpaca_client: Alpaca API client
            local_position_manager: Local position tracking service
            reconcile_interval: Seconds between automatic reconciliations
            auto_resolve: Automatically resolve simple drifts
        """
        self.alpaca_client = alpaca_client
        self.local_manager = local_position_manager
        self.reconcile_interval = reconcile_interval
        self.auto_resolve = auto_resolve

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # History
        self._reconciliation_history: List[ReconciliationResult] = []
        self._pending_drifts: Dict[str, PositionDrift] = {}
        self._max_history = 100

        logger.info(
            f"PositionReconciler initialized (interval={reconcile_interval}s, "
            f"auto_resolve={auto_resolve})"
        )

    def start(self) -> None:
        """Start automatic reconciliation in background thread."""
        with self._lock:
            if self._running:
                logger.warning("Reconciler already running")
                return

            self._running = True
            self._thread = threading.Thread(
                target=self._reconciliation_loop,
                name="PositionReconciler",
                daemon=True,
            )
            self._thread.start()
            logger.info("Position reconciliation started")

    def stop(self) -> None:
        """Stop automatic reconciliation."""
        with self._lock:
            self._running = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)
            logger.info("Position reconciliation stopped")

    def _reconciliation_loop(self) -> None:
        """Background loop for automatic reconciliation."""
        while self._running:
            try:
                self.reconcile()
            except Exception as e:
                logger.error(f"Reconciliation error: {e}")

            # Sleep in small increments to allow faster shutdown
            for _ in range(self.reconcile_interval):
                if not self._running:
                    break
                time.sleep(1)

    def reconcile(self) -> ReconciliationResult:
        """
        Perform a full reconciliation between local and remote positions.

        Returns:
            ReconciliationResult with details of any drifts found
        """
        start_time = time.monotonic()
        result = ReconciliationResult(
            timestamp=datetime.now(),
            success=True,
            positions_checked=0,
            drifts_detected=0,
            drifts_resolved=0,
        )

        try:
            # Get positions from both sources
            remote_positions = self._get_remote_positions()
            local_positions = self._get_local_positions()

            remote_symbols = set(remote_positions.keys())
            local_symbols = set(local_positions.keys())

            all_symbols = remote_symbols | local_symbols
            result.positions_checked = len(all_symbols)

            for symbol in all_symbols:
                drift = self._check_position(
                    symbol,
                    local_positions.get(symbol),
                    remote_positions.get(symbol),
                )

                if drift:
                    result.drifts.append(drift)
                    result.drifts_detected += 1
                    self._pending_drifts[symbol] = drift

                    if self.auto_resolve:
                        resolved = self._try_resolve(drift)
                        if resolved:
                            result.drifts_resolved += 1

        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")
            result.success = False
            result.errors.append(str(e))

        result.duration_ms = (time.monotonic() - start_time) * 1000

        # Store in history
        self._reconciliation_history.append(result)
        if len(self._reconciliation_history) > self._max_history:
            self._reconciliation_history.pop(0)

        # Log summary
        if result.drifts_detected > 0:
            logger.warning(
                f"Reconciliation found {result.drifts_detected} drifts, "
                f"resolved {result.drifts_resolved}"
            )
        else:
            logger.debug(f"Reconciliation complete: {result.positions_checked} positions synced")

        return result

    def _get_remote_positions(self) -> Dict[str, Dict[str, Any]]:
        """Fetch positions from Alpaca API."""
        try:
            positions = self.alpaca_client.list_positions()
            return {
                p.symbol: {
                    'qty': float(p.qty),
                    'avg_entry_price': float(p.avg_entry_price),
                    'market_value': float(p.market_value),
                    'current_price': float(p.current_price),
                    'unrealized_pl': float(p.unrealized_pl),
                }
                for p in positions
            }
        except Exception as e:
            logger.error(f"Failed to fetch remote positions: {e}")
            raise

    def _get_local_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get positions from local position manager."""
        try:
            if hasattr(self.local_manager, 'active_positions'):
                positions = self.local_manager.active_positions
            elif hasattr(self.local_manager, 'get_positions'):
                positions = self.local_manager.get_positions()
            else:
                logger.warning("Local manager has no position accessor")
                return {}

            result = {}
            for symbol, pos in positions.items():
                if hasattr(pos, '__dict__'):
                    result[symbol] = {
                        'qty': getattr(pos, 'quantity', getattr(pos, 'qty', 0)),
                        'avg_entry_price': getattr(pos, 'entry_price', getattr(pos, 'avg_entry_price', 0)),
                    }
                elif isinstance(pos, dict):
                    result[symbol] = {
                        'qty': pos.get('quantity', pos.get('qty', 0)),
                        'avg_entry_price': pos.get('entry_price', pos.get('avg_entry_price', 0)),
                    }

            return result

        except Exception as e:
            logger.error(f"Failed to get local positions: {e}")
            raise

    def _check_position(
        self,
        symbol: str,
        local: Optional[Dict],
        remote: Optional[Dict],
    ) -> Optional[PositionDrift]:
        """
        Check for drift between local and remote position.

        Returns:
            PositionDrift if drift detected, None if synced
        """
        if local is None and remote is None:
            return None

        if local is None and remote is not None:
            return PositionDrift(
                symbol=symbol,
                status=ReconciliationStatus.MISSING_LOCAL,
                remote_qty=remote.get('qty'),
                remote_cost=remote.get('avg_entry_price'),
            )

        if remote is None and local is not None:
            return PositionDrift(
                symbol=symbol,
                status=ReconciliationStatus.MISSING_REMOTE,
                local_qty=local.get('qty'),
                local_cost=local.get('avg_entry_price'),
            )

        # Both exist - check for quantity mismatch
        local_qty = local.get('qty', 0)
        remote_qty = remote.get('qty', 0)

        # Allow small floating point differences
        if abs(local_qty - remote_qty) > 0.0001:
            return PositionDrift(
                symbol=symbol,
                status=ReconciliationStatus.QUANTITY_MISMATCH,
                local_qty=local_qty,
                remote_qty=remote_qty,
                local_cost=local.get('avg_entry_price'),
                remote_cost=remote.get('avg_entry_price'),
            )

        return None  # Synced

    def _try_resolve(self, drift: PositionDrift) -> bool:
        """
        Try to automatically resolve a drift.

        Returns:
            True if resolved, False if manual intervention needed
        """
        try:
            if drift.status == ReconciliationStatus.MISSING_LOCAL:
                # Remote has position we don't track locally - add it
                self._sync_from_remote(drift.symbol)
                drift.resolved = True
                drift.resolution = "synced_from_remote"
                logger.info(f"Resolved drift for {drift.symbol}: synced from remote")
                return True

            elif drift.status == ReconciliationStatus.MISSING_REMOTE:
                # We think we have a position that doesn't exist - remove local
                self._remove_local(drift.symbol)
                drift.resolved = True
                drift.resolution = "removed_stale_local"
                logger.info(f"Resolved drift for {drift.symbol}: removed stale local")
                return True

            elif drift.status == ReconciliationStatus.QUANTITY_MISMATCH:
                # Quantity mismatch - trust remote (broker is source of truth)
                self._sync_from_remote(drift.symbol)
                drift.resolved = True
                drift.resolution = "quantity_updated_from_remote"
                logger.info(f"Resolved drift for {drift.symbol}: quantity updated from remote")
                return True

        except Exception as e:
            logger.error(f"Failed to resolve drift for {drift.symbol}: {e}")
            drift.resolution = f"auto_resolve_failed: {e}"

        return False

    def _sync_from_remote(self, symbol: str) -> None:
        """Sync a position from remote to local."""
        remote = self._get_remote_positions().get(symbol)
        if remote and hasattr(self.local_manager, 'sync_position'):
            self.local_manager.sync_position(
                symbol=symbol,
                quantity=remote['qty'],
                entry_price=remote['avg_entry_price'],
            )

    def _remove_local(self, symbol: str) -> None:
        """Remove a position from local tracking."""
        if hasattr(self.local_manager, 'remove_position'):
            self.local_manager.remove_position(symbol)
        elif hasattr(self.local_manager, 'active_positions'):
            self.local_manager.active_positions.pop(symbol, None)

    def get_pending_drifts(self) -> List[PositionDrift]:
        """Get list of unresolved drifts."""
        return [d for d in self._pending_drifts.values() if not d.resolved]

    def get_history(self, limit: int = 10) -> List[ReconciliationResult]:
        """Get recent reconciliation history."""
        return self._reconciliation_history[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get reconciler status."""
        last_run = self._reconciliation_history[-1] if self._reconciliation_history else None

        return {
            'running': self._running,
            'reconcile_interval': self.reconcile_interval,
            'auto_resolve': self.auto_resolve,
            'pending_drifts': len(self.get_pending_drifts()),
            'last_run': last_run.timestamp.isoformat() if last_run else None,
            'last_success': last_run.success if last_run else None,
            'total_reconciliations': len(self._reconciliation_history),
        }

    def force_sync(self, symbol: Optional[str] = None) -> ReconciliationResult:
        """
        Force immediate synchronization.

        Args:
            symbol: Specific symbol to sync, or None for all

        Returns:
            ReconciliationResult
        """
        if symbol:
            logger.info(f"Forcing sync for {symbol}")
            self._sync_from_remote(symbol)
            # Clear any pending drift for this symbol
            self._pending_drifts.pop(symbol, None)

        return self.reconcile()
