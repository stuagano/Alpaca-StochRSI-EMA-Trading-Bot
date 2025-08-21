#!/usr/bin/env python3
"""
Chart Fix Validation Script
Tests all aspects of the TradingView Lightweight Charts integration fix
"""

import requests
import json
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChartFixValidator:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.test_results = []
        
    def log_test(self, test_name, success, message, details=None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} - {test_name}: {message}")
        if details:
            logger.debug(f"Details: {json.dumps(details, indent=2)}")
    
    def test_server_health(self):
        """Test if the Flask server is running"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Server Health", True, "Flask server is running", data)
                return True
            else:
                self.log_test("Server Health", False, f"Server returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_test("Server Health", False, f"Cannot connect to server: {e}")
            return False
    
    def test_chart_endpoints(self):
        """Test various chart data endpoints"""
        endpoints = [
            "/api/chart-test/AAPL",
            "/api/v2/chart-data/AAPL?timeframe=15Min&limit=50",
            "/api/chart/AAPL?timeframe=15Min&limit=50",
            "/api/chart-status"
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success', False):
                        # Check if we have chart data
                        data_count = 0
                        if 'data' in data:
                            data_count = len(data['data']) if isinstance(data['data'], list) else 1
                        elif 'candlestick_data' in data:
                            data_count = len(data['candlestick_data'])
                        
                        self.log_test(
                            f"Endpoint: {endpoint}", 
                            True, 
                            f"Returned {data_count} data points",
                            {'url': url, 'data_fields': list(data.keys())}
                        )
                    else:
                        self.log_test(
                            f"Endpoint: {endpoint}", 
                            False, 
                            f"API returned success=false: {data.get('error', 'Unknown error')}"
                        )
                else:
                    self.log_test(
                        f"Endpoint: {endpoint}", 
                        False, 
                        f"HTTP {response.status_code}: {response.text[:200]}"
                    )
            except requests.exceptions.RequestException as e:
                self.log_test(f"Endpoint: {endpoint}", False, f"Request failed: {e}")
    
    def test_data_format(self):
        """Test that chart data is in correct format for TradingView"""
        try:
            response = requests.get(f"{self.base_url}/api/chart-test/AAPL", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    chart_data = data['data']
                    if len(chart_data) > 0:
                        first_candle = chart_data[0]
                        required_fields = ['time', 'open', 'high', 'low', 'close']
                        
                        # Check all required fields exist
                        missing_fields = [field for field in required_fields if field not in first_candle]
                        if not missing_fields:
                            # Validate data types
                            valid_types = (
                                isinstance(first_candle['time'], int) and
                                isinstance(first_candle['open'], (int, float)) and
                                isinstance(first_candle['high'], (int, float)) and
                                isinstance(first_candle['low'], (int, float)) and
                                isinstance(first_candle['close'], (int, float))
                            )
                            
                            if valid_types:
                                # Check OHLC logic
                                valid_ohlc = (
                                    first_candle['high'] >= max(first_candle['open'], first_candle['close']) and
                                    first_candle['low'] <= min(first_candle['open'], first_candle['close'])
                                )
                                
                                if valid_ohlc:
                                    self.log_test(
                                        "Data Format Validation", 
                                        True, 
                                        f"Data format is correct for TradingView",
                                        {'sample_candle': first_candle, 'total_candles': len(chart_data)}
                                    )
                                else:
                                    self.log_test(
                                        "Data Format Validation", 
                                        False, 
                                        "OHLC validation failed - high/low inconsistency"
                                    )
                            else:
                                self.log_test(
                                    "Data Format Validation", 
                                    False, 
                                    "Invalid data types in candle data"
                                )
                        else:
                            self.log_test(
                                "Data Format Validation", 
                                False, 
                                f"Missing required fields: {missing_fields}"
                            )
                    else:
                        self.log_test("Data Format Validation", False, "No chart data returned")
                else:
                    self.log_test("Data Format Validation", False, "Invalid response format")
            else:
                self.log_test("Data Format Validation", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Data Format Validation", False, f"Exception: {e}")
    
    def test_timeframe_support(self):
        """Test different timeframes"""
        timeframes = ['1Min', '5Min', '15Min', '30Min', '1Hour']
        
        for timeframe in timeframes:
            try:
                url = f"{self.base_url}/api/chart-test/AAPL?timeframe={timeframe}&limit=10"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and len(data.get('data', [])) > 0:
                        self.log_test(
                            f"Timeframe: {timeframe}", 
                            True, 
                            f"Returned {len(data['data'])} candles"
                        )
                    else:
                        self.log_test(f"Timeframe: {timeframe}", False, "No data returned")
                else:
                    self.log_test(f"Timeframe: {timeframe}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test(f"Timeframe: {timeframe}", False, f"Exception: {e}")
    
    def test_multiple_symbols(self):
        """Test chart data for multiple symbols"""
        symbols = ['AAPL', 'SPY', 'QQQ', 'TSLA']
        
        for symbol in symbols:
            try:
                url = f"{self.base_url}/api/chart-test/{symbol}?limit=5"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and len(data.get('data', [])) > 0:
                        # Check that prices are reasonable for the symbol
                        first_candle = data['data'][0]
                        price = first_candle['close']
                        
                        # Very basic price sanity check
                        if 1 <= price <= 10000:
                            self.log_test(
                                f"Symbol: {symbol}", 
                                True, 
                                f"Valid price data (close: ${price})"
                            )
                        else:
                            self.log_test(
                                f"Symbol: {symbol}", 
                                False, 
                                f"Price seems unrealistic: ${price}"
                            )
                    else:
                        self.log_test(f"Symbol: {symbol}", False, "No data returned")
                else:
                    self.log_test(f"Symbol: {symbol}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test(f"Symbol: {symbol}", False, f"Exception: {e}")
    
    def generate_html_report(self):
        """Generate an HTML report of test results"""
        passed_tests = sum(1 for test in self.test_results if test['success'])
        total_tests = len(self.test_results)
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Chart Fix Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .pass-rate {{ font-size: 2rem; font-weight: bold; color: {"#28a745" if pass_rate >= 80 else "#ffc107" if pass_rate >= 60 else "#dc3545"}; }}
        .test-result {{ margin: 10px 0; padding: 10px; border-left: 4px solid {"#28a745" if pass_rate >= 80 else "#dc3545"}; background: #f8f9fa; }}
        .pass {{ border-left-color: #28a745; }}
        .fail {{ border-left-color: #dc3545; }}
        .details {{ margin-top: 10px; padding: 10px; background: #e9ecef; font-family: monospace; font-size: 0.8rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 Chart Fix Validation Report</h1>
            <div class="pass-rate">{pass_rate:.1f}% Tests Passed</div>
            <p>{passed_tests} out of {total_tests} tests passed</p>
            <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
        
        <div class="test-results">
        """
        
        for test in self.test_results:
            status_class = "pass" if test['success'] else "fail"
            status_icon = "✅" if test['success'] else "❌"
            
            html += f"""
            <div class="test-result {status_class}">
                <strong>{status_icon} {test['test']}</strong><br>
                {test['message']}
                <small style="color: #666;"> - {test['timestamp']}</small>
            """
            
            if test['details']:
                html += f"""
                <div class="details">
                    {json.dumps(test['details'], indent=2)}
                </div>
                """
            
            html += "</div>"
        
        html += """
        </div>
    </div>
</body>
</html>
        """
        
        with open('/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot/chart_validation_report.html', 'w') as f:
            f.write(html)
        
        logger.info(f"📊 HTML report generated: chart_validation_report.html")
    
    def run_all_tests(self):
        """Run all validation tests"""
        logger.info("🚀 Starting Chart Fix Validation Tests")
        logger.info(f"🎯 Target URL: {self.base_url}")
        
        # Test server health first
        if not self.test_server_health():
            logger.error("❌ Server is not running. Please start the Flask app first.")
            return False
        
        # Run all tests
        self.test_chart_endpoints()
        self.test_data_format()
        self.test_timeframe_support()
        self.test_multiple_symbols()
        
        # Generate report
        self.generate_html_report()
        
        # Summary
        passed = sum(1 for test in self.test_results if test['success'])
        total = len(self.test_results)
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        logger.info(f"📋 Test Summary: {passed}/{total} tests passed ({pass_rate:.1f}%)")
        
        if pass_rate >= 80:
            logger.info("🎉 Chart fix validation PASSED!")
            return True
        else:
            logger.warning("⚠️  Chart fix validation needs attention")
            return False

def main():
    """Main validation function"""
    validator = ChartFixValidator()
    success = validator.run_all_tests()
    
    if success:
        print("\n🎉 CHART FIX VALIDATION SUCCESSFUL!")
        print("✅ TradingView Lightweight Charts integration is working properly")
        print("✅ Professional dashboard should now display candlestick charts")
        print("✅ Multiple chart data endpoints are available")
        print("\n📋 Next steps:")
        print("1. Open http://localhost:5000/professional_trading_dashboard.html")
        print("2. Check that candlestick chart displays properly")
        print("3. Test different timeframes and symbols")
    else:
        print("\n⚠️  VALIDATION FOUND ISSUES")
        print("❌ Some tests failed - check the report for details")
        print("📋 Check chart_validation_report.html for detailed results")
    
    return success

if __name__ == "__main__":
    main()