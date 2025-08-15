#!/usr/bin/env python3
"""
AI Trading Academy - Adaptive Trading Algorithms
===============================================

Self-adapting algorithms that learn from market conditions and adjust strategies:
- Market regime detection and strategy switching
- Dynamic parameter adjustment based on volatility
- Online learning for continuous adaptation
- Ensemble methods with adaptive weighting

Educational focus: Learn how algorithms can adapt to changing market conditions
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod
from collections import deque
import json

# Scientific computing
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Import our other ML components
try:
    from .price_predictor import PricePredictionModel, create_price_predictor
    from .reinforcement_learning import AdaptiveStrategyOptimizer
except ImportError:
    # Handle relative imports when running as standalone
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from price_predictor import PricePredictionModel, create_price_predictor
    from reinforcement_learning import AdaptiveStrategyOptimizer

warnings.filterwarnings('ignore', category=FutureWarning)

@dataclass
class MarketRegime:
    """Represents a market regime"""
    regime_id: int
    name: str
    description: str
    characteristics: Dict[str, float]
    optimal_strategy: str
    confidence: float
    detected_at: datetime

@dataclass
class StrategyParameters:
    """Dynamic strategy parameters"""
    strategy_name: str
    parameters: Dict[str, Any]
    confidence: float
    valid_until: datetime
    market_regime: Optional[MarketRegime] = None

@dataclass
class AdaptationDecision:
    """Decision to adapt strategy"""
    decision_type: str  # 'parameter_change', 'strategy_switch', 'regime_change'
    old_strategy: StrategyParameters
    new_strategy: StrategyParameters
    reason: str
    confidence: float
    timestamp: datetime

class MarketRegimeDetector:
    """Detect market regimes using statistical methods"""
    
    def __init__(self, lookback_period: int = 252, n_regimes: int = 3):
        self.lookback_period = lookback_period
        self.n_regimes = n_regimes
        self.regime_model = None
        self.scaler = StandardScaler()
        self.current_regime = None
        self.regime_history = []
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Define regime characteristics
        self.regime_definitions = {
            0: {"name": "Low Volatility Bull", "strategy": "trend_following"},
            1: {"name": "High Volatility", "strategy": "mean_reversion"},
            2: {"name": "Bear Market", "strategy": "defensive"}
        }
    
    def calculate_market_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate features for regime detection"""
        
        features_df = df.copy()
        
        # Returns and volatility
        features_df['returns'] = df['close'].pct_change()
        features_df['volatility'] = features_df['returns'].rolling(20).std()
        features_df['volatility_long'] = features_df['returns'].rolling(60).std()
        
        # Trend features
        features_df['sma_50'] = df['close'].rolling(50).mean()
        features_df['sma_200'] = df['close'].rolling(200).mean()
        features_df['trend_ratio'] = features_df['sma_50'] / features_df['sma_200']
        features_df['price_to_sma'] = df['close'] / features_df['sma_50']
        
        # Momentum features
        features_df['roc_20'] = df['close'].pct_change(20)  # Rate of change
        features_df['roc_60'] = df['close'].pct_change(60)
        
        # Volume features
        if 'volume' in df.columns:
            features_df['volume_ma'] = df['volume'].rolling(20).mean()
            features_df['volume_ratio'] = df['volume'] / features_df['volume_ma']
        else:
            features_df['volume_ratio'] = 1.0
        
        # Regime indicators
        features_df['drawdown'] = (df['close'] / df['close'].rolling(252, min_periods=1).max() - 1)
        features_df['up_days_pct'] = (features_df['returns'] > 0).rolling(20).mean()
        
        return features_df
    
    def train_regime_detector(self, df: pd.DataFrame):
        """Train the regime detection model"""
        
        # Calculate features
        features_df = self.calculate_market_features(df)
        
        # Select features for clustering
        feature_cols = [
            'volatility', 'trend_ratio', 'roc_20', 'roc_60', 
            'volume_ratio', 'drawdown', 'up_days_pct'
        ]
        
        # Remove NaN values
        clean_df = features_df[feature_cols].dropna()
        
        if len(clean_df) < self.lookback_period:
            self.logger.warning(f"Insufficient data for regime detection: {len(clean_df)} < {self.lookback_period}")
            return
        
        # Scale features
        scaled_features = self.scaler.fit_transform(clean_df)
        
        # Fit KMeans clustering
        self.regime_model = KMeans(n_clusters=self.n_regimes, random_state=42, n_init=10)
        regime_labels = self.regime_model.fit_predict(scaled_features)
        
        # Analyze regime characteristics
        for regime_id in range(self.n_regimes):
            regime_mask = regime_labels == regime_id
            if np.any(regime_mask):
                regime_data = clean_df[regime_mask]
                
                characteristics = {
                    'avg_volatility': regime_data['volatility'].mean(),
                    'avg_trend_ratio': regime_data['trend_ratio'].mean(),
                    'avg_roc_20': regime_data['roc_20'].mean(),
                    'avg_drawdown': regime_data['drawdown'].mean(),
                    'up_days_pct': regime_data['up_days_pct'].mean(),
                    'sample_count': len(regime_data)
                }
                
                # Update regime definition with characteristics
                if regime_id in self.regime_definitions:
                    self.regime_definitions[regime_id]['characteristics'] = characteristics
        
        self.logger.info(f"Regime detector trained on {len(clean_df)} samples with {self.n_regimes} regimes")
        
        # Store the latest regime
        if len(regime_labels) > 0:
            latest_regime_id = regime_labels[-1]
            self.current_regime = self._create_regime_object(latest_regime_id)
    
    def detect_current_regime(self, df: pd.DataFrame) -> MarketRegime:
        """Detect current market regime"""
        
        if self.regime_model is None:
            self.train_regime_detector(df)
        
        # Calculate features for recent data
        features_df = self.calculate_market_features(df)
        
        feature_cols = [
            'volatility', 'trend_ratio', 'roc_20', 'roc_60', 
            'volume_ratio', 'drawdown', 'up_days_pct'
        ]
        
        # Get latest valid data point
        latest_features = features_df[feature_cols].dropna().tail(1)
        
        if len(latest_features) == 0:
            return self.current_regime or self._create_regime_object(0)
        
        # Scale and predict
        scaled_features = self.scaler.transform(latest_features)
        regime_id = self.regime_model.predict(scaled_features)[0]
        
        # Calculate confidence based on distance to cluster center
        distances = self.regime_model.transform(scaled_features)[0]
        min_distance = np.min(distances)
        confidence = 1 / (1 + min_distance)  # Higher confidence for closer points
        
        # Create regime object
        regime = self._create_regime_object(regime_id, confidence)
        
        # Update current regime and history
        if self.current_regime is None or self.current_regime.regime_id != regime_id:
            self.current_regime = regime
            self.regime_history.append(regime)
            self.logger.info(f"Regime change detected: {regime.name} (confidence: {confidence:.3f})")
        
        return regime
    
    def _create_regime_object(self, regime_id: int, confidence: float = 0.8) -> MarketRegime:
        """Create a MarketRegime object"""
        
        regime_info = self.regime_definitions.get(regime_id, {
            "name": f"Unknown Regime {regime_id}",
            "strategy": "balanced"
        })
        
        characteristics = regime_info.get('characteristics', {})
        
        return MarketRegime(
            regime_id=regime_id,
            name=regime_info['name'],
            description=f"Market regime with characteristics: {characteristics}",
            characteristics=characteristics,
            optimal_strategy=regime_info['strategy'],
            confidence=confidence,
            detected_at=datetime.now()
        )

