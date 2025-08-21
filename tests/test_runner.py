#!/usr/bin/env python3
"""
Comprehensive test runner for the trading bot.
Provides different test execution modes and reporting.
"""

import os
import sys
import subprocess
import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class TestRunner:
    """Main test runner class."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests"
        self.reports_dir = self.test_dir / "reports"
        
        # Ensure reports directory exists
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def run_command(self, cmd: List[str], capture_output: bool = True) -> Dict:
        """Run a command and capture results."""
        start_time = time.time()
        
        try:
            if capture_output:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
            else:
                result = subprocess.run(cmd, cwd=self.project_root)
            
            duration = time.time() - start_time
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout if capture_output else '',
                'stderr': result.stderr if capture_output else '',
                'duration': duration
            }
        
        except Exception as e:
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'duration': time.time() - start_time
            }
    
    def run_unit_tests(self, verbose: bool = False) -> Dict:
        """Run unit tests."""
        print("🧪 Running unit tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "tests/unit/",
            "--cov=.",
            "--cov-report=xml:tests/reports/coverage-unit.xml",
            "--cov-report=html:tests/reports/htmlcov-unit",
            "--junit-xml=tests/reports/junit-unit.xml",
            "-m", "not slow and not network",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = self.run_command(cmd, capture_output=not verbose)
        
        if result['success']:
            print("✅ Unit tests passed")
        else:
            print("❌ Unit tests failed")
            if result['stderr']:
                print(f"Error: {result['stderr']}")
        
        return result
    
    def run_integration_tests(self, verbose: bool = False) -> Dict:
        """Run integration tests."""
        print("🔧 Running integration tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "tests/integration/",
            "--cov=.",
            "--cov-append",
            "--cov-report=xml:tests/reports/coverage-integration.xml",
            "--cov-report=html:tests/reports/htmlcov-integration",
            "--junit-xml=tests/reports/junit-integration.xml",
            "-m", "not slow and not network",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = self.run_command(cmd, capture_output=not verbose)
        
        if result['success']:
            print("✅ Integration tests passed")
        else:
            print("❌ Integration tests failed")
            if result['stderr']:
                print(f"Error: {result['stderr']}")
        
        return result
    
    def run_performance_tests(self, verbose: bool = False) -> Dict:
        """Run performance tests."""
        print("⚡ Running performance tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "tests/performance/",
            "--benchmark-only",
            "--benchmark-json=tests/reports/benchmark-results.json",
            "-m", "performance",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = self.run_command(cmd, capture_output=not verbose)
        
        if result['success']:
            print("✅ Performance tests passed")
        else:
            print("❌ Performance tests failed")
            if result['stderr']:
                print(f"Error: {result['stderr']}")
        
        return result
    
    def run_smoke_tests(self, verbose: bool = False) -> Dict:
        """Run smoke tests."""
        print("💨 Running smoke tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "tests/",
            "-m", "smoke",
            "--tb=short",
            "--maxfail=1"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = self.run_command(cmd, capture_output=not verbose)
        
        if result['success']:
            print("✅ Smoke tests passed")
        else:
            print("❌ Smoke tests failed")
            if result['stderr']:
                print(f"Error: {result['stderr']}")
        
        return result
    
    def run_security_tests(self, verbose: bool = False) -> Dict:
        """Run security tests."""
        print("🔒 Running security tests...")
        
        security_results = {}
        
        # Run bandit security scan
        print("  Running Bandit security scan...")
        bandit_cmd = [
            "bandit", "-r", ".", "-f", "json",
            "-o", "tests/reports/bandit-report.json"
        ]
        
        bandit_result = self.run_command(bandit_cmd)
        security_results['bandit'] = bandit_result
        
        # Run safety dependency check
        print("  Running Safety dependency check...")
        safety_cmd = [
            "safety", "check", "--json",
            "--output", "tests/reports/safety-report.json"
        ]
        
        safety_result = self.run_command(safety_cmd)
        security_results['safety'] = safety_result
        
        # Overall success if no critical issues
        overall_success = bandit_result['success'] and safety_result['success']
        
        if overall_success:
            print("✅ Security tests passed")
        else:
            print("⚠️  Security issues detected")
        
        return {
            'success': overall_success,
            'results': security_results,
            'duration': sum(r['duration'] for r in security_results.values())
        }
    
    def run_lint_checks(self, verbose: bool = False) -> Dict:
        """Run code quality checks."""
        print("🧹 Running code quality checks...")
        
        lint_results = {}
        
        # Run flake8
        print("  Running flake8...")
        flake8_cmd = ["flake8", ".", "--statistics"]
        lint_results['flake8'] = self.run_command(flake8_cmd)
        
        # Run black check
        print("  Running black check...")
        black_cmd = ["black", "--check", "--diff", "."]
        lint_results['black'] = self.run_command(black_cmd)
        
        # Run isort check
        print("  Running isort check...")
        isort_cmd = ["isort", "--check-only", "--diff", "."]
        lint_results['isort'] = self.run_command(isort_cmd)
        
        # Run mypy (allow failures)
        print("  Running mypy...")
        mypy_cmd = ["mypy", ".", "--ignore-missing-imports"]
        lint_results['mypy'] = self.run_command(mypy_cmd)
        
        # Calculate overall success (mypy failures allowed)
        critical_checks = ['flake8', 'black', 'isort']
        overall_success = all(lint_results[check]['success'] for check in critical_checks)
        
        if overall_success:
            print("✅ Code quality checks passed")
        else:
            print("❌ Code quality issues found")
        
        return {
            'success': overall_success,
            'results': lint_results,
            'duration': sum(r['duration'] for r in lint_results.values())
        }
    
    def create_test_fixtures(self) -> Dict:
        """Create test fixtures."""
        print("📁 Creating test fixtures...")
        
        try:
            # Create market data fixtures
            cmd = [
                "python", "-c",
                """
