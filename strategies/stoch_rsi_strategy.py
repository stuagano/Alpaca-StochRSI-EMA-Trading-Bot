from strategies.strategy_base import Strategy
from indicator import rsi, stochastic

class StochRSIStrategy(Strategy):
    """
    A trading strategy based on the Stochastic RSI indicator.
    """
    def __init__(self, config):
        super().__init__(config)
        self.stoch_rsi_params = self.config.indicators.stochRSI
        self.lookback_period = self.config.candle_lookback_period

    def generate_signal(self, df):
        """
        Generate a trading signal using the StochRSI indicator.
        """
        if not self.stoch_rsi_params.enabled:
            return 0

        df = rsi(df)
        df = stochastic(df, TYPE='StochRSI')
        
        if 'StochRSI Signal' not in df.columns:
            return 0
            
        signal_list = list(df['StochRSI Signal'].iloc[-self.lookback_period:])
        
        if 1 in signal_list:
            return 1  # Buy signal
        
        return 0 # No signal
