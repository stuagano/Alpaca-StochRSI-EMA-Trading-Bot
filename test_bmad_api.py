#!/usr/bin/env python3
"""
Test BMAD Status API
"""

import json
import os
from pathlib import Path

def load_bmad_status():
    """Load BMAD status from various sources"""
    
    # Priority 1: .bmad/status.json
    bmad_status = Path('.bmad/status.json')
    if bmad_status.exists():
        print("✅ Found: .bmad/status.json")
        with open(bmad_status, 'r') as f:
            data = json.load(f)
            print(f"  Version: {data.get('version')}")
            print(f"  Status: {data.get('project', {}).get('status')}")
            print(f"  Completeness: {data.get('methodology', {}).get('completeness')}%")
            print(f"  Documentation Files: {data.get('documentation', {}).get('bmad_files')}")
            print(f"  Phases Complete: {len([p for p in data.get('phases', {}).values() if p.get('completeness') == 100])}/4")
            return data
    else:
        print("❌ Not found: .bmad/status.json")
    
    # Priority 2: .bmad-status.json (root)
    alt_status = Path('.bmad-status.json')
    if alt_status.exists():
        print("✅ Found: .bmad-status.json")
        with open(alt_status, 'r') as f:
            data = json.load(f)
            print(f"  Status: {data.get('status')}")
            return data
    else:
        print("❌ Not found: .bmad-status.json")
    
    # Priority 3: BMAD-STATUS.md
    md_status = Path('BMAD-STATUS.md')
    if md_status.exists():
        print("✅ Found: BMAD-STATUS.md")
        with open(md_status, 'r') as f:
            content = f.read()
            if 'PRODUCTION READY' in content:
                print("  Status: PRODUCTION READY (from markdown)")
    else:
        print("❌ Not found: BMAD-STATUS.md")
    
    return None

def check_documentation():
    """Check BMAD documentation files"""
    from glob import glob
    
    print("\n📁 BMAD Documentation Check:")
    
    categories = {
        'methodology': 'docs/BMAD/methodology/*.md',
        'phases': 'docs/BMAD/phases/*.md',
        'guides': 'docs/BMAD/guides/*.md',
        'templates': 'docs/BMAD/templates/*.md',
        'metrics': 'docs/BMAD/metrics/*.md',
        'schemas': 'docs/BMAD/schemas/*.json',
        'readme': 'docs/BMAD/README.md'
    }
    
    total_files = 0
    for category, pattern in categories.items():
        if category == 'readme':
            # Special handling for single file
            files = glob(pattern)
        else:
            files = glob(pattern)
        total_files += len(files)
        status = "✅" if len(files) > 0 else "❌"
        print(f"  {status} {category}: {len(files)} files")
    
    print(f"\n  Total BMAD files: {total_files}")
    return total_files

def check_extension_config():
    """Check extension configuration files"""
    print("\n🔧 Extension Configuration:")
    
    configs = [
        ('.project-config.json', 'Master configuration (single source of truth)'),
        ('.gemini-config.json', 'Gemini extension config (primary discovery)'),
        ('.aiconfig', 'AI configuration'),
        ('GEMINI.md', 'Gemini context file'),
        ('.bmad/config.yml', 'BMAD YAML config')
    ]
    
    for config, description in configs:
        path = Path(config)
        if path.exists():
            print(f"  ✅ {description}: {config}")
        else:
            print(f"  ❌ {description}: {config}")

def main():
    print("=" * 50)
    print("BMAD Status Check for Gemini Extension")
    print("=" * 50)
    
    # Check status files
    status = load_bmad_status()
    
    # Check documentation
    doc_count = check_documentation()
    
    # Check extension config
    check_extension_config()
    
    # Summary
    print("\n" + "=" * 50)
    print("Summary:")
    if status and doc_count >= 25:
        print("✅ BMAD is FULLY CONFIGURED and READY")
        print("✅ All documentation is in place (25 files)")
        print("✅ Status files are properly formatted")
        print("\nThe Gemini extension should discover via .gemini-config.json")
        print("\nIf the extension still doesn't show the status:")
        print("1. Ensure extension reads .gemini-config.json")
        print("2. Restart the Flask server: python flask_app.py")
        print("3. Clear browser cache and refresh")
        print("4. Check that extension points to .project-config.json")
    else:
        print("⚠️ BMAD configuration incomplete")
        print(f"Documentation files: {doc_count}/25")
    
    print("=" * 50)

if __name__ == "__main__":
    main()