# MCP Workflow Examples for Trading Bot Development

## Overview
This document provides practical examples of using MCP tools (Claude Flow + Ref Tools) for efficient trading bot development workflows.

## Setup Requirements
1. **Claude Flow MCP** - Already configured ✅
2. **Ref Tools MCP** - Configure with API key: `ref-8524f3d9b07eaa536507`

## Workflow Examples

### 1. Research → Implement → Test Workflow

#### Step 1: Initialize Development Swarm
```javascript
// Start with swarm coordination
mcp__claude-flow__swarm_init({ topology: "mesh", maxAgents: 6 })

// Spawn specialized agents
mcp__claude-flow__agent_spawn({ type: "researcher" })
mcp__claude-flow__agent_spawn({ type: "coder" })
mcp__claude-flow__agent_spawn({ type: "tester" })
```

#### Step 2: Research API Documentation
```javascript
// Search for specific Alpaca API functionality
ref_search_documentation("Alpaca API place bracket order with stop loss take profit Python")

// Read detailed implementation guide
ref_read_url("https://alpaca.markets/docs/api-references/trading-api/orders/#bracket-orders")

// Search for error handling patterns
ref_search_documentation("Alpaca API error handling retry mechanisms rate limiting best practices")
```

#### Step 3: Store Research Findings
```javascript
// Store documentation findings in memory
mcp__claude-flow__memory_usage({
  action: "store",
  key: "bracket_order_implementation",
  value: "Alpaca bracket orders require parent order with stop_loss and take_profit parameters",
  namespace: "trading_bot"
})

// Store error handling patterns
mcp__claude-flow__memory_usage({
  action: "store", 
  key: "alpaca_error_handling",
  value: "Implement exponential backoff for 429 rate limit errors",
  namespace: "trading_bot"
})
```

#### Step 4: Orchestrate Implementation
```javascript
// Orchestrate development task with research context
mcp__claude-flow__task_orchestrate({
  task: "implement bracket order functionality with proper error handling",
  strategy: "adaptive",
  priority: "high"
})
```

### 2. Frontend Development Workflow

#### Research TradingView Integration
```javascript
// Initialize frontend development swarm
mcp__claude-flow__swarm_init({ topology: "hierarchical", maxAgents: 4 })
mcp__claude-flow__agent_spawn({ type: "frontend-dev" })

// Research TradingView Lightweight Charts
ref_search_documentation("TradingView Lightweight Charts real-time candlestick data update JavaScript")

// Get implementation examples
ref_read_url("https://tradingview.github.io/lightweight-charts/docs/getting-started")

// Search for WebSocket integration patterns
ref_search_documentation("TradingView charts WebSocket real-time data streaming best practices")
```

#### Store Frontend Research
```javascript
mcp__claude-flow__memory_usage({
  action: "store",
  key: "tradingview_implementation",
  value: "Use chart.update() method for real-time data, implement WebSocket for streaming",
  namespace: "frontend"
})
```

### 3. Risk Management Research Workflow

#### Research Trading Strategies
```javascript
// Spawn risk management specialist
mcp__claude-flow__agent_spawn({ type: "risk-analyst" })

// Research position sizing strategies
ref_search_documentation("algorithmic trading position sizing Kelly criterion risk management python")

// Research stop loss strategies
ref_search_documentation("trailing stop loss implementation dynamic stop loss trading strategies")

// Research portfolio risk metrics
ref_search_documentation("portfolio risk metrics VaR Sharpe ratio maximum drawdown calculation")
```

#### Store Risk Management Knowledge
```javascript
// Store position sizing research
mcp__claude-flow__memory_usage({
  action: "store",
  key: "position_sizing_strategy", 
  value: "Implement Kelly criterion with maximum 2% risk per trade",
  namespace: "risk_management"
})

// Store stop loss patterns
mcp__claude-flow__memory_usage({
  action: "store",
  key: "stop_loss_implementation",
  value: "Use ATR-based trailing stops with 2x ATR distance",
  namespace: "risk_management"
})
```

### 4. Debugging Workflow

#### Research Error Resolution
```javascript
// When encountering specific errors, research solutions
ref_search_documentation("FastAPI 422 validation error request body parsing troubleshooting")

// Search for specific error patterns
ref_search_documentation("Alpaca API insufficient buying power error handling best practices")

// Research testing strategies
ref_search_documentation("Playwright testing financial applications form submission automation")
```

#### Document Solutions
```javascript
// Store debugging solutions
mcp__claude-flow__memory_usage({
  action: "store",
  key: "fastapi_422_fix",
  value: "Validate request models match API expectations, check required fields",
  namespace: "debugging"
})
```

### 5. Performance Optimization Workflow

