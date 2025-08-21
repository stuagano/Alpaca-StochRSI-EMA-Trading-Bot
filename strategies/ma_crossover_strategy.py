from strategies.strategy_base import Strategy
import pandas_ta as ta
from indicators.volume_analysis import get_volume_analyzer
import logging

logger = logging.getLogger(__name__)

class MACrossoverStrategy(Strategy):
    """
    A trading strategy based on a moving average crossover.
    """
    def __init__(self, config):
        super().__init__(config)
        self.ema_params = self.config.indicators.EMA
        self.short_window = self.ema_params.fast_period
        self.long_window = self.ema_params.slow_period
        
        # Initialize volume analyzer
        self.volume_analyzer = get_volume_analyzer(self.config.volume_confirmation)
        self.require_volume_confirmation = getattr(self.config.volume_confirmation, 'require_volume_confirmation', True)
        
        logger.info(f"MA Crossover Strategy initialized with volume confirmation: {self.require_volume_confirmation}")

    def generate_signal(self, df):
        """
        Generate a trading signal using a moving average crossover with volume confirmation.
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
        base_signal = 0
        if (df[short_ema_col].iloc[-2] < df[long_ema_col].iloc[-2] and
            df[short_ema_col].iloc[-1] > df[long_ema_col].iloc[-1]):
            base_signal = 1  # Buy signal
        
        # Apply volume confirmation if required
        if base_signal != 0 and self.require_volume_confirmation:
            if self.config.volume_confirmation.enabled:
                try:
                    # Get volume confirmation
                    volume_result = self.volume_analyzer.confirm_signal_with_volume(df, base_signal)
                    
                    if volume_result.is_confirmed:
                        logger.info(f"MA Crossover signal CONFIRMED by volume - Ratio: {volume_result.volume_ratio:.2f}, "
                                   f"Relative: {volume_result.relative_volume:.2f}, Strength: {volume_result.confirmation_strength:.2f}")
                        return base_signal
                    else:
                        logger.info(f"MA Crossover signal REJECTED by volume - Ratio: {volume_result.volume_ratio:.2f}, "
                                   f"Relative: {volume_result.relative_volume:.2f}")
                        return 0
                except Exception as e:
                    logger.error(f"Error in volume confirmation: {e}")
                    # If volume confirmation fails, return base signal (fail-safe)
                    return base_signal
            else:
                # Volume confirmation disabled, return base signal
                return base_signal
        
        return base_signal
