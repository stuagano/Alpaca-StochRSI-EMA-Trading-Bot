import pandas as pd
import pytest
from backtesting.backtesting_engine import BacktestingEngine
from strategies.ma_crossover_strategy import MACrossoverStrategy
from config.config import load_config

@pytest.fixture
def config():
    return load_config()

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        'high': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        'low': [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
        'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        'volume': [1000] * 10
    }, index=pd.to_datetime(pd.date_range('2023-01-01', periods=10)))

def test_backtesting_engine(config, sample_data):
    strategy = MACrossoverStrategy(config)
    engine = BacktestingEngine(strategy, 'AAPL', '2023-01-01', '2023-01-10')
    
    # Create a crossover event in the data
    data = pd.DataFrame({
        'Open': [100] * 100,
        'High': [100] * 100,
        'Low': [100] * 100,
        'Close': [100] * 100,
        'Volume': [1000] * 100
    }, index=pd.to_datetime(pd.date_range('2023-01-01', periods=100)))
    data.loc[data.index[50:], 'Close'] = 90
    data.loc[data.index[80:], 'Close'] = 110
    data.loc[data.index[99], 'Close'] = 150
    engine.data = data

    results = engine.run()
    
    assert len(results['trades']) > 0
    assert results['performance']['total_returns'] > 0