#### Research Performance Patterns
```javascript
// Initialize performance optimization swarm
mcp__claude-flow__agent_spawn({ type: "performance-analyst" })

// Research microservices optimization
ref_search_documentation("FastAPI microservices performance optimization async database connections")

// Research caching strategies  
ref_search_documentation("Redis caching trading data real-time market data performance optimization")

// Research database optimization
ref_search_documentation("PostgreSQL performance tuning trading applications time series data")
```

#### Orchestrate Optimization Tasks
```javascript
mcp__claude-flow__task_orchestrate({
  task: "optimize microservices performance based on research findings",
  strategy: "parallel",
  priority: "medium"
})
```

## Advanced Patterns

### 1. Session-Aware Research
Ref Tools automatically tracks your search history within a session to avoid duplicate results:

```javascript
// First search
ref_search_documentation("Alpaca API authentication")

// Refined search - won't return duplicate results
ref_search_documentation("Alpaca API authentication environment variables best practices")

// Even more specific search - builds on previous context
ref_search_documentation("Alpaca API authentication docker container secrets management")
```

### 2. Cross-Reference Pattern
Use multiple searches to build comprehensive understanding:

```javascript
// Search multiple related topics
ref_search_documentation("Alpaca API WebSocket streaming market data")
ref_search_documentation("Python asyncio WebSocket client implementation")
ref_search_documentation("FastAPI WebSocket endpoint real-time data broadcasting")

// Synthesize findings
mcp__claude-flow__memory_usage({
  action: "store",
  key: "websocket_architecture",
  value: "Combine Alpaca WebSocket client with FastAPI WebSocket endpoints for real-time data flow",
  namespace: "architecture"
})
```

### 3. Documentation Validation Pattern
Verify implementation against official documentation:

```javascript
// After implementing a feature, validate against docs
ref_search_documentation("Alpaca API order placement validation required fields")

// Read official specification
ref_read_url("https://alpaca.markets/docs/api-references/trading-api/orders/")

// Cross-check with community best practices
ref_search_documentation("Alpaca API order placement error handling community examples")
```

## Token Efficiency Examples

### Before MCP Integration
```javascript
// Manual approach - high token usage
// 1. Search web manually
// 2. Copy/paste large documentation pages (15k+ tokens)
// 3. Extract relevant information manually
// 4. High context pollution
// Cost: ~$0.18 per documentation lookup (Claude Opus)
```

### After MCP Integration
```javascript
// Efficient MCP approach
ref_search_documentation("specific targeted query")  // ~100 tokens
// Returns 5k tokens of highly relevant content
// Cost: ~$0.075 per documentation lookup (Claude Opus)
// Savings: 58% cost reduction
```

## Best Practices

### 1. Query Formulation
```javascript
// ❌ Too broad
ref_search_documentation("trading API")

// ✅ Specific and actionable
ref_search_documentation("Alpaca API place market order with error handling Python example")
```

### 2. Iterative Research
```javascript
// Start broad, then narrow down
ref_search_documentation("algorithmic trading risk management strategies")
ref_search_documentation("position sizing Kelly criterion implementation python")
ref_search_documentation("Kelly criterion trading risk percentage calculation example")
```

### 3. Memory Management
```javascript
// Store key findings for later reference
mcp__claude-flow__memory_usage({
  action: "store",
  key: "research_session_" + Date.now(),
  value: JSON.stringify({
    topic: "bracket_orders",
    findings: ["requires parent order", "stop_loss and take_profit params"],
    implementation_notes: "use alpaca.submit_order() with order_class='bracket'"
  }),
  namespace: "research"
})
```

### 4. Swarm Coordination
```javascript
// Coordinate multiple agents with documentation context
mcp__claude-flow__task_orchestrate({
  task: "implement feature based on documentation research",
  strategy: "sequential",
  context: "use findings from bracket_order_implementation memory key"
})
```

## Troubleshooting

### Common Issues

1. **MCP Server Not Found**
   ```bash
   # Add Ref Tools MCP
   claude mcp add ref-tools "https://api.ref.tools/mcp?apiKey=ref-8524f3d9b07eaa536507"
   ```

2. **No Search Results**
   - Try broader search terms
   - Check internet connectivity
   - Verify API key is valid

3. **Token Limits**
   - Ref Tools automatically limits to 5k tokens
   - Use more specific queries for targeted results

### Debug Commands
```bash
# List available MCP servers
claude mcp list

# Test Ref Tools connection
claude mcp test Ref ref_search_documentation '{"query": "test"}'
```

## Next Steps

1. **Configure Ref Tools MCP** using the provided API key
2. **Start with simple queries** to test the integration
3. **Integrate into development workflow** for real projects
4. **Combine with Claude Flow** for powerful swarm-based development

---

*Example workflows for efficient trading bot development using MCP tools*