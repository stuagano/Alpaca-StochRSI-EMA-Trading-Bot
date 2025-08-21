# BMAD Documentation Templates

## Overview

This directory contains reusable templates for generating consistent documentation across all BMAD phases. Templates ensure standardization, completeness, and efficiency in documentation creation.

## Available Templates

### Core BMAD Templates

#### 1. Strategy Documentation Template
**File**: `strategy-template.md`  
**Usage**: Document trading strategies comprehensively
**Includes**: Parameters, logic, performance, examples, risks

#### 2. API Endpoint Template  
**File**: `api-endpoint-template.md`  
**Usage**: Document REST API endpoints
**Includes**: Request/response, authentication, examples, errors

#### 3. Configuration Guide Template
**File**: `config-template.md`  
**Usage**: Document system configuration
**Includes**: Environment variables, files, validation, examples

#### 4. Lessons Learned Template
**File**: `lessons-template.md`  
**Usage**: Capture cycle learnings systematically
**Includes**: Successes, challenges, insights, recommendations

#### 5. Performance Report Template
**File**: `performance-template.md`  
**Usage**: Generate performance analysis reports
**Includes**: Metrics, trends, analysis, recommendations

### Phase-Specific Templates

#### Build Phase Templates
- **Component Template**: `build/component-template.md`
- **Feature Template**: `build/feature-template.md`
- **Bug Fix Template**: `build/bugfix-template.md`

#### Measure Phase Templates
- **Metrics Report**: `measure/metrics-template.md`
- **Dashboard Config**: `measure/dashboard-template.yaml`
- **Alert Config**: `measure/alerts-template.yaml`

#### Analyze Phase Templates
- **Analysis Report**: `analyze/analysis-template.md`
- **Pattern Report**: `analyze/patterns-template.md`
- **Optimization Report**: `analyze/optimization-template.md`

#### Document Phase Templates
- **Documentation Index**: `document/index-template.md`
- **User Guide**: `document/user-guide-template.md`
- **Troubleshooting**: `document/troubleshooting-template.md`

## Template Usage

### Command Line Usage

```bash
# Use specific template
npx claude-flow bmad document --template strategy "new-strategy"

# List available templates
npx claude-flow bmad template list

# Create documentation from template
npx claude-flow bmad template use strategy-template \
  --output "docs/strategies/my-strategy.md" \
  --vars "strategy_name=MyStrategy,version=1.0"
```

### Programmatic Usage

```python
from bmad.templates import TemplateEngine

# Load template
engine = TemplateEngine()
template = engine.load_template("strategy-template.md")

# Render with variables
content = template.render({
    'strategy_name': 'StochRSI Enhanced',
    'version': '2.0.0',
    'author': 'BMAD System',
    'parameters': strategy_params,
    'performance': performance_data
})

# Save rendered content
with open('docs/strategies/stochrsi-enhanced.md', 'w') as f:
    f.write(content)
```

## Template Variables

### Common Variables
All templates support these standard variables:

```yaml
# Basic metadata
name: Component/Strategy/Feature name
version: Version number
author: Author/Creator
timestamp: Current timestamp
project: Project name

# Content sections
description: Detailed description
overview: Brief overview
examples: Usage examples
notes: Additional notes
tags: Categorization tags
```

### Strategy Template Variables
```yaml
# Strategy specific
strategy_name: Strategy name
strategy_type: Type (trend|momentum|mean_reversion)
timeframe: Trading timeframe
parameters: Strategy parameters
entry_conditions: Entry logic
exit_conditions: Exit logic
risk_management: Risk rules
performance_metrics: Historical performance
backtest_results: Backtesting data
```

### API Template Variables
```yaml
# API specific
endpoint_path: API endpoint path
http_method: HTTP method (GET|POST|PUT|DELETE)
authentication: Auth requirements
request_schema: Request format
response_schema: Response format
error_codes: Error responses
rate_limits: Rate limiting info
examples: Usage examples
```

## Custom Templates

### Creating Custom Templates

1. **Create Template File**
```markdown
# {{name}} Custom Documentation

## Overview
{{description}}

## Configuration
```yaml
{{configuration}}
```

## Usage
{{usage_instructions}}

## Examples
{{examples}}

---
*Generated: {{timestamp}}*
*Version: {{version}}*
```

