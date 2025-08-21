# BMAD Troubleshooting Guide

## Overview

This comprehensive troubleshooting guide helps resolve common issues encountered when implementing and using BMAD methodology with Claude-Flow in trading bot development projects.

## Quick Diagnostic Commands

### System Health Check
```bash
# Check BMAD system status
npx claude-flow bmad doctor

# Validate configuration
npx claude-flow bmad config validate

# Check system requirements
npx claude-flow bmad system-check

# View current cycle status
npx claude-flow bmad status
```

### Debug Mode
```bash
# Enable debug logging
export BMAD_LOG_LEVEL=DEBUG

# Run with verbose output
npx claude-flow bmad cycle "test" --verbose --dry-run

# Trace execution
npx claude-flow bmad debug --trace
```

## Overview

This guide provides solutions to common issues encountered when implementing and using BMAD methodology. Issues are organized by category with step-by-step resolution procedures.

## Installation and Setup Issues

### Issue: Claude-Flow Installation Fails

**Symptoms:**
- `npm install -g claude-flow@alpha` fails
- Permission errors during installation
- Command not found after installation

**Solutions:**
```bash
# Solution 1: Use npx (recommended)
npx claude-flow@alpha --version

# Solution 2: Fix npm permissions
sudo npm install -g claude-flow@alpha --unsafe-perm=true

# Solution 3: Use local installation
npm install claude-flow@alpha
./node_modules/.bin/claude-flow --version

# Solution 4: Clear npm cache
npm cache clean --force
npm install -g claude-flow@alpha
```

#### For Permission Issues (macOS/Linux):
```bash
# Option 1: Use npm with --unsafe-perm
sudo npm install -g claude-flow@alpha --unsafe-perm

# Option 2: Configure npm to use different directory
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
npm install -g claude-flow@alpha

# Option 3: Use npx instead
npx claude-flow@alpha bmad --help
```

#### For Windows Issues:
```cmd
# Run as Administrator
npm install -g claude-flow@alpha

# Or use Chocolatey
choco install nodejs
npm install -g claude-flow@alpha
```

**Verification:**
```bash
# Check installation
npx claude-flow --version
npx claude-flow bmad --help
```

### Issue: BMAD Initialization Fails

**Symptoms:**
- `bmad init` command fails
- Configuration file not created
- Permission denied errors

**Diagnostic Steps:**
```bash
# Check current directory permissions
ls -la
pwd

# Check if directory is a git repository
git status

# Verify Node.js and npm versions
node --version
npm --version
```

**Solutions:**
```bash
# Ensure you're in project root
cd /path/to/your/project

# Initialize git if needed
git init

# Create directory if needed
mkdir -p docs/BMAD

# Initialize with explicit configuration
npx claude-flow bmad init \
  --project "trading-bot" \
  --template trading \
  --force
```

### Issue: Configuration Validation Errors

**Symptoms:**
- `bmad config validate` fails
- YAML syntax errors
- Missing required fields

**Common Configuration Fixes:**
```yaml
# Common bmad.config.yml issues and fixes

# ❌ Wrong indentation
project:
name: trading-bot  # Wrong - needs proper indentation

# ✅ Correct indentation
project:
  name: trading-bot

# ❌ Missing quotes for special characters
project:
  name: trading-bot@2.0

# ✅ Quoted strings
project:
  name: "trading-bot@2.0"

# ❌ Incorrect data types
phases:
  build:
    duration: "4h"  # Should be a number for some fields
    auto_test: "true"  # Should be boolean

# ✅ Correct data types
phases:
  build:
    duration: 4  # hours as number
    auto_test: true  # boolean
```

**Validation Command:**
```bash
# Validate with detailed output
npx claude-flow bmad config validate --verbose

# Fix common issues automatically
npx claude-flow bmad config fix --auto
```

## Cycle Execution Issues

### Issue: Cycle Fails to Start

