# BMAD Quick Start Guide

## Overview

This quick start guide gets you up and running with BMAD methodology in under 30 minutes. Follow these steps to implement your first BMAD cycle in the trading bot project.

## Prerequisites

- Node.js 16+ installed
- Python 3.8+ installed  
- Git repository access
- Basic familiarity with trading bot concepts

## 10-Minute Setup

### Step 1: Install Claude-Flow with BMAD (2 minutes)

```bash
# Install Claude-Flow globally
npm install -g claude-flow@alpha

# Verify installation
npx claude-flow --version

# Check BMAD availability
npx claude-flow bmad --help
```

### Step 2: Initialize BMAD in Your Project (3 minutes)

```bash
# Navigate to your trading bot project
cd /path/to/your/trading-bot

# Initialize BMAD configuration
npx claude-flow bmad init --project "trading-bot" --template trading

# This creates:
# - bmad.config.yml
# - .bmad/ directory
# - Initial documentation structure
```

### Step 3: Configure for Trading Bot (2 minutes)

```yaml
# Edit bmad.config.yml
project:
  name: trading-bot
  type: trading
  version: 1.0.0

phases:
  build:
    duration: 4h
    auto_test: true
  measure:
    duration: 2h
    metrics_collection: true
  analyze:
    duration: 3h
    ml_enabled: false  # Start simple
  document:
    duration: 1h
    auto_generate: true

# Save and close
```

### Step 4: Verify Setup (3 minutes)

```bash
# Test BMAD configuration
npx claude-flow bmad config validate

# Check system requirements
npx claude-flow bmad doctor

# View available commands
npx claude-flow bmad help
```

## Your First BMAD Cycle (20 minutes)

### Choose a Simple Task

For your first cycle, pick something small but complete:
- Add a new simple indicator
- Optimize an existing function
- Add error handling to a component
- Improve logging in a module

**Example**: Let's add a Simple Moving Average (SMA) indicator.

### BUILD Phase (8 minutes)

```bash
# Start your first BMAD cycle
npx claude-flow bmad cycle "add-sma-indicator" --priority medium

# This automatically starts the BUILD phase
```

#### Create the indicator file:

```python
# indicators/sma_indicator.py
class SMAIndicator:
    """Simple Moving Average indicator for BMAD demo"""
    
    def __init__(self, period=20):
        self.period = period
        self.name = f"SMA_{period}"
    
    def calculate(self, prices):
        """Calculate Simple Moving Average"""
        if len(prices) < self.period:
            return None
        
        return sum(prices[-self.period:]) / self.period
    
    def calculate_series(self, price_series):
        """Calculate SMA for entire price series"""
        sma_values = []
        
        for i in range(len(price_series)):
            if i >= self.period - 1:
                window = price_series[i - self.period + 1:i + 1]
                sma_values.append(sum(window) / self.period)
            else:
                sma_values.append(None)
        
        return sma_values
```

#### Add a simple test:

```python
# tests/test_sma_indicator.py
import unittest
from indicators.sma_indicator import SMAIndicator

class TestSMAIndicator(unittest.TestCase):
    
    def setUp(self):
        self.sma = SMAIndicator(period=3)
    
    def test_calculate_simple(self):
        """Test simple SMA calculation"""
        prices = [10, 20, 30]
        result = self.sma.calculate(prices)
        self.assertEqual(result, 20.0)  # (10+20+30)/3 = 20
    
    def test_insufficient_data(self):
        """Test with insufficient data"""
        prices = [10, 20]
        result = self.sma.calculate(prices)
        self.assertIsNone(result)
    
    def test_calculate_series(self):
        """Test series calculation"""
        prices = [10, 20, 30, 40, 50]
        result = self.sma.calculate_series(prices)
        expected = [None, None, 20.0, 30.0, 40.0]
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()
```

```bash
# Run tests to verify BUILD phase
python -m pytest tests/test_sma_indicator.py -v

# Complete BUILD phase
npx claude-flow bmad build --complete
```

### MEASURE Phase (4 minutes)

```bash
# Start MEASURE phase
npx claude-flow bmad measure "sma-performance"
```

#### Simple performance test:

```python
# measurement/sma_performance.py
import time
import numpy as np
from indicators.sma_indicator import SMAIndicator

def measure_sma_performance():
    """Measure SMA indicator performance"""
    
    sma = SMAIndicator(period=20)
    
    # Test with different data sizes
    test_sizes = [100, 1000, 10000]
    results = {}
    
    for size in test_sizes:
        # Generate test data
        prices = np.random.randn(size).cumsum() + 100
        
        # Measure calculation time
        start_time = time.time()
        sma_values = sma.calculate_series(prices.tolist())
        end_time = time.time()
        
        results[f"size_{size}"] = {
            'calculation_time': end_time - start_time,
            'values_calculated': len([v for v in sma_values if v is not None]),
            'performance_per_value': (end_time - start_time) / size
        }
    
    return results

if __name__ == '__main__':
    results = measure_sma_performance()
    
    print("SMA Performance Results:")
    for test, metrics in results.items():
        print(f"{test}: {metrics['calculation_time']:.4f}s for {metrics['values_calculated']} values")
```

```bash
# Run performance measurement
python measurement/sma_performance.py

# Complete MEASURE phase
npx claude-flow bmad measure --complete
```

### ANALYZE Phase (5 minutes)

```bash
# Start ANALYZE phase
npx claude-flow bmad analyze "sma-results"
```

#### Simple analysis:

