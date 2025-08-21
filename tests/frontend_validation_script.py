#!/usr/bin/env python3
"""
Frontend Validation Script
Tests all API endpoints and validates data structure for frontend compatibility.
"""

import requests
import json
import sys
from datetime import datetime

class FrontendValidator:
    def __init__(self, base_url="http://localhost:8765"):
        self.base_url = base_url
        self.test_results = []
        
    def log_test(self, test_name, passed, message, data=None):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    
    def test_api_endpoint(self, endpoint, expected_fields=None):
        """Test an API endpoint and validate response structure"""
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
            data = response.json()
            
            if response.status_code != 200:
                self.log_test(f"API {endpoint}", False, f"HTTP {response.status_code}")
                return None
                
            if not data.get('success', False):
                self.log_test(f"API {endpoint}", False, f"API returned success: false - {data.get('error', 'Unknown error')}")
                return None
                
            if expected_fields:
                missing_fields = [field for field in expected_fields if field not in data]
                if missing_fields:
                    self.log_test(f"API {endpoint}", False, f"Missing fields: {missing_fields}")
                    return None
                    
            self.log_test(f"API {endpoint}", True, f"Response valid with {len(data)} fields")
            return data
            
        except requests.exceptions.RequestException as e:
            self.log_test(f"API {endpoint}", False, f"Request failed: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            self.log_test(f"API {endpoint}", False, f"Invalid JSON response: {str(e)}")
            return None
    
    def validate_account_data(self, data):
        """Validate account data structure for frontend compatibility"""
        required_fields = ['balance', 'buying_power', 'cash']
        frontend_fields = ['equity', 'unrealized_pl', 'day_pl', 'total_pl']
        
        # Check required fields
        missing_required = [field for field in required_fields if field not in data]
        if missing_required:
            self.log_test("Account Data Structure", False, f"Missing required fields: {missing_required}")
            return False
            
        # Check if numeric values are valid
        try:
            balance = float(data['balance'])
            buying_power = float(data['buying_power'])
            cash = float(data['cash'])
            
            if balance < 0 or buying_power < 0 or cash < 0:
                self.log_test("Account Data Values", False, "Negative account values detected")
                return False
                
        except (ValueError, TypeError) as e:
            self.log_test("Account Data Values", False, f"Invalid numeric values: {str(e)}")
            return False
            
        self.log_test("Account Data Structure", True, f"Valid account data: ${balance:,.2f} balance")
        return True
    
    def validate_positions_data(self, data):
        """Validate positions data structure for frontend compatibility"""
        if not isinstance(data.get('positions'), list):
            self.log_test("Positions Data Structure", False, "positions field is not a list")
            return False
            
        positions = data['positions']
        if len(positions) == 0:
            self.log_test("Positions Data Structure", True, "No positions (empty portfolio)")
            return True
            
        required_position_fields = ['symbol', 'qty', 'avg_entry_price', 'unrealized_pl', 'current_price']
        
        for i, position in enumerate(positions):
            missing_fields = [field for field in required_position_fields if field not in position]
            if missing_fields:
                self.log_test("Positions Data Structure", False, f"Position {i} missing fields: {missing_fields}")
                return False
                
            try:
                qty = int(position['qty'])
                avg_price = float(position['avg_entry_price'])
                current_price = float(position['current_price'])
                unrealized_pl = float(position['unrealized_pl'])
                
                if qty == 0:
                    self.log_test("Positions Data Values", False, f"Position {position['symbol']} has zero quantity")
                    return False
                    
            except (ValueError, TypeError) as e:
                self.log_test("Positions Data Values", False, f"Position {position.get('symbol', i)} invalid values: {str(e)}")
                return False
        
        total_pl = sum(float(p['unrealized_pl']) for p in positions)
        self.log_test("Positions Data Structure", True, f"Valid positions data: {len(positions)} positions, ${total_pl:,.2f} total P&L")
        return True
    
    def validate_signals_data(self, data):
        """Validate signals data structure"""
        if 'signals' not in data:
            self.log_test("Signals Data Structure", False, "Missing signals field")
            return False
            
        signals = data['signals']
        if not isinstance(signals, list):
            self.log_test("Signals Data Structure", False, "signals field is not a list")
            return False
            
        if len(signals) == 0:
            self.log_test("Signals Data Structure", True, f"No active signals - {data.get('message', 'Bot not running')}")
            return True
            
        # If there are signals, validate their structure
        for signal in signals:
            if 'signal' not in signal or 'timestamp' not in signal:
                self.log_test("Signals Data Structure", False, "Signal missing required fields")
                return False
                
        self.log_test("Signals Data Structure", True, f"Valid signals data: {len(signals)} signals")
        return True
    
    def run_comprehensive_tests(self):
        """Run all frontend validation tests"""
        print("🚀 Starting Frontend Validation Tests...")
        print("=" * 60)
        
        # Test server accessibility
        try:
            response = requests.get(self.base_url, timeout=5)
            self.log_test("Server Accessibility", True, f"Server responding on {self.base_url}")
        except:
            self.log_test("Server Accessibility", False, f"Cannot connect to {self.base_url}")
            return self.generate_report()
        
        # Test account endpoint
        account_data = self.test_api_endpoint('/api/account', ['success', 'balance', 'buying_power'])
        if account_data:
            self.validate_account_data(account_data)
        
        # Test positions endpoint
        positions_data = self.test_api_endpoint('/api/positions', ['success', 'positions'])
        if positions_data:
            self.validate_positions_data(positions_data)
        
        # Test signals endpoint
        signals_data = self.test_api_endpoint('/api/signals/current?symbol=AAPL', ['success', 'signals'])
        if signals_data:
            self.validate_signals_data(signals_data)
        
        # Test chart data endpoint
        chart_data = self.test_api_endpoint('/api/v2/chart-data/AAPL?timeframe=15Min&limit=100')
        if chart_data:
            if 'candlestick_data' in chart_data and isinstance(chart_data['candlestick_data'], list):
                self.log_test("Chart Data Structure", True, f"Valid chart data: {len(chart_data['candlestick_data'])} bars")
            else:
                self.log_test("Chart Data Structure", False, "Invalid or missing candlestick_data")
        
        # Test market status endpoint
        market_data = self.test_api_endpoint('/api/market_status')
        if market_data:
            if 'is_open' in market_data:
                self.log_test("Market Status Structure", True, f"Market is {'open' if market_data['is_open'] else 'closed'}")
            else:
                self.log_test("Market Status Structure", False, "Missing is_open field")
        
        return self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 60)
        print("📊 VALIDATION REPORT")
        print("=" * 60)
        
        passed = len([r for r in self.test_results if r['passed']])
        failed = len([r for r in self.test_results if not r['passed']])
        total = len(self.test_results)
        
        print(f"✅ Tests Passed: {passed}")
        print(f"❌ Tests Failed: {failed}")
        print(f"📈 Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n🎯 FRONTEND COMPATIBILITY:")
        
        # Check if the main data issues are resolved
        account_passed = any(r['test'].startswith('Account') and r['passed'] for r in self.test_results)
        positions_passed = any(r['test'].startswith('Positions') and r['passed'] for r in self.test_results)
        
        if account_passed and positions_passed:
            print("✅ Frontend data binding issues appear to be resolved")
            print("✅ Account and positions data should display correctly")
        else:
            print("❌ Frontend data binding issues still present")
            print("❌ Dashboard may not display data correctly")
        
        # Save detailed report
        report_file = '/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot/tests/validation_report.json'
        try:
            with open(report_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'summary': {'passed': passed, 'failed': failed, 'total': total},
                    'results': self.test_results
                }, f, indent=2)
            print(f"\n📁 Detailed report saved to: {report_file}")
        except Exception as e:
            print(f"\n⚠️ Could not save report: {e}")
        
        return passed == total

if __name__ == "__main__":
    validator = FrontendValidator()
    success = validator.run_comprehensive_tests()
    
    sys.exit(0 if success else 1)