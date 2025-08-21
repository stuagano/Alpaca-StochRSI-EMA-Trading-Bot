"""
Enhanced StochRSI Indicator Implementation for Lightweight Charts
Provides StochRSI calculations with proper data formatting for TradingView charts
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class StochRSIIndicator:
    """
    Enhanced StochRSI indicator with optimized calculations for real-time trading.
    
    StochRSI combines Stochastic and RSI indicators to identify overbought/oversold conditions
    with better sensitivity than traditional RSI.
    """
    
    def __init__(self, rsi_length: int = 14, stoch_length: int = 14, 
                 k_smoothing: int = 3, d_smoothing: int = 3):
        """
        Initialize StochRSI parameters.
        
        Args:
            rsi_length: Period for RSI calculation (default 14)
            stoch_length: Period for Stochastic calculation on RSI (default 14)
            k_smoothing: %K smoothing period (default 3)
            d_smoothing: %D smoothing period (default 3)
        """
        self.rsi_length = rsi_length
        self.stoch_length = stoch_length
        self.k_smoothing = k_smoothing
        self.d_smoothing = d_smoothing
        
        # Signal thresholds
        self.oversold_threshold = 20
        self.overbought_threshold = 80
        
        logger.info(f"StochRSI initialized: RSI={rsi_length}, Stoch={stoch_length}, K={k_smoothing}, D={d_smoothing}")
    
    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """
        Calculate RSI (Relative Strength Index).
        
        Args:
            prices: Series of closing prices
            
        Returns:
            RSI values as pandas Series
        """
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Use Wilder's smoothing (exponential moving average)
        avg_gains = gains.ewm(com=self.rsi_length - 1, min_periods=self.rsi_length).mean()
        avg_losses = losses.ewm(com=self.rsi_length - 1, min_periods=self.rsi_length).mean()
        
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_stochastic_on_rsi(self, rsi: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Stochastic oscillator on RSI values.
        
        Args:
            rsi: RSI values
            
        Returns:
            Tuple of (%K, %D) series
        """
        # Calculate %K
        rsi_low = rsi.rolling(window=self.stoch_length, min_periods=self.stoch_length).min()
        rsi_high = rsi.rolling(window=self.stoch_length, min_periods=self.stoch_length).max()
        
        # Avoid division by zero
        rsi_range = rsi_high - rsi_low
        stoch_k_raw = np.where(rsi_range != 0, (rsi - rsi_low) / rsi_range * 100, 50)
        
        # Apply smoothing to %K
        stoch_k = pd.Series(stoch_k_raw, index=rsi.index).rolling(
            window=self.k_smoothing, min_periods=1
        ).mean()
        
        # Calculate %D (smoothed %K)
        stoch_d = stoch_k.rolling(window=self.d_smoothing, min_periods=1).mean()
        
        return stoch_k, stoch_d
    
    def calculate_full_stoch_rsi(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """
        Calculate complete StochRSI indicator.
        
        Args:
            prices: Series of closing prices
            
        Returns:
            Dictionary containing RSI, StochRSI %K, and StochRSI %D
        """
        # Calculate RSI
        rsi = self.calculate_rsi(prices)
        
        # Calculate Stochastic on RSI
        stoch_k, stoch_d = self.calculate_stochastic_on_rsi(rsi)
        
        return {
            'RSI': rsi,
            'StochRSI_K': stoch_k,
            'StochRSI_D': stoch_d
        }
    
    def generate_signals(self, stoch_k: pd.Series, stoch_d: pd.Series) -> Dict[str, pd.Series]:
        """
        Generate buy/sell signals based on StochRSI.
        
        Args:
            stoch_k: %K values
            stoch_d: %D values
            
        Returns:
            Dictionary with signal information
        """
        signals = pd.Series(0, index=stoch_k.index)  # 0 = no signal
        signal_strength = pd.Series(0.0, index=stoch_k.index)
        signal_type = pd.Series('NEUTRAL', index=stoch_k.index)
        
        # Generate signals
        for i in range(1, len(stoch_k)):
            if pd.isna(stoch_k.iloc[i]) or pd.isna(stoch_d.iloc[i]):
                continue
                
            current_k = stoch_k.iloc[i]
            current_d = stoch_d.iloc[i]
            prev_k = stoch_k.iloc[i-1]
            prev_d = stoch_d.iloc[i-1]
            
            # Buy signal: %K crosses above %D in oversold region
            if (prev_k <= prev_d and current_k > current_d and 
                current_k < self.oversold_threshold):
                signals.iloc[i] = 1
                signal_strength.iloc[i] = min((self.oversold_threshold - current_k) / self.oversold_threshold, 1.0)
                signal_type.iloc[i] = 'BUY'
                
            # Sell signal: %K crosses below %D in overbought region  
            elif (prev_k >= prev_d and current_k < current_d and 
                  current_k > self.overbought_threshold):
                signals.iloc[i] = -1
                signal_strength.iloc[i] = min((current_k - self.overbought_threshold) / (100 - self.overbought_threshold), 1.0)
                signal_type.iloc[i] = 'SELL'
        
        return {
            'signals': signals,
            'signal_strength': signal_strength,
            'signal_type': signal_type
        }
    
    def format_for_lightweight_charts(self, data: Dict[str, pd.Series], 
                                    timestamps: pd.DatetimeIndex) -> Dict[str, List[Dict]]:
        """
        Format StochRSI data for TradingView Lightweight Charts.
        
        Args:
            data: Dictionary containing RSI and StochRSI data
            timestamps: DatetimeIndex for time conversion
            
        Returns:
            Dictionary formatted for Lightweight Charts
        """
        formatted_data = {}
        
        # Convert timestamps to UNIX timestamps
        unix_timestamps = (timestamps.astype(np.int64) // 10**9).astype(int)
        
        for key, series in data.items():
            if series is not None and len(series) > 0:
                formatted_data[key.lower()] = [
                    {'time': int(ts), 'value': float(val)}
                    for ts, val in zip(unix_timestamps, series)
                    if not pd.isna(val) and ts > 0
                ]
        
        return formatted_data
    
    def get_current_signals(self, prices: pd.Series) -> Dict:
        """
        Get current StochRSI signals and status.
        
        Args:
            prices: Series of closing prices
            
        Returns:
            Dictionary with current signal information
        """
        try:
            # Calculate indicators
            indicators = self.calculate_full_stoch_rsi(prices)
            signals = self.generate_signals(indicators['StochRSI_K'], indicators['StochRSI_D'])
            
            # Get latest values
            latest_k = indicators['StochRSI_K'].iloc[-1] if len(indicators['StochRSI_K']) > 0 else None
            latest_d = indicators['StochRSI_D'].iloc[-1] if len(indicators['StochRSI_D']) > 0 else None
            latest_rsi = indicators['RSI'].iloc[-1] if len(indicators['RSI']) > 0 else None
            latest_signal = signals['signals'].iloc[-1] if len(signals['signals']) > 0 else 0
            latest_strength = signals['signal_strength'].iloc[-1] if len(signals['signal_strength']) > 0 else 0
            latest_type = signals['signal_type'].iloc[-1] if len(signals['signal_type']) > 0 else 'NEUTRAL'
            
            # Determine market condition
            condition = 'NEUTRAL'
            if latest_k is not None:
                if latest_k < self.oversold_threshold:
                    condition = 'OVERSOLD'
                elif latest_k > self.overbought_threshold:
                    condition = 'OVERBOUGHT'
            
            return {
                'stochRSI': {
                    'k': latest_k,
                    'd': latest_d,
                    'signal': latest_signal,
                    'strength': latest_strength,
                    'type': latest_type,
                    'condition': condition,
                    'oversold_threshold': self.oversold_threshold,
                    'overbought_threshold': self.overbought_threshold
                },
                'rsi': latest_rsi,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating current signals: {e}")
            return {
                'stochRSI': {
                    'k': None,
                    'd': None,
                    'signal': 0,
                    'strength': 0,
                    'type': 'NEUTRAL',
                    'condition': 'UNKNOWN',
                    'oversold_threshold': self.oversold_threshold,
                    'overbought_threshold': self.overbought_threshold
                },
                'rsi': None,
                'timestamp': pd.Timestamp.now().isoformat(),
                'error': str(e)
            }


def calculate_stoch_rsi_for_chart(data: pd.DataFrame, config: Dict) -> Dict:
    """
    Calculate StochRSI data specifically formatted for chart display.
    
    Args:
        data: DataFrame with OHLCV data
        config: Configuration dictionary with indicator parameters
        
    Returns:
        Dictionary with formatted StochRSI data for charts
    """
    try:
        # Extract parameters from config
        stoch_rsi_params = config.get('indicators', {}).get('stochRSI_params', {})
        rsi_length = stoch_rsi_params.get('rsi_length', 14)
        stoch_length = stoch_rsi_params.get('stoch_length', 14)
        k_smoothing = stoch_rsi_params.get('K', 3)
        d_smoothing = stoch_rsi_params.get('D', 3)
        
        # Initialize indicator
        stoch_rsi = StochRSIIndicator(
            rsi_length=rsi_length,
            stoch_length=stoch_length,
            k_smoothing=k_smoothing,
            d_smoothing=d_smoothing
        )
        
        # Calculate indicators
        indicators = stoch_rsi.calculate_full_stoch_rsi(data['close'])
        signals = stoch_rsi.generate_signals(indicators['StochRSI_K'], indicators['StochRSI_D'])
        
        # Combine all data
        all_data = {**indicators, **signals}
        
        # Format for charts
        chart_data = stoch_rsi.format_for_lightweight_charts(all_data, data.index)
        
        # Add current signal info
        current_signals = stoch_rsi.get_current_signals(data['close'])
        
        return {
            'chart_data': chart_data,
            'current_signals': current_signals,
            'parameters': {
                'rsi_length': rsi_length,
                'stoch_length': stoch_length,
                'k_smoothing': k_smoothing,
                'd_smoothing': d_smoothing
            }
        }
        
    except Exception as e:
        logger.error(f"Error in calculate_stoch_rsi_for_chart: {e}")
        return {
            'chart_data': {},
            'current_signals': {},
            'parameters': {},
            'error': str(e)
        }


def get_signal_markers_for_chart(data: pd.DataFrame, stoch_k: pd.Series, 
                                stoch_d: pd.Series, oversold: float = 20, 
                                overbought: float = 80) -> List[Dict]:
    """
    Generate signal markers for TradingView Lightweight Charts.
    
    Args:
        data: OHLCV DataFrame
        stoch_k: StochRSI %K series
        stoch_d: StochRSI %D series
        oversold: Oversold threshold (default 20)
        overbought: Overbought threshold (default 80)
        
    Returns:
        List of marker dictionaries for Lightweight Charts
    """
    markers = []
    
    try:
        # Convert timestamps to UNIX
        unix_timestamps = (data.index.astype(np.int64) // 10**9).astype(int)
        
        for i in range(1, min(len(stoch_k), len(stoch_d), len(data))):
            if pd.isna(stoch_k.iloc[i]) or pd.isna(stoch_d.iloc[i]):
                continue
                
            current_k = stoch_k.iloc[i]
            current_d = stoch_d.iloc[i]
            prev_k = stoch_k.iloc[i-1]
            prev_d = stoch_d.iloc[i-1]
            
            # Buy signal
            if (prev_k <= prev_d and current_k > current_d and current_k < oversold):
                markers.append({
                    'time': int(unix_timestamps[i]),
                    'position': 'belowBar',
                    'color': '#26a641',
                    'shape': 'arrowUp',
                    'text': 'StochRSI Buy',
                    'size': 1
                })
                
            # Sell signal
            elif (prev_k >= prev_d and current_k < current_d and current_k > overbought):
                markers.append({
                    'time': int(unix_timestamps[i]),
                    'position': 'aboveBar', 
                    'color': '#f85149',
                    'shape': 'arrowDown',
                    'text': 'StochRSI Sell',
                    'size': 1
                })
        
        logger.info(f"Generated {len(markers)} signal markers")
        return markers
        
    except Exception as e:
        logger.error(f"Error generating signal markers: {e}")
        return []