**Symptoms:**
- `bmad cycle` command hangs or fails
- "No active cycle" errors
- Resource allocation failures

**Diagnostic Commands:**
```bash
# Check system status
npx claude-flow bmad doctor

# Check for active cycles
npx claude-flow bmad status

# Check resource availability
ps aux | grep claude-flow
df -h  # Check disk space
free -h  # Check memory (Linux/macOS)
```

**Solutions:**
```bash
# Clear any stuck cycles
npx claude-flow bmad cycle --abort-all

# Reset BMAD state
npx claude-flow bmad reset --force

# Start with minimal configuration
npx claude-flow bmad cycle "test-cycle" \
  --phases "build:60%,measure:15%,analyze:15%,document:10%" \
  --timeout 30m
```

### Issue: Phase Transition Failures

**Symptoms:**
- Stuck in one phase
- "Phase completion requirements not met" errors
- Incomplete phase outputs

**Phase-Specific Diagnostics:**

#### BUILD Phase Issues:
```bash
# Check build requirements
npx claude-flow bmad build --check-requirements

# Common BUILD phase fixes
# 1. Ensure tests pass
python -m pytest
npm test

# 2. Check code quality
pylint your_code.py
npm run lint

# 3. Verify documentation
npx claude-flow bmad build --check-docs
```

#### MEASURE Phase Issues:
```bash
# Check measurement tools
which pytest
which coverage

# Test metric collection
npx claude-flow bmad measure --dry-run

# Fix measurement dependencies
pip install pytest pytest-cov
npm install --save-dev jest
```

#### ANALYZE Phase Issues:
```bash
# Check analysis dependencies
python -c "import numpy, pandas, scipy"

# Test analysis with sample data
npx claude-flow bmad analyze --sample-data

# Skip complex analysis temporarily
npx claude-flow bmad analyze --simple-mode
```

#### DOCUMENT Phase Issues:
```bash
# Check documentation tools
which sphinx-build
which pandoc

# Generate basic documentation
npx claude-flow bmad document --basic-only

# Fix template issues
npx claude-flow bmad template validate
```

### Issue: Performance Problems

**Symptoms:**
- Slow cycle execution
- High CPU/memory usage
- Timeouts during phases

**Performance Optimization:**

#### System Resource Optimization:
```bash
# Check system resources
top
htop  # If available
iostat 1  # Check I/O

# Optimize BMAD configuration
# bmad.config.yml
performance:
  parallel_execution: true
  max_workers: 4  # Adjust based on CPU cores
  memory_limit: "2GB"
  timeout_multiplier: 1.5

phases:
  build:
    parallel_tasks: true
    incremental: true
  measure:
    sampling_rate: 0.1  # Reduce if too intensive
  analyze:
    quick_mode: true
    ml_enabled: false  # Disable for faster execution
```

#### Database and Storage Optimization:
```bash
# Clean up old data
npx claude-flow bmad cleanup --older-than 30d

# Optimize database
npx claude-flow bmad db optimize

# Use faster storage for temporary files
export BMAD_TEMP_DIR="/tmp/bmad"  # Use RAM disk if available
```

## Integration Issues

### Issue: CI/CD Integration Problems

**Symptoms:**
- BMAD commands fail in CI environment
- Permission issues in containers
- Missing dependencies in CI

**CI/CD Fixes:**

#### GitHub Actions:
```yaml
# .github/workflows/bmad.yml
name: BMAD Integration

on: [push, pull_request]

jobs:
  bmad-cycle:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          cache: 'pip'
      
      - name: Install Dependencies
        run: |
          npm install -g claude-flow@alpha
          pip install -r requirements.txt
      
      - name: Run BMAD Cycle
        run: |
          npx claude-flow bmad cycle "ci-validation" \
            --ci-mode \
            --timeout 30m \
            --output-format json
        env:
          BMAD_CI: true
          NODE_ENV: production
```

