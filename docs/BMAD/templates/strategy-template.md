# {{strategy_name}} Trading Strategy

## Overview
{{description}}

**Strategy Type**: {{strategy_type}}  
**Timeframe**: {{timeframe}}  
**Version**: {{version}}  
**Author**: {{author}}  
**Last Updated**: {{timestamp}}  

## Strategy Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
{{#each parameters}}
| {{name}} | {{type}} | {{default}} | {{range}} | {{description}} |
{{/each}}

## Trading Logic

### Entry Conditions
{{entry_conditions}}

### Exit Conditions
{{exit_conditions}}

### Position Sizing
{{position_sizing}}

## Risk Management

### Stop Loss Rules
{{stop_loss_rules}}

### Risk per Trade
- **Maximum Risk**: {{max_risk_per_trade}}%
- **Position Size Calculation**: {{position_size_calculation}}

### Portfolio Risk
- **Maximum Exposure**: {{max_portfolio_exposure}}%
- **Correlation Limits**: {{correlation_limits}}

## Performance Metrics

### Backtesting Results
{{#if backtest_results}}
| Metric | Value |
|--------|-------|
| Total Return | {{backtest_results.total_return}}% |
| Sharpe Ratio | {{backtest_results.sharpe_ratio}} |
| Max Drawdown | {{backtest_results.max_drawdown}}% |
| Win Rate | {{backtest_results.win_rate}}% |
| Profit Factor | {{backtest_results.profit_factor}} |
| Average Trade | {{backtest_results.avg_trade}}% |
{{/if}}

### Live Performance
{{#if live_performance}}
| Metric | Value |
|--------|-------|
| Live Return | {{live_performance.total_return}}% |
| Live Sharpe | {{live_performance.sharpe_ratio}} |
| Live Drawdown | {{live_performance.max_drawdown}}% |
| Trades Executed | {{live_performance.total_trades}} |
{{/if}}

## Implementation

### Code Example

```python
from strategies.{{strategy_class_name}} import {{strategy_class_name}}

# Initialize strategy
strategy = {{strategy_class_name}}(
{{#each parameters}}
    {{name}}={{default}},
{{/each}}
)

# Configure risk management
strategy.set_risk_params(
    max_risk_per_trade={{max_risk_per_trade}},
    stop_loss_pct={{stop_loss_pct}}
)

# Generate signals
signals = strategy.generate_signals(market_data)

# Execute trades
for signal in signals:
    if signal.action == 'BUY':
        strategy.execute_buy(signal)
    elif signal.action == 'SELL':
        strategy.execute_sell(signal)
```

### Configuration File

```yaml
# config/strategies/{{strategy_name}}.yml
strategy:
  name: "{{strategy_name}}"
  enabled: {{enabled}}
  
  parameters:
{{#each parameters}}
    {{name}}: {{default}}
{{/each}}
  
  risk_management:
    max_risk_per_trade: {{max_risk_per_trade}}
    stop_loss_pct: {{stop_loss_pct}}
    position_size_method: "{{position_size_method}}"
  
  execution:
    timeframe: "{{timeframe}}"
    markets: {{markets}}
    trading_hours: "{{trading_hours}}"
```

## Market Conditions

### Optimal Conditions
{{optimal_conditions}}

### Suboptimal Conditions
{{suboptimal_conditions}}

### Market Regime Analysis
{{#if market_regimes}}
| Regime | Performance | Recommended Action |
|--------|-------------|--------------------|
{{#each market_regimes}}
| {{name}} | {{performance}} | {{action}} |
{{/each}}
{{/if}}

## Usage Guidelines

### When to Use
- {{usage_when_to_use}}

### When NOT to Use
- {{usage_when_not_to_use}}

### Recommended Pairs/Assets
{{recommended_assets}}

## Monitoring and Maintenance

### Key Metrics to Monitor
{{monitoring_metrics}}

### Performance Alerts
{{performance_alerts}}

### Maintenance Schedule
- **Daily**: {{daily_maintenance}}
- **Weekly**: {{weekly_maintenance}}
- **Monthly**: {{monthly_maintenance}}

## Troubleshooting

### Common Issues

#### Issue: Low Win Rate
**Symptoms**: Win rate below {{min_win_rate}}%  
**Possible Causes**: 
- Market conditions changed
- Parameters need reoptimization
- Increased market noise

**Solutions**:
1. Review recent market conditions
2. Rerun parameter optimization
3. Adjust entry criteria

#### Issue: High Drawdown
**Symptoms**: Drawdown exceeds {{max_acceptable_drawdown}}%  
**Possible Causes**:
- Position sizes too large
- Insufficient diversification
- Risk management failure

**Solutions**:
1. Reduce position sizes
2. Implement stricter stop losses
3. Review correlation limits

### Emergency Procedures

#### Immediate Stop
```python
# Emergency stop all positions
strategy.emergency_stop()
strategy.close_all_positions()
```

#### Strategy Pause
```python
# Pause strategy temporarily
strategy.pause_trading()
```

## Testing and Validation

### Unit Tests
```bash
# Run strategy unit tests
python -m pytest tests/strategies/test_{{strategy_name}}.py -v
```

### Backtesting
```bash
# Run comprehensive backtest
python backtesting/run_backtest.py --strategy {{strategy_name}} --period 2Y
```

### Paper Trading
```bash
# Start paper trading
python trading/paper_trading.py --strategy {{strategy_name}} --duration 30d
```

## Version History

{{#each version_history}}
### Version {{version}} - {{date}}
{{changes}}
{{/each}}

## References and Research

### Academic Papers
{{academic_references}}

### Implementation References
{{implementation_references}}

### Related Strategies
{{related_strategies}}

## Disclaimer

{{disclaimer_text}}

**Risk Warning**: Trading involves substantial risk of loss and is not suitable for all investors.

---

*Strategy Documentation Template v2.0.0*  
*Generated: {{generation_timestamp}}*  
*BMAD Methodology Documentation*