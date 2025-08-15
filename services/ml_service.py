#!/usr/bin/env python3
"""
AI Trading Academy - Machine Learning Service
============================================

Service layer for ML-powered trading features:
- Price prediction and forecasting
- Reinforcement learning strategy optimization
- Adaptive algorithm management
- Model performance tracking and evaluation

Educational focus: Integrate ML seamlessly into trading workflows
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from datetime import datetime, timedelta
from pathlib import Path
import joblib
import json
from dataclasses import asdict

# Import ML components
from ml_models.price_predictor import (
    create_price_predictor, PredictionResult, ModelPerformance,
    EnsemblePricePredictor
)
from ml_models.reinforcement_learning import (
    create_adaptive_optimizer, AdaptiveStrategyOptimizer,
    RLAgentPerformance, TradingEnvironment
)
from ml_models.adaptive_algorithms import (
    create_adaptive_manager, AdaptiveAlgorithmManager,
    MarketRegimeDetector, AdaptationDecision
)

# Import other services
from config.config_manager import get_config_manager
from utils.logging_config import get_logger

class MLModelManager:
    """Manages ML model lifecycle and predictions"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.logger = get_logger(self.__class__.__name__)
        
        # Model storage
        self.price_predictor = None
        self.rl_optimizer = None
        self.adaptive_manager = None
        
        # Model paths
        self.model_dir = Path("ml_models/trained_models")
        self.model_dir.mkdir(exist_ok=True)
        
        # Performance tracking
        self.prediction_history = []
        self.model_performances = {}
        
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize ML models with default configurations"""
        
        try:
            # Initialize price predictor
            self.price_predictor = create_price_predictor("ensemble")
            self.logger.info("Price predictor initialized")
            
            # Initialize RL optimizer
            self.rl_optimizer = create_adaptive_optimizer(
                use_deep_learning=True
            )
            self.logger.info("RL optimizer initialized")
            
            # Get base strategy parameters for adaptive manager
            trading_config = self.config_manager.get_trading_config()
            base_params = {
                'strategy_name': trading_config.strategy_mode,
                'position_size_percentage': trading_config.position_size_percentage,
                'stop_loss_percentage': getattr(trading_config, 'stop_loss_percentage', 3.0),
                'take_profit_percentage': getattr(trading_config, 'take_profit_percentage', 5.0),
                'max_positions': trading_config.max_positions
            }
            
            self.adaptive_manager = create_adaptive_manager(base_params)
            self.logger.info("Adaptive algorithm manager initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ML models: {e}")
    
    def train_price_predictor(self, data: pd.DataFrame, 
                            target_horizon: int = 1) -> Dict[str, ModelPerformance]:
        """Train price prediction models"""
        
        self.logger.info(f"Training price predictor on {len(data)} samples...")
        
        try:
            if isinstance(self.price_predictor, EnsemblePricePredictor):
                performances = self.price_predictor.train(data, target_horizon)
                
                # Store performances
                for i, performance in enumerate(performances):
                    self.model_performances[f"price_predictor_{performance.model_name}"] = performance
                
                # Save trained models
                self._save_price_predictor()
                
                self.logger.info(f"Price predictor training completed with {len(performances)} models")
                return {perf.model_name: perf for perf in performances}
                
            else:
                performance = self.price_predictor.train(data, target_horizon)
                self.model_performances["price_predictor"] = performance
                
                self._save_price_predictor()
                
                self.logger.info("Price predictor training completed")
                return {"single_model": performance}
                
        except Exception as e:
            self.logger.error(f"Price predictor training failed: {e}")
            return {}
    
    def get_price_prediction(self, data: pd.DataFrame, 
                           target_horizon: int = 1) -> Optional[PredictionResult]:
        """Get price prediction from trained model"""
        
        if not self.price_predictor or not self.price_predictor.is_trained:
            self.logger.warning("Price predictor not trained. Cannot make prediction.")
            return None
        
        try:
            prediction = self.price_predictor.predict(data, target_horizon)
            
            # Store prediction in history
            self.prediction_history.append(prediction)
            
            # Limit history size
            if len(self.prediction_history) > 1000:
                self.prediction_history = self.prediction_history[-1000:]
            
            self.logger.info(f"Price prediction: ${prediction.predicted_price:.2f} "
                           f"(confidence: {prediction.confidence:.1%})")
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Price prediction failed: {e}")
            return None
    
    def train_rl_optimizer(self, data: pd.DataFrame, 
                          episodes: int = 1000) -> Dict[str, RLAgentPerformance]:
        """Train reinforcement learning models"""
        
        self.logger.info(f"Training RL optimizer with {episodes} episodes...")
        
        try:
            performances = self.rl_optimizer.compare_agents(data, episodes)
            
            # Store performances
            for agent_type, performance in performances.items():
                self.model_performances[f"rl_{agent_type}"] = performance
            
            # Save trained models
            self._save_rl_optimizer()
            
            self.logger.info(f"RL training completed with {len(performances)} agents")
            return performances
            
        except Exception as e:
            self.logger.error(f"RL training failed: {e}")
            return {}
    
    def optimize_strategy_with_rl(self, data: pd.DataFrame, 
                                base_params: Dict[str, Any],
                                episodes: int = 1000) -> Dict[str, Any]:
        """Use RL to optimize trading strategy"""
        
        try:
            optimized_params = self.rl_optimizer.optimize_trading_strategy(
                data, base_params, episodes
            )
            
            self.logger.info("Strategy optimization completed using RL")
            return optimized_params
            
        except Exception as e:
            self.logger.error(f"RL strategy optimization failed: {e}")
            return base_params
    
    def initialize_adaptive_manager(self, historical_data: pd.DataFrame):
        """Initialize the adaptive algorithm manager"""
        
        try:
            self.adaptive_manager.initialize(historical_data)
            self.logger.info("Adaptive algorithm manager initialized with historical data")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize adaptive manager: {e}")
    
    def get_adaptive_strategy(self, current_data: pd.DataFrame,
                            recent_performance: Optional[Dict[str, float]] = None) -> Optional[AdaptationDecision]:
        """Get adaptive strategy recommendation"""
        
        if not self.adaptive_manager:
            self.logger.warning("Adaptive manager not initialized")
            return None
        
        try:
            adaptation_decision = self.adaptive_manager.adapt_strategy(
                current_data, recent_performance
            )
            
            if adaptation_decision.decision_type != 'no_change':
                self.logger.info(f"Strategy adaptation: {adaptation_decision.reason}")
            
            return adaptation_decision
            
        except Exception as e:
            self.logger.error(f"Adaptive strategy generation failed: {e}")
            return None
    
    def _save_price_predictor(self):
        """Save trained price predictor"""
        
        try:
            if hasattr(self.price_predictor, 'models'):
                # Ensemble predictor
                for model in self.price_predictor.models:
                    if hasattr(model, 'model') and model.model is not None:
                        model_path = self.model_dir / f"price_predictor_{model.model_name}.joblib"
                        joblib.dump(model.model, model_path)
            else:
                # Single model
                if hasattr(self.price_predictor, 'model') and self.price_predictor.model is not None:
                    model_path = self.model_dir / "price_predictor.joblib"
                    joblib.dump(self.price_predictor.model, model_path)
            
            self.logger.info("Price predictor models saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save price predictor: {e}")
    
    def _save_rl_optimizer(self):
        """Save trained RL optimizer"""
        
        try:
            rl_path = self.model_dir / "rl_optimizer_state.json"
            self.rl_optimizer.save_agents(str(rl_path))
            
            self.logger.info("RL optimizer state saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save RL optimizer: {e}")
    
    def get_ml_status(self) -> Dict[str, Any]:
        """Get status of all ML components"""
        
        status = {
            'price_predictor': {
                'available': self.price_predictor is not None,
                'trained': self.price_predictor.is_trained if self.price_predictor else False,
                'model_type': type(self.price_predictor).__name__ if self.price_predictor else None
            },
            'rl_optimizer': {
                'available': self.rl_optimizer is not None,
                'trained_agents': len(self.rl_optimizer.trained_agents) if self.rl_optimizer else 0
            },
            'adaptive_manager': {
                'available': self.adaptive_manager is not None,
                'initialized': bool(self.adaptive_manager.current_strategy) if self.adaptive_manager else False
            },
            'model_performances': {
                name: {
                    'r2_score': perf.r2_score if hasattr(perf, 'r2_score') else None,
                    'accuracy': perf.accuracy_direction if hasattr(perf, 'accuracy_direction') else None,
                    'avg_reward': perf.average_reward if hasattr(perf, 'average_reward') else None
                }
                for name, perf in self.model_performances.items()
            },
            'prediction_history_size': len(self.prediction_history)
        }
        
        return status

class MLTradingService:
    """Main service for ML-powered trading features"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.logger = get_logger(self.__class__.__name__)
        
        # Initialize ML model manager
        self.model_manager = MLModelManager()
        
        # Service state
        self.is_initialized = False
        self.last_prediction = None
        self.last_adaptation = None
        
        self.logger.info("ML Trading Service initialized")
    
    def initialize_ml_system(self, historical_data: pd.DataFrame, 
                           train_models: bool = True) -> Dict[str, Any]:
        """Initialize the complete ML system"""
        
        self.logger.info("Initializing ML trading system...")
        
        results = {}
        
        try:
            # Initialize adaptive manager first
            self.model_manager.initialize_adaptive_manager(historical_data)
            results['adaptive_manager'] = 'initialized'
            
            # Train models if requested
            if train_models:
                # Train price predictor
                if len(historical_data) >= 100:
                    price_performances = self.model_manager.train_price_predictor(
                        historical_data, target_horizon=1
                    )
                    results['price_predictor'] = price_performances
                else:
                    self.logger.warning("Insufficient data for price predictor training")
                    results['price_predictor'] = 'insufficient_data'
                
                # Train RL optimizer
                if len(historical_data) >= 500:
                    rl_performances = self.model_manager.train_rl_optimizer(
                        historical_data, episodes=500
                    )
                    results['rl_optimizer'] = rl_performances
                else:
                    self.logger.warning("Insufficient data for RL training")
                    results['rl_optimizer'] = 'insufficient_data'
            
            self.is_initialized = True
            results['status'] = 'success'
            
            self.logger.info("ML trading system initialization completed")
            
        except Exception as e:
            self.logger.error(f"ML system initialization failed: {e}")
            results['status'] = 'failed'
            results['error'] = str(e)
        
        return results
    
    def get_ml_trading_signals(self, current_data: pd.DataFrame,
                             recent_performance: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Get comprehensive ML trading signals"""
        
        signals = {
            'timestamp': datetime.now().isoformat(),
            'price_prediction': None,
            'adaptive_strategy': None,
            'confidence_score': 0.0,
            'recommendations': []
        }
        
        try:
            # Get price prediction
            prediction = self.model_manager.get_price_prediction(current_data)
            if prediction:
                self.last_prediction = prediction
                signals['price_prediction'] = {
                    'predicted_price': prediction.predicted_price,
                    'current_price': current_data['close'].iloc[-1],
                    'price_change_pct': (prediction.predicted_price / current_data['close'].iloc[-1] - 1) * 100,
                    'confidence': prediction.confidence,
                    'model_used': prediction.model_used,
                    'horizon_hours': prediction.prediction_horizon
                }
                signals['confidence_score'] += prediction.confidence * 0.4
                
                # Add recommendation based on prediction
                if prediction.predicted_price > current_data['close'].iloc[-1] * 1.01:
                    signals['recommendations'].append('Consider buying - price predicted to rise')
                elif prediction.predicted_price < current_data['close'].iloc[-1] * 0.99:
                    signals['recommendations'].append('Consider selling - price predicted to fall')
            
            # Get adaptive strategy
            adaptation = self.model_manager.get_adaptive_strategy(
                current_data, recent_performance
            )
            if adaptation:
                self.last_adaptation = adaptation
                signals['adaptive_strategy'] = {
                    'decision_type': adaptation.decision_type,
                    'reason': adaptation.reason,
                    'confidence': adaptation.confidence,
                    'strategy_name': adaptation.new_strategy.strategy_name,
                    'key_parameters': {
                        k: v for k, v in adaptation.new_strategy.parameters.items()
                        if isinstance(v, (int, float, str, bool))
                    }
                }
                signals['confidence_score'] += adaptation.confidence * 0.3
                
                # Add recommendation based on adaptation
                if adaptation.decision_type != 'no_change':
                    signals['recommendations'].append(f'Strategy adapted: {adaptation.reason}')
            
            # Calculate overall confidence
            signals['confidence_score'] = min(1.0, signals['confidence_score'])
            
            # Add general recommendations based on combined signals
            if signals['confidence_score'] > 0.7:
                signals['recommendations'].append('High confidence in ML signals')
            elif signals['confidence_score'] < 0.3:
                signals['recommendations'].append('Low confidence - consider manual review')
            
        except Exception as e:
            self.logger.error(f"Failed to generate ML trading signals: {e}")
            signals['error'] = str(e)
        
        return signals
    
    def evaluate_prediction_accuracy(self, actual_prices: List[float],
                                   timestamps: List[datetime]) -> Dict[str, float]:
        """Evaluate the accuracy of recent predictions"""
        
        if not self.model_manager.prediction_history:
            return {'error': 'No predictions to evaluate'}
        
        try:
            # Match predictions with actual outcomes
            correct_direction = 0
            total_predictions = 0
            absolute_errors = []
            
            for prediction in self.model_manager.prediction_history[-50:]:  # Last 50 predictions
                # Find matching actual price (simplified)
                pred_time = prediction.timestamp
                
                # Find closest actual price
                closest_idx = None
                min_time_diff = timedelta(days=365)
                
                for i, ts in enumerate(timestamps):
                    time_diff = abs(ts - pred_time)
                    if time_diff < min_time_diff:
                        min_time_diff = time_diff
                        closest_idx = i
                
                if closest_idx is not None and min_time_diff < timedelta(hours=2):
                    actual_price = actual_prices[closest_idx]
                    
                    # Calculate error
                    absolute_error = abs(prediction.predicted_price - actual_price)
                    absolute_errors.append(absolute_error)
                    
                    # Check direction accuracy (simplified)
                    # This would need the previous price for proper direction calculation
                    total_predictions += 1
            
            if total_predictions > 0:
                return {
                    'total_predictions_evaluated': total_predictions,
                    'mean_absolute_error': np.mean(absolute_errors) if absolute_errors else 0,
                    'median_absolute_error': np.median(absolute_errors) if absolute_errors else 0,
                    'prediction_count': len(self.model_manager.prediction_history)
                }
            else:
                return {'error': 'No matching predictions and actuals found'}
                
        except Exception as e:
            self.logger.error(f"Prediction evaluation failed: {e}")
            return {'error': str(e)}
    
    def get_rl_strategy_recommendation(self, data: pd.DataFrame,
                                     current_strategy_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get RL-optimized strategy recommendation"""
        
        try:
            optimized_params = self.model_manager.optimize_strategy_with_rl(
                data, current_strategy_params, episodes=200
            )
            
            # Calculate parameter changes
            changes = {}
            for param, new_value in optimized_params.items():
                if param in current_strategy_params:
                    old_value = current_strategy_params[param]
                    if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                        if old_value != 0:
                            change_pct = (new_value - old_value) / old_value * 100
                            changes[param] = {
                                'old_value': old_value,
                                'new_value': new_value,
                                'change_pct': change_pct
                            }
            
            return {
                'optimized_parameters': optimized_params,
                'parameter_changes': changes,
                'recommendation': 'Apply RL-optimized parameters for better performance',
                'confidence': optimized_params.get('rl_insights', {}).get('avg_reward', 0.5)
            }
            
        except Exception as e:
            self.logger.error(f"RL strategy recommendation failed: {e}")
            return {'error': str(e)}
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get comprehensive ML service status"""
        
        status = {
            'service_initialized': self.is_initialized,
            'last_prediction_time': self.last_prediction.timestamp if self.last_prediction else None,
            'last_adaptation_time': self.last_adaptation.timestamp if self.last_adaptation else None,
            'ml_models': self.model_manager.get_ml_status()
        }
        
        return status

# Singleton instance
_ml_service_instance = None

def get_ml_service() -> MLTradingService:
    """Get singleton ML trading service instance"""
    global _ml_service_instance
    
    if _ml_service_instance is None:
        _ml_service_instance = MLTradingService()
    
    return _ml_service_instance