# Configuration Structure - Ultra-Simplified

## Single Discovery Method

All project configuration uses **one primary discovery method** to eliminate complexity.

## Configuration Files

### 🎯 Core Files (Only 2!)
- **`.project-config.json`** - Single source of truth for all project settings
- **`.gemini-config.json`** - Gemini extension config (references master)

### 📋 Supporting Files  
- **`.aiconfig`** - AI configuration  
- **`GEMINI.md`** - Gemini context file
- **`.bmad/config.yml`** - BMAD YAML config
- **`.bmad/status.json`** - BMAD status (the actual data)

## What Was Removed

❌ **Removed ALL redundant discovery methods:**
- `.gemini-architect.json` 
- `.gemini-ea-config.json`
- `.bmad-status.json`
- `bmad.config.json`
- `.aiindex` *(removed)*
- `docs/.aiindex` *(removed)*
- `gemini-extension.json` *(removed)*

## How It Works

1. **`.project-config.json`** contains all project information
2. **`.gemini-config.json`** references the master config using `$ref`
3. **Single discovery path** - no confusion or fallbacks

## For Gemini Enterprise Architect

The extension discovers the project through **ONE method only**:
- **`.gemini-config.json`** → **`.project-config.json`**

**That's it!** No secondary paths, no fallbacks, no confusion.

## Benefits

✅ **Ultra-clean** - only 2 config files for discovery  
✅ **No confusion** - one clear path  
✅ **Zero duplication** - single source of truth  
✅ **Easy maintenance** - update one file  
✅ **Predictable** - extension knows exactly where to look