class AdaptiveParameterController:
    """Control strategy parameters based on market conditions"""
    
    def __init__(self, base_parameters: Dict[str, Any]):
        self.base_parameters = base_parameters
        self.current_parameters = base_parameters.copy()
        self.parameter_history = []
        self.adaptation_rules = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize adaptation rules
        self._setup_adaptation_rules()
    
    def _setup_adaptation_rules(self):
        """Setup rules for parameter adaptation"""
        
        # Volatility-based adaptations
        self.adaptation_rules['volatility'] = {
            'low': {  # Low volatility < 0.15
                'position_size_multiplier': 1.2,
                'stop_loss_multiplier': 0.8,
                'take_profit_multiplier': 1.1,
                'indicator_sensitivity': 0.9
            },
            'medium': {  # Medium volatility 0.15-0.30
                'position_size_multiplier': 1.0,
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.0,
                'indicator_sensitivity': 1.0
            },
            'high': {  # High volatility > 0.30
                'position_size_multiplier': 0.7,
                'stop_loss_multiplier': 1.5,
                'take_profit_multiplier': 0.8,
                'indicator_sensitivity': 1.2
            }
        }
        
        # Trend-based adaptations
        self.adaptation_rules['trend'] = {
            'strong_up': {
                'trend_following_weight': 1.3,
                'mean_reversion_weight': 0.7
            },
            'weak_up': {
                'trend_following_weight': 1.1,
                'mean_reversion_weight': 0.9
            },
            'sideways': {
                'trend_following_weight': 0.8,
                'mean_reversion_weight': 1.2
            },
            'weak_down': {
                'trend_following_weight': 0.9,
                'mean_reversion_weight': 1.1
            },
            'strong_down': {
                'trend_following_weight': 0.6,
                'mean_reversion_weight': 1.4
            }
        }
    
    def adapt_parameters(self, market_data: pd.DataFrame, 
                        regime: Optional[MarketRegime] = None) -> StrategyParameters:
        """Adapt parameters based on current market conditions"""
        
        # Calculate market characteristics
        recent_data = market_data.tail(50)  # Last 50 periods
        returns = recent_data['close'].pct_change().dropna()
        
        current_volatility = returns.std() * np.sqrt(252)  # Annualized
        current_trend = self._calculate_trend_strength(recent_data)
        
        # Start with base parameters
        adapted_params = self.base_parameters.copy()
        
        # Apply volatility-based adaptations
        vol_category = self._categorize_volatility(current_volatility)
        vol_rules = self.adaptation_rules['volatility'][vol_category]
        
        for param, multiplier in vol_rules.items():
            if param in adapted_params:
                if isinstance(adapted_params[param], (int, float)):
                    adapted_params[param] *= multiplier
        
        # Apply trend-based adaptations
        trend_category = self._categorize_trend(current_trend)
        trend_rules = self.adaptation_rules['trend'][trend_category]
        
        adapted_params.update(trend_rules)
        
        # Apply regime-specific adaptations if available
        if regime:
            adapted_params.update(self._get_regime_adaptations(regime))
        
        # Create StrategyParameters object
        strategy_params = StrategyParameters(
            strategy_name=adapted_params.get('strategy_name', 'adaptive_strategy'),
            parameters=adapted_params,
            confidence=0.8,  # Could be calculated based on parameter certainty
            valid_until=datetime.now() + timedelta(hours=24),
            market_regime=regime
        )
        
        # Store in history
        self.parameter_history.append(strategy_params)
        self.current_parameters = adapted_params
        
        self.logger.info(f"Parameters adapted for {vol_category} volatility, {trend_category} trend")
        
        return strategy_params
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Calculate trend strength (-1 to 1)"""
        
        if len(data) < 20:
            return 0.0
        
        # Calculate multiple timeframe trends
        short_trend = (data['close'].iloc[-1] / data['close'].iloc[-10] - 1)
        medium_trend = (data['close'].iloc[-1] / data['close'].iloc[-20] - 1)
        
        # Weighted average
        trend_strength = 0.6 * short_trend + 0.4 * medium_trend
        
        return np.clip(trend_strength, -1, 1)
    
    def _categorize_volatility(self, volatility: float) -> str:
        """Categorize volatility level"""
        if volatility < 0.15:
            return 'low'
        elif volatility < 0.30:
            return 'medium'
        else:
            return 'high'
    
    def _categorize_trend(self, trend_strength: float) -> str:
        """Categorize trend strength"""
        if trend_strength > 0.05:
            return 'strong_up'
        elif trend_strength > 0.02:
            return 'weak_up'
        elif trend_strength > -0.02:
            return 'sideways'
        elif trend_strength > -0.05:
            return 'weak_down'
        else:
            return 'strong_down'
    
    def _get_regime_adaptations(self, regime: MarketRegime) -> Dict[str, Any]:
        """Get adaptations specific to market regime"""
        
        adaptations = {}
        
        if regime.name == "Low Volatility Bull":
            adaptations.update({
                'position_size_percentage': min(10.0, self.base_parameters.get('position_size_percentage', 5.0) * 1.3),
                'take_profit_percentage': self.base_parameters.get('take_profit_percentage', 5.0) * 1.2
            })
        
        elif regime.name == "High Volatility":
            adaptations.update({
                'position_size_percentage': max(2.0, self.base_parameters.get('position_size_percentage', 5.0) * 0.6),
                'stop_loss_percentage': self.base_parameters.get('stop_loss_percentage', 3.0) * 1.5
            })
        
        elif regime.name == "Bear Market":
            adaptations.update({
                'position_size_percentage': max(1.0, self.base_parameters.get('position_size_percentage', 5.0) * 0.5),
                'max_positions': min(2, self.base_parameters.get('max_positions', 5))
            })
        
        return adaptations

class OnlineLearningStrategy:
    """Strategy that continuously learns and adapts"""
    
    def __init__(self, initial_strategy: str = "balanced", learning_rate: float = 0.01):
        self.initial_strategy = initial_strategy
        self.learning_rate = learning_rate
        
        # Strategy weights
        self.strategy_weights = {
            'trend_following': 0.33,
            'mean_reversion': 0.33,
            'momentum': 0.34
        }
        
        # Performance tracking
        self.strategy_performance = {name: deque(maxlen=100) for name in self.strategy_weights.keys()}
        self.recent_predictions = deque(maxlen=50)
        self.recent_outcomes = deque(maxlen=50)
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def update_strategy_weights(self, strategy_results: Dict[str, float]):
        """Update strategy weights based on recent performance"""
        
        # Store results
        for strategy_name, result in strategy_results.items():
            if strategy_name in self.strategy_performance:
                self.strategy_performance[strategy_name].append(result)
        
        # Calculate performance scores
        performance_scores = {}
        for strategy_name, results in self.strategy_performance.items():
            if len(results) > 10:  # Need minimum history
                # Use recent average with decay
                weights = np.exp(np.linspace(-1, 0, len(results)))  # More weight on recent
                performance_scores[strategy_name] = np.average(results, weights=weights)
            else:
                performance_scores[strategy_name] = 0.0
        
        # Normalize to probabilities
        total_score = sum(max(0, score) for score in performance_scores.values())
        
        if total_score > 0:
            # Update weights with learning rate
            for strategy_name in self.strategy_weights:
                old_weight = self.strategy_weights[strategy_name]
                new_weight = max(0, performance_scores[strategy_name]) / total_score
                
                # Apply learning rate
                self.strategy_weights[strategy_name] = (
                    (1 - self.learning_rate) * old_weight + 
                    self.learning_rate * new_weight
                )
        
        # Log updates
        self.logger.info("Strategy weights updated:")
        for strategy_name, weight in self.strategy_weights.items():
            self.logger.info(f"  {strategy_name}: {weight:.3f}")
    
    def get_adaptive_signal(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Generate adaptive signal based on learned weights"""
        
        # Calculate individual strategy signals
        signals = {}
        
        # Trend following signal
        if len(market_data) >= 20:
            sma_short = market_data['close'].tail(10).mean()
            sma_long = market_data['close'].tail(20).mean()
            signals['trend_following'] = 1.0 if sma_short > sma_long else -1.0
        else:
            signals['trend_following'] = 0.0
        
        # Mean reversion signal
        if len(market_data) >= 20:
            current_price = market_data['close'].iloc[-1]
            mean_price = market_data['close'].tail(20).mean()
            std_price = market_data['close'].tail(20).std()
            
            if std_price > 0:
                z_score = (current_price - mean_price) / std_price
                signals['mean_reversion'] = -np.tanh(z_score)  # Opposite of z-score
            else:
                signals['mean_reversion'] = 0.0
        else:
            signals['mean_reversion'] = 0.0
        
        # Momentum signal
        if len(market_data) >= 10:
            momentum = market_data['close'].pct_change(5).iloc[-1]
            signals['momentum'] = np.tanh(momentum * 100)  # Scale and bound
        else:
            signals['momentum'] = 0.0
        
        # Combine signals with learned weights
        adaptive_signal = sum(
            signals[strategy] * weight 
            for strategy, weight in self.strategy_weights.items()
        )
        
        return {
            'adaptive_signal': adaptive_signal,
            'individual_signals': signals,
            'strategy_weights': self.strategy_weights.copy()
        }

