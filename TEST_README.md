# Trading Bot Test Suite

This directory contains a comprehensive test suite for the Alpaca StochRSI-EMA Trading Bot. The test suite provides high coverage and ensures reliability across all system components.

## Test Structure

### Test Files

- **`test_trading_bot.py`** - Unit tests for the main TradingBot class
  - Bot initialization and configuration
  - Position entry/exit logic
  - Order recording and management
  - Risk calculations and validation
  - Strategy execution
  - Error handling

- **`test_risk_management.py`** - Tests for the enhanced risk management system
  - Position sizing validation
  - Stop loss calculations
  - Portfolio risk limits
  - Trailing stop functionality
  - Risk violation detection
  - Emergency controls and overrides

- **`test_data_manager.py`** - Tests for the unified data management system
  - API connection and initialization
  - Data fetching and caching
  - Indicator calculations
  - Thread safety
  - Circuit breaker functionality
  - Real-time streaming

- **`test_integration.py`** - End-to-end integration tests
  - Complete trading workflows
  - Component interactions
  - Data flow validation
  - Configuration propagation
  - Error handling across systems

## Configuration

### pytest.ini
The `pytest.ini` file contains comprehensive pytest configuration including:
- Test discovery patterns
- Coverage settings (minimum 80% required)
- Custom markers for test categorization
- Logging configuration
- Performance settings

### Test Markers
Tests are categorized using custom markers:
- `unit` - Unit tests for individual components
- `integration` - Integration tests for component interactions
- `slow` - Tests that take longer to execute
- `network` - Tests requiring network access
- `api` - Tests interacting with external APIs
- `risk` - Risk management related tests
- `trading` - Trading operation tests
- `data` - Data management tests
- `strategy` - Trading strategy tests
- `performance` - Performance related tests
- `security` - Security related tests

## Running Tests

### Prerequisites
Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Quick Start
Run all tests with coverage:
```bash
python run_tests.py --all
```

### Test Runner Options

#### Basic Test Execution
```bash
# Run all tests
python run_tests.py --all

# Run unit tests only
python run_tests.py --unit

# Run integration tests only
python run_tests.py --integration

# Run quick subset for development
python run_tests.py --quick
```

#### Component-Specific Tests
```bash
# Run risk management tests
python run_tests.py --risk

# Run data management tests
python run_tests.py --data

# Run trading bot tests
python run_tests.py --trading

# Run performance tests
python run_tests.py --performance
```

#### Specific Test Files or Functions
```bash
# Run specific test file
python run_tests.py --file test_trading_bot.py

# Run specific test function
python run_tests.py --file test_trading_bot.py --function test_trading_bot_initialization
```

#### Test Selection by Markers
```bash
# Run tests with specific markers
python run_tests.py --markers unit integration

# Run only risk-related tests
python run_tests.py --markers risk
```

#### Failed Test Management
```bash
# Re-run only failed tests
python run_tests.py --failed

# Run only new tests (based on git changes)
python run_tests.py --new
```

### Coverage and Reporting

#### Coverage Reports
```bash
# Generate detailed coverage report
python run_tests.py --coverage

# Run tests without coverage (faster)
python run_tests.py --all --no-coverage
```

#### HTML Test Reports
```bash
# Generate comprehensive HTML test report
python run_tests.py --report
```

### Code Quality

#### Test Code Quality Checks
```bash
# Check test code quality (flake8, black, isort)
python run_tests.py --quality
```

#### Security Testing
```bash
# Run security tests and vulnerability scans
python run_tests.py --security
```

### Performance Testing

#### Benchmarks
```bash
# Run performance benchmarks
python run_tests.py --benchmark
```

#### Parallel Execution
```bash
# Run tests in parallel (requires pytest-xdist)
python run_tests.py --all --parallel
```

### Advanced Options
```bash
# Verbose output
python run_tests.py --all --verbose

# Combine multiple options
python run_tests.py --unit --coverage --verbose
```

## Direct pytest Usage

For more advanced pytest features, you can run pytest directly:

```bash
# Basic test run
pytest tests/

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test class
pytest tests/test_trading_bot.py::TestTradingBotInitialization

# Run with custom markers
pytest tests/ -m "unit and not slow"

# Run in parallel
pytest tests/ -n auto

# Stop on first failure
pytest tests/ -x

# Show local variables in traceback
pytest tests/ -l

# Increase verbosity
pytest tests/ -vv
```

