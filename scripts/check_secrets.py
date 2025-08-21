#!/usr/bin/env python3
"""
Security script to check for secrets and sensitive data in code.
Used by pre-commit hooks to prevent committing sensitive information.
"""

import os
import re
import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple


# Patterns for detecting sensitive information
SECRET_PATTERNS = {
    'aws_access_key': r'AKIA[0-9A-Z]{16}',
    'aws_secret_key': r'[0-9a-zA-Z/+]{40}',
    'api_key': r'(?i)(api_key|apikey)\s*[:=]\s*["\']?[0-9a-zA-Z_\-]{20,}["\']?',
    'secret_key': r'(?i)(secret_key|secretkey)\s*[:=]\s*["\']?[0-9a-zA-Z_\-]{20,}["\']?',
    'password': r'(?i)password\s*[:=]\s*["\'][^"\']{8,}["\']',
    'token': r'(?i)(token|auth_token)\s*[:=]\s*["\']?[0-9a-zA-Z_\-]{20,}["\']?',
    'private_key': r'-----BEGIN (RSA )?PRIVATE KEY-----',
    'ssh_key': r'ssh-rsa AAAAB3NzaC1yc2E',
    'alpaca_key': r'(?i)(alpaca|trading).*key\s*[:=]\s*["\']?[A-Z0-9]{20,}["\']?',
    'database_url': r'(?i)(database_url|db_url)\s*[:=]\s*["\']?(postgresql|mysql|mongodb)://[^"\']+["\']?',
    'email_address': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
}

# File patterns to check
INCLUDE_PATTERNS = [
    r'.*\.py$',
    r'.*\.yaml$',
    r'.*\.yml$',
    r'.*\.json$',
    r'.*\.env$',
    r'.*\.cfg$',
    r'.*\.conf$',
    r'.*\.ini$',
    r'.*\.txt$',
]

# File patterns to exclude
EXCLUDE_PATTERNS = [
    r'.*\.git/.*',
    r'.*/__pycache__/.*',
    r'.*\.pyc$',
    r'.*\.pyo$',
    r'.*\.db$',
    r'.*\.sqlite3?$',
    r'.*tests/fixtures/.*',
    r'.*venv/.*',
    r'.*env/.*',
    r'.*node_modules/.*',
]

# Whitelist for known false positives
WHITELIST = [
    'example_key',
    'test_key',
    'dummy_password',
    'placeholder',
    'your_api_key_here',
    'INSERT_YOUR_KEY_HERE',
    'REPLACE_WITH_YOUR_KEY',
    'fake_secret',
    'mock_token',
    'sample_key',
]


class SecretDetector:
    """Detect secrets and sensitive information in files."""
    
    def __init__(self):
        self.violations = []
        self.whitelisted_items = set(WHITELIST)
    
    def should_check_file(self, file_path: str) -> bool:
        """Check if file should be scanned."""
        # Check exclude patterns
        for pattern in EXCLUDE_PATTERNS:
            if re.match(pattern, file_path):
                return False
        
        # Check include patterns
        for pattern in INCLUDE_PATTERNS:
            if re.match(pattern, file_path):
                return True
        
        return False
    
    def is_whitelisted(self, match: str) -> bool:
        """Check if match is in whitelist."""
        match_lower = match.lower()
        return any(whitelist_item.lower() in match_lower for whitelist_item in self.whitelisted_items)
    
    def scan_file(self, file_path: str) -> List[Dict]:
        """Scan a single file for secrets."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for secret_type, pattern in SECRET_PATTERNS.items():
                        matches = re.finditer(pattern, line)
                        
                        for match in matches:
                            matched_text = match.group()
                            
                            # Skip if whitelisted
                            if self.is_whitelisted(matched_text):
                                continue
                            
                            # Special handling for email addresses (only flag if suspicious)
                            if secret_type == 'email_address':
                                if not self.is_suspicious_email(matched_text):
                                    continue
                            
                            violations.append({
                                'file': file_path,
                                'line': line_num,
                                'type': secret_type,
                                'match': matched_text[:50] + '...' if len(matched_text) > 50 else matched_text,
                                'context': line.strip()[:100]
                            })
        
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
        
        return violations
    
    def is_suspicious_email(self, email: str) -> bool:
        """Check if email looks suspicious (not a generic example)."""
        suspicious_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']
        generic_patterns = ['example.com', 'test.com', 'domain.com', 'company.com']
        
        email_lower = email.lower()
        
        # Skip generic examples
        for pattern in generic_patterns:
            if pattern in email_lower:
                return False
        
        # Flag personal email domains in business code
        for domain in suspicious_domains:
            if domain in email_lower:
                return True
        
        return False
    
    def scan_directory(self, directory: str) -> List[Dict]:
        """Scan all files in directory recursively."""
        all_violations = []
        
        for root, dirs, files in os.walk(directory):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                if self.should_check_file(file_path):
                    violations = self.scan_file(file_path)
                    all_violations.extend(violations)
        
        return all_violations
    
    def scan_files(self, file_paths: List[str]) -> List[Dict]:
        """Scan specific files."""
        all_violations = []
        
        for file_path in file_paths:
            if os.path.isfile(file_path) and self.should_check_file(file_path):
                violations = self.scan_file(file_path)
                all_violations.extend(violations)
        
        return all_violations


def generate_report(violations: List[Dict]) -> str:
    """Generate human-readable report."""
    if not violations:
        return "✅ No secrets or sensitive data detected."
    
    report = [
        "🚨 SECURITY ALERT: Potential secrets detected!",
        "=" * 50,
        ""
    ]
    
    # Group by file
    files_violations = {}
    for violation in violations:
        file_path = violation['file']
        if file_path not in files_violations:
            files_violations[file_path] = []
        files_violations[file_path].append(violation)
    
    for file_path, file_violations in files_violations.items():
        report.append(f"📁 File: {file_path}")
        report.append("-" * 40)
        
        for violation in file_violations:
            report.append(f"  Line {violation['line']}: {violation['type']}")
            report.append(f"    Match: {violation['match']}")
            report.append(f"    Context: {violation['context']}")
            report.append("")
        
        report.append("")
    
    # Summary
    report.extend([
        "📊 SUMMARY:",
        f"  Total violations: {len(violations)}",
        f"  Files affected: {len(files_violations)}",
        "",
        "🛠️  ACTIONS REQUIRED:",
        "  1. Remove or encrypt sensitive data",
        "  2. Use environment variables for secrets",
        "  3. Add false positives to whitelist if appropriate",
        "  4. Consider using .gitignore for sensitive files",
        ""
    ])
    
    return "\n".join(report)


def main():
    """Main entry point."""
    detector = SecretDetector()
    
    if len(sys.argv) > 1:
        # Scan specific files (used by pre-commit)
        file_paths = sys.argv[1:]
        violations = detector.scan_files(file_paths)
    else:
        # Scan current directory
        violations = detector.scan_directory('.')
    
    # Generate report
    report = generate_report(violations)
    print(report)
    
    # Exit with error code if violations found
    if violations:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()