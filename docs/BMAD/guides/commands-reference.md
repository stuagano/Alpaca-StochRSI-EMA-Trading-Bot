# BMAD Commands Reference Guide

## Overview

This guide provides comprehensive documentation for all BMAD-related commands available through Claude-Flow integration. These commands enable systematic execution of the Build, Measure, Analyze, and Document phases.

## Installation

```bash
# Install Claude-Flow with BMAD support
npm install -g claude-flow@alpha

# Or use npx (recommended)
npx claude-flow@alpha bmad --help
```

## Core BMAD Commands

### Initialize BMAD Workflow

```bash
npx claude-flow bmad init [options]

Options:
  --project <name>      Project name
  --config <file>       Configuration file path
  --template <type>     Project template (trading|web|api|ml)
  --verbose            Enable verbose output
  
Example:
  npx claude-flow bmad init --project "trading-bot" --template trading
```

### Run Complete BMAD Cycle

```bash
npx claude-flow bmad cycle <task> [options]

Arguments:
  task                  Task or feature to cycle through

Options:
  --iterations <n>      Number of BMAD iterations (default: 1)
  --parallel           Run phases in parallel where possible
  --report             Generate cycle report
  --metrics            Track cycle metrics
  
Example:
  npx claude-flow bmad cycle "implement-new-indicator" --iterations 3 --report
```

## Phase-Specific Commands

### Build Phase Commands

```bash
# Start build phase
npx claude-flow bmad build <component> [options]

Options:
  --type <type>        Component type (feature|fix|refactor|test)
  --priority <level>   Priority level (low|medium|high|critical)
  --estimate <time>    Time estimate (e.g., "2h", "1d")
  --dependencies       List dependencies
  --test              Run tests during build
  --watch             Watch mode for continuous building
  
Examples:
  npx claude-flow bmad build "stoch-rsi-indicator" --type feature --priority high
  npx claude-flow bmad build "fix-order-execution" --type fix --test
  npx claude-flow bmad build "refactor-api" --watch
```

### Measure Phase Commands

```bash
# Start measure phase
npx claude-flow bmad measure <metrics> [options]

Options:
  --component <name>   Specific component to measure
  --duration <time>    Measurement duration
  --interval <time>    Sampling interval
  --output <format>    Output format (json|csv|html)
  --realtime          Real-time measurement mode
  --dashboard         Launch metrics dashboard
  
Examples:
  npx claude-flow bmad measure "performance" --duration 1h --interval 10s
  npx claude-flow bmad measure "trading-metrics" --realtime --dashboard
  npx claude-flow bmad measure "system-resources" --output json
```

### Analyze Phase Commands

```bash
# Start analyze phase
npx claude-flow bmad analyze <data> [options]

Options:
  --input <file>       Input data file
  --type <analysis>    Analysis type (statistical|ml|pattern|bottleneck)
  --depth <level>      Analysis depth (shallow|normal|deep)
  --visualize         Generate visualizations
  --ml-enabled        Enable machine learning analysis
  --report           Generate analysis report
  
Examples:
  npx claude-flow bmad analyze "metrics.json" --type statistical --visualize
  npx claude-flow bmad analyze "performance-data" --depth deep --ml-enabled
  npx claude-flow bmad analyze "trading-results" --report --type pattern
```

### Document Phase Commands

```bash
# Start document phase
npx claude-flow bmad document <topic> [options]

Options:
  --type <doc-type>    Documentation type (api|strategy|guide|lesson)
  --format <format>    Output format (md|html|pdf|yaml)
  --template <name>    Use specific template
  --auto-generate     Auto-generate from code
  --validate         Validate existing documentation
  --deploy           Deploy to documentation site
  
Examples:
  npx claude-flow bmad document "api-endpoints" --type api --format yaml
  npx claude-flow bmad document "lessons-learned" --type lesson
  npx claude-flow bmad document "all" --auto-generate --validate --deploy
```

## Workflow Commands

### Iteration Management

```bash
# Run iterative improvement
npx claude-flow bmad iterate <feature> [options]

Options:
  --max-iterations <n>  Maximum iterations
  --target-metric <m>   Target metric to achieve
  --threshold <value>   Success threshold
  --auto-optimize      Enable automatic optimization
  
Example:
  npx claude-flow bmad iterate "strategy-optimization" \
    --max-iterations 10 \
    --target-metric "sharpe_ratio" \
    --threshold 2.0
```

### Optimization Commands

```bash
# Run optimization workflow
npx claude-flow bmad optimize <component> [options]

Options:
  --metrics <list>     Metrics to optimize
  --constraints       Apply constraints
  --algorithm <type>   Optimization algorithm
  --parallel          Parallel optimization
  
Example:
  npx claude-flow bmad optimize "trading-strategy" \
    --metrics "return,drawdown" \
    --algorithm genetic
```

## Integration Commands

### Swarm Integration

```bash
# Initialize BMAD with swarm support
npx claude-flow bmad swarm init [options]

Options:
  --topology <type>    Swarm topology (mesh|hierarchical|star)
  --agents <n>        Number of agents
  --phases <list>     Phases to parallelize
  
Example:
  npx claude-flow bmad swarm init \
    --topology hierarchical \
    --agents 8 \
    --phases "build,measure,analyze"
```

### CI/CD Integration

```bash
# Setup BMAD CI/CD pipeline
npx claude-flow bmad cicd setup [options]

Options:
  --platform <name>    CI/CD platform (github|gitlab|jenkins)
  --triggers <list>    Trigger events
  --stages <list>      Pipeline stages
  
Example:
  npx claude-flow bmad cicd setup \
    --platform github \
    --triggers "push,pr" \
    --stages "build,test,measure,deploy"
```

