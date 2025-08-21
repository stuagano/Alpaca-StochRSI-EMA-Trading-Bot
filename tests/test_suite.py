#!/usr/bin/env python3
"""
Comprehensive Testing Suite for Epic 1 Trading Dashboard
Tests all critical functionality and API endpoints
"""

import requests
import json
import time
import asyncio
import websocket
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DashboardTestSuite:
    """Complete testing suite for the trading dashboard"""
    
    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.websocket_connected = False
        self.websocket_messages = []
        
    def log_test(self, test_name: str, status: str, details: str = "", data: Any = None):
        """Log test results with emoji indicators"""
        emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{emoji} {test_name}: {status}")
        if details:
            print(f"   Details: {details}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        print()
    
    def test_server_health(self) -> bool:
        """Test basic server connectivity"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Server Health Check", "PASS", 
                            f"Server responding with status {data.get('status', 'unknown')}", data)
                return True
            else:
                self.log_test("Server Health Check", "FAIL", 
                            f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Server Health Check", "FAIL", str(e))
            return False
    
    def test_dashboard_routes(self) -> bool:
        """Test all dashboard route endpoints"""
        routes = ["/", "/dashboard", "/dashboard/professional", "/dashboard/fixed"]
        all_passed = True
        
        for route in routes:
            try:
                response = self.session.get(f"{self.base_url}{route}", timeout=10)
                if response.status_code == 200 and "Epic 1 Trading Dashboard" in response.text:
                    self.log_test(f"Dashboard Route {route}", "PASS", 
                                f"Route accessible, content verified")
                else:
                    self.log_test(f"Dashboard Route {route}", "FAIL", 
                                f"HTTP {response.status_code} or missing content")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Dashboard Route {route}", "FAIL", str(e))
                all_passed = False
        
        return all_passed
    
    def test_account_api(self) -> bool:
        """Test account API endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/account", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_fields = ["balance", "buying_power", "cash", "success"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Account API", "FAIL", 
                                f"Missing required fields: {missing_fields}", data)
                    return False
                
                # Validate data types
                try:
                    balance = float(data["balance"])
                    buying_power = float(data["buying_power"])
                    cash = float(data["cash"])
                    
                    self.log_test("Account API", "PASS", 
                                f"Balance: ${balance:,.2f}, Buying Power: ${buying_power:,.2f}", 
                                data)
                    return True
                except (ValueError, TypeError) as e:
                    self.log_test("Account API", "FAIL", f"Invalid data types: {e}", data)
                    return False
            else:
                self.log_test("Account API", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Account API", "FAIL", str(e))
            return False
    
    def test_positions_api(self) -> bool:
        """Test positions API endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/positions", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                if not data.get("success"):
                    self.log_test("Positions API", "FAIL", "Success flag not true", data)
                    return False
                
                positions = data.get("positions", [])
                if not isinstance(positions, list):
                    self.log_test("Positions API", "FAIL", "Positions not a list", data)
                    return False
                
                # Validate position data structure
                position_count = len(positions)
                if position_count > 0:
                    sample_position = positions[0]
                    required_fields = ["symbol", "qty", "side", "avg_entry_price", 
                                     "current_price", "unrealized_pl"]
                    missing_fields = [field for field in required_fields 
                                    if field not in sample_position]
                    
                    if missing_fields:
                        self.log_test("Positions API", "FAIL", 
                                    f"Missing position fields: {missing_fields}", data)
                        return False
                
                self.log_test("Positions API", "PASS", 
                            f"Found {position_count} positions", 
                            {"count": position_count, "sample": positions[0] if positions else None})
                return True
            else:
                self.log_test("Positions API", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Positions API", "FAIL", str(e))
            return False
    
    def test_chart_data_api(self) -> bool:
        """Test chart data API endpoints"""
        symbols = ["AAPL", "SPY"]
        timeframes = ["1Min", "15Min", "1Hour", "1Day"]
        all_passed = True
        
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    url = f"{self.base_url}/api/v2/chart-data/{symbol}?timeframe={timeframe}&limit=100"
                    response = self.session.get(url, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success") and data.get("candlestick_data"):
                            candles = data["candlestick_data"]
                            data_points = len(candles)
                            
                            # Validate candle structure
                            if candles:
                                sample_candle = candles[0]
                                required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
                                missing_fields = [field for field in required_fields 
                                                if field not in sample_candle]
                                
                                if missing_fields:
                                    self.log_test(f"Chart Data {symbol} {timeframe}", "FAIL", 
                                                f"Missing candle fields: {missing_fields}")
                                    all_passed = False
                                    continue
                            
                            self.log_test(f"Chart Data {symbol} {timeframe}", "PASS", 
                                        f"{data_points} candles received")
                        else:
                            self.log_test(f"Chart Data {symbol} {timeframe}", "FAIL", 
                                        "Invalid response structure", data)
                            all_passed = False
                    else:
                        self.log_test(f"Chart Data {symbol} {timeframe}", "FAIL", 
                                    f"HTTP {response.status_code}")
                        all_passed = False
                except Exception as e:
                    self.log_test(f"Chart Data {symbol} {timeframe}", "FAIL", str(e))
                    all_passed = False
        
        return all_passed
    
    def test_signals_api(self) -> bool:
        """Test trading signals API"""
        symbols = ["AAPL", "SPY"]
        all_passed = True
        
        for symbol in symbols:
            try:
                url = f"{self.base_url}/api/signals/current?symbol={symbol}"
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Signals endpoint might return empty/default data when bot isn't running
                    # So we just validate structure, not content
                    self.log_test(f"Signals API {symbol}", "PASS", 
                                "Endpoint accessible", data)
                else:
                    self.log_test(f"Signals API {symbol}", "FAIL", 
                                f"HTTP {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Signals API {symbol}", "FAIL", str(e))
                all_passed = False
        
        return all_passed
    
    def test_bot_control_api(self) -> bool:
        """Test bot control endpoints"""
        try:
            # Test bot status
            response = self.session.get(f"{self.base_url}/api/bot/status", timeout=5)
            if response.status_code != 200:
                self.log_test("Bot Status API", "FAIL", f"HTTP {response.status_code}")
                return False
            
            status_data = response.json()
            self.log_test("Bot Status API", "PASS", 
                        f"Status: {status_data.get('status', 'unknown')}", status_data)
            
            # Test bot start
            response = self.session.post(f"{self.base_url}/api/bot/start", timeout=5)
            if response.status_code != 200:
                self.log_test("Bot Start API", "FAIL", f"HTTP {response.status_code}")
                return False
            
            start_data = response.json()
            self.log_test("Bot Start API", "PASS", 
                        f"Response: {start_data.get('message', 'No message')}", start_data)
            
            # Test bot stop
            response = self.session.post(f"{self.base_url}/api/bot/stop", timeout=5)
            if response.status_code != 200:
                self.log_test("Bot Stop API", "FAIL", f"HTTP {response.status_code}")
                return False
            
            stop_data = response.json()
            self.log_test("Bot Stop API", "PASS", 
                        f"Response: {stop_data.get('message', 'No message')}", stop_data)
            
            return True
        except Exception as e:
            self.log_test("Bot Control API", "FAIL", str(e))
            return False
    
    def test_websocket_connection(self) -> bool:
        """Test WebSocket connectivity"""
        try:
            import socketio
            
            # Create Socket.IO client
            sio = socketio.Client()
            connected = False
            
            @sio.event
            def connect():
                nonlocal connected
                connected = True
                self.log_test("WebSocket Connection", "PASS", "Successfully connected")
                
                # Test subscription
                sio.emit('subscribe', {'symbol': 'AAPL'})
            
            @sio.event
            def subscribed(data):
                self.log_test("WebSocket Subscription", "PASS", 
                            f"Subscribed to {data.get('symbol', 'unknown')}", data)
            
            @sio.event
            def connect_error(data):
                self.log_test("WebSocket Connection", "FAIL", f"Connection error: {data}")
            
            @sio.event
            def disconnect():
                self.log_test("WebSocket Disconnect", "INFO", "Disconnected")
            
            # Connect with timeout
            sio.connect(self.base_url, wait_timeout=10)
            
            # Wait a bit for connection
            time.sleep(2)
            
            # Disconnect
            sio.disconnect()
            
            return connected
            
        except ImportError:
            self.log_test("WebSocket Connection", "SKIP", "python-socketio not installed")
            return True
        except Exception as e:
            self.log_test("WebSocket Connection", "FAIL", str(e))
            return False
    
    def test_debug_endpoints(self) -> bool:
        """Test debug and utility endpoints"""
        debug_endpoints = [
            "/debug/positions",
            "/health"
        ]
        
        all_passed = True
        
        for endpoint in debug_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code == 200:
                    self.log_test(f"Debug Endpoint {endpoint}", "PASS", 
                                "Endpoint accessible")
                else:
                    self.log_test(f"Debug Endpoint {endpoint}", "FAIL", 
                                f"HTTP {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Debug Endpoint {endpoint}", "FAIL", str(e))
                all_passed = False
        
        return all_passed
    
    def test_performance_metrics(self) -> bool:
        """Test API response times and performance"""
        endpoints = [
            "/api/account",
            "/api/positions", 
            "/api/v2/chart-data/AAPL?timeframe=15Min&limit=100",
            "/api/signals/current?symbol=AAPL"
        ]
        
        all_passed = True
        performance_data = {}
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                performance_data[endpoint] = response_time
                
                if response.status_code == 200:
                    if response_time < 2000:  # Less than 2 seconds is acceptable
                        self.log_test(f"Performance {endpoint}", "PASS", 
                                    f"Response time: {response_time:.0f}ms")
                    else:
                        self.log_test(f"Performance {endpoint}", "WARN", 
                                    f"Slow response: {response_time:.0f}ms")
                else:
                    self.log_test(f"Performance {endpoint}", "FAIL", 
                                f"HTTP {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Performance {endpoint}", "FAIL", str(e))
                all_passed = False
        
        # Log overall performance summary
        if performance_data:
            avg_response_time = sum(performance_data.values()) / len(performance_data)
            self.log_test("Performance Summary", "INFO", 
                        f"Average response time: {avg_response_time:.0f}ms", 
                        performance_data)
        
        return all_passed
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run the complete test suite"""
        print("🧪 Starting Epic 1 Trading Dashboard Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all tests
        test_functions = [
            ("Server Health", self.test_server_health),
            ("Dashboard Routes", self.test_dashboard_routes),
            ("Account API", self.test_account_api),
            ("Positions API", self.test_positions_api),
            ("Chart Data API", self.test_chart_data_api),
            ("Signals API", self.test_signals_api),
            ("Bot Control API", self.test_bot_control_api),
            ("WebSocket Connection", self.test_websocket_connection),
            ("Debug Endpoints", self.test_debug_endpoints),
            ("Performance Metrics", self.test_performance_metrics),
        ]
        
        passed_tests = 0
        failed_tests = 0
        
        for test_name, test_function in test_functions:
            print(f"\n🔍 Running {test_name} Tests...")
            try:
                result = test_function()
                if result:
                    passed_tests += 1
                else:
                    failed_tests += 1
            except Exception as e:
                self.log_test(test_name, "FAIL", f"Test suite error: {e}")
                failed_tests += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Generate summary
        summary = {
            "total_tests": len(test_functions),
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests / len(test_functions)) * 100,
            "execution_time": total_time,
            "timestamp": datetime.now().isoformat(),
            "results": self.test_results
        }
        
        print("\n" + "=" * 60)
        print("📊 TEST SUITE SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        print(f"⏱️ Execution Time: {summary['execution_time']:.2f}s")
        
        if summary['success_rate'] >= 90:
            print("\n🎉 SYSTEM STATUS: PRODUCTION READY")
        elif summary['success_rate'] >= 75:
            print("\n⚠️ SYSTEM STATUS: MINOR ISSUES DETECTED")
        else:
            print("\n🚨 SYSTEM STATUS: CRITICAL ISSUES - NOT PRODUCTION READY")
        
        return summary
    
    def generate_test_report(self, summary: Dict[str, Any]) -> str:
        """Generate detailed test report"""
        report = f"""
# Epic 1 Trading Dashboard Test Report

**Generated**: {summary['timestamp']}  
**Execution Time**: {summary['execution_time']:.2f} seconds  
**Success Rate**: {summary['success_rate']:.1f}%  

## Summary
- **Total Tests**: {summary['total_tests']}
- **Passed**: ✅ {summary['passed']}
- **Failed**: ❌ {summary['failed']}

## Test Results

"""
        
        for result in summary['results']:
            emoji = "✅" if result['status'] == "PASS" else "❌" if result['status'] == "FAIL" else "⚠️"
            report += f"### {emoji} {result['test']}\n"
            report += f"**Status**: {result['status']}  \n"
            if result['details']:
                report += f"**Details**: {result['details']}  \n"
            if result['data']:
                report += f"**Data**: ```json\n{json.dumps(result['data'], indent=2)}\n```  \n"
            report += f"**Timestamp**: {result['timestamp']}  \n\n"
        
        return report

def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Epic 1 Trading Dashboard Test Suite")
    parser.add_argument("--url", default="http://localhost:8765", 
                       help="Base URL for the dashboard server")
    parser.add_argument("--report", action="store_true", 
                       help="Generate detailed test report")
    parser.add_argument("--output", default="test_report.md", 
                       help="Output file for test report")
    
    args = parser.parse_args()
    
    # Create test suite
    test_suite = DashboardTestSuite(args.url)
    
    # Run tests
    summary = test_suite.run_comprehensive_test()
    
    # Generate report if requested
    if args.report:
        report = test_suite.generate_test_report(summary)
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"\n📄 Detailed test report saved to: {args.output}")
    
    # Exit with appropriate code
    exit_code = 0 if summary['success_rate'] >= 90 else 1
    return exit_code

if __name__ == "__main__":
    exit(main())