```python
# analysis/sma_analysis.py
def analyze_sma_implementation():
    """Analyze SMA implementation and results"""
    
    analysis = {
        'implementation_quality': {
            'code_simplicity': 'Good - clear and readable',
            'test_coverage': 'Basic - covers main scenarios',
            'error_handling': 'Adequate - handles edge cases'
        },
        'performance_analysis': {
            'speed': 'Acceptable for small datasets',
            'memory_usage': 'Efficient - no unnecessary storage',
            'scalability': 'May need optimization for large datasets'
        },
        'insights': [
            'Implementation is correct and functional',
            'Performance is adequate for typical use cases',
            'Consider numpy implementation for better performance',
            'Could add more sophisticated error handling'
        ],
        'recommendations': [
            'Add input validation',
            'Consider vectorized implementation',
            'Add more comprehensive tests',
            'Document usage examples'
        ]
    }
    
    return analysis

if __name__ == '__main__':
    analysis = analyze_sma_implementation()
    
    print("SMA Analysis Results:")
    for category, items in analysis.items():
        print(f"\n{category.upper()}:")
        if isinstance(items, dict):
            for key, value in items.items():
                print(f"  {key}: {value}")
        elif isinstance(items, list):
            for item in items:
                print(f"  - {item}")
```

```bash
# Run analysis
python analysis/sma_analysis.py

# Complete ANALYZE phase
npx claude-flow bmad analyze --complete
```

### DOCUMENT Phase (3 minutes)

```bash
# Start DOCUMENT phase
npx claude-flow bmad document "sma-indicator"
```

#### Create documentation:

```markdown
# SMA Indicator Documentation

## Overview
Simple Moving Average (SMA) indicator implementation for the trading bot.

## Usage

```python
from indicators.sma_indicator import SMAIndicator

# Create SMA with 20-period
sma = SMAIndicator(period=20)

# Calculate for current prices
result = sma.calculate([10, 15, 20, 25, 30])
print(f"SMA: {result}")

# Calculate for entire series
prices = [10, 15, 20, 25, 30, 35, 40]
sma_series = sma.calculate_series(prices)
print(f"SMA series: {sma_series}")
```

## Parameters
- `period` (int): Number of periods for moving average calculation

## Methods
- `calculate(prices)`: Calculate SMA for given price list
- `calculate_series(price_series)`: Calculate SMA for entire price series

## Performance
- Suitable for datasets up to 10,000 points
- Average calculation time: 0.001s per 1,000 values
- Memory efficient implementation

## Testing
Run tests with: `python -m pytest tests/test_sma_indicator.py`

## Implementation Notes
- Returns `None` for insufficient data points
- Uses simple arithmetic mean calculation
- No external dependencies required
```

```bash
# Complete DOCUMENT phase
npx claude-flow bmad document --complete

# Complete entire cycle
npx claude-flow bmad cycle --complete
```

## Verify Your Success

```bash
# View cycle summary
npx claude-flow bmad report cycle --latest

# Check metrics
npx claude-flow bmad metrics summary

# View generated documentation
ls docs/BMAD/
```

## What You've Accomplished

Congratulations! You've completed your first BMAD cycle and:

✅ **Built** a functional SMA indicator with tests  
✅ **Measured** its performance characteristics  
✅ **Analyzed** implementation quality and identified improvements  
✅ **Documented** the component for future use  

## Next Steps

### Immediate (Next 30 minutes)
1. **Review Generated Reports**: Look at the cycle report and metrics
2. **Explore Templates**: Check out `docs/BMAD/templates/` for more examples
3. **Try Phase Commands**: Experiment with individual phase commands

### This Week
1. **Implement Recommendations**: Apply the analysis recommendations
2. **Larger Feature**: Try BMAD with a more complex feature
3. **Team Integration**: Share BMAD with your team members

### This Month
1. **Full Integration**: Integrate BMAD into your regular development workflow
2. **Automation**: Set up CI/CD integration for automated BMAD cycles
3. **Customization**: Customize BMAD configuration for your specific needs

## Common First-Time Issues

### Issue: "Command not found"
**Solution**: Ensure Claude-Flow is installed globally:
```bash
npm install -g claude-flow@alpha
```

### Issue: "Configuration validation failed"
**Solution**: Check your `bmad.config.yml` syntax:
```bash
npx claude-flow bmad config validate --verbose
```

### Issue: "Phase transition failed"
**Solution**: Ensure previous phase completed successfully:
```bash
npx claude-flow bmad status
```

### Issue: "Metrics collection failed"
**Solution**: Check if measurement tools are available:
```bash
npx claude-flow bmad doctor
```

## Quick Reference Commands

```bash
# Essential BMAD commands for daily use

# Start new cycle
npx claude-flow bmad cycle "feature-name"

# Individual phases
npx claude-flow bmad build "component"
npx claude-flow bmad measure "performance"
npx claude-flow bmad analyze "results"
npx claude-flow bmad document "topic"

# Status and monitoring
npx claude-flow bmad status
npx claude-flow bmad metrics summary
npx claude-flow bmad report cycle

# Configuration
npx claude-flow bmad config validate
npx claude-flow bmad doctor
```

## Getting Help

- **Documentation**: `/docs/BMAD/` directory
- **Commands Help**: `npx claude-flow bmad help [command]`
- **Community**: Check GitHub issues and discussions
- **Examples**: Look in `/docs/BMAD/guides/workflow-examples.md`

## Success Tips

1. **Start Small**: Begin with simple, well-defined tasks
2. **Be Consistent**: Complete all phases, even for small changes
3. **Measure Everything**: Don't skip the measurement phase
4. **Document as You Go**: Don't leave documentation for last
5. **Learn from Analysis**: Apply insights to improve future cycles
6. **Iterate Frequently**: Shorter cycles lead to faster learning

Welcome to systematic, data-driven development with BMAD! 🚀

---

*BMAD Quick Start Guide v2.0.0*
*Get productive with BMAD in 30 minutes*