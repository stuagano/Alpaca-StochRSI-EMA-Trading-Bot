import pandas as pd
from .strategies import *
from services.unified_data_manager import get_data_manager

class BacktestingEngine:
    def __init__(self, strategy, symbol, start_date, end_date):
        self.strategy = strategy
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.data_manager = get_data_manager()
        self.data = self.data_manager.get_historical_data(symbol, '1Day', start_hours_ago=90*24) # Approx 3 months
        self.trades = []
        self.position = None
        self.cash = 100000  # Starting cash
        self.portfolio_value = []

    def run(self):
        for i in range(len(self.data)):
            row = self.data.iloc[i]
            signal = self.strategy.generate_signal(self.data.iloc[:i+1])
            
            if signal == 1 and not self.position:
                # Buy
                self.position = {'price': row['Close'], 'date': row.name}
                self.trades.append(('buy', row.name, row['Close']))
            elif signal == -1 and self.position:
                # Sell
                self.cash += row['Close'] - self.position['price']
                self.trades.append(('sell', row.name, row['Close']))
                self.position = None
            
            # Update portfolio value
            value = self.cash
            if self.position:
                value += row['Close'] - self.position['price']
            self.portfolio_value.append(value)
            
        return self.get_results()

    def get_results(self):
        return {
            'trades': self.trades,
            'portfolio_value': self.portfolio_value,
            'performance': self.calculate_performance()
        }

    def calculate_performance(self):
        returns = pd.Series(self.portfolio_value).pct_change().dropna()
        sharpe_ratio = returns.mean() / returns.std() * (252**0.5) # Annualized
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'total_returns': (self.portfolio_value[-1] / self.portfolio_value[0]) - 1
        }
