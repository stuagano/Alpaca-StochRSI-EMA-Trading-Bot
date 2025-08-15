#!/usr/bin/env python3
"""
AI Trading Academy - Price Prediction Models
============================================

Advanced machine learning models for price forecasting using multiple techniques:
- LSTM neural networks for time series prediction
- Random Forest for feature-based prediction
- Gradient Boosting for ensemble learning
- Technical indicator-based features

Educational focus: Learn how ML can enhance trading decisions
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

# ML Libraries
try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.model_selection import train_test_split, TimeSeriesSplit
    from sklearn.preprocessing import StandardScaler, MinMaxScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    import joblib
    
    # Try to import deep learning libraries
    try:
        import tensorflow as tf
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout
        from tensorflow.keras.optimizers import Adam
        TENSORFLOW_AVAILABLE = True
    except ImportError:
        TENSORFLOW_AVAILABLE = False
        warnings.warn("TensorFlow not available. LSTM models will be disabled.")
    
except ImportError as e:
    raise ImportError(f"Required ML libraries not installed: {e}")

warnings.filterwarnings('ignore', category=FutureWarning)

@dataclass
class PredictionResult:
    """Results from price prediction model"""
    predicted_price: float
    confidence: float
    prediction_horizon: int  # hours ahead
    model_used: str
    features_used: List[str]
    timestamp: datetime
    actual_price: Optional[float] = None
    error: Optional[float] = None

@dataclass
class ModelPerformance:
    """Model performance metrics"""
    model_name: str
    mse: float
    mae: float
    r2_score: float
    accuracy_direction: float  # % of correct directional predictions
    training_samples: int
    validation_samples: int
    feature_importance: Dict[str, float]

class FeatureEngineer:
    """Create advanced features for ML models"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive technical indicator features"""
        
        # Ensure we have OHLCV columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        feature_df = df.copy()
        
        # Price-based features
        feature_df['price_change'] = feature_df['close'].pct_change()
        feature_df['price_change_2'] = feature_df['close'].pct_change(periods=2)
        feature_df['price_change_5'] = feature_df['close'].pct_change(periods=5)
        
        # Volatility features
        feature_df['volatility_5'] = feature_df['price_change'].rolling(5).std()
        feature_df['volatility_10'] = feature_df['price_change'].rolling(10).std()
        feature_df['volatility_20'] = feature_df['price_change'].rolling(20).std()
        
        # Moving averages
        for period in [5, 10, 20, 50]:
            feature_df[f'sma_{period}'] = feature_df['close'].rolling(period).mean()
            feature_df[f'ema_{period}'] = feature_df['close'].ewm(span=period).mean()
            feature_df[f'price_to_sma_{period}'] = feature_df['close'] / feature_df[f'sma_{period}']
            feature_df[f'price_to_ema_{period}'] = feature_df['close'] / feature_df[f'ema_{period}']
        
        # RSI
        delta = feature_df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        feature_df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = feature_df['close'].ewm(span=12).mean()
        ema_26 = feature_df['close'].ewm(span=26).mean()
        feature_df['macd'] = ema_12 - ema_26
        feature_df['macd_signal'] = feature_df['macd'].ewm(span=9).mean()
        feature_df['macd_histogram'] = feature_df['macd'] - feature_df['macd_signal']
        
        # Bollinger Bands
        sma_20 = feature_df['close'].rolling(20).mean()
        std_20 = feature_df['close'].rolling(20).std()
        feature_df['bb_upper'] = sma_20 + (std_20 * 2)
        feature_df['bb_lower'] = sma_20 - (std_20 * 2)
        feature_df['bb_width'] = (feature_df['bb_upper'] - feature_df['bb_lower']) / sma_20
        feature_df['bb_position'] = (feature_df['close'] - feature_df['bb_lower']) / (feature_df['bb_upper'] - feature_df['bb_lower'])
        
        # Volume features
        feature_df['volume_sma_10'] = feature_df['volume'].rolling(10).mean()
        feature_df['volume_ratio'] = feature_df['volume'] / feature_df['volume_sma_10']
        feature_df['price_volume'] = feature_df['close'] * feature_df['volume']
        
        # Time-based features
        if isinstance(feature_df.index, pd.DatetimeIndex):
            feature_df['hour'] = feature_df.index.hour
            feature_df['day_of_week'] = feature_df.index.dayofweek
            feature_df['month'] = feature_df.index.month
        
        # Lag features
        for lag in [1, 2, 3, 5]:
            feature_df[f'close_lag_{lag}'] = feature_df['close'].shift(lag)
            feature_df[f'volume_lag_{lag}'] = feature_df['volume'].shift(lag)
            feature_df[f'rsi_lag_{lag}'] = feature_df['rsi'].shift(lag)
        
        # Forward-looking target (what we want to predict)
        for horizon in [1, 2, 4, 8]:  # 1, 2, 4, 8 periods ahead
            feature_df[f'target_price_{horizon}h'] = feature_df['close'].shift(-horizon)
            feature_df[f'target_return_{horizon}h'] = feature_df['close'].pct_change(periods=-horizon)
        
        return feature_df
    
    def select_features(self, df: pd.DataFrame, target_col: str) -> List[str]:
        """Select the most important features for modeling"""
        
        # Remove target columns and non-feature columns
        exclude_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp'] + [col for col in df.columns if col.startswith('target_')]
        
        # Get potential feature columns
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        # Remove columns with too many NaN values
        feature_cols = [col for col in feature_cols if df[col].notna().sum() > len(df) * 0.8]
        
        self.logger.info(f"Selected {len(feature_cols)} features for modeling")
        
        return feature_cols