#### Docker Integration:
```dockerfile
# Dockerfile for BMAD
FROM node:18-alpine

# Install system dependencies
RUN apk add --no-cache python3 py3-pip git

# Install Claude-Flow
RUN npm install -g claude-flow@alpha

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install project dependencies
RUN pip install -r requirements.txt

# Run BMAD
CMD ["npx", "claude-flow", "bmad", "cycle", "docker-build"]
```

### Issue: Team Collaboration Problems

**Symptoms:**
- Conflicting cycle executions
- Shared resource conflicts
- Inconsistent team configurations

**Team Coordination Solutions:**

#### Shared Configuration:
```yaml
# team-bmad.config.yml
team:
  coordination:
    enabled: true
    lock_service: "redis://localhost:6379"
    conflict_resolution: "queue"  # queue, abort, merge
  
  shared_resources:
    database: "postgresql://bmad:password@localhost/bmad_team"
    file_storage: "s3://bmad-team-bucket"
    metrics_endpoint: "http://metrics.company.com/bmad"
  
  notifications:
    slack_webhook: "${SLACK_WEBHOOK_URL}"
    email_notifications: true
    cycle_updates: true
```

#### Resource Locking:
```bash
# Check for resource conflicts
npx claude-flow bmad team status

# Acquire team lock before starting cycle
npx claude-flow bmad cycle "feature" --team-lock

# Release locks manually if needed
npx claude-flow bmad team unlock --force
```

## Data and Metrics Issues

### Issue: Metrics Collection Failures

**Symptoms:**
- Missing metrics data
- "No data collected" errors
- Inconsistent measurements

**Metrics Troubleshooting:**

#### Verify Measurement Tools:
```bash
# Check required tools
which pytest
which coverage
which git

# Test individual collectors
npx claude-flow bmad measure --collector git --test
npx claude-flow bmad measure --collector performance --test
```

#### Fix Data Collection:
```python
# measurement/diagnostics.py
def diagnose_metrics_collection():
    """Diagnose metrics collection issues"""
    
    diagnostics = {
        'git_access': test_git_access(),
        'file_permissions': test_file_permissions(),
        'database_connection': test_database_connection(),
        'external_apis': test_external_apis()
    }
    
    return diagnostics

def test_git_access():
    """Test git repository access"""
    try:
        import subprocess
        result = subprocess.run(['git', 'status'], capture_output=True, text=True)
        return {'status': 'ok' if result.returncode == 0 else 'error', 'output': result.stdout}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
```

#### Alternative Data Sources:
```yaml
# Use alternative data sources if primary fails
measurement:
  fallback_enabled: true
  sources:
    primary: "git+performance+tests"
    fallback: "basic+manual"
  
  basic_metrics:
    - "lines_of_code"
    - "file_count"
    - "test_count"
  
  manual_override:
    enabled: true
    quality_score: 8.5  # Manual quality assessment
```

### Issue: Analysis Failures

**Symptoms:**
- Analysis phase crashes
- "Insufficient data" errors
- ML model failures

**Analysis Troubleshooting:**

#### Data Quality Checks:
```python
# analysis/data_validation.py
def validate_analysis_data(data):
    """Validate data before analysis"""
    
    issues = []
    
    # Check data completeness
    if not data or len(data) == 0:
        issues.append("No data provided")
    
    # Check data types
    for key, value in data.items():
        if value is None:
            issues.append(f"Missing value for {key}")
    
    # Check data ranges
    numeric_fields = ['performance', 'quality_score', 'duration']
    for field in numeric_fields:
        if field in data and (data[field] < 0 or data[field] > 100):
            issues.append(f"Invalid range for {field}: {data[field]}")
    
    return issues
```

#### Simplified Analysis Mode:
```bash
# Skip complex analysis if failing
npx claude-flow bmad analyze --mode simple

# Use basic statistical analysis only
npx claude-flow bmad analyze --disable-ml --basic-stats-only

# Manual analysis override
npx claude-flow bmad analyze --manual-mode
```