from tests.fixtures.market_data_fixtures import FixtureManager
from tests.fixtures.order_fixtures import create_csv_fixtures

# Create market data fixtures
manager = FixtureManager()
manager.create_all_standard_fixtures()

# Create order fixtures  
create_csv_fixtures()

print('Test fixtures created successfully')
                """
            ]
            
            result = self.run_command(cmd)
            
            if result['success']:
                print("✅ Test fixtures created")
            else:
                print("❌ Failed to create test fixtures")
                print(f"Error: {result['stderr']}")
            
            return result
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration': 0
            }
    
    def generate_coverage_report(self) -> Dict:
        """Generate combined coverage report."""
        print("📊 Generating coverage report...")
        
        try:
            # Combine coverage data
            combine_cmd = ["coverage", "combine"]
            combine_result = self.run_command(combine_cmd)
            
            # Generate HTML report
            html_cmd = [
                "coverage", "html", 
                "-d", "tests/reports/htmlcov-combined",
                "--title", "Trading Bot Combined Coverage Report"
            ]
            html_result = self.run_command(html_cmd)
            
            # Generate terminal report
            report_cmd = ["coverage", "report", "--show-missing"]
            report_result = self.run_command(report_cmd)
            
            # Save terminal report to file
            if report_result['success']:
                report_file = self.reports_dir / "coverage-report.txt"
                with open(report_file, 'w') as f:
                    f.write(report_result['stdout'])
            
            overall_success = combine_result['success'] and html_result['success']
            
            if overall_success:
                print("✅ Coverage report generated")
                print(f"📁 HTML report: {self.reports_dir}/htmlcov-combined/index.html")
            else:
                print("❌ Failed to generate coverage report")
            
            return {
                'success': overall_success,
                'duration': sum(r['duration'] for r in [combine_result, html_result, report_result])
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration': 0
            }
    
    def run_all_tests(self, 
                     include_performance: bool = False,
                     include_security: bool = True,
                     verbose: bool = False) -> Dict:
        """Run complete test suite."""
        print("🚀 Running complete test suite...")
        print("=" * 50)
        
        start_time = time.time()
        results = {}
        
        # Create fixtures first
        results['fixtures'] = self.create_test_fixtures()
        
        # Run lint checks
        results['lint'] = self.run_lint_checks(verbose)
        
        # Run smoke tests first
        results['smoke'] = self.run_smoke_tests(verbose)
        
        # Run unit tests
        results['unit'] = self.run_unit_tests(verbose)
        
        # Run integration tests
        results['integration'] = self.run_integration_tests(verbose)
        
        # Run performance tests if requested
        if include_performance:
            results['performance'] = self.run_performance_tests(verbose)
        
        # Run security tests if requested
        if include_security:
            results['security'] = self.run_security_tests(verbose)
        
        # Generate coverage report
        results['coverage'] = self.generate_coverage_report()
        
        total_duration = time.time() - start_time
        
        # Calculate overall success
        critical_tests = ['smoke', 'unit', 'integration', 'lint']
        overall_success = all(
            results.get(test, {}).get('success', False) 
            for test in critical_tests
        )
        
        # Generate summary
        print("\n" + "=" * 50)
        print("📈 TEST SUMMARY")
        print("=" * 50)
        
        for test_type, result in results.items():
            if isinstance(result, dict) and 'success' in result:
                status = "✅ PASS" if result['success'] else "❌ FAIL"
                duration = result.get('duration', 0)
                print(f"{test_type.upper():12} {status:8} ({duration:.2f}s)")
        
        print(f"\nTotal Duration: {total_duration:.2f}s")
        print(f"Overall Result: {'✅ SUCCESS' if overall_success else '❌ FAILURE'}")
        
        # Save results to file
        results_file = self.reports_dir / f"test-results-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'overall_success': overall_success,
                'total_duration': total_duration,
                'results': results
            }, f, indent=2)
        
        print(f"\n📁 Detailed results saved to: {results_file}")
        
        return {
            'success': overall_success,
            'results': results,
            'duration': total_duration
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Trading Bot Test Runner")
    
    parser.add_argument(
        '--mode', 
        choices=['all', 'unit', 'integration', 'performance', 'smoke', 'security', 'lint'],
        default='all',
        help='Test mode to run'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--no-performance',
        action='store_true',
        help='Skip performance tests in all mode'
    )
    
    parser.add_argument(
        '--no-security',
        action='store_true',
        help='Skip security tests in all mode'
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Run specific test mode
    if args.mode == 'all':
        result = runner.run_all_tests(
            include_performance=not args.no_performance,
            include_security=not args.no_security,
            verbose=args.verbose
        )
    elif args.mode == 'unit':
        result = runner.run_unit_tests(args.verbose)
    elif args.mode == 'integration':
        result = runner.run_integration_tests(args.verbose)
    elif args.mode == 'performance':
        result = runner.run_performance_tests(args.verbose)
    elif args.mode == 'smoke':
        result = runner.run_smoke_tests(args.verbose)
    elif args.mode == 'security':
        result = runner.run_security_tests(args.verbose)
    elif args.mode == 'lint':
        result = runner.run_lint_checks(args.verbose)
    
    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()