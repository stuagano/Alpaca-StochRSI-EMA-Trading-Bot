# {{backtest_name}} Backtesting Framework

## Backtest Overview

**Backtest Name**: {{backtest_name}}  
**Strategy**: {{strategy_name}}  
**Version**: {{version}}  
**Author**: {{author}}  
**Created**: {{timestamp}}  
**Data Period**: {{start_date}} to {{end_date}}  
**Framework**: {{framework_type}}  

### Executive Summary
{{executive_summary}}

### Key Results
{{#key_results}}
- **{{metric_name}}**: {{metric_value}}
{{/key_results}}

## Backtest Configuration

### Data Specifications
```yaml
data_config:
  source: {{data_source}}
  symbols: {{symbols}}
  timeframe: {{timeframe}}
  start_date: {{start_date}}
  end_date: {{end_date}}
  data_quality:
    missing_data_threshold: {{missing_threshold}}%
    outlier_detection: {{outlier_detection}}
    corporate_actions: {{corporate_actions}}
  
  adjustments:
    dividend_adjustment: {{dividend_adj}}
    split_adjustment: {{split_adj}}
    survivorship_bias: {{survivorship_bias}}
```

### Strategy Parameters
```yaml
strategy_config:
  {{#strategy_parameters}}
  {{param_name}}: {{param_value}}  # {{param_description}}
  {{/strategy_parameters}}
  
  risk_management:
    {{#risk_parameters}}
    {{param_name}}: {{param_value}}
    {{/risk_parameters}}
  
  execution:
    {{#execution_parameters}}
    {{param_name}}: {{param_value}}
    {{/execution_parameters}}
```

### Execution Settings
```yaml
execution_config:
  initial_capital: {{initial_capital}}
  commission_structure:
    equity: {{equity_commission}}
    options: {{options_commission}}
    futures: {{futures_commission}}
  
  slippage_model:
    type: {{slippage_type}}
    equity_slippage: {{equity_slippage}}
    volume_impact: {{volume_impact}}
  
  market_impact:
    enabled: {{market_impact_enabled}}
    model: {{market_impact_model}}
    parameters:
      {{#impact_parameters}}
      {{param_name}}: {{param_value}}
      {{/impact_parameters}}
```

## Backtesting Framework

### Core Backtesting Engine
```python
class {{backtest_name}}Engine:
    """Advanced backtesting engine for {{strategy_name}}"""
    
    def __init__(self, config):
        self.config = config
        self.data_handler = DataHandler(config['data'])
        self.strategy = {{strategy_name}}Strategy(config['strategy'])
        self.portfolio = Portfolio(config['execution']['initial_capital'])
        self.execution_handler = ExecutionHandler(config['execution'])
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Initialize tracking
        self.trades = []
        self.daily_returns = []
        self.metrics = {}
    
    def run_backtest(self):
        \"\"\"Execute complete backtest\"\"\"
        print(f\"Starting backtest: {self.config['name']}\")
        
        # Initialize components
        self.initialize_backtest()
        
        # Main backtest loop
        for timestamp, market_data in self.data_handler.get_data_iterator():
            self.process_market_data(timestamp, market_data)
        
        # Finalize and analyze results
        self.finalize_backtest()
        
        return self.generate_results()
    
    def process_market_data(self, timestamp, market_data):
        \"\"\"Process single market data point\"\"\"
        # Update portfolio with current prices
        self.portfolio.update_positions(market_data)
        
        # Generate strategy signals
        signals = self.strategy.generate_signals(market_data)
        
        # Execute trades based on signals
        for signal in signals:
            self.execute_signal(signal, market_data)
        
        # Record daily performance
        self.record_daily_performance(timestamp)
    
    def execute_signal(self, signal, market_data):
        \"\"\"Execute trading signal with realistic constraints\"\"\"
        # Check position limits
        if not self.portfolio.can_execute_signal(signal):
            return None
        
        # Calculate realistic execution details
        execution_details = self.execution_handler.calculate_execution(
            signal, market_data, self.portfolio
        )
        
        # Execute the trade
        trade = self.portfolio.execute_trade(execution_details)
        
        if trade:
            self.trades.append(trade)
            self.log_trade(trade)
        
        return trade
```

### Data Handling
```python
class AdvancedDataHandler:
    \"\"\"Handle complex backtesting data requirements\"\"\"
    
    def __init__(self, config):
        self.config = config
        self.data_sources = self.initialize_data_sources()
        self.data_cache = {}
        
    def get_market_data(self, symbol, start_date, end_date):
        \"\"\"Get adjusted market data for backtesting\"\"\"
        # Check cache first
        cache_key = f\"{symbol}_{start_date}_{end_date}\"
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        # Load raw data
        raw_data = self.load_raw_data(symbol, start_date, end_date)
        
        # Apply adjustments
        adjusted_data = self.apply_adjustments(raw_data)
        
        # Quality checks
        validated_data = self.validate_data_quality(adjusted_data)
        
        # Cache results
        self.data_cache[cache_key] = validated_data
        
        return validated_data
    
    def apply_adjustments(self, data):
        \"\"\"Apply dividend and split adjustments\"\"\"
        if self.config.get('dividend_adjustment', True):
            data = self.adjust_for_dividends(data)
        
        if self.config.get('split_adjustment', True):
            data = self.adjust_for_splits(data)
        
        return data
    
    def validate_data_quality(self, data):
        \"\"\"Validate data quality and handle issues\"\"\"
        # Check for missing data
        missing_ratio = data.isnull().sum().sum() / (len(data) * len(data.columns))
        if missing_ratio > self.config.get('missing_data_threshold', 0.05):
            raise ValueError(f\"Too much missing data: {missing_ratio:.2%}\")
        
        # Fill missing data
        data = self.handle_missing_data(data)
        
        # Detect and handle outliers
        data = self.handle_outliers(data)
        
        return data
```

### Execution Simulation
```python
class RealisticExecutionHandler:
    \"\"\"Simulate realistic trade execution\"\"\"
    
    def __init__(self, config):
        self.config = config
        self.commission_model = CommissionModel(config['commission_structure'])
        self.slippage_model = SlippageModel(config['slippage_model'])
        self.market_impact_model = MarketImpactModel(config.get('market_impact', {}))
    
    def calculate_execution(self, signal, market_data, portfolio):
        \"\"\"Calculate realistic execution details\"\"\"
        # Base execution price
        base_price = self.get_execution_price(signal, market_data)
        
        # Calculate slippage
        slippage = self.slippage_model.calculate_slippage(
            signal, market_data, portfolio
        )
        
        # Calculate market impact
        market_impact = self.market_impact_model.calculate_impact(
            signal, market_data, portfolio
        )
        
        # Final execution price
        execution_price = base_price + slippage + market_impact
        
        # Calculate commission
        commission = self.commission_model.calculate_commission(
            signal, execution_price
        )
        
        return {
            'symbol': signal['symbol'],
            'action': signal['action'],
            'quantity': signal['quantity'],
            'execution_price': execution_price,
            'base_price': base_price,
            'slippage': slippage,
            'market_impact': market_impact,
            'commission': commission,
            'timestamp': market_data['timestamp']
        }
    
    def get_execution_price(self, signal, market_data):
        \"\"\"Determine base execution price\"\"\"
        if signal['order_type'] == 'market':
            # Use bid/ask spread
            if signal['action'] == 'buy':
                return market_data['ask']
            else:
                return market_data['bid']
        elif signal['order_type'] == 'limit':
            return signal['limit_price']
        else:
            # Default to close price
            return market_data['close']
```

## Performance Analysis

### Performance Metrics
```python
class ComprehensivePerformanceAnalyzer:
    \"\"\"Comprehensive performance analysis\"\"\"
    
    def __init__(self):
        self.metrics = {}
        self.benchmark_data = None
    
    def analyze_performance(self, portfolio_returns, trades_data, benchmark_returns=None):
        \"\"\"Generate comprehensive performance analysis\"\"\"
        
        self.metrics = {
            'return_metrics': self.calculate_return_metrics(portfolio_returns),
            'risk_metrics': self.calculate_risk_metrics(portfolio_returns),
            'trade_metrics': self.calculate_trade_metrics(trades_data),
            'drawdown_metrics': self.calculate_drawdown_metrics(portfolio_returns),
            'ratio_metrics': self.calculate_ratio_metrics(portfolio_returns, benchmark_returns)
        }
        
        if benchmark_returns is not None:
            self.metrics['benchmark_comparison'] = self.compare_to_benchmark(
                portfolio_returns, benchmark_returns
            )
        
        return self.metrics
    
    def calculate_return_metrics(self, returns):
        \"\"\"Calculate return-based metrics\"\"\"
        return {
            'total_return': (1 + returns).prod() - 1,
            'annualized_return': (1 + returns.mean()) ** 252 - 1,
            'compound_annual_growth_rate': ((1 + returns).prod() ** (252 / len(returns))) - 1,
            'best_day': returns.max(),
            'worst_day': returns.min(),
            'positive_days': (returns > 0).sum() / len(returns),
            'average_daily_return': returns.mean(),
            'median_daily_return': returns.median()
        }
    
    def calculate_risk_metrics(self, returns):
        \"\"\"Calculate risk-based metrics\"\"\"
        return {
            'volatility': returns.std() * np.sqrt(252),
            'downside_deviation': returns[returns < 0].std() * np.sqrt(252),
            'value_at_risk_95': returns.quantile(0.05),
            'value_at_risk_99': returns.quantile(0.01),
            'conditional_var_95': returns[returns <= returns.quantile(0.05)].mean(),
            'skewness': returns.skew(),
            'kurtosis': returns.kurt(),
            'semi_variance': (returns[returns < returns.mean()] ** 2).mean()
        }
    
    def calculate_trade_metrics(self, trades):
        \"\"\"Calculate trade-level metrics\"\"\"
        if not trades:
            return {}
        
        trade_returns = [trade['pnl'] / trade['entry_value'] for trade in trades]
        winning_trades = [r for r in trade_returns if r > 0]
        losing_trades = [r for r in trade_returns if r < 0]
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(trades) if trades else 0,
            'average_win': np.mean(winning_trades) if winning_trades else 0,
            'average_loss': np.mean(losing_trades) if losing_trades else 0,
            'largest_win': max(winning_trades) if winning_trades else 0,
            'largest_loss': min(losing_trades) if losing_trades else 0,
            'profit_factor': abs(sum(winning_trades) / sum(losing_trades)) if losing_trades else float('inf'),
            'average_trade_duration': np.mean([trade['duration'] for trade in trades]),
            'average_bars_held': np.mean([trade['bars_held'] for trade in trades])
        }
```

### Monte Carlo Analysis
```python
class MonteCarloAnalyzer:
    \"\"\"Monte Carlo simulation for strategy validation\"\"\"
    
    def __init__(self, num_simulations={{num_simulations}}):
        self.num_simulations = num_simulations
        self.results = []
    
    def run_monte_carlo(self, trade_returns, num_trades_per_sim=None):
        \"\"\"Run Monte Carlo simulation on trade returns\"\"\"
        if num_trades_per_sim is None:
            num_trades_per_sim = len(trade_returns)
        
        simulation_results = []
        
        for _ in range(self.num_simulations):
            # Randomly sample trades with replacement
            simulated_trades = np.random.choice(
                trade_returns, size=num_trades_per_sim, replace=True
            )
            
            # Calculate portfolio performance
            sim_performance = self.calculate_simulation_performance(simulated_trades)
            simulation_results.append(sim_performance)
        
        return self.analyze_simulation_results(simulation_results)
    
    def analyze_simulation_results(self, results):
        \"\"\"Analyze Monte Carlo simulation results\"\"\"
        total_returns = [r['total_return'] for r in results]
        max_drawdowns = [r['max_drawdown'] for r in results]
        sharpe_ratios = [r['sharpe_ratio'] for r in results]
        
        return {
            'total_return': {
                'mean': np.mean(total_returns),
                'std': np.std(total_returns),
                'percentile_5': np.percentile(total_returns, 5),
                'percentile_95': np.percentile(total_returns, 95),
                'probability_positive': sum(1 for r in total_returns if r > 0) / len(total_returns)
            },
            'max_drawdown': {
                'mean': np.mean(max_drawdowns),
                'std': np.std(max_drawdowns),
                'percentile_5': np.percentile(max_drawdowns, 5),
                'percentile_95': np.percentile(max_drawdowns, 95)
            },
            'sharpe_ratio': {
                'mean': np.mean(sharpe_ratios),
                'std': np.std(sharpe_ratios),
                'percentile_5': np.percentile(sharpe_ratios, 5),
                'percentile_95': np.percentile(sharpe_ratios, 95)
            }
        }
```

## Results and Visualization

### Performance Summary
```python
def generate_performance_summary(backtest_results):
    \"\"\"Generate comprehensive performance summary\"\"\"
    
    summary = {
        'strategy_name': '{{strategy_name}}',
        'backtest_period': f\"{{{start_date}}} to {{{end_date}}}\",
        'total_return': f\"{backtest_results['total_return']:.2%}\",
        'annualized_return': f\"{backtest_results['annualized_return']:.2%}\",
        'volatility': f\"{backtest_results['volatility']:.2%}\",
        'sharpe_ratio': f\"{backtest_results['sharpe_ratio']:.2f}\",
        'max_drawdown': f\"{backtest_results['max_drawdown']:.2%}\",
        'total_trades': backtest_results['total_trades'],
        'win_rate': f\"{backtest_results['win_rate']:.2%}\"
    }
    
    return summary
```

### Interactive Visualizations
```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class BacktestVisualizer:
    \"\"\"Create interactive backtest visualizations\"\"\"
    
    def create_performance_dashboard(self, backtest_data):
        \"\"\"Create comprehensive performance dashboard\"\"\"
        
        fig = make_subplots(
            rows=4, cols=2,
            subplot_titles=(
                'Equity Curve',
                'Drawdown',
                'Monthly Returns Heatmap',
                'Trade Distribution',
                'Rolling Sharpe Ratio',
                'Underwater Plot',
                'Return Distribution',
                'Risk-Return Scatter'
            ),
            specs=[
                [{\"colspan\": 2}, None],
                [{}, {}],
                [{}, {}],
                [{}, {}]
            ]
        )
        
        # Equity curve
        fig.add_trace(
            go.Scatter(
                x=backtest_data['dates'],
                y=backtest_data['portfolio_value'],
                mode='lines',
                name='Portfolio Value',
                line=dict(color='blue', width=2)
            ),
            row=1, col=1
        )
        
        # Drawdown
        fig.add_trace(
            go.Scatter(
                x=backtest_data['dates'],
                y=backtest_data['drawdown'],
                mode='lines',
                name='Drawdown',
                fill='tonexty',
                line=dict(color='red', width=1)
            ),
            row=2, col=1
        )
        
        # Continue adding other visualizations...
        
        fig.update_layout(
            height=1200,
            showlegend=True,
            title=f\"{{strategy_name}} Backtest Results\"
        )
        
        return fig
```

## Validation and Testing

### Walk-Forward Analysis
```python
class WalkForwardAnalyzer:
    \"\"\"Walk-forward analysis for strategy validation\"\"\"
    
    def __init__(self, in_sample_period={{in_sample_days}}, out_sample_period={{out_sample_days}}):
        self.in_sample_period = in_sample_period
        self.out_sample_period = out_sample_period
        self.results = []
    
    def run_walk_forward(self, data, strategy_class, param_ranges):
        \"\"\"Run walk-forward analysis\"\"\"
        
        start_date = data.index[0]
        end_date = data.index[-1]
        
        current_date = start_date + timedelta(days=self.in_sample_period)
        
        while current_date + timedelta(days=self.out_sample_period) <= end_date:
            # Define periods
            is_start = current_date - timedelta(days=self.in_sample_period)
            is_end = current_date
            oos_start = current_date
            oos_end = current_date + timedelta(days=self.out_sample_period)
            
            # In-sample optimization
            is_data = data[is_start:is_end]
            best_params = self.optimize_parameters(is_data, strategy_class, param_ranges)
            
            # Out-of-sample testing
            oos_data = data[oos_start:oos_end]
            oos_results = self.test_strategy(oos_data, strategy_class, best_params)
            
            self.results.append({
                'in_sample_period': (is_start, is_end),
                'out_sample_period': (oos_start, oos_end),
                'best_params': best_params,
                'oos_performance': oos_results
            })
            
            # Move to next period
            current_date += timedelta(days=self.out_sample_period)
        
        return self.analyze_walk_forward_results()
```

### Robustness Testing
```python
class RobustnessValidator:
    \"\"\"Test strategy robustness across different conditions\"\"\"
    
    def test_parameter_sensitivity(self, strategy, param_name, param_range, base_data):
        \"\"\"Test sensitivity to parameter changes\"\"\"
        results = []
        
        for param_value in param_range:
            # Update strategy parameter
            strategy_config = strategy.config.copy()
            strategy_config[param_name] = param_value
            
            # Run backtest
            test_strategy = strategy.__class__(strategy_config)
            backtest_result = self.run_backtest(test_strategy, base_data)
            
            results.append({
                'parameter_value': param_value,
                'total_return': backtest_result['total_return'],
                'sharpe_ratio': backtest_result['sharpe_ratio'],
                'max_drawdown': backtest_result['max_drawdown']
            })
        
        return results
    
    def test_market_conditions(self, strategy, data_periods):
        \"\"\"Test strategy across different market conditions\"\"\"
        condition_results = {}
        
        for condition_name, period_data in data_periods.items():
            backtest_result = self.run_backtest(strategy, period_data)
            condition_results[condition_name] = backtest_result
        
        return condition_results
```

## Documentation and Reporting

### Automated Report Generation
```python
class BacktestReportGenerator:
    \"\"\"Generate comprehensive backtest reports\"\"\"
    
    def generate_full_report(self, backtest_results):
        \"\"\"Generate complete backtest report\"\"\"
        
        report = {
            'executive_summary': self.generate_executive_summary(backtest_results),
            'strategy_description': self.generate_strategy_description(),
            'backtest_methodology': self.generate_methodology_section(),
            'performance_analysis': self.generate_performance_analysis(backtest_results),
            'risk_analysis': self.generate_risk_analysis(backtest_results),
            'trade_analysis': self.generate_trade_analysis(backtest_results),
            'benchmark_comparison': self.generate_benchmark_comparison(backtest_results),
            'sensitivity_analysis': self.generate_sensitivity_analysis(backtest_results),
            'conclusions_recommendations': self.generate_conclusions(backtest_results)
        }
        
        return report
    
    def export_report(self, report, format='html'):
        \"\"\"Export report in specified format\"\"\"
        if format == 'html':
            return self.generate_html_report(report)
        elif format == 'pdf':
            return self.generate_pdf_report(report)
        elif format == 'word':
            return self.generate_word_report(report)
        else:
            raise ValueError(f\"Unsupported format: {format}\")
```

---

*{{backtest_name}} Backtesting Documentation v{{version}}*  
*Generated: {{timestamp}}*  
*Strategy: {{strategy_name}}*  
*Period: {{start_date}} to {{end_date}}*