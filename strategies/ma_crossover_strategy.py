"""Compatibility shim for the legacy MACrossover strategy import."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from strategies.base_strategy import Strategy


class MACrossoverStrategy(Strategy):
    """Minimal placeholder to satisfy existing imports."""

    def __init__(self, config: Any) -> None:
        super().__init__(name="MACrossover")
        self.config = config

    def generate_signals(self, historical_data: Dict[str, Any], timestamp: datetime) -> List[Dict[str, Any]]:
        """Return no signals until the full implementation is restored."""

        return []
