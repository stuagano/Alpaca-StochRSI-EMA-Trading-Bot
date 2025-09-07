#!/usr/bin/env python3
"""
Comprehensive test runner for the Alpaca Trading Bot
Runs both pytest (backend) and Playwright (frontend) tests with detailed reporting
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

class TestRunner:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'pytest': {'status': 'not_run', 'results': {}},
            'playwright': {'status': 'not_run', 'results': {}},
            'coverage': {'status': 'not_run', 'results': {}}
        }
    
    def check_dependencies(self):
        """Check if required testing dependencies are installed"""
        print("🔍 Checking test dependencies...")
        
        # Check pytest
        try:
            subprocess.run(['pytest', '--version'], capture_output=True, check=True)
            print("✅ pytest is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ pytest not found. Install with: pip install pytest pytest-asyncio pytest-cov")
            return False
        
        # Check playwright
        try:
            subprocess.run(['npx', 'playwright', '--version'], capture_output=True, check=True)
            print("✅ Playwright is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Playwright not found. Install with: cd tests/frontend && npm install @playwright/test")
            return False
        
        return True
    
    def run_pytest_tests(self):
        """Run backend API tests with pytest"""
        print("\n🧪 Running pytest (backend API tests)...")
        
        os.chdir(self.project_root)
        
        cmd = [
            'pytest',
            'tests/backend/',
            '-v',
            '--tb=short',
            '--cov=unified_trading_service_with_frontend',
            '--cov-report=html:tests/reports/coverage-html',
            '--cov-report=json:tests/reports/coverage.json',
            '--json-report',
            '--json-report-file=tests/reports/pytest-report.json'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            self.test_results['pytest']['status'] = 'completed'
            self.test_results['pytest']['exit_code'] = result.returncode
            self.test_results['pytest']['stdout'] = result.stdout
            self.test_results['pytest']['stderr'] = result.stderr
            
            if result.returncode == 0:
                print("✅ All pytest tests passed!")
            else:
                print(f"❌ Some pytest tests failed (exit code: {result.returncode})")
                
            # Parse pytest results if JSON report exists
            json_report_path = self.project_root / 'tests/reports/pytest-report.json'
            if json_report_path.exists():
                with open(json_report_path) as f:
                    pytest_data = json.load(f)
                    self.test_results['pytest']['results'] = {
                        'tests_collected': pytest_data.get('summary', {}).get('total', 0),
                        'tests_passed': pytest_data.get('summary', {}).get('passed', 0),
                        'tests_failed': pytest_data.get('summary', {}).get('failed', 0),
                        'tests_skipped': pytest_data.get('summary', {}).get('skipped', 0),
                        'duration': pytest_data.get('duration', 0)
                    }
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("❌ pytest tests timed out after 5 minutes")
            self.test_results['pytest']['status'] = 'timeout'
            return False
        except Exception as e:
            print(f"❌ Error running pytest: {e}")
            self.test_results['pytest']['status'] = 'error'
            self.test_results['pytest']['error'] = str(e)
            return False
    
    def run_playwright_tests(self):
        """Run frontend UI tests with Playwright"""
        print("\n🎭 Running Playwright (frontend UI tests)...")
        
        frontend_test_dir = self.project_root / 'tests/frontend'
        if not frontend_test_dir.exists():
            print("❌ Frontend test directory not found")
            return False
        
        os.chdir(frontend_test_dir)
        
        # Install playwright if needed
        try:
            subprocess.run(['npx', 'playwright', 'install'], check=True, timeout=120)
        except subprocess.TimeoutExpired:
            print("⚠️  Playwright install timed out, proceeding...")
        except Exception as e:
            print(f"⚠️  Playwright install warning: {e}")
        
        # Run tests
        cmd = ['npx', 'playwright', 'test', '--reporter=html,json']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            self.test_results['playwright']['status'] = 'completed'
            self.test_results['playwright']['exit_code'] = result.returncode
            self.test_results['playwright']['stdout'] = result.stdout
            self.test_results['playwright']['stderr'] = result.stderr
            
            if result.returncode == 0:
                print("✅ All Playwright tests passed!")
            else:
                print(f"❌ Some Playwright tests failed (exit code: {result.returncode})")
            
            # Parse Playwright results if JSON report exists
            json_report_path = frontend_test_dir / 'test-results.json'
            if json_report_path.exists():
                with open(json_report_path) as f:
                    playwright_data = json.load(f)
                    self.test_results['playwright']['results'] = {
                        'tests_total': len(playwright_data.get('tests', [])),
                        'tests_passed': len([t for t in playwright_data.get('tests', []) if t.get('status') == 'passed']),
                        'tests_failed': len([t for t in playwright_data.get('tests', []) if t.get('status') == 'failed']),
                        'duration': playwright_data.get('stats', {}).get('duration', 0)
                    }
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("❌ Playwright tests timed out after 10 minutes")
            self.test_results['playwright']['status'] = 'timeout'
            return False
        except Exception as e:
            print(f"❌ Error running Playwright: {e}")
            self.test_results['playwright']['status'] = 'error'
            self.test_results['playwright']['error'] = str(e)
            return False
    
    def check_service_status(self):
        """Check if the trading service is running"""
        print("\n🔍 Checking trading service status...")
        
        try:
            import requests
            response = requests.get('http://localhost:9100', timeout=5)
            if response.status_code == 200:
                print("✅ Trading service is running on port 9100")
                
                # Check API endpoint
                api_response = requests.get('http://localhost:9000/api/account', timeout=5)
                if api_response.status_code == 200:
                    print("✅ API endpoints are responding")
                else:
                    print(f"⚠️  API endpoints responding with status {api_response.status_code}")
                    
                return True
            else:
                print(f"⚠️  Trading service responded with status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException:
            print("❌ Trading service is not running")
            print("   Start it with: python unified_trading_service_with_frontend.py")
            return False
        except ImportError:
            print("⚠️  requests library not available for service check")
            return True  # Continue with tests anyway
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n📊 Generating test report...")
        
        # Create reports directory
        reports_dir = self.project_root / 'tests/reports'
        reports_dir.mkdir(exist_ok=True)
        
        # Save detailed results
        with open(reports_dir / 'test_summary.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        # Generate markdown report
        report_md = self.generate_markdown_report()
        with open(reports_dir / 'test_report.md', 'w') as f:
            f.write(report_md)
        
        print(f"📋 Test reports saved in: {reports_dir}")
        print(f"   - test_summary.json (detailed results)")
        print(f"   - test_report.md (summary report)")
        
        if (reports_dir / 'coverage-html/index.html').exists():
            print(f"   - coverage-html/index.html (code coverage)")
    
    def generate_markdown_report(self):
        """Generate markdown test report"""
        pytest_results = self.test_results['pytest'].get('results', {})
        playwright_results = self.test_results['playwright'].get('results', {})
        
        report = f"""# Trading Bot Test Report
        
