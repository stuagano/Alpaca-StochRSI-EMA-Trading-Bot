#!/usr/bin/env python3
"""
Comprehensive test runner for the Trading Bot Test Suite.
Provides convenient commands for running different test categories.
"""

import os
import sys
import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path

class TestRunner:
    """Main test runner class."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests"
        self.reports_dir = self.test_dir / "reports"
        
        # Ensure reports directory exists
        self.reports_dir.mkdir(exist_ok=True)
        
    def run_unit_tests(self, coverage=True, verbose=False):
        """Run unit tests."""
        print("🧪 Running Unit Tests...")
        
        cmd = ["pytest", "tests/unit/"]
        
        if coverage:
            cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
        
        if verbose:
            cmd.append("-v")
            
        cmd.extend([
            "--tb=short",
            f"--html={self.reports_dir}/unit_test_report.html",
            "--self-contained-html"
        ])
        
        return self._run_command(cmd)
    
    def run_integration_tests(self, verbose=False):
        """Run integration tests."""
        print("🔗 Running Integration Tests...")
        
        cmd = ["pytest", "tests/integration/"]
        
        if verbose:
            cmd.append("-v")
            
        cmd.extend([
            "--tb=short",
            f"--html={self.reports_dir}/integration_test_report.html",
            "--self-contained-html"
        ])
        
        return self._run_command(cmd)
    
    def run_performance_tests(self, verbose=False):
        """Run performance tests."""
        print("🚀 Running Performance Tests...")
        
        cmd = ["pytest", "tests/performance/"]
        
        if verbose:
            cmd.append("-v")
            
        cmd.extend([
            "--tb=short",
            "--benchmark-json=" + str(self.reports_dir / "benchmark_results.json"),
            f"--html={self.reports_dir}/performance_test_report.html",
            "--self-contained-html"
        ])
        
        return self._run_command(cmd)
    
    def run_security_tests(self, verbose=False):
        """Run security tests."""
        print("🔒 Running Security Tests...")
        
        cmd = ["pytest", "tests/security/", "-m", "security"]
        
        if verbose:
            cmd.append("-v")
            
        cmd.extend([
            "--tb=short",
            f"--html={self.reports_dir}/security_test_report.html",
            "--self-contained-html"
        ])
        
        return self._run_command(cmd)
    
    def run_e2e_tests(self, verbose=False):
        """Run end-to-end tests."""
        print("🎯 Running End-to-End Tests...")
        
        cmd = ["pytest", "tests/e2e/"]
        
        if verbose:
            cmd.append("-v")
            
        cmd.extend([
            "--tb=short",
            f"--html={self.reports_dir}/e2e_test_report.html",
            "--self-contained-html"
        ])
        
        return self._run_command(cmd)
    
    def run_all_tests(self, coverage=True, verbose=False):
        """Run complete test suite."""
        print("🏁 Running Complete Test Suite...")
        
        cmd = ["pytest"]
        
        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=html",
                "--cov-report=term",
                "--cov-report=xml"
            ])
        
        if verbose:
            cmd.append("-v")
            
        cmd.extend([
            "--tb=short",
            f"--html={self.reports_dir}/complete_test_report.html",
            "--self-contained-html",
            "--junitxml=" + str(self.reports_dir / "junit_results.xml")
        ])
        
        return self._run_command(cmd)
    
    def run_smoke_tests(self):
        """Run smoke tests for quick validation."""
        print("💨 Running Smoke Tests...")
        
        cmd = [
            "pytest",
            "-m", "smoke",
            "--tb=short",
            "-v",
            f"--html={self.reports_dir}/smoke_test_report.html",
            "--self-contained-html"
        ]
        
        return self._run_command(cmd)
    
    def run_ci_tests(self):
        """Run tests suitable for CI/CD pipeline."""
        print("🔄 Running CI/CD Test Suite...")
        
        cmd = [
            "pytest",
            "--cov=src",
            "--cov-report=xml",
            "--cov-report=term",
            "--tb=short",
            "--maxfail=5",  # Stop after 5 failures
            "-x",  # Stop on first failure for faster feedback
            "--junitxml=" + str(self.reports_dir / "ci_junit_results.xml")
        ]
        
        return self._run_command(cmd)
    
    def run_quick_tests(self):
        """Run quick tests (excluding slow tests)."""
        print("⚡ Running Quick Tests...")
        
        cmd = [
            "pytest",
            "-m", "not slow",
            "--tb=short",
            "-v"
        ]
        
        return self._run_command(cmd)
    
    def run_load_tests(self, users=10, duration=60):
        """Run load tests using locust."""
        print(f"📈 Running Load Tests ({users} users, {duration}s)...")
        
        # Check if locust is available
        try:
            subprocess.run(["locust", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Locust not found. Install with: pip install locust")
            return False
            
        # Run locust tests
        cmd = [
            "locust",
            "-f", "tests/performance/load_test.py",
            "--host=http://localhost:5000",
            f"--users={users}",
            f"--spawn-rate=2",
            f"--run-time={duration}s",
            "--headless",
            "--html=" + str(self.reports_dir / "load_test_report.html")
        ]
        
        return self._run_command(cmd)
    
    def generate_test_data(self):
        """Generate test fixtures and data."""
        print("📊 Generating Test Data...")
        
        try:
            # Generate market data fixtures
            subprocess.run([
                sys.executable, "-m", "tests.fixtures.market_data_fixtures"
            ], check=True, cwd=self.project_root)
            
            # Generate order fixtures
            subprocess.run([
                sys.executable, "-m", "tests.fixtures.order_fixtures"
            ], check=True, cwd=self.project_root)
            
            print("✅ Test data generated successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to generate test data: {e}")
            return False
    
    def clean_test_artifacts(self):
        """Clean test artifacts and temporary files."""
        print("🧹 Cleaning Test Artifacts...")
        
        patterns_to_clean = [
            ".coverage*",
            "htmlcov/",
            ".pytest_cache/",
            "*.pyc",
            "__pycache__/",
            "test_*.db",
            "*.log"
        ]
        
        for pattern in patterns_to_clean:
            cmd = ["find", str(self.project_root), "-name", pattern, "-delete"]
            subprocess.run(cmd, capture_output=True)
        
        print("✅ Test artifacts cleaned")
    
    def validate_test_environment(self):
        """Validate test environment setup."""
        print("🔍 Validating Test Environment...")
        
        checks = []
        
        # Check Python version
        python_version = sys.version_info
        checks.append({
            "name": "Python Version",
            "status": python_version >= (3, 8),
            "message": f"Python {python_version.major}.{python_version.minor}"
        })
        
        # Check required packages
        required_packages = ["pytest", "pytest-cov", "pytest-html"]
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                checks.append({
                    "name": f"Package {package}",
                    "status": True,
                    "message": "Available"
                })
            except ImportError:
                checks.append({
                    "name": f"Package {package}",
                    "status": False,
                    "message": "Missing"
                })
        
        # Check test directories
        test_dirs = ["unit", "integration", "performance", "security", "fixtures", "mocks"]
        for test_dir in test_dirs:
            dir_path = self.test_dir / test_dir
            checks.append({
                "name": f"Directory tests/{test_dir}",
                "status": dir_path.exists(),
                "message": "Exists" if dir_path.exists() else "Missing"
            })
        
        # Display results
        all_passed = True
        for check in checks:
            status_icon = "✅" if check["status"] else "❌"
            print(f"{status_icon} {check['name']}: {check['message']}")
            if not check["status"]:
                all_passed = False
        
        return all_passed
    
    def _run_command(self, cmd):
        """Run command and handle output."""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False,
                check=True
            )
            
            execution_time = time.time() - start_time
            print(f"✅ Tests completed in {execution_time:.2f} seconds")
            return True
            
        except subprocess.CalledProcessError as e:
            execution_time = time.time() - start_time
            print(f"❌ Tests failed after {execution_time:.2f} seconds")
            print(f"Exit code: {e.returncode}")
            return False
    
    def create_test_report_summary(self):
        """Create a summary of all test reports."""
        print("📄 Creating Test Report Summary...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.reports_dir / f"test_summary_{timestamp}.md"
        
        with open(summary_file, "w") as f:
            f.write("# Test Execution Summary\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # List available reports
            f.write("## Available Reports\n\n")
            for report_file in self.reports_dir.glob("*.html"):
                f.write(f"- [{report_file.stem}]({report_file.name})\n")
            
            f.write("\n## Coverage Report\n\n")
            coverage_dir = self.project_root / "htmlcov"
            if coverage_dir.exists():
                f.write(f"- [Coverage Report](../htmlcov/index.html)\n")
            
            f.write("\n## Benchmark Results\n\n")
            benchmark_file = self.reports_dir / "benchmark_results.json"
            if benchmark_file.exists():
                f.write(f"- [Benchmark Results](benchmark_results.json)\n")
        
        print(f"✅ Test summary created: {summary_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Trading Bot Test Runner")
    parser.add_argument("command", choices=[
        "unit", "integration", "performance", "security", "e2e",
        "all", "smoke", "ci", "quick", "load",
        "generate-data", "clean", "validate", "summary"
    ], help="Test command to run")
    
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage reporting")
    parser.add_argument("--users", type=int, default=10, help="Number of users for load testing")
    parser.add_argument("--duration", type=int, default=60, help="Duration for load testing (seconds)")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Command mapping
    commands = {
        "unit": lambda: runner.run_unit_tests(
            coverage=not args.no_coverage,
            verbose=args.verbose
        ),
        "integration": lambda: runner.run_integration_tests(verbose=args.verbose),
        "performance": lambda: runner.run_performance_tests(verbose=args.verbose),
        "security": lambda: runner.run_security_tests(verbose=args.verbose),
        "e2e": lambda: runner.run_e2e_tests(verbose=args.verbose),
        "all": lambda: runner.run_all_tests(
            coverage=not args.no_coverage,
            verbose=args.verbose
        ),
        "smoke": runner.run_smoke_tests,
        "ci": runner.run_ci_tests,
        "quick": runner.run_quick_tests,
        "load": lambda: runner.run_load_tests(args.users, args.duration),
        "generate-data": runner.generate_test_data,
        "clean": runner.clean_test_artifacts,
        "validate": runner.validate_test_environment,
        "summary": runner.create_test_report_summary
    }
    
    print(f"🚀 Starting {args.command} tests...")
    print(f"📁 Project root: {runner.project_root}")
    print(f"📊 Reports directory: {runner.reports_dir}")
    print("-" * 50)
    
    success = commands[args.command]()
    
    if success:
        print("\n🎉 Test execution completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Test execution failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()