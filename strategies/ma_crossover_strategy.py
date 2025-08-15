from strategies.strategy_base import Strategy
import pandas_ta as ta

class MACrossoverStrategy(Strategy):
    """
    A trading strategy based on a moving average crossover.
    """
    def __init__(self, config):
        super().__init__(config)
        self.ema_params = self.config.indicators.EMA
        self.short_window = self.ema_params.fast_period
        self.long_window = self.ema_params.slow_period

    def generate_signal(self, df):
        """
        Generate a trading signal using a moving average crossover.
        """
        if not self.ema_params.enabled:
            return 0

        # Calculate short and long term moving averages
        df.ta.ema(length=self.short_window, append=True)
        df.ta.ema(length=self.long_window, append=True)
        
        short_ema_col = f'EMA_{self.short_window}'
        long_ema_col = f'EMA_{self.long_window}'

        if short_ema_col not in df.columns or long_ema_col not in df.columns:
            return 0

        # Check for crossover in the last 2 periods
        if (df[short_ema_col].iloc[-2] < df[long_ema_col].iloc[-2] and
            df[short_ema_col].iloc[-1] > df[long_ema_col].iloc[-1]):
            return 1  # Buy signal
            
        return 0 # No signal
