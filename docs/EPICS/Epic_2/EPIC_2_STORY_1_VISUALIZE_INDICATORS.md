# EPIC 2, STORY 1: VISUALIZE STRATEGY INDICATORS

**User Story: Visualize Strategy Indicators on Candlestick Charts**

**As a user, I want to see the indicators for each trading strategy overlaid on the candlestick charts so that I can understand how the strategies work and make more informed decisions.**

**Acceptance Criteria:**

1.  **MA Crossover Indicator:**
    *   When viewing the charts, the fast and slow moving averages should be displayed as two separate lines on the main candlestick chart.
    *   The colors of the lines should be distinct and easily distinguishable (e.g., blue for the fast MA, orange for the slow MA).
    *   A clear legend should be present, labeling each line (e.g., "Fast MA," "Slow MA").

2.  **StochRSI Indicator:**
    *   The Stochastic RSI values (%K and %D) should be displayed in a separate pane below the main price chart.
    *   This pane must include horizontal lines indicating the overbought and oversold levels, with their values clearly labeled.
    *   The %K and %D lines should be rendered in distinct colors.
    *   A legend should identify the %K and %D lines.

3.  **Indicator Toggle / Controls:**
    *   The dashboard must provide controls (e.g., checkboxes or toggle switches) that allow users to show or hide the indicators for each strategy.
    *   Users should be able to view the indicators for any strategy, regardless of which one is currently active in the bot.

4.  **Data Accuracy and Synchronization:**
    *   The indicator data rendered on the chart must be calculated using the same parameters as the trading strategies and must be accurately aligned with the price candles.
    *   The indicators should update automatically when the chart data is refreshed or a new ticker is selected.
