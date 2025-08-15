import pandas as pd
import pytest
from strategies.stoch_rsi_strategy import StochRSIStrategy
from strategies.ma_crossover_strategy import MACrossoverStrategy
from config.config import load_config

@pytest.fixture
def config():
    return load_config()

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        'Open': [100 + i for i in range(50)],
        'High': [101 + i for i in range(50)],
        'Low': [99 + i for i in range(50)],
        'Close': [100 + i for i in range(50)],
        'Volume': [1000] * 50
    }, index=pd.to_datetime(pd.date_range('2023-01-01', periods=50)))

def test_stoch_rsi_strategy(config, sample_data):
    strategy = StochRSIStrategy(config)
    # This is a simple test to ensure the strategy runs without errors.
    # A more sophisticated test would mock the data to produce a known signal.
    signal = strategy.generate_signal(sample_data)
    assert signal in [0, 1, -1]

def test_ma_crossover_strategy(config, sample_data):
    strategy = MACrossoverStrategy(config)
    # Create a crossover event
    sample_data.loc[sample_data.index[30:], 'Close'] = 90
    sample_data.loc[sample_data.index[49], 'Close'] = 150
    signal = strategy.generate_signal(sample_data)
    assert signal == 1
