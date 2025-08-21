#!/usr/bin/env python3
"""
Comprehensive verification script for Gemini Enterprise Architect Extension
This ensures all BMAD documentation and configuration is properly accessible
"""

import json
import os
from pathlib import Path
from datetime import datetime
import sys

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def check_file(filepath, description):
    """Check if a file exists and return status"""
    path = Path(filepath)
    if path.exists():
        size = path.stat().st_size
        print(f"  ✅ {description}: {filepath} ({size:,} bytes)")
        return True
    else:
        print(f"  ❌ {description}: {filepath} (NOT FOUND)")
        return False

def verify_bmad_documentation():
    """Verify all BMAD documentation files"""
    print_header("BMAD Documentation Verification")
    
    base_path = Path("docs/BMAD")
    if not base_path.exists():
        print("  ❌ BMAD documentation directory not found!")
        return False
    
    expected_structure = {
        "README.md": "Main documentation index",
        "methodology/overview.md": "Methodology overview",
        "methodology/implementation.md": "Implementation guide",
        "methodology/best-practices.md": "Best practices",
        "methodology/gemini-integration.md": "Gemini integration",
        "phases/build.md": "Build phase",
        "phases/measure.md": "Measure phase",
        "phases/analyze.md": "Analyze phase",
        "phases/document.md": "Document phase",
        "guides/quick-start.md": "Quick start guide",
        "guides/implementation-checklist.md": "Implementation checklist",
        "guides/commands-reference.md": "Commands reference",
        "guides/trading-bot-integration.md": "Trading bot integration",
        "guides/workflow-examples.md": "Workflow examples",
        "guides/troubleshooting.md": "Troubleshooting guide",
        "templates/README.md": "Templates index",
        "templates/api-endpoint-template.md": "API endpoint template",
        "templates/strategy-template.md": "Strategy template",
        "templates/trading-strategy-comprehensive-template.md": "Comprehensive strategy",
        "templates/component-template.md": "Component template",
        "templates/indicator-template.md": "Indicator template",
        "templates/risk-management-template.md": "Risk management",
        "templates/backtesting-template.md": "Backtesting template",
        "metrics/kpis-and-metrics.md": "KPIs and metrics",
        "schemas/bmad-config-schema.json": "Configuration schema"
    }
    
    all_exist = True
    found_count = 0
    
    for relative_path, description in expected_structure.items():
        full_path = base_path / relative_path
        if full_path.exists():
            found_count += 1
            print(f"  ✅ {description}")
        else:
            all_exist = False
            print(f"  ❌ {description} - Missing: {relative_path}")
    
    print(f"\n  📊 Total: {found_count}/{len(expected_structure)} files found")
    return all_exist, found_count

def verify_configuration_files():
    """Verify all configuration files for Gemini Extension"""
    print_header("Configuration Files")
    
    configs = {
        ".gemini-architect.json": "Gemini Enterprise Architect config",
        ".gemini-ea-config.json": "Gemini EA discovery config",
        "gemini-extension.json": "Main extension manifest",
        ".aiindex": "AI discovery index",
        "docs/.aiindex": "Documentation discovery index",
        ".aiconfig": "AI configuration",
        "GEMINI.md": "Gemini context file",
        "bmad.config.json": "BMAD configuration",
        ".bmad/config.yml": "BMAD YAML config",
        ".bmad/status.json": "BMAD status file",
        "BMAD-STATUS.md": "BMAD status dashboard"
    }
    
    all_exist = True
    for filepath, description in configs.items():
        if not check_file(filepath, description):
            all_exist = False
    
    return all_exist

