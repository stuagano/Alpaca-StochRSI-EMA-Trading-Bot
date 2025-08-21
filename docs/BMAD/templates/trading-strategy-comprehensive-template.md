# {{strategy_name}} Trading Strategy

## Strategy Overview

**Strategy Name**: {{strategy_name}}  
**Strategy Type**: {{strategy_type}}  
**Version**: {{version}}  
**Author**: {{author}}  
**Created**: {{timestamp}}  
**Last Updated**: {{last_updated}}  

### Executive Summary
{{executive_summary}}

### Strategy Classification
- **Primary Type**: {{primary_type}}
- **Secondary Type**: {{secondary_type}}
- **Complexity Level**: {{complexity_level}}
- **Risk Level**: {{risk_level}}
- **Target Timeframe**: {{target_timeframe}}
- **Market Suitability**: {{market_suitability}}

## Strategy Logic

### Core Concept
{{core_concept}}

### Entry Conditions
{{#entry_conditions}}
#### {{condition_name}}
**Type**: {{condition_type}}  
**Description**: {{condition_description}}  
**Parameters**:
{{#condition_parameters}}
- `{{param_name}}`: {{param_value}} ({{param_description}})
{{/condition_parameters}}

**Implementation**:
```python
def {{condition_function}}(self, data):
    """{{condition_description}}"""
    {{condition_implementation}}
    return signal
```

**Signal Strength**: {{signal_strength}}/10  
**Frequency**: {{signal_frequency}}  
{{/entry_conditions}}

### Exit Conditions
{{#exit_conditions}}
#### {{exit_name}}
**Type**: {{exit_type}}  
**Trigger**: {{exit_trigger}}  
**Implementation**:
```python
def {{exit_function}}(self, position, current_data):
    """{{exit_description}}"""
    {{exit_implementation}}
    return should_exit, exit_reason
```
{{/exit_conditions}}

### Risk Management
```python
class {{strategy_name}}RiskManager:
    """Risk management for {{strategy_name}} strategy"""
    
    def __init__(self):
        self.max_position_size = {{max_position_size}}
        self.stop_loss_pct = {{stop_loss_pct}}
        self.take_profit_pct = {{take_profit_pct}}
        self.max_daily_loss = {{max_daily_loss}}
    
    def calculate_position_size(self, account_value, risk_per_trade):
        """Calculate appropriate position size"""
        max_risk_amount = account_value * risk_per_trade
        stop_loss_amount = self.stop_loss_pct * {{base_price}}
        position_size = max_risk_amount / stop_loss_amount
        
        return min(position_size, self.max_position_size)
    
    def check_risk_limits(self, current_positions, new_trade):
        """Check if new trade violates risk limits"""
        {{risk_check_implementation}}
        return is_within_limits, risk_violations
```

## Technical Implementation

### Core Strategy Class
```python
class {{strategy_name}}Strategy(BaseStrategy):
    """{{strategy_description}}"""
    
    def __init__(self, config):
        super().__init__(config)
        {{#strategy_parameters}}
        self.{{param_name}} = config.get('{{param_name}}', {{param_default}})
        {{/strategy_parameters}}
        
        # Initialize indicators
        {{#indicators}}
        self.{{indicator_name}} = {{indicator_class}}({{indicator_params}})
        {{/indicators}}
        
        # Initialize risk manager
        self.risk_manager = {{strategy_name}}RiskManager()
    
    def analyze(self, data):
        """Main strategy analysis method"""
        signals = []
        
        # Calculate indicators
        {{#indicator_calculations}}
        {{indicator_name}}_value = self.{{indicator_name}}.calculate(data)
        {{/indicator_calculations}}
        
        # Check entry conditions
        entry_signal = self.check_entry_conditions(data, {{indicator_values}})
        if entry_signal:
            signals.append(entry_signal)
        
        # Check exit conditions for existing positions
        exit_signals = self.check_exit_conditions(data, {{indicator_values}})
        signals.extend(exit_signals)
        
        return signals
    
    def check_entry_conditions(self, data, {{indicator_params}}):
        """Check all entry conditions"""
        {{entry_conditions_implementation}}
        
        if all_conditions_met:
            return {
                'type': 'entry',
                'action': '{{entry_action}}',
                'confidence': confidence_score,
                'indicators': indicator_values,
                'reasoning': entry_reasoning
            }
        return None
    
    def check_exit_conditions(self, data, {{indicator_params}}):
        """Check exit conditions for current positions"""
        exit_signals = []
        
        for position in self.current_positions:
            {{exit_conditions_implementation}}
            
            if should_exit:
                exit_signals.append({
                    'type': 'exit',
                    'position_id': position.id,
                    'reason': exit_reason,
                    'urgency': exit_urgency
                })
        
        return exit_signals
```

### Required Indicators
{{#required_indicators}}
#### {{indicator_name}}
**Purpose**: {{indicator_purpose}}  
**Parameters**: {{indicator_parameters}}  
**Calculation Period**: {{calculation_period}}  

```python
# {{indicator_name}} implementation
class {{indicator_class}}:
    def __init__(self, {{indicator_init_params}}):
        {{indicator_init_implementation}}
    
    def calculate(self, data):
        """Calculate {{indicator_name}}"""
        {{indicator_calculation}}
        return result
```
{{/required_indicators}}

## Configuration

### Strategy Parameters
```yaml
{{strategy_name}}:
  # Core parameters
  {{#core_parameters}}
  {{param_name}}: {{param_value}}  # {{param_description}}
  {{/core_parameters}}
  
  # Risk management
  risk_management:
    {{#risk_parameters}}
    {{param_name}}: {{param_value}}  # {{param_description}}
    {{/risk_parameters}}
  
  # Indicator settings
  indicators:
    {{#indicator_settings}}
    {{indicator_name}}:
      {{#indicator_params}}
      {{param_name}}: {{param_value}}
      {{/indicator_params}}
    {{/indicator_settings}}
  
  # Market conditions
  market_conditions:
    {{#market_conditions}}
    {{condition_name}}: {{condition_value}}
    {{/market_conditions}}
```

### Environment Variables
```bash
# Strategy-specific environment variables
{{#env_variables}}
export {{var_name}}={{var_value}}  # {{var_description}}
{{/env_variables}}
```

## Backtesting Results

### Historical Performance
{{#backtest_periods}}
#### {{period_name}} ({{period_start}} to {{period_end}})
- **Total Return**: {{total_return}}%
- **Annualized Return**: {{annualized_return}}%
- **Sharpe Ratio**: {{sharpe_ratio}}
- **Maximum Drawdown**: {{max_drawdown}}%
- **Win Rate**: {{win_rate}}%
- **Profit Factor**: {{profit_factor}}
- **Total Trades**: {{total_trades}}
- **Average Trade**: {{avg_trade}}%
{{/backtest_periods}}

### Performance by Market Conditions
{{#market_condition_performance}}
#### {{condition_name}}
- **Return**: {{condition_return}}%
- **Win Rate**: {{condition_win_rate}}%
- **Average Trade Duration**: {{avg_duration}}
- **Best Trade**: {{best_trade}}%
- **Worst Trade**: {{worst_trade}}%
{{/market_condition_performance}}

### Monthly Returns
```
{{monthly_returns_table}}
```

### Drawdown Analysis
```python
# Drawdown statistics
drawdown_stats = {
    'max_drawdown': {{max_drawdown}},
    'avg_drawdown': {{avg_drawdown}},
    'drawdown_frequency': {{drawdown_frequency}},
    'recovery_time_avg': {{recovery_time_avg}},
    'longest_drawdown': {{longest_drawdown}}
}
```

## Risk Analysis

### Risk Metrics
- **Value at Risk (95%)**: {{var_95}}%
- **Conditional VaR (95%)**: {{cvar_95}}%
- **Beta**: {{beta}}
- **Alpha**: {{alpha}}%
- **Correlation to Market**: {{market_correlation}}
- **Volatility**: {{volatility}}%

### Risk Scenarios
{{#risk_scenarios}}
#### {{scenario_name}}
**Probability**: {{scenario_probability}}%  
**Impact**: {{scenario_impact}}%  
**Mitigation**: {{scenario_mitigation}}
{{/risk_scenarios}}

### Stress Testing
{{#stress_tests}}
#### {{stress_test_name}}
**Scenario**: {{stress_scenario}}  
**Result**: {{stress_result}}  
**Recovery Time**: {{recovery_time}}
{{/stress_tests}}

## Usage Examples

### Basic Usage
```python
from strategies import {{strategy_name}}Strategy

# Initialize strategy
config = {
    {{#example_config}}
    '{{config_key}}': {{config_value}},
    {{/example_config}}
}

strategy = {{strategy_name}}Strategy(config)

# Analyze market data
market_data = get_market_data('{{example_symbol}}', '{{example_timeframe}}')
signals = strategy.analyze(market_data)

# Process signals
for signal in signals:
    if signal['type'] == 'entry':
        print(f"Entry signal: {signal['action']} with confidence {signal['confidence']}")
    elif signal['type'] == 'exit':
        print(f"Exit signal for position {signal['position_id']}: {signal['reason']}")
```

### Advanced Usage with Risk Management
```python
from strategies import {{strategy_name}}Strategy
from risk_management import PortfolioManager

# Initialize components
strategy = {{strategy_name}}Strategy(config)
portfolio = PortfolioManager(initial_capital={{initial_capital}})

# Trading loop
for timestamp, data in market_data_stream:
    # Get signals
    signals = strategy.analyze(data)
    
    # Process each signal
    for signal in signals:
        if signal['type'] == 'entry':
            # Calculate position size
            risk_per_trade = 0.02  # 2% risk per trade
            position_size = strategy.risk_manager.calculate_position_size(
                portfolio.account_value, risk_per_trade
            )
            
            # Check risk limits
            is_safe, violations = strategy.risk_manager.check_risk_limits(
                portfolio.positions, signal
            )
            
            if is_safe:
                # Execute trade
                portfolio.open_position(
                    symbol=signal['symbol'],
                    action=signal['action'],
                    size=position_size,
                    strategy_name='{{strategy_name}}'
                )
        
        elif signal['type'] == 'exit':
            # Close position
            portfolio.close_position(signal['position_id'])
```

## Monitoring and Alerts

### Key Metrics to Monitor
{{#monitoring_metrics}}
- **{{metric_name}}**: {{metric_description}} (Alert if {{alert_condition}})
{{/monitoring_metrics}}

### Alert Configuration
```python
class {{strategy_name}}Alerts:
    def __init__(self):
        self.alert_thresholds = {
            {{#alert_thresholds}}
            '{{threshold_name}}': {{threshold_value}},
            {{/alert_thresholds}}
        }
    
    def check_alerts(self, current_metrics):
        """Check for alert conditions"""
        alerts = []
        
        {{#alert_checks}}
        if current_metrics['{{metric_name}}'] {{comparison_operator}} self.alert_thresholds['{{threshold_name}}']:
            alerts.append({
                'type': '{{alert_type}}',
                'metric': '{{metric_name}}',
                'value': current_metrics['{{metric_name}}'],
                'threshold': self.alert_thresholds['{{threshold_name}}'],
                'message': '{{alert_message}}'
            })
        {{/alert_checks}}
        
        return alerts
```

## Optimization

### Parameter Optimization
{{#optimization_parameters}}
#### {{param_name}}
**Current Value**: {{current_value}}  
**Optimization Range**: {{min_value}} to {{max_value}}  
**Step Size**: {{step_size}}  
**Impact on Performance**: {{performance_impact}}
{{/optimization_parameters}}

### Optimization Results
```python
# Best parameters found through optimization
optimized_params = {
    {{#optimized_params}}
    '{{param_name}}': {{optimized_value}},  # Improved performance by {{improvement}}%
    {{/optimized_params}}
}

# Performance comparison
baseline_performance = {{baseline_performance}}
optimized_performance = {{optimized_performance}}
improvement = {{improvement_percentage}}%
```

## Testing

### Unit Tests
```python
import unittest
from strategies import {{strategy_name}}Strategy

class Test{{strategy_name}}Strategy(unittest.TestCase):
    
    def setUp(self):
        self.config = {{test_config}}
        self.strategy = {{strategy_name}}Strategy(self.config)
        self.test_data = self.load_test_data()
    
    def test_entry_signal_generation(self):
        """Test entry signal generation"""
        # Test data that should generate entry signal
        entry_data = self.test_data['entry_scenario']
        signals = self.strategy.analyze(entry_data)
        
        self.assertTrue(any(s['type'] == 'entry' for s in signals))
        entry_signal = next(s for s in signals if s['type'] == 'entry')
        self.assertEqual(entry_signal['action'], '{{expected_action}}')
        self.assertGreater(entry_signal['confidence'], {{min_confidence}})
    
    def test_exit_signal_generation(self):
        """Test exit signal generation"""
        # Setup position
        self.strategy.current_positions = [self.create_test_position()]
        
        # Test data that should generate exit signal
        exit_data = self.test_data['exit_scenario']
        signals = self.strategy.analyze(exit_data)
        
        self.assertTrue(any(s['type'] == 'exit' for s in signals))
    
    def test_risk_limits(self):
        """Test risk management limits"""
        # Test position size calculation
        account_value = {{test_account_value}}
        risk_per_trade = {{test_risk_per_trade}}
        
        position_size = self.strategy.risk_manager.calculate_position_size(
            account_value, risk_per_trade
        )
        
        self.assertLessEqual(position_size, self.strategy.risk_manager.max_position_size)
        self.assertGreater(position_size, 0)
```

### Integration Tests
```python
class Test{{strategy_name}}Integration(unittest.TestCase):
    
    def test_full_trading_cycle(self):
        """Test complete trading cycle"""
        # Initialize strategy with real-like data
        strategy = {{strategy_name}}Strategy(self.production_config)
        
        # Simulate trading session
        for data_point in self.historical_data:
            signals = strategy.analyze(data_point)
            
            for signal in signals:
                # Validate signal structure
                self.assertIn('type', signal)
                self.assertIn('confidence', signal)
                
                if signal['type'] == 'entry':
                    self.assertIn('action', signal)
                    self.assertIn('reasoning', signal)
```

## Deployment

### Production Deployment
```python
# production_config.py
PRODUCTION_CONFIG = {
    'strategy_name': '{{strategy_name}}',
    'version': '{{version}}',
    'environment': 'production',
    
    # Strategy parameters (optimized)
    {{#production_params}}
    '{{param_name}}': {{param_value}},
    {{/production_params}}
    
    # Risk settings (conservative)
    'risk_management': {
        'max_position_size': {{prod_max_position}},
        'stop_loss_pct': {{prod_stop_loss}},
        'max_daily_loss': {{prod_max_daily_loss}}
    },
    
    # Monitoring
    'monitoring': {
        'alert_email': '{{alert_email}}',
        'dashboard_update_freq': {{dashboard_freq}},
        'log_level': 'INFO'
    }
}
```

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy strategy code
COPY strategies/ ./strategies/
COPY config/ ./config/

# Set environment variables
ENV STRATEGY_NAME={{strategy_name}}
ENV ENVIRONMENT=production

# Run strategy
CMD ["python", "-m", "strategies.{{strategy_name}}", "--config", "production"]
```

## Troubleshooting

### Common Issues
{{#common_issues}}
#### {{issue_title}}
**Symptoms**: {{issue_symptoms}}  
**Probable Cause**: {{issue_cause}}  
**Solution**: 
```python
{{issue_solution}}
```
**Prevention**: {{issue_prevention}}
{{/common_issues}}

### Debug Mode
```python
# Enable debug mode
strategy = {{strategy_name}}Strategy(config, debug=True)

# Access debug information
debug_info = strategy.get_debug_info()
print(f"Last analysis: {debug_info['last_analysis']}")
print(f"Indicator values: {debug_info['indicators']}")
print(f"Signal history: {debug_info['signal_history']}")
```

### Performance Debugging
```python
class {{strategy_name}}Profiler:
    def __init__(self, strategy):
        self.strategy = strategy
        self.profiling_data = {}
    
    def profile_analysis(self, data):
        """Profile strategy analysis performance"""
        import time
        import cProfile
        import pstats
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        result = self.strategy.analyze(data)
        
        profiler.disable()
        stats = pstats.Stats(profiler)
        
        return {
            'result': result,
            'execution_time': stats.total_tt,
            'function_calls': stats.total_calls,
            'bottlenecks': stats.sort_stats('cumulative').print_stats(10)
        }
```

## Maintenance

### Regular Maintenance Tasks
{{#maintenance_tasks}}
- **{{task_name}}**: {{task_description}} (Frequency: {{task_frequency}})
{{/maintenance_tasks}}

### Version History
{{#version_history}}
### Version {{version_number}} ({{release_date}})
{{#version_changes}}
- {{change_type}}: {{change_description}}
{{/version_changes}}
{{/version_history}}

### Upgrade Guide
```python
# Upgrading from v{{old_version}} to v{{new_version}}
{{#upgrade_steps}}
# Step {{step_number}}: {{step_description}}
{{step_code}}
{{/upgrade_steps}}
```

## References

### Academic Sources
{{#academic_references}}
- {{reference_title}} ({{reference_year}}) - {{reference_authors}}
{{/academic_references}}

### Market Data Sources
{{#data_sources}}
- **{{source_name}}**: {{source_description}} ({{source_url}})
{{/data_sources}}

### Related Strategies
{{#related_strategies}}
- **{{strategy_name}}**: {{strategy_relationship}}
{{/related_strategies}}

---

*{{strategy_name}} Strategy Documentation v{{version}}*  
*Generated: {{timestamp}}*  
*Last Backtest: {{last_backtest_date}}*  
*Next Review: {{next_review_date}}*