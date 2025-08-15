#### indicator.py

from config.config import config
import pandas as pd
import numpy as np

############################################################
#TECHNICAL INDICATORS

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

        df_temp = df.copy()
        df_temp['n-High'] = df_temp['RSI'].rolling(period).max()
        df_temp['n-Low'] = df_temp['RSI'].rolling(period).min()
        df_temp['Stoch %K'] = (((df_temp['RSI'] - df_temp['n-Low'])/(df_temp['n-High'] - df_temp['n-Low']))*100).rolling(smoothK).mean()
        df_temp['Stoch %D'] = df_temp['Stoch %K'].rolling(smoothD).mean()
        k = df_temp['Stoch %K']
        d = df_temp['Stoch %D']
        signals = []
        for i in range(len(k)):
            if k[i] > d[i] and k[i] < stochRSI_lower_band:
                signals.append(1)
            else: signals.append(0)
        df_temp['StochRSI Signal'] = signals
        df['StochRSI Signal'] = df_temp['StochRSI Signal']
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
