#!/usr/bin/env python3
"""
Adaptive Algorithm Management
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class MarketRegime:
    """Market regime characteristics"""
    regime_type: str  # trending, ranging, volatile
    volatility: float
    trend_strength: float
    volume_profile: str
    confidence: float

@dataclass
class AdaptationDecision:
    """Strategy adaptation decision"""
    decision_type: str  # adapt, maintain, switch
    reason: str
    new_strategy: Any
    confidence: float
    timestamp: datetime

class MarketRegimeDetector:
    """Detect current market regime"""
    
    def __init__(self):
        self.regime_history = []
    
    def detect_regime(self, data: pd.DataFrame) -> MarketRegime:
        """Detect current market regime"""
        
        if len(data) < 20:
            return MarketRegime(
                regime_type='unknown',
                volatility=0.0,
                trend_strength=0.0,
                volume_profile='normal',
                confidence=0.0
            )
        
        # Calculate metrics
        returns = data['close'].pct_change()
        volatility = returns.std()
        
        # Simple trend detection
        sma_20 = data['close'].rolling(20).mean()
        trend_strength = (data['close'].iloc[-1] - sma_20.iloc[-1]) / sma_20.iloc[-1]
        
        # Determine regime
        if abs(trend_strength) > 0.02:
            regime_type = 'trending'
        elif volatility > 0.02:
            regime_type = 'volatile'
        else:
            regime_type = 'ranging'
        
        # Volume profile
        volume_avg = data['volume'].mean()
        current_volume = data['volume'].iloc[-1]
        volume_profile = 'high' if current_volume > volume_avg * 1.5 else 'normal'
        
        regime = MarketRegime(
            regime_type=regime_type,
            volatility=volatility,
            trend_strength=trend_strength,
            volume_profile=volume_profile,
            confidence=0.75
        )
        
        self.regime_history.append(regime)
        return regime

class StrategyAdapter:
    """Adapt trading strategy based on conditions"""
    
    def __init__(self, base_strategy: Dict[str, Any]):
        self.base_strategy = base_strategy
        self.adaptation_history = []
    
    def adapt_for_regime(self, regime: MarketRegime) -> Dict[str, Any]:
        """Adapt strategy for market regime"""
        
        adapted_strategy = self.base_strategy.copy()
        
        if regime.regime_type == 'trending':
            # Increase position size in trends
            adapted_strategy['position_size_percentage'] *= 1.2
            adapted_strategy['take_profit_percentage'] *= 1.5
        elif regime.regime_type == 'volatile':
            # Reduce risk in volatile markets
            adapted_strategy['position_size_percentage'] *= 0.7
            adapted_strategy['stop_loss_percentage'] *= 0.8
        elif regime.regime_type == 'ranging':
            # Tighter stops in ranging markets
            adapted_strategy['stop_loss_percentage'] *= 0.9
            adapted_strategy['take_profit_percentage'] *= 0.8
        
        return adapted_strategy

class AdaptiveAlgorithmManager:
    """Manage adaptive trading algorithms"""
    
    def __init__(self, base_strategy_params: Dict[str, Any]):
        self.base_strategy_params = base_strategy_params
        self.regime_detector = MarketRegimeDetector()
        self.strategy_adapter = StrategyAdapter(base_strategy_params)
        self.current_strategy = None
        self.performance_tracker = []
    
    def initialize(self, historical_data: pd.DataFrame):
        """Initialize with historical data"""
        if len(historical_data) > 0:
            regime = self.regime_detector.detect_regime(historical_data)
            self.current_strategy = self.strategy_adapter.adapt_for_regime(regime)
        else:
            self.current_strategy = self.base_strategy_params
    
    def adapt_strategy(self, current_data: pd.DataFrame,
                       recent_performance: Optional[Dict[str, float]] = None) -> AdaptationDecision:
        """Adapt strategy based on current conditions"""
        
        # Detect current regime
        regime = self.regime_detector.detect_regime(current_data)
        
        # Adapt strategy
        new_strategy = self.strategy_adapter.adapt_for_regime(regime)
        
        # Determine decision type
        if recent_performance and recent_performance.get('win_rate', 0.5) < 0.3:
            decision_type = 'switch'
            reason = 'Poor recent performance detected'
        elif regime.regime_type != 'unknown':
            decision_type = 'adapt'
            reason = f'Adapting to {regime.regime_type} market conditions'
        else:
            decision_type = 'no_change'
            reason = 'Maintaining current strategy'
        
        # Create strategy object
        strategy_obj = type('Strategy', (), {
            'strategy_name': self.base_strategy_params.get('strategy_name', 'adaptive'),
            'parameters': new_strategy
        })()
        
        decision = AdaptationDecision(
            decision_type=decision_type,
            reason=reason,
            new_strategy=strategy_obj,
            confidence=regime.confidence,
            timestamp=datetime.now()
        )
        
        self.current_strategy = new_strategy
        return decision
    
    def track_performance(self, performance_metrics: Dict[str, float]):
        """Track strategy performance"""
        self.performance_tracker.append({
            'timestamp': datetime.now(),
            'metrics': performance_metrics
        })

def create_adaptive_manager(base_params: Dict[str, Any]) -> AdaptiveAlgorithmManager:
    """Factory function to create adaptive manager"""
    return AdaptiveAlgorithmManager(base_params)