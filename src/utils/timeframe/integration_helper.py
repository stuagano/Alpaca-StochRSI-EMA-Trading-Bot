"""
Multi-Timeframe Integration Helper
=================================

Utility functions for integrating multi-timeframe validation with existing trading system
Provides bridge between Python backend and JavaScript frontend components
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import time
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    OVERSOLD = "OVERSOLD"
    OVERBOUGHT = "OVERBOUGHT"
    NEUTRAL = "NEUTRAL"

class TrendDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class ValidationStage(Enum):
    QUICK_VALIDATION = "quick_validation"
    TREND_ANALYSIS = "trend_analysis"
    CONSENSUS_VALIDATION = "consensus_validation"
    FINAL_DECISION = "final_decision"

@dataclass
class TradingSignal:
    """Trading signal data structure"""
    symbol: str
    type: SignalType
    strength: float
    timestamp: int
    price: float = 0.0
    reason: str = ""
    indicators: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.indicators is None:
            self.indicators = {}
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['type'] = self.type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingSignal':
        """Create from dictionary"""
        signal_type = SignalType(data['type']) if isinstance(data['type'], str) else data['type']
        return cls(
            symbol=data['symbol'],
            type=signal_type,
            strength=data['strength'],
            timestamp=data['timestamp'],
            price=data.get('price', 0.0),
            reason=data.get('reason', ''),
            indicators=data.get('indicators', {}),
            metadata=data.get('metadata', {})
        )

# ... (the rest of the file)
