# Trading Bot Test Suite

This directory contains comprehensive test suites for the Alpaca StochRSI EMA Trading Bot.

## Test Structure

```
tests/
├── README.md                      # This file
├── conftest.py                    # Pytest configuration and shared fixtures
├── pytest.ini                    # Pytest settings
├── fixtures/                     # Test data and fixtures
│   ├── market_data_fixtures.py   # Market data generators
│   ├── order_fixtures.py         # Order and position fixtures
│   └── data/                     # Static test data files
├── mocks/                        # Mock implementations
│   ├── alpaca_api_mock.py        # Comprehensive Alpaca API mock
│   ├── database_mock.py          # Database mocking utilities
│   └── websocket_mock.py         # WebSocket connection mocks
├── unit/                         # Unit tests
│   ├── test_strategies.py        # Strategy unit tests
│   ├── test_trading_bot.py       # Trading bot unit tests
│   └── test_risk_management.py   # Risk management tests
├── integration/                  # Integration tests
│   ├── test_api_integration.py   # API integration tests
│   └── test_database_integration.py
├── performance/                  # Performance tests
│   ├── test_performance.py       # Performance benchmarks
│   └── load_testing/             # Load testing scripts
├── security/                     # Security tests
│   ├── test_input_validation.py  # Input validation tests
│   └── test_authentication.py    # Authentication tests
└── e2e/                         # End-to-end tests
    ├── test_trading_workflows.py # Complete trading workflows
    └── test_user_scenarios.py    # User scenario tests
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/                 # Unit tests only
pytest tests/integration/          # Integration tests only
pytest tests/performance/          # Performance tests only

# Run tests with specific markers
pytest -m "not slow"              # Skip slow tests
pytest -m "integration"           # Run integration tests only
pytest -m "security"              # Run security tests only
```

### Test Configuration

#### Environment Variables
```bash
export TESTING=True
export DATABASE_URL=sqlite:///test.db
export ALPACA_API_KEY=test_key
export ALPACA_SECRET_KEY=test_secret
export ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

#### Test Data Setup
```bash
# Generate test fixtures
python -m tests.fixtures.market_data_fixtures
python -m tests.fixtures.order_fixtures
```

## Test Categories

### Unit Tests
- Test individual functions and components in isolation
- Fast execution (< 50ms per test)
- High coverage of business logic
- Mock all external dependencies

### Integration Tests
- Test component interactions
- Database operations
- API endpoint testing
- Service integration validation

### Performance Tests
- Response time benchmarks
- Load testing scenarios
- Memory usage validation
- Scalability testing

### Security Tests
- Input validation testing
- Authentication/authorization
- Vulnerability scanning
- Penetration testing scenarios

### End-to-End Tests
- Complete user workflows
- Real system behavior
- Business process validation
- User acceptance criteria

## Test Data Management

### Using Fixtures

```python
# Market data fixtures
from tests.fixtures.market_data_fixtures import (
    get_standard_market_data,
    get_trending_data,
    get_high_volatility_data
)

def test_strategy_with_volatile_data():
    volatile_data = get_high_volatility_data("AAPL")
    strategy = StochRSIStrategy()
    result = strategy.analyze(volatile_data)
    assert result is not None
```

### Using Mocks

```python
# Mock Alpaca API
from tests.mocks.alpaca_api_mock import create_realistic_market_scenario

def test_trading_with_mock_api():
    mock_api = create_realistic_market_scenario()
    trading_bot = TradingBot(mock_api)
    result = trading_bot.execute_trade("AAPL", "buy", 10)
    assert result.success == True
```

## Performance Benchmarks

### Response Time Requirements
- API endpoints: < 200ms (p95)
- Strategy calculations: < 50ms
- Database queries: < 100ms
- WebSocket latency: < 100ms

### Load Testing Targets
- 100 concurrent users
- 1000 requests per minute
- Memory usage < 512MB
- CPU usage < 80%

## Quality Gates

### Pre-commit Requirements
- All unit tests pass
- Code coverage > 80%
- No security vulnerabilities
- Linting checks pass

### Pre-deployment Requirements
- Full test suite passes (95%+ success rate)
- Performance benchmarks met
- Security scans clear
- Integration tests pass

## Continuous Integration

### GitHub Actions Workflow
```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: |
          pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Best Practices

### Writing Good Tests
1. **Use descriptive names**: Test names should explain the scenario
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Test one thing**: Each test should have a single responsibility
4. **Use realistic data**: Test with data that represents real scenarios
5. **Mock external dependencies**: Control external factors

### Test Maintenance
- Review and fix flaky tests weekly
- Update test data fixtures regularly
- Monitor test execution performance
- Keep test documentation current

## Debugging Tests

### Debug Configuration
```json
{
  "name": "Debug Current Test",
  "type": "python",
  "request": "launch",
  "module": "pytest",
  "args": ["${file}", "-v", "--pdb"],
  "console": "integratedTerminal"
}
```

### Common Issues
1. **Flaky tests**: Usually due to timing, async operations, or shared state
2. **Slow tests**: Profile with `pytest --profile` to identify bottlenecks
3. **Mock issues**: Verify mock setup and ensure proper isolation

## Reporting and Metrics

### Coverage Reports
```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Performance Reports
```bash
# Run performance benchmarks
pytest tests/performance/ --benchmark-json=benchmark.json
```

### Test Metrics Dashboard
- Test execution time trends
- Coverage percentage over time
- Flaky test identification
- Bug detection rate

## Contributing

### Adding New Tests
1. Choose appropriate test category (unit/integration/e2e)
2. Follow naming conventions
3. Use existing fixtures when possible
4. Add documentation for complex test scenarios
5. Ensure tests are independent and repeatable

### Test Review Checklist
- [ ] Test names are descriptive
- [ ] Tests cover happy path and edge cases
- [ ] External dependencies are mocked
- [ ] Test data is realistic
- [ ] Tests are independent
- [ ] Performance impact is acceptable

## Support

For questions about testing:
- Check existing test examples in each category
- Review the comprehensive TESTING_STRATEGY.md
- Consult team documentation
- Ask on team Slack #testing channel

---

*For detailed testing strategy and procedures, see: [TESTING_STRATEGY.md](../docs/TESTING_STRATEGY.md)*