class PricePredictionModel:
    """Base class for price prediction models"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None
        self.scaler = None
        self.feature_engineer = FeatureEngineer()
        self.feature_columns = []
        self.is_trained = False
        self.performance = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def prepare_data(self, df: pd.DataFrame, target_horizon: int = 1) -> Tuple[pd.DataFrame, str]:
        """Prepare data with features and target"""
        
        # Create features
        featured_df = self.feature_engineer.create_technical_features(df)
        
        # Define target
        target_col = f'target_return_{target_horizon}h'
        
        # Select features
        self.feature_columns = self.feature_engineer.select_features(featured_df, target_col)
        
        # Drop rows with NaN in features or target
        clean_df = featured_df.dropna(subset=self.feature_columns + [target_col])
        
        self.logger.info(f"Prepared {len(clean_df)} samples with {len(self.feature_columns)} features")
        
        return clean_df, target_col
    
    def train(self, df: pd.DataFrame, target_horizon: int = 1, test_size: float = 0.2):
        """Train the prediction model"""
        raise NotImplementedError
    
    def predict(self, df: pd.DataFrame, target_horizon: int = 1) -> PredictionResult:
        """Make price prediction"""
        raise NotImplementedError
    
    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> ModelPerformance:
        """Evaluate model performance"""
        if not self.is_trained:
            raise ValueError("Model must be trained before evaluation")
        
        # Make predictions
        if self.scaler:
            X_test_scaled = self.scaler.transform(X_test[self.feature_columns])
            predictions = self.model.predict(X_test_scaled)
        else:
            predictions = self.model.predict(X_test[self.feature_columns])
        
        # Calculate metrics
        mse = mean_squared_error(y_test, predictions)
        mae = mean_absolute_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)
        
        # Directional accuracy
        actual_direction = (y_test > 0).astype(int)
        predicted_direction = (predictions > 0).astype(int)
        direction_accuracy = (actual_direction == predicted_direction).mean()
        
        # Feature importance
        feature_importance = {}
        if hasattr(self.model, 'feature_importances_'):
            feature_importance = dict(zip(self.feature_columns, self.model.feature_importances_))
        
        performance = ModelPerformance(
            model_name=self.model_name,
            mse=mse,
            mae=mae,
            r2_score=r2,
            accuracy_direction=direction_accuracy,
            training_samples=len(X_test),  # This would be training size in real implementation
            validation_samples=len(X_test),
            feature_importance=feature_importance
        )
        
        self.performance = performance
        return performance

class RandomForestPricePredictor(PricePredictionModel):
    """Random Forest-based price predictor"""
    
    def __init__(self, n_estimators: int = 100, random_state: int = 42):
        super().__init__("RandomForest")
        self.n_estimators = n_estimators
        self.random_state = random_state
    
    def train(self, df: pd.DataFrame, target_horizon: int = 1, test_size: float = 0.2):
        """Train Random Forest model"""
        
        # Prepare data
        prepared_df, target_col = self.prepare_data(df, target_horizon)
        
        X = prepared_df[self.feature_columns]
        y = prepared_df[target_col]
        
        # Split data (time series split)
        split_idx = int(len(prepared_df) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Initialize and train model
        self.model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate performance
        performance = self.evaluate(X_test, y_test)
        
        self.logger.info(f"Random Forest trained - R²: {performance.r2_score:.3f}, Direction Accuracy: {performance.accuracy_direction:.1%}")
        
        return performance
    
    def predict(self, df: pd.DataFrame, target_horizon: int = 1) -> PredictionResult:
        """Make prediction using Random Forest"""
        
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        # Prepare features for latest data point
        featured_df = self.feature_engineer.create_technical_features(df)
        
        # Get latest complete row
        latest_row = featured_df.dropna(subset=self.feature_columns).tail(1)
        
        if len(latest_row) == 0:
            raise ValueError("No valid data for prediction")
        
        # Make prediction
        X = latest_row[self.feature_columns]
        predicted_return = self.model.predict(X)[0]
        
        # Convert return to price
        current_price = df['close'].iloc[-1]
        predicted_price = current_price * (1 + predicted_return)
        
        # Calculate confidence (based on feature importance and prediction certainty)
        confidence = min(0.95, max(0.3, 1 - abs(predicted_return) * 10))  # Simple confidence metric
        
        return PredictionResult(
            predicted_price=predicted_price,
            confidence=confidence,
            prediction_horizon=target_horizon,
            model_used=self.model_name,
            features_used=self.feature_columns,
            timestamp=datetime.now()
        )

class GradientBoostingPricePredictor(PricePredictionModel):
    """Gradient Boosting-based price predictor"""
    
    def __init__(self, n_estimators: int = 100, learning_rate: float = 0.1, random_state: int = 42):
        super().__init__("GradientBoosting")
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.random_state = random_state
    
    def train(self, df: pd.DataFrame, target_horizon: int = 1, test_size: float = 0.2):
        """Train Gradient Boosting model"""
        
        # Prepare data
        prepared_df, target_col = self.prepare_data(df, target_horizon)
        
        X = prepared_df[self.feature_columns]
        y = prepared_df[target_col]
        
        # Split data (time series split)
        split_idx = int(len(prepared_df) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Initialize and train model
        self.model = GradientBoostingRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            random_state=self.random_state
        )
        
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluate performance
        performance = self.evaluate(X_test, y_test)
        
        self.logger.info(f"Gradient Boosting trained - R²: {performance.r2_score:.3f}, Direction Accuracy: {performance.accuracy_direction:.1%}")
        
        return performance
    
    def predict(self, df: pd.DataFrame, target_horizon: int = 1) -> PredictionResult:
        """Make prediction using Gradient Boosting"""
        
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        # Prepare features for latest data point
        featured_df = self.feature_engineer.create_technical_features(df)
        
        # Get latest complete row
        latest_row = featured_df.dropna(subset=self.feature_columns).tail(1)
        
        if len(latest_row) == 0:
            raise ValueError("No valid data for prediction")
        
        # Make prediction
        X = latest_row[self.feature_columns]
        predicted_return = self.model.predict(X)[0]
        
        # Convert return to price
        current_price = df['close'].iloc[-1]
        predicted_price = current_price * (1 + predicted_return)
        
        # Calculate confidence
        confidence = min(0.95, max(0.3, 1 - abs(predicted_return) * 8))
        
        return PredictionResult(
            predicted_price=predicted_price,
            confidence=confidence,
            prediction_horizon=target_horizon,
            model_used=self.model_name,
            features_used=self.feature_columns,
            timestamp=datetime.now()
        )

if TENSORFLOW_AVAILABLE:
    class LSTMPricePredictor(PricePredictionModel):
        """LSTM Neural Network-based price predictor"""
        
        def __init__(self, sequence_length: int = 60, lstm_units: int = 50, dropout: float = 0.2):
            super().__init__("LSTM")
            self.sequence_length = sequence_length
            self.lstm_units = lstm_units
            self.dropout = dropout
            self.scaler = MinMaxScaler()
        
        def create_sequences(self, data: np.ndarray, target: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
            """Create sequences for LSTM training"""
            X, y = [], []
            
            for i in range(self.sequence_length, len(data)):
                X.append(data[i-self.sequence_length:i])
                y.append(target[i])
            
            return np.array(X), np.array(y)
        
        def train(self, df: pd.DataFrame, target_horizon: int = 1, test_size: float = 0.2):
            """Train LSTM model"""
            
            # Prepare data
            prepared_df, target_col = self.prepare_data(df, target_horizon)
            
            X = prepared_df[self.feature_columns].values
            y = prepared_df[target_col].values
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Create sequences
            X_seq, y_seq = self.create_sequences(X_scaled, y)
            
            # Split data
            split_idx = int(len(X_seq) * (1 - test_size))
            X_train, X_test = X_seq[:split_idx], X_seq[split_idx:]
            y_train, y_test = y_seq[:split_idx], y_seq[split_idx:]
            
            # Build LSTM model
            self.model = Sequential([
                LSTM(self.lstm_units, return_sequences=True, input_shape=(self.sequence_length, len(self.feature_columns))),
                Dropout(self.dropout),
                LSTM(self.lstm_units, return_sequences=False),
                Dropout(self.dropout),
                Dense(25),
                Dense(1)
            ])
            
            self.model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
            
            # Train model
            history = self.model.fit(
                X_train, y_train,
                batch_size=32,
                epochs=50,
                validation_data=(X_test, y_test),
                verbose=0,
                shuffle=False  # Important for time series
            )
            
            self.is_trained = True
            
            # Evaluate performance
            predictions = self.model.predict(X_test, verbose=0).flatten()
            
            # Calculate metrics manually since evaluate method expects sklearn format
            mse = mean_squared_error(y_test, predictions)
            mae = mean_absolute_error(y_test, predictions)
            r2 = r2_score(y_test, predictions)
            
            # Directional accuracy
            actual_direction = (y_test > 0).astype(int)
            predicted_direction = (predictions > 0).astype(int)
            direction_accuracy = (actual_direction == predicted_direction).mean()
            
            performance = ModelPerformance(
                model_name=self.model_name,
                mse=mse,
                mae=mae,
                r2_score=r2,
                accuracy_direction=direction_accuracy,
                training_samples=len(X_train),
                validation_samples=len(X_test),
                feature_importance={}  # LSTM doesn't provide feature importance
            )
            
            self.performance = performance
            self.logger.info(f"LSTM trained - R²: {performance.r2_score:.3f}, Direction Accuracy: {performance.accuracy_direction:.1%}")
            
            return performance
        
        def predict(self, df: pd.DataFrame, target_horizon: int = 1) -> PredictionResult:
            """Make prediction using LSTM"""
            
            if not self.is_trained:
                raise ValueError("Model must be trained before prediction")
            
            # Prepare features
            featured_df = self.feature_engineer.create_technical_features(df)
            
            # Get last sequence_length rows
            latest_data = featured_df[self.feature_columns].tail(self.sequence_length)
            
            if len(latest_data) < self.sequence_length:
                raise ValueError(f"Need at least {self.sequence_length} data points for LSTM prediction")
            
            # Scale and reshape for LSTM
            X_scaled = self.scaler.transform(latest_data.values)
            X_seq = X_scaled.reshape(1, self.sequence_length, len(self.feature_columns))
            
            # Make prediction
            predicted_return = self.model.predict(X_seq, verbose=0)[0][0]
            
            # Convert return to price
            current_price = df['close'].iloc[-1]
            predicted_price = current_price * (1 + predicted_return)
            
            # Calculate confidence (based on recent model performance)
            confidence = min(0.9, max(0.4, self.performance.r2_score)) if self.performance else 0.6
            
            return PredictionResult(
                predicted_price=predicted_price,
                confidence=confidence,
                prediction_horizon=target_horizon,
                model_used=self.model_name,
                features_used=self.feature_columns,
                timestamp=datetime.now()
            )

class EnsemblePricePredictor:
    """Ensemble of multiple prediction models"""
    
    def __init__(self):
        self.models = []
        self.model_weights = {}
        self.is_trained = False
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize models
        self.models = [
            RandomForestPricePredictor(n_estimators=100),
            GradientBoostingPricePredictor(n_estimators=100)
        ]
        
        if TENSORFLOW_AVAILABLE:
            self.models.append(LSTMPricePredictor(sequence_length=60))
    
    def train(self, df: pd.DataFrame, target_horizon: int = 1, test_size: float = 0.2):
        """Train all models in the ensemble"""
        
        performances = []
        
        for model in self.models:
            try:
                self.logger.info(f"Training {model.model_name}...")
                performance = model.train(df, target_horizon, test_size)
                performances.append(performance)
                
            except Exception as e:
                self.logger.error(f"Failed to train {model.model_name}: {e}")
                continue
        
        # Calculate weights based on performance (R² score)
        total_r2 = sum(max(0, p.r2_score) for p in performances)
        
        if total_r2 > 0:
            for i, performance in enumerate(performances):
                weight = max(0, performance.r2_score) / total_r2
                self.model_weights[self.models[i].model_name] = weight
        else:
            # Equal weights if all models perform poorly
            equal_weight = 1.0 / len(performances)
            for model in self.models:
                if model.is_trained:
                    self.model_weights[model.model_name] = equal_weight
        
        self.is_trained = True
        
        self.logger.info("Ensemble training completed:")
        for model_name, weight in self.model_weights.items():
            self.logger.info(f"  {model_name}: {weight:.3f} weight")
        
        return performances
    
    def predict(self, df: pd.DataFrame, target_horizon: int = 1) -> PredictionResult:
        """Make ensemble prediction"""
        
        if not self.is_trained:
            raise ValueError("Ensemble must be trained before prediction")
        
        predictions = []
        weights = []
        all_features = set()
        
        # Get predictions from all trained models
        for model in self.models:
            if model.is_trained and model.model_name in self.model_weights:
                try:
                    pred = model.predict(df, target_horizon)
                    predictions.append(pred)
                    weights.append(self.model_weights[model.model_name])
                    all_features.update(pred.features_used)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get prediction from {model.model_name}: {e}")
                    continue
        
        if not predictions:
            raise ValueError("No models available for prediction")
        
        # Weighted average of predictions
        weighted_price = sum(pred.predicted_price * weight for pred, weight in zip(predictions, weights))
        weighted_price /= sum(weights)
        
        # Average confidence
        weighted_confidence = sum(pred.confidence * weight for pred, weight in zip(predictions, weights))
        weighted_confidence /= sum(weights)
        
        # Combine model names
        models_used = " + ".join(pred.model_used for pred in predictions)
        
        return PredictionResult(
            predicted_price=weighted_price,
            confidence=weighted_confidence,
            prediction_horizon=target_horizon,
            model_used=f"Ensemble({models_used})",
            features_used=list(all_features),
            timestamp=datetime.now()
        )
    
    def get_model_performances(self) -> List[ModelPerformance]:
        """Get performance metrics for all trained models"""
        return [model.performance for model in self.models if model.performance is not None]

def create_price_predictor(model_type: str = "ensemble") -> PricePredictionModel:
    """Factory function to create price prediction models"""
    
    if model_type.lower() == "randomforest":
        return RandomForestPricePredictor()
    elif model_type.lower() == "gradientboosting":
        return GradientBoostingPricePredictor()
    elif model_type.lower() == "lstm" and TENSORFLOW_AVAILABLE:
        return LSTMPricePredictor()
    elif model_type.lower() == "ensemble":
        return EnsemblePricePredictor()
    else:
        raise ValueError(f"Unknown model type: {model_type}")