## Test Data and Fixtures

### Common Fixtures
Tests use various fixtures for consistent test data:
- `mock_data_manager` - Mocked data management system
- `mock_strategy` - Mocked trading strategy
- `sample_historical_data` - Sample OHLC data
- `mock_auth_file` - Temporary authentication file
- `integrated_bot` - Fully integrated bot instance

### Test Data Generation
Tests generate realistic data using:
- pandas for OHLC data creation
- numpy for statistical distributions
- Mock objects for API responses
- Temporary files for file system operations

## Mocking Strategy

### External Dependencies
All external dependencies are mocked:
- Alpaca API calls
- File system operations
- Database connections
- Network requests
- Time-dependent functions

### Mock Patterns
- Use `unittest.mock.Mock` for simple mocking
- Use `unittest.mock.patch` for context-specific mocking
- Use `pytest.fixture` for reusable mock setups
- Mock at the appropriate abstraction level

## Coverage Goals

### Minimum Coverage
- Overall coverage: 80% minimum
- Critical components (trading_bot, risk_management): 90%+ target
- New code: 95%+ coverage required

### Coverage Exclusions
Excluded from coverage:
- Test files themselves
- Virtual environment directories
- Migration files
- Static files and templates
- Debug and development utilities

## Continuous Integration

### CI Pipeline Tests
The test suite is designed to work with CI/CD pipelines:
- Fast unit tests for quick feedback
- Comprehensive integration tests for release validation
- Coverage reporting for quality metrics
- Security scanning for vulnerability detection

### Environment Variables
Tests respect environment variables:
- `TEST_ENV=true` - Enables test-specific configurations
- `PYTEST_CURRENT_TEST` - Available during test execution
- `CI=true` - Adjusts test behavior for CI environments

## Performance Considerations

### Test Execution Speed
- Unit tests: < 5 seconds total
- Integration tests: < 30 seconds total
- Full suite with coverage: < 2 minutes

### Optimization Strategies
- Extensive use of mocking to avoid real API calls
- Parallel test execution support
- Incremental testing (only run affected tests)
- Smart fixture scoping

## Debugging Tests

### Common Issues
1. **Import Errors**: Ensure PYTHONPATH includes project root
2. **Mock Failures**: Check mock target paths and method signatures
3. **Fixture Conflicts**: Review fixture scopes and dependencies
4. **Timing Issues**: Use proper test isolation and cleanup

### Debugging Commands
```bash
# Run single test with maximum verbosity
pytest tests/test_trading_bot.py::test_specific_function -vv -s

# Run with PDB debugger
pytest tests/test_trading_bot.py --pdb

# Show test durations
pytest tests/ --durations=10

# Show fixture setup/teardown
pytest tests/ --setup-show
```

## Contributing to Tests

### Adding New Tests
1. Follow existing naming conventions
2. Use appropriate markers
3. Include docstrings explaining test purpose
4. Mock external dependencies
5. Ensure thread safety where applicable

### Test Design Principles
- **Isolation**: Each test should be independent
- **Repeatability**: Tests should produce consistent results
- **Clarity**: Test intent should be obvious
- **Coverage**: Aim for comprehensive edge case coverage
- **Performance**: Keep tests fast and focused

### Code Review Checklist
- [ ] Tests cover new functionality
- [ ] Appropriate mocking is used
- [ ] Error conditions are tested
- [ ] Tests are properly categorized with markers
- [ ] Documentation is updated if needed

## Maintenance

### Regular Tasks
- Review and update test dependencies
- Monitor test execution times
- Update mocks when APIs change
- Refresh test data as needed
- Clean up obsolete tests

### Test Health Metrics
Monitor these metrics regularly:
- Test pass rate (should be 100%)
- Test execution time trends
- Coverage percentage
- Flaky test identification

## Troubleshooting

### Common Test Failures
1. **API Rate Limits**: Ensure proper mocking
2. **File System Issues**: Use temporary files and proper cleanup
3. **Threading Problems**: Check for race conditions
4. **Configuration Conflicts**: Verify test isolation

### Getting Help
- Check test logs for detailed error information
- Review pytest documentation for advanced features
- Consult the main project README for setup instructions
- Check GitHub issues for known testing problems