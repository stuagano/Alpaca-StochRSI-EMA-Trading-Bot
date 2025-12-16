#!/bin/bash

echo "======================================"
echo "Trading Bot Dashboard Test Suite"
echo "======================================"
echo ""

# Check if Flask is running
echo "1. Checking if Flask server is running..."
if curl -s http://localhost:5001/api/v1/status > /dev/null 2>&1; then
    echo "   ✓ Flask server is running on port 5001"
else
    echo "   ✗ Flask server is NOT running"
    echo "   Start it with: python backend/api/run.py"
    echo ""
    read -p "   Do you want to start the server now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   Starting Flask server..."
        python backend/api/run.py &
        SERVER_PID=$!
        echo "   Server started with PID: $SERVER_PID"
        sleep 5
    else
        echo "   Skipping server start. Tests will likely fail."
    fi
fi

echo ""
echo "2. Running Playwright tests..."
echo "======================================"
npx playwright test --workers=1

echo ""
echo "======================================"
echo "3. Test Results"
echo "======================================"
echo ""
echo "To view detailed test report, run:"
echo "   npm run test:report"
echo ""
echo "To run tests with UI mode:"
echo "   npm run test:ui"
echo ""
echo "To debug tests:"
echo "   npm run test:debug"
