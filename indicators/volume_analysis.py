"""
Volume Analysis Module for Trading Signal Confirmation

This module provides comprehensive volume analysis capabilities including:
- Volume moving averages for signal confirmation
- Relative volume indicators
- Volume profile analysis for support/resistance levels
- Volume confirmation filters for existing trading strategies

Author: Trading Bot System
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class VolumeConfirmationResult:
    """Result object for volume confirmation analysis"""
    is_confirmed: bool
    volume_ratio: float
    relative_volume: float
    volume_trend: str
    profile_levels: Dict[str, float]
    confirmation_strength: float


@dataclass
class VolumeProfileLevel:
    """Volume profile support/resistance level"""
    price: float
    volume: float
    level_type: str  # 'support' or 'resistance'
    strength: float


class VolumeAnalyzer:
    """
    Comprehensive volume analysis for trading signal confirmation
    """
    
    def __init__(self, config=None):
        """
        Initialize the Volume Analyzer
        
        Args:
            config: Configuration object with volume parameters
        """
        self.config = config
        self.volume_period = getattr(config, 'volume_period', 20) if config else 20
        self.relative_volume_period = getattr(config, 'relative_volume_period', 50) if config else 50
        self.volume_confirmation_threshold = getattr(config, 'volume_confirmation_threshold', 1.2) if config else 1.2
        self.profile_periods = getattr(config, 'profile_periods', 100) if config else 100
        self.min_volume_ratio = getattr(config, 'min_volume_ratio', 1.0) if config else 1.0
        
        logger.info(f"VolumeAnalyzer initialized with period={self.volume_period}, threshold={self.volume_confirmation_threshold}")
    
    def calculate_volume_moving_average(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volume moving average for confirmation
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with volume moving average columns added
        """
        try:
            df = df.copy()
            
            # Calculate 20-period volume moving average
            df['volume_ma'] = df['volume'].rolling(window=self.volume_period).mean()
            
            # Calculate volume ratio (current volume / average volume)
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # Volume trend indicator
            df['volume_trend'] = np.where(
                df['volume_ratio'] > self.volume_confirmation_threshold, 'high',
                np.where(df['volume_ratio'] < 0.8, 'low', 'normal')
            )
            
            logger.debug(f"Calculated volume MA for {len(df)} periods")
            return df
            
        except Exception as e:
            logger.error(f"Error calculating volume moving average: {e}")
            return df
    
    def calculate_relative_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate relative volume indicator
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with relative volume columns added
        """
        try:
            df = df.copy()
            
            # Calculate average volume for the same time of day over past periods
            if 'timestamp' in df.columns:
                df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
                df['minute'] = pd.to_datetime(df['timestamp']).dt.minute
                
                # Group by time and calculate average volume
                time_avg_volume = df.groupby(['hour', 'minute'])['volume'].transform(
                    lambda x: x.rolling(window=min(len(x), self.relative_volume_period)).mean()
                )
                
                df['relative_volume'] = df['volume'] / time_avg_volume
            else:
                # Fallback to simple relative volume calculation
                df['relative_volume'] = df['volume'] / df['volume'].rolling(
                    window=self.relative_volume_period
                ).mean()
            
            # Relative volume strength categories
            df['rel_vol_strength'] = pd.cut(
                df['relative_volume'],
                bins=[0, 0.5, 1.0, 1.5, 2.0, np.inf],
                labels=['very_low', 'low', 'normal', 'high', 'very_high']
            )
            
            logger.debug(f"Calculated relative volume for {len(df)} periods")
            return df
            
        except Exception as e:
            logger.error(f"Error calculating relative volume: {e}")
            return df
    
    def analyze_volume_profile(self, df: pd.DataFrame, lookback_periods: int = None) -> List[VolumeProfileLevel]:
        """
        Analyze volume profile to identify support/resistance levels
        
        Args:
            df: DataFrame with OHLCV data
            lookback_periods: Number of periods to analyze (default: self.profile_periods)
            
        Returns:
            List of VolumeProfileLevel objects
        """
        try:
            if lookback_periods is None:
                lookback_periods = self.profile_periods
            
            # Use last N periods for analysis
            analysis_df = df.tail(lookback_periods).copy()
            
            if len(analysis_df) < 20:
                logger.warning("Insufficient data for volume profile analysis")
                return []
            
            # Create price bins for volume profile
            price_min = analysis_df['low'].min()
            price_max = analysis_df['high'].max()
            num_bins = min(50, len(analysis_df) // 2)  # Adaptive number of bins
            
            price_bins = np.linspace(price_min, price_max, num_bins)
            
            # Aggregate volume at each price level
            volume_at_price = {}
            
            for _, row in analysis_df.iterrows():
                # Distribute volume across the price range of each candle
                low_price = row['low']
                high_price = row['high']
                volume = row['volume']
                
                # Find bins that overlap with this candle's price range
                relevant_bins = price_bins[(price_bins >= low_price) & (price_bins <= high_price)]
                
                if len(relevant_bins) > 0:
                    volume_per_bin = volume / len(relevant_bins)
                    for price in relevant_bins:
                        if price not in volume_at_price:
                            volume_at_price[price] = 0
                        volume_at_price[price] += volume_per_bin
            
            # Convert to sorted list
            volume_profile = sorted(volume_at_price.items(), key=lambda x: x[1], reverse=True)
            
            # Identify significant levels (top 20% by volume)
            significant_levels = volume_profile[:max(1, len(volume_profile) // 5)]
            
            # Classify levels as support or resistance
            current_price = analysis_df['close'].iloc[-1]
            profile_levels = []
            
            for price, volume in significant_levels:
                level_type = 'support' if price < current_price else 'resistance'
                strength = volume / max(vol for _, vol in volume_profile)  # Normalize to 0-1
                
                profile_levels.append(VolumeProfileLevel(
                    price=price,
                    volume=volume,
                    level_type=level_type,
                    strength=strength
                ))
            
            logger.debug(f"Identified {len(profile_levels)} significant volume profile levels")
            return profile_levels
            
        except Exception as e:
            logger.error(f"Error analyzing volume profile: {e}")
            return []
    
    def confirm_signal_with_volume(self, df: pd.DataFrame, signal: int) -> VolumeConfirmationResult:
        """
        Confirm trading signal using volume analysis
        
        Args:
            df: DataFrame with OHLCV data and volume indicators
            signal: Trading signal (1 for buy, -1 for sell, 0 for no signal)
            
        Returns:
            VolumeConfirmationResult object with confirmation details
        """
        try:
            if signal == 0:
                return VolumeConfirmationResult(
                    is_confirmed=False,
                    volume_ratio=0.0,
                    relative_volume=0.0,
                    volume_trend='none',
                    profile_levels={},
                    confirmation_strength=0.0
                )
            
            # Ensure volume indicators are calculated
            df_with_volume = self.calculate_volume_moving_average(df)
            df_with_volume = self.calculate_relative_volume(df_with_volume)
            
            # Get latest volume metrics
            latest_row = df_with_volume.iloc[-1]
            volume_ratio = latest_row.get('volume_ratio', 0.0)
            relative_volume = latest_row.get('relative_volume', 0.0)
            volume_trend = latest_row.get('volume_trend', 'unknown')
            
            # Volume confirmation logic
            volume_confirmed = (
                volume_ratio >= self.volume_confirmation_threshold and
                relative_volume >= self.min_volume_ratio
            )
            
            # Calculate confirmation strength (0-1 scale)
            strength_factors = []
            
            # Volume ratio factor
            strength_factors.append(min(1.0, volume_ratio / self.volume_confirmation_threshold))
            
            # Relative volume factor
            strength_factors.append(min(1.0, relative_volume / self.min_volume_ratio))
            
            # Volume trend factor
            trend_strength = {'high': 1.0, 'normal': 0.6, 'low': 0.2, 'unknown': 0.3}
            strength_factors.append(trend_strength.get(volume_trend, 0.3))
            
            confirmation_strength = np.mean(strength_factors)
            
            # Get volume profile levels
            profile_levels = self.analyze_volume_profile(df_with_volume)
            profile_dict = {
                f"{level.level_type}_{i}": level.price 
                for i, level in enumerate(profile_levels[:5])  # Top 5 levels
            }
            
            result = VolumeConfirmationResult(
                is_confirmed=volume_confirmed,
                volume_ratio=volume_ratio,
                relative_volume=relative_volume,
                volume_trend=volume_trend,
                profile_levels=profile_dict,
                confirmation_strength=confirmation_strength
            )
            
            logger.info(f"Volume confirmation: {volume_confirmed}, strength: {confirmation_strength:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error in volume signal confirmation: {e}")
            return VolumeConfirmationResult(
                is_confirmed=False,
                volume_ratio=0.0,
                relative_volume=0.0,
                volume_trend='error',
                profile_levels={},
                confirmation_strength=0.0
            )
    
    def get_volume_dashboard_data(self, df: pd.DataFrame) -> Dict:
        """
        Get volume analysis data for dashboard display
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with volume indicators for dashboard
        """
        try:
            # Calculate all volume indicators
            df_with_volume = self.calculate_volume_moving_average(df)
            df_with_volume = self.calculate_relative_volume(df_with_volume)
            profile_levels = self.analyze_volume_profile(df_with_volume)
            
            latest_row = df_with_volume.iloc[-1]
            
            dashboard_data = {
                'current_volume': int(latest_row['volume']),
                'volume_ma': float(latest_row.get('volume_ma', 0)),
                'volume_ratio': float(latest_row.get('volume_ratio', 0)),
                'relative_volume': float(latest_row.get('relative_volume', 0)),
                'volume_trend': latest_row.get('volume_trend', 'unknown'),
                'volume_strength': latest_row.get('rel_vol_strength', 'unknown'),
                'confirmation_threshold': self.volume_confirmation_threshold,
                'profile_levels': {
                    'support': [level.price for level in profile_levels if level.level_type == 'support'][:3],
                    'resistance': [level.price for level in profile_levels if level.level_type == 'resistance'][:3]
                },
                'volume_confirmed': (
                    latest_row.get('volume_ratio', 0) >= self.volume_confirmation_threshold and
                    latest_row.get('relative_volume', 0) >= self.min_volume_ratio
                )
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting volume dashboard data: {e}")
            return {
                'current_volume': 0,
                'volume_ma': 0,
                'volume_ratio': 0,
                'relative_volume': 0,
                'volume_trend': 'error',
                'volume_strength': 'error',
                'confirmation_threshold': self.volume_confirmation_threshold,
                'profile_levels': {'support': [], 'resistance': []},
                'volume_confirmed': False
            }
    
    def calculate_volume_performance_metrics(self, trades_df: pd.DataFrame) -> Dict:
        """
        Calculate performance metrics for volume-confirmed vs non-confirmed signals
        
        Args:
            trades_df: DataFrame with trade results and volume confirmation data
            
        Returns:
            Dictionary with performance comparison metrics
        """
        try:
            if trades_df.empty or 'volume_confirmed' not in trades_df.columns:
                logger.warning("No volume confirmation data available for performance analysis")
                return {}
            
            confirmed_trades = trades_df[trades_df['volume_confirmed'] == True]
            non_confirmed_trades = trades_df[trades_df['volume_confirmed'] == False]
            
            metrics = {
                'total_trades': len(trades_df),
                'confirmed_trades': len(confirmed_trades),
                'non_confirmed_trades': len(non_confirmed_trades),
                'confirmation_rate': len(confirmed_trades) / len(trades_df) if len(trades_df) > 0 else 0,
            }
            
            # Calculate performance metrics for each group
            if len(confirmed_trades) > 0:
                metrics['confirmed_win_rate'] = (confirmed_trades['profit'] > 0).mean()
                metrics['confirmed_avg_profit'] = confirmed_trades['profit'].mean()
                metrics['confirmed_total_profit'] = confirmed_trades['profit'].sum()
            else:
                metrics['confirmed_win_rate'] = 0
                metrics['confirmed_avg_profit'] = 0
                metrics['confirmed_total_profit'] = 0
            
            if len(non_confirmed_trades) > 0:
                metrics['non_confirmed_win_rate'] = (non_confirmed_trades['profit'] > 0).mean()
                metrics['non_confirmed_avg_profit'] = non_confirmed_trades['profit'].mean()
                metrics['non_confirmed_total_profit'] = non_confirmed_trades['profit'].sum()
            else:
                metrics['non_confirmed_win_rate'] = 0
                metrics['non_confirmed_avg_profit'] = 0
                metrics['non_confirmed_total_profit'] = 0
            
            # Calculate improvement metrics
            if metrics['non_confirmed_win_rate'] > 0:
                metrics['win_rate_improvement'] = (
                    (metrics['confirmed_win_rate'] - metrics['non_confirmed_win_rate']) /
                    metrics['non_confirmed_win_rate']
                )
            else:
                metrics['win_rate_improvement'] = 0
            
            # False signal reduction
            total_signals = len(trades_df)
            false_signals_all = len(trades_df[trades_df['profit'] <= 0])
            false_signals_confirmed = len(confirmed_trades[confirmed_trades['profit'] <= 0])
            
            if total_signals > 0 and false_signals_all > 0:
                metrics['false_signal_reduction'] = (
                    (false_signals_all - false_signals_confirmed) / false_signals_all
                )
            else:
                metrics['false_signal_reduction'] = 0
            
            logger.info(f"Volume performance analysis: {metrics['confirmation_rate']:.1%} signals confirmed, "
                       f"{metrics['false_signal_reduction']:.1%} false signal reduction")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating volume performance metrics: {e}")
            return {}


def get_volume_analyzer(config=None) -> VolumeAnalyzer:
    """
    Factory function to get a VolumeAnalyzer instance
    
    Args:
        config: Configuration object
        
    Returns:
        VolumeAnalyzer instance
    """
    return VolumeAnalyzer(config)


# Export main classes and functions
__all__ = [
    'VolumeAnalyzer',
    'VolumeConfirmationResult', 
    'VolumeProfileLevel',
    'get_volume_analyzer'
]