Generated: {self.test_results['timestamp']}

## Summary

### Backend API Tests (pytest)
- Status: {self.test_results['pytest']['status']}
- Tests Collected: {pytest_results.get('tests_collected', 'N/A')}
- Tests Passed: {pytest_results.get('tests_passed', 'N/A')}
- Tests Failed: {pytest_results.get('tests_failed', 'N/A')}
- Tests Skipped: {pytest_results.get('tests_skipped', 'N/A')}
- Duration: {pytest_results.get('duration', 'N/A')}s

### Frontend UI Tests (Playwright)
- Status: {self.test_results['playwright']['status']}
- Tests Total: {playwright_results.get('tests_total', 'N/A')}
- Tests Passed: {playwright_results.get('tests_passed', 'N/A')}
- Tests Failed: {playwright_results.get('tests_failed', 'N/A')}
- Duration: {playwright_results.get('duration', 'N/A')}ms

## Test Coverage Areas

### Backend Tests
- ✅ API endpoint validation
- ✅ Order execution logic
- ✅ P&L calculations
- ✅ WebSocket functionality
- ✅ Error handling
- ✅ Data validation (no fake/demo data)
- ✅ Performance testing

### Frontend Tests  
- ✅ Crypto trading interface
- ✅ Portfolio and P&L display
- ✅ Market screener functionality
- ✅ WebSocket connection status
- ✅ Order placement controls
- ✅ Real-time data validation
- ✅ Responsive design
- ✅ Error handling

## Next Steps

1. Review any failed tests in the detailed logs
2. Check code coverage report for areas needing more tests
3. Update tests as new features are added
4. Run tests regularly in CI/CD pipeline

"""
        return report
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting comprehensive test suite for Alpaca Trading Bot")
        print("=" * 60)
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Check service status
        service_running = self.check_service_status()
        if not service_running:
            print("⚠️  Proceeding with tests anyway (service may start automatically)")
        
        # Create reports directory
        (self.project_root / 'tests/reports').mkdir(exist_ok=True)
        
        # Run tests
        pytest_success = self.run_pytest_tests()
        playwright_success = self.run_playwright_tests()
        
        # Generate report
        self.generate_report()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        if pytest_success:
            print("✅ Backend API tests: PASSED")
        else:
            print("❌ Backend API tests: FAILED")
        
        if playwright_success:
            print("✅ Frontend UI tests: PASSED")
        else:
            print("❌ Frontend UI tests: FAILED")
        
        overall_success = pytest_success and playwright_success
        
        if overall_success:
            print("\n🎉 All tests passed! Your trading bot is ready for production.")
        else:
            print("\n⚠️  Some tests failed. Review the reports for details.")
        
        print(f"\n📊 Detailed reports available in: tests/reports/")
        
        return overall_success

if __name__ == '__main__':
    runner = TestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)