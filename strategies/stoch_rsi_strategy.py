from strategies.strategy_base import Strategy
from indicator import rsi, stochastic
from indicators.volume_analysis import get_volume_analyzer
import logging

logger = logging.getLogger(__name__)
import pandas as pd
import numpy as np
from datetime import datetime
import logging

class StochRSIStrategy(Strategy):
    """
    Enhanced Stochastic RSI strategy with dynamic band adjustment based on ATR volatility.
    
    Features:
    - ATR-based dynamic band adjustment
    - Volatility-adaptive signal generation
    - Performance tracking and analysis
    - Backward compatibility with static bands
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.stoch_rsi_params = self.config.indicators.stochRSI
        self.lookback_period = self.config.candle_lookback_period
        
        # Initialize volume analyzer
        # self.volume_analyzer = get_volume_analyzer(self.config.volume_confirmation)
        # self.require_volume_confirmation = getattr(self.config.volume_confirmation, 'require_volume_confirmation', True)
        
        # logger.info(f"StochRSI Strategy initialized with volume confirmation: {self.require_volume_confirmation}")
        
        # Performance tracking
        self.performance_metrics = {
            'total_signals': 0,
            'dynamic_signals': 0,
            'static_signals': 0,
            'high_volatility_signals': 0,
            'low_volatility_signals': 0,
            'signal_strength_history': [],
            'volatility_ratio_history': [],
            'band_adjustment_history': []
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)

    def generate_signal(self, df):
        """
        Generate enhanced trading signals using dynamic StochRSI bands.
        
        Returns:
            int: 1 for buy, -1 for sell, 0 for no signal
        """
        if not self.stoch_rsi_params.enabled:
            return 0

        # Calculate RSI and StochRSI with dynamic bands
        df = rsi(df)
        df = stochastic(df, TYPE='StochRSI')
        
        if 'StochRSI Signal' not in df.columns:
            return 0
        
        # Get recent signals and data for analysis
        recent_signals = df['StochRSI Signal'].iloc[-self.lookback_period:]
        signal_strengths = df.get('Signal Strength', pd.Series([0] * len(df))).iloc[-self.lookback_period:]
        
        # Update performance metrics
        self._update_performance_metrics(df)
        
        # Enhanced signal logic
        signal = self._evaluate_signals(recent_signals, signal_strengths, df)
        
        return signal

    def _evaluate_signals(self, recent_signals, signal_strengths, df):
        """
        Evaluate signals with enhanced logic considering signal strength and volatility.
        """
        # Check for buy signals
        buy_signals = recent_signals[recent_signals == 1]
        if len(buy_signals) > 0:
            # Get the strength of the most recent buy signal
            latest_strength = signal_strengths.iloc[-1] if len(signal_strengths) > 0 else 0
            
            # Consider volatility for signal confirmation
            if self.stoch_rsi_params.dynamic_bands_enabled and 'volatility_ratio' in df.columns:
                volatility = df['volatility_ratio'].iloc[-1]
                
                # Stronger signals required in high volatility
                if volatility > self.stoch_rsi_params.atr_sensitivity:
                    threshold = 0.3  # Higher threshold for high volatility
                else:
                    threshold = 0.1  # Lower threshold for normal/low volatility
                
                if latest_strength >= threshold:
                    self.performance_metrics['total_signals'] += 1
                    if volatility > self.stoch_rsi_params.atr_sensitivity:
                        self.performance_metrics['high_volatility_signals'] += 1
                    else:
                        self.performance_metrics['low_volatility_signals'] += 1
                    return 1
            else:
                # Traditional signal logic for backward compatibility
                self.performance_metrics['total_signals'] += 1
                self.performance_metrics['static_signals'] += 1
                return 1
        
        # Check for sell signals (if enabled in enhanced mode)
        sell_signals = recent_signals[recent_signals == -1]
        if len(sell_signals) > 0 and self.stoch_rsi_params.dynamic_bands_enabled:
            latest_strength = signal_strengths.iloc[-1] if len(signal_strengths) > 0 else 0
            if latest_strength >= 0.2:  # Threshold for sell signals
                return -1
        
        return 0

    def _update_performance_metrics(self, df):
        """Update performance tracking metrics."""
        if len(df) > 0:
            # Track signal strength
            if 'Signal Strength' in df.columns:
                latest_strength = df['Signal Strength'].iloc[-1]
                self.performance_metrics['signal_strength_history'].append(latest_strength)
            
            # Track volatility ratio
            if 'volatility_ratio' in df.columns:
                latest_volatility = df['volatility_ratio'].iloc[-1]
                self.performance_metrics['volatility_ratio_history'].append(latest_volatility)
            
            # Track dynamic vs static band usage
            if self.stoch_rsi_params.dynamic_bands_enabled:
                if 'dynamic_lower_band' in df.columns:
                    static_lower = self.stoch_rsi_params.lower_band
                    dynamic_lower = df['dynamic_lower_band'].iloc[-1]
                    adjustment = abs(dynamic_lower - static_lower)
                    self.performance_metrics['band_adjustment_history'].append(adjustment)
                    
                    if adjustment > 1:  # Significant adjustment
                        self.performance_metrics['dynamic_signals'] += 1

    def get_performance_summary(self):
        """
        Get a comprehensive performance summary.
        
        Returns:
            dict: Performance metrics and analysis
        """
        metrics = self.performance_metrics.copy()
        
        # Calculate averages and statistics
        if metrics['signal_strength_history']:
            metrics['avg_signal_strength'] = np.mean(metrics['signal_strength_history'])
            metrics['max_signal_strength'] = np.max(metrics['signal_strength_history'])
            metrics['min_signal_strength'] = np.min(metrics['signal_strength_history'])
        
        if metrics['volatility_ratio_history']:
            metrics['avg_volatility_ratio'] = np.mean(metrics['volatility_ratio_history'])
            metrics['volatility_periods'] = sum(1 for v in metrics['volatility_ratio_history'] 
                                               if v > self.stoch_rsi_params.atr_sensitivity)
        
        if metrics['band_adjustment_history']:
            metrics['avg_band_adjustment'] = np.mean(metrics['band_adjustment_history'])
            metrics['max_band_adjustment'] = np.max(metrics['band_adjustment_history'])
        
        # Calculate effectiveness ratios
        total_signals = metrics['total_signals']
        if total_signals > 0:
            metrics['dynamic_signal_ratio'] = metrics['dynamic_signals'] / total_signals
            metrics['high_volatility_ratio'] = metrics['high_volatility_signals'] / total_signals
            metrics['low_volatility_ratio'] = metrics['low_volatility_signals'] / total_signals
        
        metrics['timestamp'] = datetime.now().isoformat()
        metrics['strategy_config'] = {
            'dynamic_bands_enabled': self.stoch_rsi_params.dynamic_bands_enabled,
            'atr_sensitivity': self.stoch_rsi_params.atr_sensitivity,
            'band_adjustment_factor': self.stoch_rsi_params.band_adjustment_factor,
            'atr_period': self.stoch_rsi_params.atr_period
        }
        
        return metrics

    def reset_performance_metrics(self):
        """Reset performance tracking metrics."""
        self.performance_metrics = {
            'total_signals': 0,
            'dynamic_signals': 0,
            'static_signals': 0,
            'high_volatility_signals': 0,
            'low_volatility_signals': 0,
            'signal_strength_history': [],
            'volatility_ratio_history': [],
            'band_adjustment_history': []
        }

    def get_strategy_info(self):
        """Get strategy configuration and status information."""
        return {
            'strategy_name': 'Enhanced StochRSI with Dynamic Bands',
            'version': '2.0.0',
            'dynamic_bands_enabled': self.stoch_rsi_params.dynamic_bands_enabled,
            'parameters': {
                'rsi_length': self.stoch_rsi_params.rsi_length,
                'stoch_length': self.stoch_rsi_params.stoch_length,
                'K': self.stoch_rsi_params.K,
                'D': self.stoch_rsi_params.D,
                'base_lower_band': self.stoch_rsi_params.lower_band,
                'base_upper_band': self.stoch_rsi_params.upper_band,
                'atr_period': self.stoch_rsi_params.atr_period,
                'atr_sensitivity': self.stoch_rsi_params.atr_sensitivity,
                'band_adjustment_factor': self.stoch_rsi_params.band_adjustment_factor,
                'min_band_width': self.stoch_rsi_params.min_band_width,
                'max_band_width': self.stoch_rsi_params.max_band_width
            },
            'lookback_period': self.lookback_period
        }
