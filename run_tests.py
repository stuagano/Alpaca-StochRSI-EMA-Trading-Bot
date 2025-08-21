#!/usr/bin/env python3
"""
Epic 1 Trading System - Unified Test Runner
Consolidated test runner for all Epic 1 testing needs
"""

import subprocess
import sys
import os
import time
import json
import argparse
from datetime import datetime
from pathlib import Path

class TestRunner:
    """Advanced test runner with multiple execution modes."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.test_dir = self.base_dir / "tests"
        self.coverage_dir = self.base_dir / "htmlcov"
        
    def run_unit_tests(self, verbose=False, coverage=True):
        """Run unit tests only."""
        cmd = ["python", "-m", "pytest", "tests/", "-m", "unit"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=.", 
                "--cov-report=html",
                "--cov-report=term-missing"
            ])
        
        return self._execute_command(cmd)
    
    def run_integration_tests(self, verbose=False):
        """Run integration tests only."""
        cmd = ["python", "-m", "pytest", "tests/test_integration.py", "-v"]
        
        if verbose:
            cmd.append("-s")
        
        return self._execute_command(cmd)
    
    def run_all_tests(self, verbose=False, coverage=True, parallel=False):
        """Run all tests."""
        cmd = ["python", "-m", "pytest", "tests/"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=.",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--cov-report=xml"
            ])
        
        if parallel:
            cmd.extend(["-n", "auto"])
        
        return self._execute_command(cmd)
    
    def run_specific_test(self, test_file, test_function=None, verbose=False):
        """Run a specific test file or function."""
        if test_function:
            cmd = ["python", "-m", "pytest", f"tests/{test_file}::{test_function}"]
        else:
            cmd = ["python", "-m", "pytest", f"tests/{test_file}"]
        
        if verbose:
            cmd.extend(["-v", "-s"])
        
        return self._execute_command(cmd)
    
    def run_performance_tests(self, verbose=False):
        """Run performance-related tests."""
        cmd = ["python", "-m", "pytest", "tests/", "-m", "performance", "-v"]
        
        if verbose:
            cmd.append("-s")
        
        return self._execute_command(cmd)
    
    def run_risk_tests(self, verbose=False, coverage=True):
        """Run risk management tests."""
        cmd = ["python", "-m", "pytest", "tests/test_risk_management.py", "-v"]
        
        if coverage:
            cmd.extend([
                "--cov=risk_management",
                "--cov-report=term-missing"
            ])
        
        if verbose:
            cmd.append("-s")
        
        return self._execute_command(cmd)
    
    def run_data_tests(self, verbose=False, coverage=True):
        """Run data management tests."""
        cmd = ["python", "-m", "pytest", "tests/test_data_manager.py", "-v"]
        
        if coverage:
            cmd.extend([
                "--cov=services",
                "--cov-report=term-missing"
            ])
        
        if verbose:
            cmd.append("-s")
        
        return self._execute_command(cmd)
    
    def run_trading_tests(self, verbose=False, coverage=True):
        """Run trading bot tests."""
        cmd = ["python", "-m", "pytest", "tests/test_trading_bot.py", "-v"]
        
        if coverage:
            cmd.extend([
                "--cov=trading_bot",
                "--cov-report=term-missing"
            ])
        
        if verbose:
            cmd.append("-s")
        
        return self._execute_command(cmd)
    
    def run_with_markers(self, markers, verbose=False):
        """Run tests with specific markers."""
        marker_expr = " or ".join(markers)
        cmd = ["python", "-m", "pytest", "tests/", "-m", marker_expr]
        
        if verbose:
            cmd.append("-v")
        
        return self._execute_command(cmd)
    
    def generate_coverage_report(self):
        """Generate detailed coverage report."""
        cmd = ["python", "-m", "pytest", "tests/", 
               "--cov=.", 
               "--cov-report=html",
               "--cov-report=xml",
               "--cov-report=json",
               "--cov-report=term-missing"]
        
        result = self._execute_command(cmd)
        
        if result and self.coverage_dir.exists():
            print(f"\nCoverage HTML report generated: {self.coverage_dir / 'index.html'}")
            print(f"Open in browser: file://{self.coverage_dir / 'index.html'}")
        
        return result
    
    def run_quick_tests(self):
        """Run a quick subset of tests for development."""
        cmd = ["python", "-m", "pytest", "tests/", 
               "--maxfail=3", 
               "--tb=short",
               "-q"]
        
        return self._execute_command(cmd)
    
    def run_failed_tests(self):
        """Re-run only previously failed tests."""
        cmd = ["python", "-m", "pytest", "--lf", "-v"]
        
        return self._execute_command(cmd)
    
    def run_new_tests(self):
        """Run only new tests (based on git changes)."""
        cmd = ["python", "-m", "pytest", "--nf", "-v"]
        
        return self._execute_command(cmd)
    
    def check_test_quality(self):
        """Check test code quality."""
        print("Checking test code quality...")
        
        # Check with flake8
        print("\n1. Running flake8 on test code...")
        flake8_cmd = ["flake8", "tests/", "--max-line-length=120"]
        flake8_result = self._execute_command(flake8_cmd, check_error=False)
        
        # Check with black
        print("\n2. Checking code formatting with black...")
        black_cmd = ["black", "--check", "tests/"]
        black_result = self._execute_command(black_cmd, check_error=False)
        
        # Check imports with isort
        print("\n3. Checking import sorting with isort...")
        isort_cmd = ["isort", "--check-only", "tests/"]
        isort_result = self._execute_command(isort_cmd, check_error=False)
        
        return all([flake8_result, black_result, isort_result])
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.base_dir / f"test_report_{timestamp}.html"
        
        cmd = ["python", "-m", "pytest", "tests/",
               "--html", str(report_file),
               "--self-contained-html",
               "--cov=.",
               "--cov-report=html"]
        
        result = self._execute_command(cmd)
        
        if result and report_file.exists():
            print(f"\nTest report generated: {report_file}")
            print(f"Open in browser: file://{report_file}")
        
        return result
    
    def run_security_tests(self):
        """Run security-related tests and checks."""
        print("Running security tests...")
        
        # Run bandit for security issues
        print("\n1. Running bandit security scanner...")
        bandit_cmd = ["bandit", "-r", ".", "-ll", "-x", "tests/,venv/,env/"]
        bandit_result = self._execute_command(bandit_cmd, check_error=False)
        
        # Run safety for dependency vulnerabilities
        print("\n2. Checking for dependency vulnerabilities...")
        safety_cmd = ["safety", "check"]
        safety_result = self._execute_command(safety_cmd, check_error=False)
        
        return bandit_result and safety_result
    
    def benchmark_tests(self):
        """Run performance benchmarks."""
        cmd = ["python", "-m", "pytest", "tests/", 
               "--benchmark-only",
               "--benchmark-sort=mean",
               "--benchmark-columns=min,max,mean,stddev"]
        
        return self._execute_command(cmd)
    
    def _execute_command(self, cmd, check_error=True):
        """Execute a command and handle output."""
        try:
            print(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=self.base_dir, check=check_error)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"Command failed with return code {e.returncode}")
            return False
        except FileNotFoundError:
            print(f"Command not found: {cmd[0]}")
            print("Make sure all required packages are installed:")
            print("pip install -r requirements-test.txt")
            return False


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Trading Bot Test Runner")
    
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--risk", action="store_true", help="Run risk management tests")
    parser.add_argument("--data", action="store_true", help="Run data management tests")
    parser.add_argument("--trading", action="store_true", help="Run trading bot tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--security", action="store_true", help="Run security tests")
    parser.add_argument("--quick", action="store_true", help="Run quick test subset")
    parser.add_argument("--failed", action="store_true", help="Re-run failed tests")
    parser.add_argument("--new", action="store_true", help="Run only new tests")
    
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--report", action="store_true", help="Generate HTML test report")
    parser.add_argument("--quality", action="store_true", help="Check test code quality")
    parser.add_argument("--benchmark", action="store_true", help="Run performance benchmarks")
    
    parser.add_argument("--file", type=str, help="Run specific test file")
    parser.add_argument("--function", type=str, help="Run specific test function")
    parser.add_argument("--markers", nargs="+", help="Run tests with specific markers")
    
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--parallel", "-p", action="store_true", help="Run tests in parallel")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    success = True
    
    # Determine coverage setting
    use_coverage = not args.no_coverage
    
    if args.unit:
        success = runner.run_unit_tests(args.verbose, use_coverage)
    elif args.integration:
        success = runner.run_integration_tests(args.verbose)
    elif args.risk:
        success = runner.run_risk_tests(args.verbose, use_coverage)
    elif args.data:
        success = runner.run_data_tests(args.verbose, use_coverage)
    elif args.trading:
        success = runner.run_trading_tests(args.verbose, use_coverage)
    elif args.performance:
        success = runner.run_performance_tests(args.verbose)
    elif args.security:
        success = runner.run_security_tests()
    elif args.quick:
        success = runner.run_quick_tests()
    elif args.failed:
        success = runner.run_failed_tests()
    elif args.new:
        success = runner.run_new_tests()
    elif args.coverage:
        success = runner.generate_coverage_report()
    elif args.report:
        success = runner.generate_test_report()
    elif args.quality:
        success = runner.check_test_quality()
    elif args.benchmark:
        success = runner.benchmark_tests()
    elif args.file:
        success = runner.run_specific_test(args.file, args.function, args.verbose)
    elif args.markers:
        success = runner.run_with_markers(args.markers, args.verbose)
    elif args.all:
        success = runner.run_all_tests(args.verbose, use_coverage, args.parallel)
    else:
        # Default: run all tests
        success = runner.run_all_tests(args.verbose, use_coverage, args.parallel)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()