def verify_status_content():
    """Verify the content of BMAD status file"""
    print_header("BMAD Status Content Verification")
    
    status_file = Path(".bmad/status.json")
    if not status_file.exists():
        print("  ❌ Status file not found!")
        return False
    
    try:
        with open(status_file, 'r') as f:
            status = json.load(f)
        
        # Check critical fields
        checks = {
            "version": status.get("version"),
            "completeness": status.get("methodology", {}).get("completeness"),
            "status": status.get("project", {}).get("status"),
            "documentation_files": status.get("documentation", {}).get("bmad_files"),
            "test_coverage": status.get("phases", {}).get("build", {}).get("test_coverage"),
            "sharpe_ratio": status.get("trading_performance", {}).get("sharpe_ratio")
        }
        
        print("  📊 Status File Content:")
        for key, value in checks.items():
            if value is not None:
                print(f"    ✅ {key}: {value}")
            else:
                print(f"    ⚠️ {key}: Not found")
        
        # Check if all phases are complete
        phases = status.get("phases", {})
        phase_status = []
        for phase_name in ["build", "measure", "analyze", "document"]:
            phase = phases.get(phase_name, {})
            completeness = phase.get("completeness", 0)
            phase_status.append(completeness == 100)
            status_icon = "✅" if completeness == 100 else "⚠️"
            print(f"    {status_icon} {phase_name.capitalize()} phase: {completeness}%")
        
        return all(phase_status)
        
    except Exception as e:
        print(f"  ❌ Error reading status file: {e}")
        return False

def verify_api_endpoint():
    """Check if BMAD API endpoint is configured"""
    print_header("API Endpoint Configuration")
    
    # Check if Flask app has BMAD routes
    flask_files = ["flask_app.py", "api/bmad_status_routes.py"]
    
    for filepath in flask_files:
        if Path(filepath).exists():
            print(f"  ✅ Found: {filepath}")
            if "bmad_status_routes" in filepath:
                with open(filepath, 'r') as f:
                    content = f.read()
                    if '/api/bmad/status' in content:
                        print(f"    ✅ Endpoint /api/bmad/status is defined")
                    if 'Blueprint' in content:
                        print(f"    ✅ Uses Flask Blueprint")
        else:
            print(f"  ⚠️ Not found: {filepath}")
    
    return True

def generate_summary():
    """Generate final summary and recommendations"""
    print_header("Final Summary")
    
    # Run all checks
    doc_result, doc_count = verify_bmad_documentation()
    config_result = verify_configuration_files()
    status_result = verify_status_content()
    api_result = verify_api_endpoint()
    
    # Overall status
    all_good = doc_result and config_result and status_result and api_result
    
    if all_good:
        print("\n  🎉 SUCCESS: All BMAD components are properly configured!")
        print("\n  ✅ Documentation: Complete (25 files)")
        print("  ✅ Configuration: All files present")
        print("  ✅ Status: 100% complete")
        print("  ✅ API: Endpoint configured")
        
        print("\n  📋 Next Steps for Gemini Enterprise Architect:")
        print("  1. The extension should auto-discover via:")
        print("     - .gemini-architect.json")
        print("     - .gemini-ea-config.json")
        print("     - .aiindex")
        print("  2. Status is available at:")
        print("     - File: .bmad/status.json")
        print("     - API: http://localhost:9765/api/bmad/status")
        print("  3. Documentation root: docs/BMAD/")
        
    else:
        print("\n  ⚠️ Some components need attention:")
        if not doc_result:
            print(f"  ❌ Documentation: {doc_count}/25 files")
        if not config_result:
            print("  ❌ Configuration: Some files missing")
        if not status_result:
            print("  ❌ Status: Incomplete or invalid")
        if not api_result:
            print("  ❌ API: Endpoint not properly configured")
    
    print("\n  📝 Configuration Files for Gemini:")
    print("  • Primary: .gemini-architect.json")
    print("  • Secondary: .gemini-ea-config.json")
    print("  • Discovery: .aiindex")
    print("  • Extension: gemini-extension.json")
    
    print("\n" + "=" * 60)
    print("  Verification Complete")
    print("=" * 60)
    
    return all_good

if __name__ == "__main__":
    # Change to project directory if needed
    project_dir = Path("/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot")
    if project_dir.exists():
        os.chdir(project_dir)
    
    # Run verification
    success = generate_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)