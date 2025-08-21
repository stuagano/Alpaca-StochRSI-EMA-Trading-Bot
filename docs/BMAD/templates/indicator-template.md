# {{indicator_name}} Technical Indicator

## Indicator Overview

**Indicator Name**: {{indicator_name}}  
**Category**: {{indicator_category}}  
**Type**: {{indicator_type}}  
**Version**: {{version}}  
**Author**: {{author}}  
**Created**: {{timestamp}}  

### Description
{{indicator_description}}

### Mathematical Foundation
{{mathematical_foundation}}

### Market Application
{{market_application}}

## Technical Specification

### Formula
{{#formulas}}
#### {{formula_name}}
```
{{formula_expression}}
```
**Where**:
{{#formula_variables}}
- {{variable_name}}: {{variable_description}}
{{/formula_variables}}
{{/formulas}}

### Parameters
{{#parameters}}
- **{{param_name}}**: {{param_description}}
  - Type: {{param_type}}
  - Default: {{param_default}}
  - Range: {{param_range}}
  - Impact: {{param_impact}}
{{/parameters}}

### Calculation Method
```python
class {{indicator_class_name}}:
    """{{indicator_description}}"""
    
    def __init__(self, {{init_parameters}}):
        {{#init_params}}
        self.{{param_name}} = {{param_name}}
        {{/init_params}}
        self.history = []
        self.values = []
    
    def calculate(self, data):
        """Calculate {{indicator_name}} value"""
        {{calculation_implementation}}
        
        # Store calculation
        result = {
            'value': calculated_value,
            'timestamp': data['timestamp'],
            'raw_data': data,
            'parameters': self.get_parameters()
        }
        
        self.history.append(result)
        return calculated_value
    
    def calculate_series(self, data_series):
        """Calculate {{indicator_name}} for entire data series"""
        results = []
        
        for data_point in data_series:
            value = self.calculate(data_point)
            results.append(value)
        
        return results
    
    {{#additional_methods}}
    def {{method_name}}(self, {{method_params}}):
        """{{method_description}}"""
        {{method_implementation}}
    {{/additional_methods}}
```

## Usage Examples

### Basic Usage
```python
from indicators import {{indicator_class_name}}

# Initialize indicator
{{indicator_instance}} = {{indicator_class_name}}({{example_params}})

# Calculate for single data point
price_data = {
    'open': {{example_open}},
    'high': {{example_high}},
    'low': {{example_low}},
    'close': {{example_close}},
    'volume': {{example_volume}},
    'timestamp': '{{example_timestamp}}'
}

indicator_value = {{indicator_instance}}.calculate(price_data)
print(f"{{indicator_name}}: {indicator_value}")
```

### Series Calculation
```python
import pandas as pd

# Load historical data
data = pd.read_csv('{{example_data_file}}')

# Calculate indicator series
{{indicator_instance}} = {{indicator_class_name}}({{example_params}})
indicator_series = {{indicator_instance}}.calculate_series(data.to_dict('records'))

# Add to DataFrame
data['{{indicator_name}}'] = indicator_series

# Display results
print(data[['close', '{{indicator_name}}']].tail(10))
```

### Real-time Usage
```python
class RealTimeIndicator:
    def __init__(self):
        self.{{indicator_instance}} = {{indicator_class_name}}({{example_params}})
    
    def on_price_update(self, price_data):
        """Handle real-time price updates"""
        current_value = self.{{indicator_instance}}.calculate(price_data)
        
        # Check for signals
        signal = self.check_signals(current_value, price_data)
        if signal:
            self.handle_signal(signal)
    
    def check_signals(self, indicator_value, price_data):
        """Check for trading signals"""
        {{signal_detection_logic}}
        return signal
```

## Signal Generation

### Entry Signals
{{#entry_signals}}
#### {{signal_name}}
**Condition**: {{signal_condition}}  
**Strength**: {{signal_strength}}/10  
**Implementation**:
```python
def check_{{signal_function}}(self, current_value, previous_values):
    """{{signal_description}}"""
    {{signal_implementation}}
    
    if signal_triggered:
        return {
            'type': 'entry',
            'action': '{{signal_action}}',
            'confidence': confidence_score,
            'indicator_value': current_value,
            'reasoning': '{{signal_reasoning}}'
        }
    return None
```
{{/entry_signals}}

### Exit Signals
{{#exit_signals}}
#### {{signal_name}}
**Condition**: {{signal_condition}}  
**Type**: {{signal_type}}  
**Implementation**:
```python
def check_{{signal_function}}(self, current_value, position_info):
    """{{signal_description}}"""
    {{signal_implementation}}
    
    if exit_triggered:
        return {
            'type': 'exit',
            'reason': '{{exit_reason}}',
            'urgency': '{{exit_urgency}}',
            'indicator_value': current_value
        }
    return None
```
{{/exit_signals}}

## Optimization

### Parameter Sensitivity Analysis
{{#parameter_sensitivity}}
#### {{param_name}}
- **Optimal Range**: {{optimal_range}}
- **Sensitivity**: {{sensitivity_level}}
- **Impact on Signals**: {{signal_impact}}
- **Recommended Values**:
  - Conservative: {{conservative_value}}
  - Moderate: {{moderate_value}}
  - Aggressive: {{aggressive_value}}
{{/parameter_sensitivity}}

### Optimization Code
```python
class {{indicator_class_name}}Optimizer:
    def __init__(self, historical_data):
        self.data = historical_data
        self.results = {}
    
    def optimize_parameters(self, param_ranges):
        """Optimize indicator parameters"""
        from itertools import product
        
        best_score = float('-inf')
        best_params = None
        
        # Generate parameter combinations
        param_combinations = list(product(*param_ranges.values()))
        
        for params in param_combinations:
            param_dict = dict(zip(param_ranges.keys(), params))
            score = self.evaluate_parameters(param_dict)
            
            if score > best_score:
                best_score = score
                best_params = param_dict
        
        return best_params, best_score
    
    def evaluate_parameters(self, params):
        """Evaluate parameter combination"""
        indicator = {{indicator_class_name}}(**params)
        signals = []
        
        for data_point in self.data:
            value = indicator.calculate(data_point)
            signal = self.check_signals(value, data_point)
            if signal:
                signals.append(signal)
        
        # Calculate performance score
        return self.calculate_performance_score(signals)
```

## Performance Analysis

### Computational Complexity
- **Time Complexity**: {{time_complexity}}
- **Space Complexity**: {{space_complexity}}
- **Memory Usage**: {{memory_usage}}

### Benchmarks
{{#benchmarks}}
#### {{benchmark_name}}
- **Data Size**: {{data_size}} points
- **Calculation Time**: {{calculation_time}}ms
- **Memory Usage**: {{memory_usage}}MB
- **Throughput**: {{throughput}} calculations/second
{{/benchmarks}}

### Performance Optimization
```python
class Optimized{{indicator_class_name}}:
    """Optimized version using NumPy vectorization"""
    
    def __init__(self, {{init_parameters}}):
        {{optimized_init}}
        
    def calculate_vectorized(self, data_array):
        """Vectorized calculation for better performance"""
        import numpy as np
        
        {{vectorized_implementation}}
        
        return results
    
    def update_streaming(self, new_value):
        """Efficient streaming update"""
        {{streaming_update_implementation}}
        
        return self.current_value
```

## Validation and Testing

### Unit Tests
```python
import unittest
import numpy as np

class Test{{indicator_class_name}}(unittest.TestCase):
    
    def setUp(self):
        self.{{indicator_instance}} = {{indicator_class_name}}({{test_params}})
        self.test_data = self.generate_test_data()
    
    def test_basic_calculation(self):
        """Test basic indicator calculation"""
        test_value = self.{{indicator_instance}}.calculate(self.test_data[0])
        
        self.assertIsNotNone(test_value)
        self.assertIsInstance(test_value, (int, float))
        self.assertFalse(np.isnan(test_value))
    
    def test_series_calculation(self):
        """Test series calculation consistency"""
        # Calculate individually
        individual_results = []
        for data_point in self.test_data:
            result = self.{{indicator_instance}}.calculate(data_point)
            individual_results.append(result)
        
        # Calculate as series
        series_results = self.{{indicator_instance}}.calculate_series(self.test_data)
        
        # Should be identical
        np.testing.assert_array_almost_equal(
            individual_results, series_results, decimal=10
        )
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Test with insufficient data
        with self.assertRaises(ValueError):
            self.{{indicator_instance}}.calculate([])
        
        # Test with invalid data
        invalid_data = {'invalid': 'data'}
        with self.assertRaises(KeyError):
            self.{{indicator_instance}}.calculate(invalid_data)
    
    def test_parameter_validation(self):
        """Test parameter validation"""
        # Test invalid parameters
        with self.assertRaises(ValueError):
            {{indicator_class_name}}({{invalid_params}})
```

### Signal Quality Tests
```python
class Test{{indicator_class_name}}Signals(unittest.TestCase):
    
    def test_signal_accuracy(self):
        """Test signal accuracy against known patterns"""
        # Load test data with known signals
        test_data = self.load_labeled_data()
        
        {{indicator_instance}} = {{indicator_class_name}}({{test_params}})
        detected_signals = []
        
        for data_point in test_data['data']:
            value = {{indicator_instance}}.calculate(data_point)
            signal = self.check_signals(value, data_point)
            if signal:
                detected_signals.append(signal)
        
        # Compare with expected signals
        accuracy = self.calculate_signal_accuracy(
            detected_signals, test_data['expected_signals']
        )
        
        self.assertGreater(accuracy, {{min_accuracy_threshold}})
    
    def test_false_positive_rate(self):
        """Test false positive rate"""
        # Test on random data (should generate few signals)
        random_data = self.generate_random_data()
        
        {{indicator_instance}} = {{indicator_class_name}}({{test_params}})
        false_signals = 0
        
        for data_point in random_data:
            value = {{indicator_instance}}.calculate(data_point)
            signal = self.check_signals(value, data_point)
            if signal:
                false_signals += 1
        
        false_positive_rate = false_signals / len(random_data)
        self.assertLess(false_positive_rate, {{max_false_positive_rate}})
```

## Market Analysis

### Historical Performance
{{#historical_performance}}
#### {{period_name}} ({{start_date}} to {{end_date}})
- **Signal Count**: {{signal_count}}
- **Win Rate**: {{win_rate}}%
- **Average Return per Signal**: {{avg_return}}%
- **Best Signal**: {{best_signal}}%
- **Worst Signal**: {{worst_signal}}%
- **Signal Frequency**: {{signal_frequency}} per month
{{/historical_performance}}

### Market Condition Analysis
{{#market_conditions}}
#### {{condition_name}}
**Definition**: {{condition_definition}}  
**Indicator Performance**:
- Win Rate: {{condition_win_rate}}%
- Average Return: {{condition_avg_return}}%
- Signal Quality: {{signal_quality}}/10
- Recommended Use: {{recommended_use}}
{{/market_conditions}}

### Correlation Analysis
```python
def analyze_correlations(self, market_data):
    """Analyze indicator correlations with market movements"""
    import scipy.stats as stats
    
    {{indicator_instance}} = {{indicator_class_name}}({{analysis_params}})
    indicator_values = []
    price_changes = []
    
    for i, data_point in enumerate(market_data[1:], 1):
        # Calculate indicator
        indicator_value = {{indicator_instance}}.calculate(data_point)
        indicator_values.append(indicator_value)
        
        # Calculate price change
        prev_close = market_data[i-1]['close']
        curr_close = data_point['close']
        price_change = (curr_close - prev_close) / prev_close
        price_changes.append(price_change)
    
    # Calculate correlations
    correlation, p_value = stats.pearsonr(indicator_values, price_changes)
    
    return {
        'correlation': correlation,
        'p_value': p_value,
        'significance': 'significant' if p_value < 0.05 else 'not_significant'
    }
```

## Integration

### Trading System Integration
```python
class TradingSystemIntegration:
    def __init__(self, trading_system):
        self.trading_system = trading_system
        self.{{indicator_instance}} = {{indicator_class_name}}({{integration_params}})
        
    def integrate_indicator(self):
        """Integrate indicator with trading system"""
        # Register indicator
        self.trading_system.register_indicator(
            name='{{indicator_name}}',
            instance=self.{{indicator_instance}},
            update_frequency='{{update_frequency}}'
        )
        
        # Register signal handlers
        self.trading_system.register_signal_handler(
            indicator='{{indicator_name}}',
            handler=self.handle_signals
        )
    
    def handle_signals(self, signal_data):
        """Handle indicator signals"""
        if signal_data['type'] == 'entry':
            self.trading_system.place_order(
                action=signal_data['action'],
                confidence=signal_data['confidence']
            )
        elif signal_data['type'] == 'exit':
            self.trading_system.close_positions(
                reason=signal_data['reason']
            )
```

### API Integration
```python
class {{indicator_class_name}}API:
    """REST API for {{indicator_name}} indicator"""
    
    def __init__(self, app):
        self.app = app
        self.{{indicator_instance}} = {{indicator_class_name}}()
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.route('/indicators/{{indicator_name}}/calculate', methods=['POST'])
        def calculate():
            data = request.get_json()
            
            try:
                result = self.{{indicator_instance}}.calculate(data)
                return {
                    'success': True,
                    'indicator': '{{indicator_name}}',
                    'value': result,
                    'timestamp': data.get('timestamp')
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }, 400
        
        @self.app.route('/indicators/{{indicator_name}}/parameters', methods=['GET'])
        def get_parameters():
            return {
                'parameters': self.{{indicator_instance}}.get_parameters(),
                'defaults': self.{{indicator_instance}}.get_defaults()
            }
```

## Documentation

### Configuration Documentation
```yaml
# {{indicator_name}} configuration schema
{{indicator_name}}_config:
  type: object
  properties:
    {{#config_properties}}
    {{property_name}}:
      type: {{property_type}}
      description: {{property_description}}
      default: {{property_default}}
      minimum: {{property_min}}
      maximum: {{property_max}}
    {{/config_properties}}
  required: [{{required_properties}}]
```

### Error Codes
{{#error_codes}}
- **{{error_code}}**: {{error_description}}
  - **Cause**: {{error_cause}}
  - **Solution**: {{error_solution}}
{{/error_codes}}

### Changelog
{{#changelog_entries}}
#### Version {{version}} ({{date}})
{{#changes}}
- {{change_type}}: {{change_description}}
{{/changes}}
{{/changelog_entries}}

## References

### Academic Literature
{{#academic_references}}
- {{reference_title}} by {{authors}} ({{year}})
  - {{reference_summary}}
  - DOI: {{doi}}
{{/academic_references}}

### Implementation References
{{#implementation_references}}
- {{reference_name}}: {{reference_description}}
  - URL: {{reference_url}}
  - Implementation: {{implementation_notes}}
{{/implementation_references}}

---

*{{indicator_name}} Indicator Documentation v{{version}}*  
*Generated: {{timestamp}}*  
*Mathematical Validation: {{validation_status}}*  
*Last Updated: {{last_updated}}*