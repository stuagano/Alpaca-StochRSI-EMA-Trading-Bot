#!/bin/bash

# BMAD Status Display Script
# This script displays the current BMAD implementation status

echo "🎯 BMAD Implementation Status Report"
echo "====================================="
echo ""

# Check if status files exist
if [ -f ".bmad-status.json" ]; then
    echo "✅ Status file found: .bmad-status.json"
    echo ""
    echo "📊 Current Status:"
    cat .bmad-status.json | python -m json.tool | head -30
else
    echo "❌ Status file not found"
fi

echo ""
echo "📈 Documentation Statistics:"
echo "----------------------------"
echo "BMAD Files: $(find docs/BMAD -name "*.md" | wc -l) markdown files"
echo "Total Docs: $(find docs -name "*.md" | wc -l) markdown files"

echo ""
echo "📁 BMAD Structure:"
echo "-----------------"
echo "Methodology: $(ls docs/BMAD/methodology/*.md 2>/dev/null | wc -l) files"
echo "Phases: $(ls docs/BMAD/phases/*.md 2>/dev/null | wc -l) files"
echo "Guides: $(ls docs/BMAD/guides/*.md 2>/dev/null | wc -l) files"
echo "Templates: $(ls docs/BMAD/templates/*.md 2>/dev/null | wc -l) files"

echo ""
echo "🚀 Implementation Readiness: IMMEDIATE"
echo "⏱️  Setup Time: 30 minutes"
echo "📚 Status Display: BMAD-STATUS.md"
echo ""
echo "For full status report, view: BMAD-STATUS.md"