## Monitoring Commands

### Real-time Monitoring

```bash
# Monitor BMAD execution
npx claude-flow bmad monitor [options]

Options:
  --phase <name>       Monitor specific phase
  --metrics           Show metrics
  --logs             Show logs
  --dashboard        Launch monitoring dashboard
  
Example:
  npx claude-flow bmad monitor --dashboard --metrics
```

### Progress Tracking

```bash
# Track BMAD progress
npx claude-flow bmad progress [options]

Options:
  --cycle <id>        Specific cycle ID
  --detailed         Show detailed progress
  --export <file>     Export progress report
  
Example:
  npx claude-flow bmad progress --cycle current --detailed
```

## Reporting Commands

### Generate Reports

```bash
# Generate BMAD reports
npx claude-flow bmad report <type> [options]

Options:
  --cycle <id>        Cycle ID
  --format <format>   Report format (html|pdf|json)
  --include <list>    Sections to include
  --email <address>   Email report
  
Examples:
  npx claude-flow bmad report cycle --format pdf
  npx claude-flow bmad report performance --include "metrics,analysis"
  npx claude-flow bmad report summary --email team@example.com
```

### Export Data

```bash
# Export BMAD data
npx claude-flow bmad export <data> [options]

Options:
  --format <format>   Export format
  --period <range>    Time period
  --compress         Compress output
  
Example:
  npx claude-flow bmad export metrics --format csv --period "last-7d"
```

## Configuration Commands

### Manage Configuration

```bash
# Configure BMAD settings
npx claude-flow bmad config <action> [options]

Actions:
  get <key>          Get configuration value
  set <key> <value>  Set configuration value
  list              List all configurations
  validate          Validate configuration
  
Examples:
  npx claude-flow bmad config set phases.build.timeout 300
  npx claude-flow bmad config get metrics.collection.interval
  npx claude-flow bmad config validate
```

### Template Management

```bash
# Manage BMAD templates
npx claude-flow bmad template <action> [options]

Actions:
  list              List available templates
  create <name>     Create new template
  use <name>        Use specific template
  export <name>     Export template
  
Example:
  npx claude-flow bmad template create "custom-trading"
```

## Advanced Commands

### Machine Learning Integration

```bash
# ML-enhanced BMAD operations
npx claude-flow bmad ml <operation> [options]

Operations:
  train             Train ML models on BMAD data
  predict           Make predictions
  optimize          ML-driven optimization
  analyze           ML-powered analysis
  
Example:
  npx claude-flow bmad ml train --data "historical-metrics.json"
```

### Batch Operations

```bash
# Batch BMAD operations
npx claude-flow bmad batch <file> [options]

Options:
  --parallel <n>     Parallel execution threads
  --on-error <act>   Error handling (stop|continue|retry)
  --report          Generate batch report
  
Example:
  npx claude-flow bmad batch operations.yaml --parallel 4
```

## Command Aliases

### Quick Commands

```bash
# Shortcuts for common operations
bmad-build    -> npx claude-flow bmad build
bmad-measure  -> npx claude-flow bmad measure
bmad-analyze  -> npx claude-flow bmad analyze
bmad-document -> npx claude-flow bmad document
bmad-cycle    -> npx claude-flow bmad cycle
```

### Custom Aliases

```bash
# Create custom aliases
npx claude-flow bmad alias create <name> <command>

Example:
  npx claude-flow bmad alias create "quick-test" \
    "bmad build --test && bmad measure performance"
```

## Environment Variables

```bash
# BMAD environment variables
BMAD_CONFIG_PATH      # Configuration file path
BMAD_LOG_LEVEL        # Logging level (debug|info|warn|error)
BMAD_OUTPUT_DIR       # Output directory for reports
BMAD_PARALLEL         # Enable parallel execution
BMAD_AUTO_DOCUMENT    # Auto-generate documentation
BMAD_METRICS_URL      # Metrics endpoint URL
BMAD_DASHBOARD_PORT   # Dashboard port number
```

## Error Handling

### Common Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| BMAD001 | Configuration not found | Run `bmad init` first |
| BMAD002 | Invalid phase | Check phase name spelling |
| BMAD003 | Metrics collection failed | Verify metrics endpoint |
| BMAD004 | Analysis error | Check input data format |
| BMAD005 | Documentation generation failed | Verify template exists |

### Debug Commands

```bash
# Debug BMAD operations
npx claude-flow bmad debug [options]

Options:
  --verbose         Verbose output
  --trace          Show stack traces
  --dry-run        Simulate execution
  --validate       Validate without executing
  
Example:
  npx claude-flow bmad debug --verbose --trace
```

## Best Practices

1. **Always Initialize First**
   ```bash
   npx claude-flow bmad init
   ```

2. **Use Configuration Files**
   ```bash
   npx claude-flow bmad cycle "task" --config bmad.config.yml
   ```

3. **Enable Metrics Collection**
   ```bash
   npx claude-flow bmad measure --continuous
   ```

4. **Automate Documentation**
   ```bash
   npx claude-flow bmad document --auto-generate
   ```

5. **Review Reports Regularly**
   ```bash
   npx claude-flow bmad report summary --schedule daily
   ```

## Troubleshooting

### Check BMAD Status

```bash
npx claude-flow bmad status
```

### Reset BMAD State

```bash
npx claude-flow bmad reset --confirm
```

### Get Help

```bash
npx claude-flow bmad help <command>
npx claude-flow bmad --version
```

## Conclusion

The BMAD command-line interface provides comprehensive control over the entire development lifecycle. By mastering these commands, teams can implement systematic, data-driven development practices that lead to continuous improvement.

---

*BMAD Commands Reference v2.0.0*
*Part of Claude-Flow Integration*