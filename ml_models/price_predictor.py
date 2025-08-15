#!/usr/bin/env python3
"""
Price Prediction Models
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

@dataclass
class PredictionResult:
    """Result from price prediction"""
    predicted_price: float
    confidence: float
    model_used: str
    prediction_horizon: int
    timestamp: datetime
    features_used: List[str]

@dataclass
class ModelPerformance:
    """Model performance metrics"""
    model_name: str
    r2_score: float
    mae: float
    mse: float
    accuracy_direction: float
    training_samples: int
    test_samples: int

class PricePredictor:
    """Base price predictor"""
    
    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self.model = None
        self.is_trained = False
        self.scaler = StandardScaler()
        self.feature_names = []
    
    def train(self, data: pd.DataFrame, target_horizon: int = 1) -> ModelPerformance:
        """Train the price prediction model"""
        
        # Prepare features and target
        X, y = self._prepare_data(data, target_horizon)
        
        if len(X) < 100:
            raise ValueError("Insufficient data for training")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        predictions = self.model.predict(X_test_scaled)
        mae = np.mean(np.abs(predictions - y_test))
        mse = np.mean((predictions - y_test) ** 2)
        
        # Direction accuracy
        y_test_prev = X_test['close'].values
        actual_direction = (y_test > y_test_prev).astype(int)
        pred_direction = (predictions > y_test_prev).astype(int)
        accuracy_direction = np.mean(actual_direction == pred_direction)
        
        self.is_trained = True
        
        return ModelPerformance(
            model_name=self.model_name,
            r2_score=test_score,
            mae=mae,
            mse=mse,
            accuracy_direction=accuracy_direction,
            training_samples=len(X_train),
            test_samples=len(X_test)
        )
    
    def predict(self, data: pd.DataFrame, target_horizon: int = 1) -> PredictionResult:
        """Make price prediction"""
        
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        # Prepare features
        X, _ = self._prepare_data(data, target_horizon, for_prediction=True)
        
        # Get last row for prediction
        X_last = X.iloc[-1:] if len(X) > 0 else X
        
        # Scale and predict
        X_scaled = self.scaler.transform(X_last)
        prediction = self.model.predict(X_scaled)[0]
        
        # Calculate confidence (simplified)
        confidence = min(0.9, self.model.score(X_scaled, [prediction]) + 0.3)
        
        return PredictionResult(
            predicted_price=prediction,
            confidence=confidence,
            model_used=self.model_name,
            prediction_horizon=target_horizon,
            timestamp=datetime.now(),
            features_used=self.feature_names
        )
    
    def _prepare_data(self, data: pd.DataFrame, target_horizon: int, 
                     for_prediction: bool = False) -> tuple:
        """Prepare features and target"""
        
        df = data.copy()
        
        # Create features
        df['returns'] = df['close'].pct_change()
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['high_low_ratio'] = df['high'] / df['low']
        df['close_open_ratio'] = df['close'] / df['open']
        
        # Moving averages
        for period in [5, 10, 20]:
            df[f'ma_{period}'] = df['close'].rolling(period).mean()
            df[f'ma_ratio_{period}'] = df['close'] / df[f'ma_{period}']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Target (future price)
        if not for_prediction:
            df['target'] = df['close'].shift(-target_horizon)
        
        # Drop NaN values
        df = df.dropna()
        
        # Select features
        feature_cols = [col for col in df.columns if col not in ['target', 'timestamp']]
        self.feature_names = feature_cols
        
        X = df[feature_cols]
        y = df['target'] if not for_prediction else None
        
        return X, y

class EnsemblePricePredictor:
    """Ensemble of multiple price predictors"""
    
    def __init__(self):
        self.models = [
            PricePredictor("random_forest"),
            PricePredictor("gradient_boost"),
            PricePredictor("linear_regression")
        ]
        self.is_trained = False
    
    def train(self, data: pd.DataFrame, target_horizon: int = 1) -> List[ModelPerformance]:
        """Train all models"""
        performances = []
        
        for model in self.models:
            try:
                performance = model.train(data, target_horizon)
                performances.append(performance)
            except Exception as e:
                logger.error(f"Failed to train {model.model_name}: {e}")
        
        if performances:
            self.is_trained = True
        
        return performances
    
    def predict(self, data: pd.DataFrame, target_horizon: int = 1) -> PredictionResult:
        """Make ensemble prediction"""
        
        if not self.is_trained:
            raise ValueError("Ensemble not trained")
        
        predictions = []
        weights = []
        
        for model in self.models:
            if model.is_trained:
                try:
                    pred = model.predict(data, target_horizon)
                    predictions.append(pred.predicted_price)
                    weights.append(pred.confidence)
                except Exception as e:
                    logger.error(f"Prediction failed for {model.model_name}: {e}")
        
        if not predictions:
            raise ValueError("No models available for prediction")
        
        # Weighted average
        weights = np.array(weights)
        weights = weights / weights.sum()
        ensemble_prediction = np.average(predictions, weights=weights)
        ensemble_confidence = np.mean(weights)
        
        return PredictionResult(
            predicted_price=ensemble_prediction,
            confidence=ensemble_confidence,
            model_used="ensemble",
            prediction_horizon=target_horizon,
            timestamp=datetime.now(),
            features_used=self.models[0].feature_names if self.models else []
        )

def create_price_predictor(model_type: str = "single") -> Any:
    """Factory function to create price predictor"""
    if model_type == "ensemble":
        return EnsemblePricePredictor()
    else:
        return PricePredictor(model_type)