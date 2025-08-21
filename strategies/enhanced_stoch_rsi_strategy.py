"""
Enhanced StochRSI Strategy with Volume Confirmation

This enhanced version includes:
- Volume confirmation filtering
- Enhanced signal validation
- Performance tracking
- Dashboard integration

Author: Trading Bot System
Version: 1.0.0
"""

from strategies.strategy_base import Strategy
from indicator import rsi, stochastic
from indicators.volume_analysis import get_volume_analyzer
import logging
import pandas as pd
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class EnhancedStochRSIStrategy(Strategy):
    """
    Enhanced StochRSI strategy with comprehensive volume confirmation
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.stoch_rsi_params = self.config.indicators.stochRSI
        self.lookback_period = self.config.candle_lookback_period
        
        # Initialize volume analyzer
        self.volume_analyzer = get_volume_analyzer(self.config.volume_confirmation)
        self.require_volume_confirmation = getattr(
            self.config.volume_confirmation, 'require_volume_confirmation', True
        )
        
        # Performance tracking
        self.signal_history = []
        self.volume_confirmation_stats = {
            'total_signals': 0,
            'volume_confirmed': 0,
            'volume_rejected': 0
        }
        
        logger.info(f"Enhanced StochRSI Strategy initialized with volume confirmation: {self.require_volume_confirmation}")
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Generate a trading signal using the StochRSI indicator with volume confirmation.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            1 for buy signal, -1 for sell signal, 0 for no signal
        """
        if not self.stoch_rsi_params.enabled:
            return 0

        try:
            # Generate base StochRSI signal
            df_with_indicators = self._calculate_stoch_rsi_indicators(df)
            base_signal = self._get_stoch_rsi_signal(df_with_indicators)
            
            if base_signal == 0:
                return 0
            
            # Update signal statistics
            self.signal_history.append({
                'timestamp': df.index[-1] if hasattr(df, 'index') else pd.Timestamp.now(),
                'base_signal': base_signal,
                'volume_confirmed': False,
                'volume_data': {}
            })
            
            self.volume_confirmation_stats['total_signals'] += 1
            
            # Apply volume confirmation if required
            if self.require_volume_confirmation and self.config.volume_confirmation.enabled:
                volume_result = self.volume_analyzer.confirm_signal_with_volume(df_with_indicators, base_signal)
                
                # Update signal history with volume data
                self.signal_history[-1]['volume_confirmed'] = volume_result.is_confirmed
                self.signal_history[-1]['volume_data'] = {
                    'volume_ratio': volume_result.volume_ratio,
                    'relative_volume': volume_result.relative_volume,
                    'volume_trend': volume_result.volume_trend,
                    'confirmation_strength': volume_result.confirmation_strength
                }
                
                if volume_result.is_confirmed:
                    self.volume_confirmation_stats['volume_confirmed'] += 1
                    logger.info(
                        f"StochRSI signal CONFIRMED - Volume ratio: {volume_result.volume_ratio:.2f}, "
                        f"Relative volume: {volume_result.relative_volume:.2f}, "
                        f"Strength: {volume_result.confirmation_strength:.2f}"
                    )
                    return base_signal
                else:
                    self.volume_confirmation_stats['volume_rejected'] += 1
                    logger.info(
                        f"StochRSI signal REJECTED - Volume ratio: {volume_result.volume_ratio:.2f}, "
                        f"Relative volume: {volume_result.relative_volume:.2f}"
                    )
                    return 0
            
            # Volume confirmation disabled or not available
            return base_signal
            
        except Exception as e:
            logger.error(f"Error generating StochRSI signal: {e}")
            return 0
    
    def _calculate_stoch_rsi_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate StochRSI indicators
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with StochRSI indicators added
        """
        df_copy = df.copy()
        df_copy = rsi(df_copy)
        df_copy = stochastic(df_copy, TYPE='StochRSI')
        return df_copy
    
    def _get_stoch_rsi_signal(self, df: pd.DataFrame) -> int:
        """
        Extract StochRSI signal from DataFrame
        
        Args:
            df: DataFrame with StochRSI indicators
            
        Returns:
            Signal value (1, -1, or 0)
        """
        if 'StochRSI Signal' not in df.columns:
            return 0
        
        signal_list = list(df['StochRSI Signal'].iloc[-self.lookback_period:])
        
        # Check for buy signals
        if 1 in signal_list:
            return 1
        
        # Could add sell signals here in the future
        # if -1 in signal_list:
        #     return -1
        
        return 0
    
    def get_strategy_performance(self) -> Dict:
        """
        Get comprehensive strategy performance metrics
        
        Returns:
            Dictionary with performance data
        """
        stats = self.volume_confirmation_stats.copy()
        
        if stats['total_signals'] > 0:
            stats['confirmation_rate'] = stats['volume_confirmed'] / stats['total_signals']
            stats['rejection_rate'] = stats['volume_rejected'] / stats['total_signals']
        else:
            stats['confirmation_rate'] = 0
            stats['rejection_rate'] = 0
        
        # Recent signal analysis
        recent_signals = self.signal_history[-20:] if len(self.signal_history) >= 20 else self.signal_history
        
        if recent_signals:
            recent_confirmed = sum(1 for s in recent_signals if s['volume_confirmed'])
            stats['recent_confirmation_rate'] = recent_confirmed / len(recent_signals)
            
            # Average volume metrics for confirmed signals
            confirmed_signals = [s for s in recent_signals if s['volume_confirmed']]
            if confirmed_signals:
                avg_volume_ratio = sum(s['volume_data'].get('volume_ratio', 0) for s in confirmed_signals) / len(confirmed_signals)
                avg_rel_volume = sum(s['volume_data'].get('relative_volume', 0) for s in confirmed_signals) / len(confirmed_signals)
                avg_strength = sum(s['volume_data'].get('confirmation_strength', 0) for s in confirmed_signals) / len(confirmed_signals)
                
                stats['avg_confirmed_volume_ratio'] = avg_volume_ratio
                stats['avg_confirmed_relative_volume'] = avg_rel_volume
                stats['avg_confirmation_strength'] = avg_strength
        else:
            stats['recent_confirmation_rate'] = 0
        
        return stats
    
    def get_dashboard_data(self, df: pd.DataFrame) -> Dict:
        """
        Get data for dashboard display
        
        Args:
            df: DataFrame with current market data
            
        Returns:
            Dictionary with dashboard data
        """
        try:
            # Get base strategy data
            df_with_indicators = self._calculate_stoch_rsi_indicators(df)
            
            dashboard_data = {
                'strategy_name': 'Enhanced StochRSI',
                'current_signal': self._get_stoch_rsi_signal(df_with_indicators),
                'stoch_rsi_enabled': self.stoch_rsi_params.enabled,
                'volume_confirmation_enabled': self.config.volume_confirmation.enabled,
                'performance': self.get_strategy_performance()
            }
            
            # Add volume analysis data
            if hasattr(self.volume_analyzer, 'get_volume_dashboard_data'):
                volume_data = self.volume_analyzer.get_volume_dashboard_data(df_with_indicators)
                dashboard_data['volume_analysis'] = volume_data
            
            # Add current indicator values
            if len(df_with_indicators) > 0:
                latest_row = df_with_indicators.iloc[-1]
                dashboard_data['current_indicators'] = {
                    'rsi': latest_row.get('RSI', 0),
                    'stoch_k': latest_row.get('Stoch %K', 0),
                    'stoch_d': latest_row.get('Stoch %D', 0),
                    'volume': latest_row.get('volume', 0)
                }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {
                'strategy_name': 'Enhanced StochRSI',
                'current_signal': 0,
                'error': str(e)
            }
    
    def reset_performance_stats(self):
        """Reset performance tracking statistics"""
        self.signal_history = []
        self.volume_confirmation_stats = {
            'total_signals': 0,
            'volume_confirmed': 0,
            'volume_rejected': 0
        }
        logger.info("StochRSI strategy performance stats reset")


# Alias for backward compatibility
StochRSIStrategyWithVolume = EnhancedStochRSIStrategy