class AdaptiveAlgorithmManager:
    """Main manager for adaptive trading algorithms"""
    
    def __init__(self, base_strategy_params: Dict[str, Any]):
        self.base_strategy_params = base_strategy_params
        
        # Components
        self.regime_detector = MarketRegimeDetector()
        self.parameter_controller = AdaptiveParameterController(base_strategy_params)
        self.online_learner = OnlineLearningStrategy()
        
        # State tracking
        self.current_strategy = None
        self.adaptation_history = []
        self.performance_tracker = deque(maxlen=1000)
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def initialize(self, historical_data: pd.DataFrame):
        """Initialize the adaptive system with historical data"""
        
        self.logger.info("Initializing adaptive algorithm manager...")
        
        # Train regime detector
        self.regime_detector.train_regime_detector(historical_data)
        
        # Initialize parameter controller
        initial_regime = self.regime_detector.detect_current_regime(historical_data)
        self.current_strategy = self.parameter_controller.adapt_parameters(
            historical_data, initial_regime
        )
        
        self.logger.info("Adaptive system initialized successfully")
    
    def adapt_strategy(self, current_data: pd.DataFrame, 
                      recent_performance: Optional[Dict[str, float]] = None) -> AdaptationDecision:
        """Main adaptation method - decides if and how to adapt strategy"""
        
        # Detect current market regime
        current_regime = self.regime_detector.detect_current_regime(current_data)
        
        # Get adaptive parameters
        new_strategy = self.parameter_controller.adapt_parameters(current_data, current_regime)
        
        # Update online learning if performance data available
        if recent_performance:
            self.online_learner.update_strategy_weights(recent_performance)
        
        # Get adaptive signals
        adaptive_signals = self.online_learner.get_adaptive_signal(current_data)
        
        # Incorporate adaptive signals into strategy parameters
        new_strategy.parameters.update({
            'adaptive_signal': adaptive_signals['adaptive_signal'],
            'signal_weights': adaptive_signals['strategy_weights']
        })
        
        # Decide if adaptation is needed
        adaptation_needed = self._should_adapt(self.current_strategy, new_strategy)
        
        if adaptation_needed:
            decision_type = self._determine_adaptation_type(self.current_strategy, new_strategy)
            reason = self._generate_adaptation_reason(decision_type, current_regime)
            
            adaptation_decision = AdaptationDecision(
                decision_type=decision_type,
                old_strategy=self.current_strategy,
                new_strategy=new_strategy,
                reason=reason,
                confidence=new_strategy.confidence,
                timestamp=datetime.now()
            )
            
            # Apply adaptation
            self.current_strategy = new_strategy
            self.adaptation_history.append(adaptation_decision)
            
            self.logger.info(f"Strategy adapted: {decision_type} - {reason}")
            
            return adaptation_decision
        
        else:
            # No adaptation needed
            return AdaptationDecision(
                decision_type='no_change',
                old_strategy=self.current_strategy,
                new_strategy=self.current_strategy,
                reason="Current strategy remains optimal",
                confidence=0.8,
                timestamp=datetime.now()
            )
    
    def _should_adapt(self, old_strategy: Optional[StrategyParameters], 
                     new_strategy: StrategyParameters) -> bool:
        """Determine if strategy adaptation is needed"""
        
        if old_strategy is None:
            return True
        
        # Check for regime change
        if (old_strategy.market_regime and new_strategy.market_regime and 
            old_strategy.market_regime.regime_id != new_strategy.market_regime.regime_id):
            return True
        
        # Check for significant parameter changes
        significant_changes = 0
        for param, new_value in new_strategy.parameters.items():
            if param in old_strategy.parameters:
                old_value = old_strategy.parameters[param]
                if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                    if abs(new_value - old_value) / max(abs(old_value), 1e-10) > 0.1:  # 10% change
                        significant_changes += 1
        
        return significant_changes >= 2  # Adapt if 2+ parameters changed significantly
    
    def _determine_adaptation_type(self, old_strategy: Optional[StrategyParameters], 
                                  new_strategy: StrategyParameters) -> str:
        """Determine the type of adaptation"""
        
        if old_strategy is None:
            return 'initial_setup'
        
        # Check for regime change
        if (old_strategy.market_regime and new_strategy.market_regime and 
            old_strategy.market_regime.regime_id != new_strategy.market_regime.regime_id):
            return 'regime_change'
        
        # Check for strategy name change
        if old_strategy.strategy_name != new_strategy.strategy_name:
            return 'strategy_switch'
        
        return 'parameter_change'
    
    def _generate_adaptation_reason(self, decision_type: str, regime: MarketRegime) -> str:
        """Generate human-readable reason for adaptation"""
        
        if decision_type == 'regime_change':
            return f"Market regime changed to {regime.name}"
        elif decision_type == 'strategy_switch':
            return "Optimal strategy changed based on market conditions"
        elif decision_type == 'parameter_change':
            return "Strategy parameters adjusted for current market volatility and trend"
        else:
            return "Initial strategy setup based on current market conditions"
    
    def get_current_strategy(self) -> Optional[StrategyParameters]:
        """Get the current active strategy"""
        return self.current_strategy
    
    def get_adaptation_history(self, limit: int = 10) -> List[AdaptationDecision]:
        """Get recent adaptation history"""
        return self.adaptation_history[-limit:] if self.adaptation_history else []
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of adaptive algorithm performance"""
        
        if not self.adaptation_history:
            return {"status": "No adaptations yet"}
        
        # Count adaptation types
        adaptation_types = {}
        for decision in self.adaptation_history:
            decision_type = decision.decision_type
            adaptation_types[decision_type] = adaptation_types.get(decision_type, 0) + 1
        
        # Calculate average confidence
        avg_confidence = np.mean([d.confidence for d in self.adaptation_history])
        
        # Get regime distribution
        regime_counts = {}
        for decision in self.adaptation_history:
            if decision.new_strategy.market_regime:
                regime_name = decision.new_strategy.market_regime.name
                regime_counts[regime_name] = regime_counts.get(regime_name, 0) + 1
        
        return {
            'total_adaptations': len(self.adaptation_history),
            'adaptation_types': adaptation_types,
            'average_confidence': avg_confidence,
            'regime_distribution': regime_counts,
            'current_strategy': self.current_strategy.strategy_name if self.current_strategy else None,
            'current_regime': self.current_strategy.market_regime.name if self.current_strategy and self.current_strategy.market_regime else None
        }
    
    def save_state(self, filepath: str):
        """Save the current state of the adaptive system"""
        
        state_data = {
            'base_strategy_params': self.base_strategy_params,
            'current_strategy': self.current_strategy.__dict__ if self.current_strategy else None,
            'adaptation_history': [decision.__dict__ for decision in self.adaptation_history],
            'regime_definitions': self.regime_detector.regime_definitions,
            'strategy_weights': self.online_learner.strategy_weights,
            'timestamp': datetime.now().isoformat()
        }
        
        # Convert datetime objects to strings
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)
        
        with open(filepath, 'w') as f:
            json.dump(state_data, f, default=convert_datetime, indent=2)
        
        self.logger.info(f"Adaptive system state saved to {filepath}")

def create_adaptive_manager(base_strategy_params: Dict[str, Any]) -> AdaptiveAlgorithmManager:
    """Factory function to create adaptive algorithm manager"""
    return AdaptiveAlgorithmManager(base_strategy_params)