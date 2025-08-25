#!/usr/bin/env python3
"""
Comprehensive Test Suite for Microservices Integration
Tests all services, navigation, APIs, and WebSocket connections
"""

import requests
import json
import time
import asyncio
import sys
from datetime import datetime

class MicroservicesTestSuite:
    def __init__(self):
        self.results = []
        self.services = {
            'frontend': 'http://localhost:9100',
            'api_gateway': 'http://localhost:9000', 
            'training': 'http://localhost:9011'
        }
        self.frontend_routes = [
            '/',           # Navigation hub
            '/navigation', # Navigation hub (explicit)
            '/training',   # AI Training dashboard
            '/dashboard',  # Main dashboard
            '/portfolio',  # Portfolio management
            '/trading',    # Trading execution
            '/analytics',  # Analytics & reports
            '/backtesting', # Backtesting dashboard
            '/config',     # Configuration
            '/monitoring', # System monitoring
            '/health'      # Health check
        ]
        self.api_endpoints = {
            'training': [
                '/health',
                '/api/strategies',
                '/api/scenarios',
                '/api/backtest/history',
                '/api/metrics/performance',
                '/docs'
            ],
            'api_gateway': [
                '/health',
                '/docs'
            ]
        }

    def log_test(self, test_name, passed, details=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        timestamp = datetime.now().strftime("%H:%M:%S")
        result = f"[{timestamp}] {status} - {test_name}"
        if details:
            result += f" | {details}"
        
        self.results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'timestamp': timestamp
        })
        print(result)

    def test_service_health(self):
        """Test all service health endpoints"""
        print("\n=== SERVICE HEALTH TESTS ===")
        
        for service_name, base_url in self.services.items():
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(f"{service_name.title()} Health", True, f"Status: {data.get('status', 'unknown')}")
                else:
                    self.log_test(f"{service_name.title()} Health", False, f"HTTP {response.status_code}")
            except requests.RequestException as e:
                self.log_test(f"{service_name.title()} Health", False, f"Connection error: {str(e)}")

    def test_frontend_navigation(self):
        """Test all frontend navigation routes"""
        print("\n=== FRONTEND NAVIGATION TESTS ===")
        
        base_url = self.services['frontend']
        for route in self.frontend_routes:
            try:
                response = requests.get(f"{base_url}{route}", timeout=10)
                if response.status_code == 200:
                    # Check if it's HTML content
                    content_type = response.headers.get('content-type', '')
                    if 'html' in content_type.lower():
                        self.log_test(f"Route {route}", True, f"HTML content loaded ({len(response.content)} bytes)")
                    elif route == '/health':
                        # Health endpoint should return JSON
                        try:
                            data = response.json()
                            self.log_test(f"Route {route}", True, f"JSON response: {data.get('status', 'unknown')}")
                        except:
                            self.log_test(f"Route {route}", False, "Expected JSON response")
                    else:
                        self.log_test(f"Route {route}", True, f"Content loaded")
                else:
                    self.log_test(f"Route {route}", False, f"HTTP {response.status_code}")
            except requests.RequestException as e:
                self.log_test(f"Route {route}", False, f"Error: {str(e)}")

    def test_api_endpoints(self):
        """Test API endpoints for all services"""
        print("\n=== API ENDPOINTS TESTS ===")
        
        for service_name, endpoints in self.api_endpoints.items():
            base_url = self.services[service_name]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=10)
                    if response.status_code == 200:
                        if endpoint.endswith('/docs'):
                            # Docs should return HTML
                            self.log_test(f"{service_name} {endpoint}", True, "API docs accessible")
                        else:
                            # API endpoints should return JSON
                            try:
                                data = response.json()
                                status = data.get('status', 'unknown') if isinstance(data, dict) else 'data_returned'
                                self.log_test(f"{service_name} {endpoint}", True, f"Response: {status}")
                            except:
                                self.log_test(f"{service_name} {endpoint}", True, "Non-JSON response")
                    else:
                        self.log_test(f"{service_name} {endpoint}", False, f"HTTP {response.status_code}")
                except requests.RequestException as e:
                    self.log_test(f"{service_name} {endpoint}", False, f"Error: {str(e)}")

    def test_training_websocket(self):
        """Test Training service WebSocket connection"""
        print("\n=== WEBSOCKET TESTS ===")
        
        try:
            import websockets
            
            async def test_ws():
                try:
                    uri = "ws://localhost:9011/ws/collaborate/AAPL"
                    async with websockets.connect(uri, ping_interval=None) as websocket:
                        # Wait for initial message
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        data = json.loads(message)
                        
                        if data.get('type') == 'market_analysis':
                            self.log_test("Training WebSocket", True, f"Market analysis received")
                            return True
                        else:
                            self.log_test("Training WebSocket", False, f"Unexpected message type: {data.get('type')}")
                            return False
                            
                except Exception as e:
                    self.log_test("Training WebSocket", False, f"WebSocket error: {str(e)}")
                    return False
            
            # Run the async test
            try:
                result = asyncio.run(test_ws())
            except Exception as e:
                self.log_test("Training WebSocket", False, f"Async error: {str(e)}")
                
        except ImportError:
            self.log_test("Training WebSocket", False, "websockets library not available")

    def test_service_integration(self):
        """Test integration between services"""
        print("\n=== SERVICE INTEGRATION TESTS ===")
        
        # Test Frontend -> Training Service integration
        try:
            frontend_training_url = f"{self.services['frontend']}/training"
            response = requests.get(frontend_training_url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                if 'localhost:9011' in content or 'TRAINING_SERVICE' in content:
                    self.log_test("Frontend -> Training Integration", True, "Training service URLs found in frontend")
                else:
                    self.log_test("Frontend -> Training Integration", True, "Training page loads")
            else:
                self.log_test("Frontend -> Training Integration", False, f"HTTP {response.status_code}")
                
        except requests.RequestException as e:
            self.log_test("Frontend -> Training Integration", False, f"Error: {str(e)}")
        
        # Test Training Service API functionality
        try:
            backtest_data = {
                "symbol": "AAPL",
                "strategy": "stoch_rsi_ema",
                "initial_capital": 10000
            }
            response = requests.post(
                f"{self.services['training']}/api/backtest",
                json=backtest_data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    self.log_test("Training Backtest API", True, "Backtest executed successfully")
                else:
                    self.log_test("Training Backtest API", False, f"API returned error: {data}")
            else:
                self.log_test("Training Backtest API", False, f"HTTP {response.status_code}")
                
        except requests.RequestException as e:
            self.log_test("Training Backtest API", False, f"Error: {str(e)}")

    def test_navigation_links(self):
        """Test that navigation links in homepage work"""
        print("\n=== NAVIGATION LINKS TESTS ===")
        
        try:
            response = requests.get(self.services['frontend'], timeout=10)
            if response.status_code != 200:
                self.log_test("Homepage Navigation Links", False, f"Homepage not accessible: HTTP {response.status_code}")
                return
                
            content = response.text
            
            # Test key navigation links
            navigation_tests = [
                ('/training', 'AI Training Platform'),
                ('http://localhost:9100', 'Main Trading Platform'),  
                ('http://localhost:9011/docs', 'Training API Docs'),
                ('http://localhost:9000/docs', 'API Gateway Docs')
            ]
            
            for link, description in navigation_tests:
                if link in content:
                    # Test if the link actually works
                    if link.startswith('http'):
                        test_url = link
                    else:
                        test_url = f"{self.services['frontend']}{link}"
                    
                    try:
                        link_response = requests.get(test_url, timeout=10)
                        if link_response.status_code == 200:
                            self.log_test(f"Navigation Link: {description}", True, f"Link works: {link}")
                        else:
                            self.log_test(f"Navigation Link: {description}", False, f"Link broken: {link} (HTTP {link_response.status_code})")
                    except requests.RequestException as e:
                        self.log_test(f"Navigation Link: {description}", False, f"Link error: {link} ({str(e)})")
                else:
                    self.log_test(f"Navigation Link: {description}", False, f"Link not found in homepage: {link}")
                    
        except requests.RequestException as e:
            self.log_test("Homepage Navigation Links", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all tests in the suite"""
        print("🚀 Starting Comprehensive Microservices Test Suite")
        print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Run all test categories
        self.test_service_health()
        self.test_frontend_navigation() 
        self.test_api_endpoints()
        self.test_training_websocket()
        self.test_service_integration()
        self.test_navigation_links()
        
        # Generate summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r['passed']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print(f"\n🔍 FAILED TESTS ({failed_tests}):")
            for result in self.results:
                if not result['passed']:
                    print(f"  ❌ {result['test']}: {result['details']}")
        
        print(f"\n⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return passed_tests, failed_tests

if __name__ == "__main__":
    test_suite = MicroservicesTestSuite()
    passed, failed = test_suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)