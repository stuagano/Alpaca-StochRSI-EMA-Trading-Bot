# Trading Bot Improvement TODO List

This list outlines potential improvements to the Alpaca Trading Bot, categorized by impact area.

### 1. Strategy and Risk Management
- [ ] **Abstract Strategies:**
    - [ ] Create a `Strategy` base class.
    - [ ] Refactor the current StochRSI logic into a `StochRSIStrategy` class.
    - [ ] Implement a new strategy (e.g., Moving Average Crossover) as a separate class.
- [ ] **Dynamic Risk Models:**
    - [ ] Integrate the Average True Range (ATR) indicator.
    - [ ] Use ATR to set dynamic stop-loss levels based on volatility.
    - [ ] Explore other risk models in the `risk_management` directory.
- [ ] **Advanced Position Sizing:**
    - [ ] Implement a position sizing model that adjusts based on risk.
    - [ ] Allow for different position sizing models to be configured.

### 2. Data Handling and Performance
- [ ] **Use a Database:**
    - [ ] Set up a local time-series database (e.g., InfluxDB, TimescaleDB).
    - [ ] Create a service to fetch and store historical data in the database.
    - [ ] Modify the `RealtimeDataManager` to use the database as a primary data source.
- [ ] **Real-time Streaming:**
    - [ ] Implement a connection to Alpaca's real-time streaming API.
    - [ ] Update the `RealtimeDataManager` to consume the real-time stream.

### 3. Code Structure and Maintainability
- [ ] **Configuration Management:**
    - [ ] Consolidate all configuration into a single, structured file (e.g., `config.yml`).
    - [ ] Use a library like `pydantic` for configuration validation.
- [ ] **Comprehensive Logging:**
    - [ ] Implement structured logging (e.g., using the `logging` module with a JSON formatter).
    - [ ] Add detailed logging to all critical components of the bot.

### 4. Dashboard and UI
- [ ] **Interactive Backtesting:**
    - [ ] Add a "Backtesting" tab to the Flask dashboard.
    - [ ] Allow users to select a strategy and a date range for backtesting.
    - [ ] Display backtesting results, including performance metrics and trade history.
- [ ] **Enhanced Charting:**
    - [ ] Make the dashboard charts more interactive (zoom, pan).
    - [ ] Allow users to add/remove indicators on the charts dynamically.

### 5. Testing and Reliability
- [ ] **Unit and Integration Tests:**
    - [ ] Write unit tests for all indicator calculations.
    - [ ] Write integration tests for the trading strategy logic.
    - [ ] Mock the Alpaca API to test order submission and position management.
