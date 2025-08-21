#!/usr/bin/env python3
"""
Documentation Validation Script for AI Extension Compatibility

This script validates that documentation is properly indexed and accessible
for AI extensions, particularly Gemini Enterprise Architect extensions.

Usage:
    python scripts/validate-docs.py [--fix] [--verbose]
"""

import os
import json
import sys
import argparse
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import yaml
import re
from datetime import datetime

class DocumentationValidator:
    """Validates documentation structure and accessibility for AI extensions"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.docs_path = self.project_root / "docs"
        self.bmad_path = self.docs_path / "BMAD"
        self.issues = []
        self.warnings = []
        
    def validate_all(self, fix_issues: bool = False) -> Tuple[bool, List[str], List[str]]:
        """Run all validation checks"""
        print("🔍 Validating documentation for AI extension compatibility...\n")
        
        # Core validation checks
        self._validate_file_structure()
        self._validate_manifest_files()
        self._validate_index_files()
        self._validate_context_file()
        self._validate_bmad_documentation()
        self._validate_file_permissions()
        self._validate_schema_compliance()
        
        if fix_issues:
            self._fix_common_issues()
            
        return len(self.issues) == 0, self.issues, self.warnings
    
    def _validate_file_structure(self):
        """Validate required file structure exists"""
        print("📁 Checking file structure...")
        
        required_files = [
            "gemini-extension.json",
            "GEMINI.md",
            ".aiconfig",
            "docs/.aiindex",
            "docs/README.md",
            "docs/BMAD/README.md"
        ]
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                self.issues.append(f"Missing required file: {file_path}")
            else:
                print(f"  ✅ {file_path}")
                
        # Check BMAD structure
        bmad_dirs = ["methodology", "phases", "guides", "templates", "schemas", "metrics"]
        for dir_name in bmad_dirs:
            dir_path = self.bmad_path / dir_name
            if not dir_path.exists():
                self.warnings.append(f"BMAD directory missing: docs/BMAD/{dir_name}")
            else:
                print(f"  ✅ docs/BMAD/{dir_name}")
    
    def _validate_manifest_files(self):
        """Validate manifest files are properly formatted"""
        print("\n📋 Checking manifest files...")
        
        # Validate gemini-extension.json
        manifest_path = self.project_root / "gemini-extension.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                required_keys = ["name", "version", "contextFileName", "documentation"]
                for key in required_keys:
                    if key not in manifest:
                        self.issues.append(f"Missing key in gemini-extension.json: {key}")
                    else:
                        print(f"  ✅ {key}: {manifest.get(key)}")
                        
                # Validate documentation paths exist
                if "documentation" in manifest:
                    doc_config = manifest["documentation"]
                    for index_file in doc_config.get("indexFiles", []):
                        index_path = self.project_root / index_file.lstrip('./')
                        if not index_path.exists():
                            self.issues.append(f"Index file not found: {index_file}")
                            
            except json.JSONDecodeError as e:
                self.issues.append(f"Invalid JSON in gemini-extension.json: {e}")
        
        # Validate .aiconfig
        aiconfig_path = self.project_root / ".aiconfig"
        if aiconfig_path.exists():
            try:
                with open(aiconfig_path, 'r') as f:
                    content = f.read()
                    # Basic YAML validation
                    if content.strip():
                        yaml.safe_load(content)
                        print(f"  ✅ .aiconfig format valid")
            except yaml.YAMLError as e:
                self.issues.append(f"Invalid YAML in .aiconfig: {e}")
    
    def _validate_index_files(self):
        """Validate documentation index files"""
        print("\n📇 Checking index files...")
        
        # Validate .aiindex
        aiindex_path = self.docs_path / ".aiindex"
        if aiindex_path.exists():
            try:
                with open(aiindex_path, 'r') as f:
                    index_data = json.load(f)
                
                # Check index structure
                required_sections = ["documentationIndex", "categories", "searchIndex"]
                for section in required_sections:
                    if section not in index_data:
                        self.issues.append(f"Missing section in .aiindex: {section}")
                    else:
                        print(f"  ✅ {section}")
                        
                # Validate file references
                if "categories" in index_data:
                    for category, info in index_data["categories"].items():
                        for file_ref in info.get("files", []):
                            file_path = self.docs_path / file_ref
                            if not file_path.exists():
                                self.warnings.append(f"Referenced file not found: {file_ref}")
                                
            except json.JSONDecodeError as e:
                self.issues.append(f"Invalid JSON in .aiindex: {e}")
    
    def _validate_context_file(self):
        """Validate GEMINI.md context file"""
        print("\n🎯 Checking context file...")
        
        context_path = self.project_root / "GEMINI.md"
        if context_path.exists():
            with open(context_path, 'r') as f:
                content = f.read()
            
            # Check for required sections
            required_sections = [
                "Project Overview",
                "Documentation Structure",
                "BMAD Methodology Context",
                "Gemini AI Integration Points",
                "Trading Bot System Context"
            ]
            
            for section in required_sections:
                if section.lower() not in content.lower():
                    self.warnings.append(f"Missing section in GEMINI.md: {section}")
                else:
                    print(f"  ✅ {section}")
            
            # Check file size (should be substantial)
            if len(content) < 5000:
                self.warnings.append("GEMINI.md seems too short for comprehensive context")
            else:
                print(f"  ✅ Content length: {len(content)} characters")
    
    def _validate_bmad_documentation(self):
        """Validate BMAD-specific documentation"""
        print("\n🔄 Checking BMAD documentation...")
        
        # Check core BMAD files
        bmad_files = {
            "README.md": "BMAD overview",
            "methodology/overview.md": "Methodology fundamentals",
            "methodology/gemini-integration.md": "Gemini integration guide",
            "phases/build.md": "Build phase documentation",
            "phases/measure.md": "Measure phase documentation",
            "phases/analyze.md": "Analyze phase documentation",
            "phases/document.md": "Document phase documentation"
        }
        
        for file_path, description in bmad_files.items():
            full_path = self.bmad_path / file_path
            if not full_path.exists():
                self.issues.append(f"Missing BMAD file: {file_path} ({description})")
            else:
                # Check file content
                with open(full_path, 'r') as f:
                    content = f.read()
                if len(content) < 500:
                    self.warnings.append(f"BMAD file seems incomplete: {file_path}")
                else:
                    print(f"  ✅ {file_path}")
    
    def _validate_file_permissions(self):
        """Validate file permissions for AI extension access"""
        print("\n🔒 Checking file permissions...")
        
        critical_files = [
            "gemini-extension.json",
            "GEMINI.md",
            ".aiconfig",
            "docs/.aiindex",
            "docs/README.md"
        ]
        
        for file_path in critical_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                # Check if file is readable
                if not os.access(full_path, os.R_OK):
                    self.issues.append(f"File not readable: {file_path}")
                else:
                    print(f"  ✅ {file_path} - readable")
    
    def _validate_schema_compliance(self):
        """Validate configuration files against schemas"""
        print("\n📋 Checking schema compliance...")
        
        schema_path = self.bmad_path / "schemas" / "bmad-config-schema.json"
        if schema_path.exists():
            try:
                with open(schema_path, 'r') as f:
                    schema = json.load(f)
                print(f"  ✅ BMAD schema loaded")
                
                # Validate .aiindex against schema reference
                aiindex_path = self.docs_path / ".aiindex"
                if aiindex_path.exists():
                    with open(aiindex_path, 'r') as f:
                        index_data = json.load(f)
                    
                    if "$schema" in index_data:
                        print(f"  ✅ .aiindex references schema")
                    else:
                        self.warnings.append(".aiindex missing $schema reference")
                        
            except (json.JSONDecodeError, FileNotFoundError) as e:
                self.warnings.append(f"Schema validation issue: {e}")
    
    def _fix_common_issues(self):
        """Attempt to fix common issues automatically"""
        print("\n🔧 Attempting to fix common issues...")
        
        # Create missing directories
        dirs_to_create = [
            self.docs_path / "BMAD" / "methodology",
            self.docs_path / "BMAD" / "phases",
            self.docs_path / "BMAD" / "guides",
            self.docs_path / "BMAD" / "templates",
            self.docs_path / "BMAD" / "schemas",
            self.docs_path / "BMAD" / "metrics"
        ]
        
        for dir_path in dirs_to_create:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"  ✅ Created directory: {dir_path.relative_to(self.project_root)}")
        
        # Update timestamps
        files_to_update = ["docs/.aiindex", ".aiconfig"]
        current_time = datetime.now().isoformat() + "Z"
        
        for file_path in files_to_update:
            full_path = self.project_root / file_path
            if full_path.exists() and file_path.endswith('.json'):
                try:
                    with open(full_path, 'r') as f:
                        data = json.load(f)
                    
                    if "lastUpdated" in data:
                        data["lastUpdated"] = current_time
                        
                        with open(full_path, 'w') as f:
                            json.dump(data, f, indent=2)
                        print(f"  ✅ Updated timestamp in {file_path}")
                        
                except (json.JSONDecodeError, KeyError):
                    pass
    
    def generate_report(self) -> str:
        """Generate a comprehensive validation report"""
        report = []
        report.append("# Documentation Validation Report")
        report.append(f"**Generated**: {datetime.now().isoformat()}")
        report.append(f"**Project**: {self.project_root.name}")
        report.append("")
        
        if not self.issues and not self.warnings:
            report.append("## ✅ All Validations Passed")
            report.append("Documentation is properly configured for AI extension discovery.")
        else:
            if self.issues:
                report.append("## ❌ Critical Issues")
                for issue in self.issues:
                    report.append(f"- {issue}")
                report.append("")
            
            if self.warnings:
                report.append("## ⚠️ Warnings")
                for warning in self.warnings:
                    report.append(f"- {warning}")
                report.append("")
        
        report.append("## 🔧 Recommended Actions")
        if self.issues:
            report.append("1. Fix critical issues listed above")
            report.append("2. Run validation again with `--fix` flag")
            report.append("3. Verify AI extension can discover documentation")
        else:
            report.append("1. Documentation structure is valid")
            report.append("2. AI extensions should be able to discover BMAD docs")
            report.append("3. Consider addressing warnings for optimal performance")
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Validate documentation for AI extension compatibility")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix common issues")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--report", type=str, help="Save report to file")
    
    args = parser.parse_args()
    
    # Find project root
    current_dir = Path.cwd()
    project_root = current_dir
    
    # Look for project indicators
    while project_root.parent != project_root:
        if (project_root / "gemini-extension.json").exists() or \
           (project_root / "GEMINI.md").exists() or \
           (project_root / "docs" / "BMAD").exists():
            break
        project_root = project_root.parent
    
    if args.verbose:
        print(f"Project root: {project_root}")
    
    # Run validation
    validator = DocumentationValidator(str(project_root))
    success, issues, warnings = validator.validate_all(fix_issues=args.fix)
    
    # Generate and display report
    report = validator.generate_report()
    print("\n" + "="*60)
    print(report)
    
    # Save report if requested
    if args.report:
        with open(args.report, 'w') as f:
            f.write(report)
        print(f"\n📄 Report saved to: {args.report}")
    
    # Exit with appropriate code
    if success:
        print("\n🎉 Validation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Validation failed. Please address the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()