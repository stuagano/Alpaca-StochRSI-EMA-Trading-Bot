#### indicator.py

from config.config import config
import pandas as pd
import numpy as np

############################################################
#TECHNICAL INDICATORS

def atr(df, period=14):
    """
    Calculate Average True Range (ATR) for volatility measurement.
    
    Args:
        df: DataFrame with OHLC data
        period: ATR calculation period (default: 14)
    
    Returns:
        DataFrame with ATR column added
    """
    df_temp = df.copy()
    
    # Calculate True Range components
    df_temp['h-l'] = df_temp['high'] - df_temp['low']
    df_temp['h-pc'] = abs(df_temp['high'] - df_temp['close'].shift(1))
    df_temp['l-pc'] = abs(df_temp['low'] - df_temp['close'].shift(1))
    
    # True Range is the maximum of the three components
    df_temp['TR'] = df_temp[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    
    # ATR is the exponential moving average of True Range
    df_temp['ATR'] = df_temp['TR'].ewm(span=period, adjust=False).mean()
    
    df['ATR'] = df_temp['ATR']
    return df

def calculate_dynamic_bands(df, base_lower=35, base_upper=100, atr_period=20, sensitivity=0.7, 
                          adjustment_factor=0.3, min_width=10, max_width=50):
    """
    Calculate dynamic StochRSI bands based on ATR volatility.
    
    Args:
        df: DataFrame with price data and ATR
        base_lower: Base lower band value
        base_upper: Base upper band value
        atr_period: Period for ATR average calculation
        sensitivity: Sensitivity multiplier for volatility detection
        adjustment_factor: How much to adjust bands (0.0-1.0)
        min_width: Minimum band width
        max_width: Maximum band width
    
    Returns:
        DataFrame with dynamic band columns added
    """
    df_temp = df.copy()
    
    # Calculate ATR moving average for comparison
    df_temp['ATR_MA'] = df_temp['ATR'].rolling(window=atr_period).mean()
    
    # Calculate volatility ratio
    df_temp['volatility_ratio'] = df_temp['ATR'] / df_temp['ATR_MA']
    
    # Initialize dynamic bands
    df_temp['dynamic_lower_band'] = float(base_lower)
    df_temp['dynamic_upper_band'] = float(base_upper)
    
    # Calculate band adjustments based on volatility
    for i in range(len(df_temp)):
        if pd.isna(df_temp['volatility_ratio'].iloc[i]):
            continue
            
        vol_ratio = df_temp['volatility_ratio'].iloc[i]
        
        if vol_ratio > sensitivity:
            # High volatility - widen bands
            band_expansion = (vol_ratio - 1) * adjustment_factor * 100
            new_lower = max(base_lower - band_expansion, base_lower - max_width)
            new_upper = min(base_upper + band_expansion, base_upper + max_width)
        elif vol_ratio < (1 / sensitivity):
            # Low volatility - tighten bands
            band_contraction = (1 - vol_ratio) * adjustment_factor * 100
            new_lower = min(base_lower + band_contraction, base_lower + min_width)
            new_upper = max(base_upper - band_contraction, base_upper - min_width)
        else:
            # Normal volatility - use base bands
            new_lower = base_lower
            new_upper = base_upper
        
        # Ensure minimum band width
        band_width = new_upper - new_lower
        if band_width < min_width:
            mid_point = (new_lower + new_upper) / 2
            new_lower = mid_point - min_width / 2
            new_upper = mid_point + min_width / 2
        
        df_temp.loc[df_temp.index[i], 'dynamic_lower_band'] = float(new_lower)
        df_temp.loc[df_temp.index[i], 'dynamic_upper_band'] = float(new_upper)
    
    df['dynamic_lower_band'] = df_temp['dynamic_lower_band']
    df['dynamic_upper_band'] = df_temp['dynamic_upper_band']
    df['volatility_ratio'] = df_temp['volatility_ratio']
    df['ATR_MA'] = df_temp['ATR_MA']
    
    return df

def stochastic(df, TYPE = 'Stoch'):
    if TYPE == 'Stoch':
        stoch_params = config.indicators.stoch
        period = stoch_params.K_Length
        smoothK = stoch_params.smooth_K
        smoothD = stoch_params.smooth_D
        stoch_lower_band = stoch_params.lower_band
        
        df_temp = df.copy()
        df_temp['n-High'] = df_temp['close'].rolling(period).max()
        df_temp['n-Low'] = df_temp['close'].rolling(period).min()
        df_temp['Stoch %K'] = (((df_temp['close'] - df_temp['n-Low'])/(df_temp['n-High'] - df_temp['n-Low']))*100).rolling(smoothK).mean()
        df_temp['Stoch %D'] = df_temp['Stoch %K'].rolling(smoothD).mean()
        k = df_temp['Stoch %K']
        d = df_temp['Stoch %D']
        signals = []
        for i in range(len(k)):
            if k[i] > d[i] and k[i] > stoch_lower_band and k[i - 1] < stoch_lower_band:
                signals.append(1)
            else: signals.append(0)
        df_temp['Stoch Signal'] = signals
        df['Stoch Signal'] = df_temp['Stoch Signal'].diff()
        return df
    
    elif TYPE == 'StochRSI':
        stoch_rsi_params = config.indicators.stochRSI
        period = stoch_rsi_params.stoch_length
        smoothK = stoch_rsi_params.K
        smoothD = stoch_rsi_params.D
        stochRSI_lower_band = stoch_rsi_params.lower_band
        stochRSI_upper_band = stoch_rsi_params.upper_band

        df_temp = df.copy()
        df_temp['n-High'] = df_temp['RSI'].rolling(period).max()
        df_temp['n-Low'] = df_temp['RSI'].rolling(period).min()
        df_temp['Stoch %K'] = (((df_temp['RSI'] - df_temp['n-Low'])/(df_temp['n-High'] - df_temp['n-Low']))*100).rolling(smoothK).mean()
        df_temp['Stoch %D'] = df_temp['Stoch %K'].rolling(smoothD).mean()
        
        # Add ATR calculation for dynamic bands
        if stoch_rsi_params.dynamic_bands_enabled:
            df_temp = atr(df_temp, period=stoch_rsi_params.atr_period)
            df_temp = calculate_dynamic_bands(
                df_temp,
                base_lower=stochRSI_lower_band,
                base_upper=stochRSI_upper_band,
                atr_period=stoch_rsi_params.atr_period,
                sensitivity=stoch_rsi_params.atr_sensitivity,
                adjustment_factor=stoch_rsi_params.band_adjustment_factor,
                min_width=stoch_rsi_params.min_band_width,
                max_width=stoch_rsi_params.max_band_width
            )
            
            # Use dynamic bands for signal generation
            lower_band_values = df_temp['dynamic_lower_band']
            upper_band_values = df_temp['dynamic_upper_band']
        else:
            # Use static bands for backward compatibility
            lower_band_values = [stochRSI_lower_band] * len(df_temp)
            upper_band_values = [stochRSI_upper_band] * len(df_temp)
        
        k = df_temp['Stoch %K']
        d = df_temp['Stoch %D']
        signals = []
        signal_strength = []  # Track signal strength for performance analysis
        
        for i in range(len(k)):
            current_lower = lower_band_values[i] if hasattr(lower_band_values, '__getitem__') else stochRSI_lower_band
            current_upper = upper_band_values[i] if hasattr(upper_band_values, '__getitem__') else stochRSI_upper_band
            
            # Enhanced signal logic with dynamic bands
            if k[i] > d[i] and k[i] < current_lower:
                signals.append(1)
                # Calculate signal strength based on how oversold and band position
                strength = (current_lower - k[i]) / current_lower
                signal_strength.append(min(strength, 1.0))
            elif k[i] < d[i] and k[i] > current_upper:
                signals.append(-1)  # Sell signal for overbought condition
                strength = (k[i] - current_upper) / (100 - current_upper)
                signal_strength.append(min(strength, 1.0))
            else:
                signals.append(0)
                signal_strength.append(0.0)
        
        df_temp['StochRSI Signal'] = signals
        df_temp['Signal Strength'] = signal_strength
        
        # Copy results back to original dataframe
        df['StochRSI Signal'] = df_temp['StochRSI Signal']
        df['Signal Strength'] = df_temp['Signal Strength']
        df['Stoch %K'] = df_temp['Stoch %K']
        df['Stoch %D'] = df_temp['Stoch %D']
        
        if stoch_rsi_params.dynamic_bands_enabled:
            df['dynamic_lower_band'] = df_temp['dynamic_lower_band']
            df['dynamic_upper_band'] = df_temp['dynamic_upper_band']
            df['volatility_ratio'] = df_temp['volatility_ratio']
            df['ATR'] = df_temp['ATR']
            df['ATR_MA'] = df_temp['ATR_MA']
        
        return df

def rsi(ohlc: pd.DataFrame) -> pd.Series:
    period = config.indicators.stochRSI.rsi_length
    delta = ohlc["close"].diff()
    up, down = delta.copy(), delta.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    _gain = up.ewm(com=(period - 1), min_periods=period).mean()
    _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()
    RS = _gain / _loss
    RSI = 100 - (100 / (1 + RS))
    ohlc['RSI'] = RSI
    return ohlc

def implement_ema_strategy(prices):
    period = config.indicators.EMA.ema_period
    cols = list(prices.columns)
    ema = prices['Close'].ewm(span = period, adjust = False).mean()
    prices["EMA"] = ema
    prices['Signal_EMA'] = np.where(prices['EMA'] < prices['Close'], 1.0, 0.0)
    prices['EMA Signal'] = prices['Signal_EMA']
    cols += ["EMA Signal"]
    return prices[cols]

############################################################
