#!/usr/bin/env python3
"""
Flask API Testing Script
Validates all endpoints in the new Flask architecture
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import sys

class APITester:
    """Test all Flask API endpoints"""

    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.results = []
        self.session = requests.Session()

    def test_endpoint(self, method: str, endpoint: str, data: Dict = None,
                     expected_status: int = 200) -> Tuple[bool, str]:
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url, json=data)
            else:
                return False, f"Unsupported method: {method}"

            # Check status code
            if response.status_code != expected_status:
                return False, f"Expected {expected_status}, got {response.status_code}"

            # Try to parse JSON
            try:
                response.json()
            except:
                if expected_status == 200:
                    return False, "Invalid JSON response"

            return True, "Success"

        except requests.exceptions.ConnectionError:
            return False, "Connection refused - is the server running?"
        except Exception as e:
            return False, str(e)

    def run_tests(self):
        """Run all API tests"""
        print("=" * 60)
        print("FLASK API ENDPOINT TESTING")
        print("=" * 60)
        print(f"Testing API at: {self.base_url}\n")

        # Define test cases
        test_cases = [
            # Core API endpoints
            ("GET", "/api/v1/status", None, 200, "System Status"),
            ("GET", "/api/v1/account", None, 200, "Account Information"),
            ("GET", "/api/v1/positions", None, 200, "Current Positions"),
            ("GET", "/api/v1/signals", None, 200, "Trading Signals"),
            ("GET", "/api/v1/orders", None, 200, "Recent Orders"),

            # P&L endpoints
            ("GET", "/api/v1/pnl/current", None, 200, "Current P&L"),

            # Trading endpoints (test without actually executing)
            ("POST", "/api/v1/trading/stop", {}, 200, "Stop Trading"),
        ]

        # Run tests
        passed = 0
        failed = 0

        for method, endpoint, data, expected_status, description in test_cases:
            print(f"\nTesting: {description}")
            print(f"  {method} {endpoint}")

            success, message = self.test_endpoint(method, endpoint, data, expected_status)

            if success:
                print(f"  ✓ PASSED: {message}")
                passed += 1
                self.results.append({
                    "endpoint": endpoint,
                    "method": method,
                    "status": "PASSED",
                    "message": message
                })
            else:
                print(f"  ✗ FAILED: {message}")
                failed += 1
                self.results.append({
                    "endpoint": endpoint,
                    "method": method,
                    "status": "FAILED",
                    "message": message
                })

            # Small delay between tests
            time.sleep(0.5)

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {passed + failed}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        print(f"Success Rate: {(passed/(passed+failed)*100):.1f}%")

        # Save results
        self.save_results()

        return failed == 0

    def test_websocket(self):
        """Test WebSocket connection"""
        print("\n" + "=" * 60)
        print("WEBSOCKET CONNECTION TEST")
        print("=" * 60)

        try:
            import socketio

            sio = socketio.Client()
            connected = False

            @sio.event
            def connect():
                nonlocal connected
                connected = True
                print("  ✓ WebSocket connected successfully")

            @sio.event
            def disconnect():
                print("  WebSocket disconnected")

            try:
                sio.connect(self.base_url)
                time.sleep(2)

                if connected:
                    # Test emit
                    sio.emit('request_update', {'type': 'all'})
                    print("  ✓ WebSocket emit test passed")

                sio.disconnect()
                return True

            except Exception as e:
                print(f"  ✗ WebSocket error: {e}")
                return False

        except ImportError:
            print("  ⚠ python-socketio not installed, skipping WebSocket test")
            return None

    def test_data_flow(self):
        """Test complete data flow"""
        print("\n" + "=" * 60)
        print("DATA FLOW TEST")
        print("=" * 60)

        try:
            # 1. Get account
            print("\n1. Fetching account data...")
            response = self.session.get(f"{self.base_url}/api/v1/account")
            if response.status_code == 200:
                account = response.json()
                print(f"   Portfolio Value: ${account.get('portfolio_value', 0):,.2f}")
                print(f"   Buying Power: ${account.get('buying_power', 0):,.2f}")

            # 2. Get positions
            print("\n2. Fetching positions...")
            response = self.session.get(f"{self.base_url}/api/v1/positions")
            if response.status_code == 200:
                positions = response.json()
                print(f"   Open Positions: {len(positions)}")
                for pos in positions[:3]:  # Show first 3
                    print(f"   - {pos['symbol']}: {pos['qty']} @ ${pos.get('avg_entry_price', 0)}")

            # 3. Get signals
            print("\n3. Fetching signals...")
            response = self.session.get(f"{self.base_url}/api/v1/signals")
            if response.status_code == 200:
                signals = response.json()
                print(f"   Active Signals: {len(signals)}")
                for signal in signals[:3]:  # Show first 3
                    print(f"   - {signal['symbol']}: {signal.get('action', 'HOLD')} (RSI: {signal.get('rsi', 0):.1f})")

            return True

        except Exception as e:
            print(f"\n  ✗ Data flow test failed: {e}")
            return False

    def save_results(self):
        """Save test results to file"""
        report_file = "flask_api_test_results.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "results": self.results,
            "summary": {
                "total": len(self.results),
                "passed": len([r for r in self.results if r["status"] == "PASSED"]),
                "failed": len([r for r in self.results if r["status"] == "FAILED"])
            }
        }

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nTest results saved to: {report_file}")

def main():
    """Run API tests"""
    import argparse

    parser = argparse.ArgumentParser(description='Test Flask API endpoints')
    parser.add_argument('--url', default='http://localhost:5001',
                       help='Base URL of Flask API')
    parser.add_argument('--full', action='store_true',
                       help='Run full test suite including WebSocket and data flow')

    args = parser.parse_args()

    # Create tester
    tester = APITester(args.url)

    # Check if server is running
    print("Checking server connectivity...")
    success, message = tester.test_endpoint("GET", "/api/v1/status")
    if not success:
        print(f"\n✗ ERROR: Cannot connect to server at {args.url}")
        print(f"  {message}")
        print("\nPlease ensure the Flask server is running:")
        print("  python backend/api/run.py")
        sys.exit(1)

    print("✓ Server is running\n")

    # Run tests
    all_passed = tester.run_tests()

    # Run additional tests if requested
    if args.full:
        ws_result = tester.test_websocket()
        if ws_result is not None:
            all_passed = all_passed and ws_result

        flow_result = tester.test_data_flow()
        all_passed = all_passed and flow_result

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)

if __name__ == '__main__':
    main()