2. **Register Template**
```python
# Register custom template
engine.register_template("custom-template", "path/to/template.md")
```

3. **Use Custom Template**
```bash
npx claude-flow bmad template use custom-template \
  --vars "name=MyComponent,description=Custom component"
```

### Template Inheritance

Templates can extend other templates:

```markdown
<!-- Extends: base-template.md -->

# Extended {{name}} Documentation

{{> base_content}}

## Additional Section
{{additional_content}}
```

## Template Best Practices

### 1. Consistent Structure
- Use standard section headers
- Include required metadata
- Follow naming conventions
- Maintain consistent formatting

### 2. Variable Usage
- Use descriptive variable names
- Provide default values
- Include variable documentation
- Validate required variables

### 3. Content Guidelines
- Write clear, concise content
- Include practical examples
- Provide troubleshooting tips
- Link to related documentation

### 4. Template Maintenance
- Version control templates
- Test template rendering
- Update regularly
- Document template changes

## Template Validation

### Validation Rules
```yaml
# Template validation schema
validation:
  required_sections:
    - overview
    - configuration
    - examples
  
  required_variables:
    - name
    - version
    - timestamp
  
  formatting:
    max_line_length: 120
    heading_style: "atx"
    code_block_style: "fenced"
```

### Validation Commands
```bash
# Validate template
npx claude-flow bmad template validate strategy-template.md

# Validate all templates
npx claude-flow bmad template validate-all

# Check template completeness
npx claude-flow bmad template check-completeness
```

## Integration Examples

### Automated Documentation Generation

```python
class AutoDocGenerator:
    def __init__(self):
        self.engine = TemplateEngine()
    
    def generate_strategy_docs(self, strategy):
        """Auto-generate strategy documentation"""
        
        # Prepare template variables
        variables = {
            'strategy_name': strategy.name,
            'version': strategy.version,
            'description': strategy.description,
            'parameters': self.extract_parameters(strategy),
            'performance': self.get_performance_data(strategy),
            'timestamp': datetime.now().isoformat()
        }
        
        # Render template
        content = self.engine.render_template(
            'strategy-template.md',
            variables
        )
        
        # Save documentation
        output_path = f"docs/strategies/{strategy.name.lower()}.md"
        with open(output_path, 'w') as f:
            f.write(content)
        
        return output_path
```

### CI/CD Integration

```yaml
# .github/workflows/documentation.yml
name: Auto-Generate Documentation

on:
  push:
    paths:
      - 'strategies/**'
      - 'indicators/**'

jobs:
  generate-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Generate Documentation
        run: |
          npx claude-flow bmad template use strategy-template \
            --auto-detect-variables \
            --output-dir docs/strategies/
          
          npx claude-flow bmad template use api-template \
            --from-openapi api/openapi.yaml \
            --output docs/api/
      
      - name: Commit Documentation
        run: |
          git add docs/
          git commit -m "Auto-update documentation"
          git push
```

## Template Library

### Community Templates
- **Basic Strategy**: Simple trading strategy documentation
- **Complex Strategy**: Multi-component strategy with dependencies
- **API Service**: Microservice API documentation
- **Configuration**: System configuration guide
- **Troubleshooting**: Problem resolution guide

### Industry-Specific Templates
- **Financial**: Trading, risk management, compliance
- **Technical**: System architecture, deployment
- **User**: End-user guides, tutorials
- **Developer**: API references, code examples

## Future Enhancements

### Planned Features
- **Interactive Templates**: Dynamic content generation
- **Multi-Language**: Support for multiple output languages
- **Visual Templates**: Include charts and diagrams
- **Collaborative**: Team-based template editing

### Roadmap
1. **Q1**: Enhanced variable validation
2. **Q2**: Interactive template editor
3. **Q3**: Multi-format output (PDF, HTML)
4. **Q4**: AI-assisted template generation

## Support

### Template Issues
- Report template bugs via GitHub issues
- Request new templates via feature requests
- Contribute templates via pull requests

### Documentation
- Template usage examples in `/examples/`
- Video tutorials in `/tutorials/`
- Best practices guide in `/guides/`

---

*BMAD Templates v2.0.0*  
*Part of BMAD Documentation System*