## Documentation Issues

### Issue: Documentation Generation Fails

**Symptoms:**
- Empty documentation files
- Template processing errors
- Missing documentation sections

**Documentation Fixes:**

#### Template Issues:
```bash
# Validate templates
npx claude-flow bmad template validate --all

# Reset to default templates
npx claude-flow bmad template reset --confirm

# Use basic template if complex ones fail
npx claude-flow bmad document --template basic
```

#### Manual Documentation:
```markdown
<!-- Use this template if auto-generation fails -->
# Manual BMAD Cycle Documentation

## Cycle Overview
- **Cycle ID**: [manual-cycle-001]
- **Duration**: [X hours]
- **Team Size**: [X people]

## Build Phase Results
- Features implemented: [list]
- Tests added/updated: [count]
- Code quality score: [X/10]

## Measure Phase Results
- Performance metrics: [summary]
- Quality metrics: [summary]
- Issues identified: [list]

## Analyze Phase Results
- Key insights: [list]
- Improvement opportunities: [list]
- Recommendations: [list]

## Document Phase Results
- Documentation updated: [list]
- Knowledge captured: [summary]
```

## Emergency Procedures

### Complete System Reset

If BMAD is completely broken and you need to start fresh:

```bash
# 1. Stop all BMAD processes
pkill -f claude-flow

# 2. Clear BMAD state
rm -rf .bmad/
rm -f bmad.config.yml

# 3. Clear npm cache
npm cache clean --force

# 4. Reinstall Claude-Flow
npm uninstall -g claude-flow
npm install -g claude-flow@alpha

# 5. Reinitialize
npx claude-flow bmad init --fresh-start
```

### Recovery from Corrupted State

```bash
# Check for corruption
npx claude-flow bmad doctor --full-check

# Repair common issues
npx claude-flow bmad repair --auto

# Restore from backup if available
npx claude-flow bmad restore --backup-id latest

# Manual state cleanup
npx claude-flow bmad cleanup --reset-locks --clear-temp
```

## Prevention Strategies

### Regular Maintenance

```bash
# Weekly maintenance routine
#!/bin/bash

# Clean up old data
npx claude-flow bmad cleanup --older-than 30d

# Validate configuration
npx claude-flow bmad config validate

# Check system health
npx claude-flow bmad doctor

# Update if needed
npm update -g claude-flow

# Backup current state
npx claude-flow bmad backup --auto
```

### Monitoring Setup

```yaml
# monitoring.yml
monitoring:
  health_checks:
    interval: "5m"
    endpoints:
      - "bmad_status"
      - "cycle_health"
      - "resource_usage"
  
  alerts:
    slack_webhook: "${SLACK_WEBHOOK}"
    email: "team@company.com"
    conditions:
      - "cycle_duration > 8h"
      - "error_rate > 0.1"
      - "resource_usage > 0.9"
```

## Getting Help

### Debug Information Collection

When reporting issues, collect this information:

```bash
# System information
npx claude-flow bmad debug --collect-info > bmad-debug.txt

# Configuration
cat bmad.config.yml

# Recent logs
tail -n 100 ~/.bmad/logs/bmad.log

# System status
npx claude-flow bmad doctor --verbose
```

### Support Channels

1. **Documentation**: Check `/docs/BMAD/` for detailed guides
2. **GitHub Issues**: Report bugs and request features
3. **Community Discussions**: Ask questions and share solutions
4. **Team Chat**: Internal team support (if applicable)

### Escalation Process

1. **Level 1**: Try solutions in this troubleshooting guide
2. **Level 2**: Search existing documentation and issues
3. **Level 3**: Ask in community forums with debug information
4. **Level 4**: Create detailed bug report with reproduction steps

---

*BMAD Troubleshooting Guide v2.0.0*
*Comprehensive problem resolution for BMAD methodology*