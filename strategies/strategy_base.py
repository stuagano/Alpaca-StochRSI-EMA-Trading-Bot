from abc import ABC, abstractmethod

class Strategy(ABC):
    """
    Abstract base class for a trading strategy.
    """
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def generate_signal(self, df):
        """
        Generate a trading signal from a DataFrame of historical data.

        :param df: DataFrame with OHLC data.
        :return: 1 for a buy signal, -1 for a sell signal, 0 for no signal.
        """
        pass
