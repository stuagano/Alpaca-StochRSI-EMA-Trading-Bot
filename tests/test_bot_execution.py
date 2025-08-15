#!/usr/bin/env python
"""
Trading Bot Execution Test Script
This script tests the trading bot execution and captures output for feedback loop
"""

import sys
import os
import json
import time
import logging
from datetime import datetime
import subprocess
import threading

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TradingBotTester:
    def __init__(self):
        self.setup_logging()
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'errors': [],
            'warnings': [],
            'performance_metrics': {}
        }
    
    def setup_logging(self):
        """Setup logging for test execution"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('tests/test_execution.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def test_imports(self):
        """Test if all required modules can be imported"""
        self.logger.info("Testing module imports...")
        test_result = {'name': 'module_imports', 'status': 'pending', 'details': []}
        
        modules_to_test = [
            'pandas', 'numpy', 'alpaca_trade_api', 
            'ta', 'flask', 'pydantic', 'yaml'
        ]
        
        for module in modules_to_test:
            try:
                __import__(module)
                test_result['details'].append(f"✓ {module} imported successfully")
            except ImportError as e:
                test_result['details'].append(f"✗ {module} failed: {str(e)}")
                self.results['errors'].append(f"Import error: {module} - {str(e)}")
        
        # Try importing pandas_ta specifically
        try:
            import pandas_ta
            test_result['details'].append("✓ pandas_ta imported successfully")
        except ImportError:
            self.logger.warning("pandas_ta not installed, installing now...")
            subprocess.run([sys.executable, "-m", "pip", "install", "pandas-ta"], 
                         capture_output=True, text=True)
            try:
                import pandas_ta
                test_result['details'].append("✓ pandas_ta installed and imported")
            except:
                test_result['details'].append("✗ pandas_ta installation failed")
        
        test_result['status'] = 'passed' if not any('✗' in d for d in test_result['details']) else 'failed'
        self.results['tests'].append(test_result)
        return test_result['status'] == 'passed'
    
    def test_configuration(self):
        """Test configuration loading"""
        self.logger.info("Testing configuration...")
        test_result = {'name': 'configuration', 'status': 'pending', 'details': []}
        
        try:
            # Check if config files exist
            config_files = [
                'config/config.yml',
                'AUTH/authAlpaca.txt',
                'AUTH/Tickers.txt'
            ]
            
            for config_file in config_files:
                if os.path.exists(config_file):
                    test_result['details'].append(f"✓ {config_file} exists")
                else:
                    test_result['details'].append(f"✗ {config_file} missing")
            
            # Try loading config
            from config.config import config
            test_result['details'].append(f"✓ Config loaded: strategy={config.strategy}")
            test_result['status'] = 'passed'
            
        except Exception as e:
            test_result['status'] = 'failed'
            test_result['details'].append(f"✗ Config loading failed: {str(e)}")
            self.results['errors'].append(f"Config error: {str(e)}")
        
        self.results['tests'].append(test_result)
        return test_result['status'] == 'passed'
    
    def test_api_connection(self):
        """Test Alpaca API connection"""
        self.logger.info("Testing API connection...")
        test_result = {'name': 'api_connection', 'status': 'pending', 'details': []}
        
        try:
            import json
            with open('AUTH/authAlpaca.txt', 'r') as f:
                auth_data = json.load(f)
            
            import alpaca_trade_api as tradeapi
            api = tradeapi.REST(
                auth_data['APCA-API-KEY-ID'],
                auth_data['APCA-API-SECRET-KEY'],
                auth_data['BASE-URL']
            )
            
            # Test account access
            account = api.get_account()
            test_result['details'].append(f"✓ API connected: Account status={account.status}")
            test_result['details'].append(f"  Buying power: ${account.buying_power}")
            test_result['details'].append(f"  Paper trading: {'paper' in auth_data['BASE-URL']}")
            test_result['status'] = 'passed'
            
        except Exception as e:
            test_result['status'] = 'failed'
            test_result['details'].append(f"✗ API connection failed: {str(e)}")
            self.results['errors'].append(f"API error: {str(e)}")
        
        self.results['tests'].append(test_result)
        return test_result['status'] == 'passed'
    
    def run_bot_with_timeout(self, timeout=30):
        """Run the trading bot with a timeout"""
        self.logger.info(f"Running trading bot for {timeout} seconds...")
        test_result = {'name': 'bot_execution', 'status': 'pending', 'details': [], 'output': []}
        
        def run_bot():
            try:
                process = subprocess.Popen(
                    [sys.executable, 'main.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                start_time = time.time()
                output_lines = []
                
                while time.time() - start_time < timeout:
                    line = process.stdout.readline()
                    if line:
                        output_lines.append(line.strip())
                        self.logger.info(f"BOT: {line.strip()}")
                    
                    # Check if process has terminated
                    if process.poll() is not None:
                        break
                    
                    time.sleep(0.1)
                
                # Terminate the process if still running
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                
                # Get any remaining output
                stdout, stderr = process.communicate(timeout=2)
                if stdout:
                    output_lines.extend(stdout.strip().split('\n'))
                if stderr:
                    self.results['errors'].append(f"Bot stderr: {stderr}")
                
                test_result['output'] = output_lines[-50:]  # Keep last 50 lines
                test_result['details'].append(f"✓ Bot ran for {time.time() - start_time:.1f} seconds")
                test_result['status'] = 'passed'
                
            except Exception as e:
                test_result['status'] = 'failed'
                test_result['details'].append(f"✗ Bot execution error: {str(e)}")
                self.results['errors'].append(f"Execution error: {str(e)}")
        
        run_bot()
        self.results['tests'].append(test_result)
        return test_result
    
    def generate_report(self):
        """Generate test report"""
        self.logger.info("Generating test report...")
        
        # Calculate statistics
        total_tests = len(self.results['tests'])
        passed_tests = sum(1 for t in self.results['tests'] if t['status'] == 'passed')
        failed_tests = sum(1 for t in self.results['tests'] if t['status'] == 'failed')
        
        report = f"""
{'='*60}
TRADING BOT TEST EXECUTION REPORT
{'='*60}
Timestamp: {self.results['timestamp']}
Total Tests: {total_tests}
Passed: {passed_tests}
Failed: {failed_tests}
Success Rate: {(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%

TEST RESULTS:
{'='*60}
"""
        
        for test in self.results['tests']:
            report += f"\n{test['name'].upper()} - {test['status'].upper()}\n"
            for detail in test.get('details', []):
                report += f"  {detail}\n"
            
            if 'output' in test and test['output']:
                report += "\n  Last Output Lines:\n"
                for line in test['output'][-10:]:
                    report += f"    {line}\n"
        
        if self.results['errors']:
            report += f"\n{'='*60}\nERRORS:\n"
            for error in self.results['errors']:
                report += f"  • {error}\n"
        
        if self.results['warnings']:
            report += f"\n{'='*60}\nWARNINGS:\n"
            for warning in self.results['warnings']:
                report += f"  • {warning}\n"
        
        report += f"\n{'='*60}\n"
        
        # Save report
        report_file = f"tests/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        # Save JSON results
        json_file = f"tests/test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        self.logger.info(f"Report saved to {report_file}")
        self.logger.info(f"JSON results saved to {json_file}")
        
        return report

def main():
    """Main test execution"""
    tester = TradingBotTester()
    
    print("\n" + "="*60)
    print("STARTING TRADING BOT TEST SUITE")
    print("="*60 + "\n")
    
    # Run tests
    if tester.test_imports():
        print("✓ Module imports successful")
    else:
        print("✗ Module import issues detected")
    
    if tester.test_configuration():
        print("✓ Configuration loaded successfully")
    else:
        print("✗ Configuration issues detected")
    
    if tester.test_api_connection():
        print("✓ API connection successful")
    else:
        print("✗ API connection failed")
    
    # Run the bot
    print("\nRunning trading bot...")
    bot_result = tester.run_bot_with_timeout(timeout=20)
    
    # Generate and print report
    report = tester.generate_report()
    print(report)
    
    return 0 if all(t['status'] == 'passed' for t in tester.results['tests']) else 1

if __name__ == "__main__":
    sys.exit(main())