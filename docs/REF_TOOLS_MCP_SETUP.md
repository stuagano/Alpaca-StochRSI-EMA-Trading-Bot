# Ref Tools MCP Integration Guide

## Overview
Ref Tools MCP provides efficient documentation search capabilities for the Alpaca Trading Bot project. This integration enables token-efficient access to API documentation, trading guides, and technical references.

## Features
- **Agentic Search**: AI-powered search for exactly the right documentation context
- **Token Efficiency**: Smart filtering to minimize context usage and reduce costs
- **Session Tracking**: Avoids repeated results and optimizes search trajectory
- **Relevant Content Extraction**: Returns only the most relevant 5k tokens from large docs

## Setup Instructions

### Option 1: HTTP Server (Recommended)
Add to your Claude Code MCP configuration:

```json
{
  "Ref": {
    "type": "http",
    "url": "https://api.ref.tools/mcp?apiKey=YOUR_API_KEY"
  }
}
```

### Option 2: Local stdio Server
```json
{
  "Ref": {
    "command": "npx",
    "args": ["ref-tools-mcp@latest"],
    "env": {
      "REF_API_KEY": "YOUR_API_KEY"
    }
  }
}
```

## Available Tools

### 1. `ref_search_documentation`
Search for technical documentation with AI-powered relevance matching.

**Parameters:**
- `query` (required): Full sentence or question about what you're looking for

**Usage Examples:**
```javascript
// Search for Alpaca API documentation
ref_search_documentation("Alpaca Trading API place market order endpoint documentation")

// Search for TradingView charting guides  
ref_search_documentation("TradingView Lightweight Charts real-time data streaming setup")

// Search for risk management patterns
ref_search_documentation("trading bot risk management position sizing best practices")
```

### 2. `ref_read_url`
Fetch and convert webpage content to markdown for detailed reading.

**Parameters:**
- `url` (required): The URL of the webpage to read

**Usage Examples:**
```javascript
// Read specific API documentation
ref_read_url("https://alpaca.markets/docs/api-references/trading-api/orders/")

// Read TradingView documentation
ref_read_url("https://tradingview.github.io/lightweight-charts/docs/getting-started")
```

## Integration with Trading Bot Project

### Common Search Patterns

#### 1. Alpaca API Documentation
```javascript
// Authentication setup
ref_search_documentation("Alpaca API authentication headers API key secret setup")

// Order management
ref_search_documentation("Alpaca API cancel order modify order status endpoints")

// Market data
ref_search_documentation("Alpaca market data real-time streaming WebSocket subscription")

// Account information
ref_search_documentation("Alpaca account endpoint portfolio value buying power")
```

#### 2. TradingView Integration
```javascript
// Chart setup
ref_search_documentation("TradingView Lightweight Charts initialization configuration options")

// Real-time updates
ref_search_documentation("TradingView charts update data real-time streaming best practices")

// Technical indicators
ref_search_documentation("TradingView charts technical indicators RSI MACD EMA implementation")
```

#### 3. Trading Strategy Documentation
```javascript
// Risk management
ref_search_documentation("algorithmic trading risk management stop loss position sizing")

// Technical analysis
ref_search_documentation("Stochastic RSI EMA crossover trading strategy implementation")

// Portfolio management
ref_search_documentation("portfolio rebalancing algorithms dynamic allocation strategies")
```

### Workflow Integration

#### 1. Development Workflow
```bash
# Search for implementation guidance
ref_search_documentation("FastAPI microservices authentication middleware setup")

# Read specific documentation
ref_read_url("https://fastapi.tiangolo.com/tutorial/middleware/")

# Search for testing patterns
ref_search_documentation("Playwright testing financial dashboard real-time data")
```

#### 2. Debugging Workflow
```bash
# Search for error resolution
ref_search_documentation("Alpaca API 422 validation error order placement troubleshooting")

# Find configuration examples
ref_search_documentation("Docker Compose microservices networking port configuration")
```

## Token Efficiency Benefits

### Before Ref Tools MCP
- Manual web searches → copy/paste large documentation pages
- 20k+ tokens for a single API documentation page
- High context pollution reducing model performance
- Expensive token usage (e.g., $0.09 per 6k irrelevant tokens with Claude Opus)

### After Ref Tools MCP  
- AI-powered relevant search results
- Maximum 5k tokens per documentation fetch
- Smart filtering of irrelevant sections
- Session-aware result deduplication
- Significant cost savings and improved model performance

## Cost Analysis Example

**Scenario**: Looking up Alpaca API order placement documentation

**Without Ref Tools**:
- Manual fetch: 15,000 tokens
- Relevant content: ~3,000 tokens
- Waste: 12,000 tokens
- Cost per step (Claude Opus): ~$0.18

**With Ref Tools**:
- Smart fetch: 5,000 tokens
- Relevant content: ~4,500 tokens  
- Waste: 500 tokens
- Cost per step (Claude Opus): ~$0.075
- **Savings**: ~$0.105 per step (58% reduction)

## Best Practices

### 1. Query Formulation
- Use full sentences or questions instead of keywords
- Be specific about what you're trying to accomplish
- Include relevant technology stack in queries

**Good**: "How to implement real-time WebSocket streaming with Alpaca market data API"
**Bad**: "websocket alpaca"

### 2. Iterative Search Strategy
1. Start with broad search to understand available options
2. Refine with specific implementation questions
3. Use `ref_read_url` for detailed implementation guides

### 3. Session Management
- Ref Tools tracks search history within sessions
- Avoid repeating identical searches
- Build on previous search results for deeper investigation

## Integration with Claude Flow MCP

Ref Tools MCP works alongside your existing Claude Flow setup:

```javascript
// Initialize swarm with documentation research capability
mcp__claude-flow__swarm_init({ topology: "mesh", maxAgents: 5 })

// Spawn researcher agent
mcp__claude-flow__agent_spawn({ type: "researcher" })

// Use Ref Tools for documentation research
ref_search_documentation("your research query")

// Store findings in Claude Flow memory
mcp__claude-flow__memory_usage({
  action: "store", 
  key: "research_findings",
  value: "documentation insights",
  namespace: "trading_bot"
})
```

## Testing the Integration

### 1. Basic Search Test
```javascript
ref_search_documentation("Alpaca Trading API getting started authentication setup")
```

### 2. URL Reading Test  
```javascript
ref_read_url("https://alpaca.markets/docs/")
```

### 3. Trading-Specific Test
```javascript
ref_search_documentation("Python alpaca-trade-api library place market order example code")
```

## Troubleshooting

### Common Issues

1. **API Key Not Working**
   - Verify API key from ref.tools
   - Check environment variable setup
   - Ensure proper JSON formatting in MCP config

2. **No Search Results**
   - Try broader search terms
   - Check internet connectivity
   - Verify MCP server is running

3. **Token Limits**
   - Ref Tools automatically limits to 5k tokens
   - Use more specific queries to get better targeted results

### Debug Commands

```bash
# Test MCP server connection
claude mcp list

# Verify Ref Tools is loaded
claude mcp test Ref ref_search_documentation '{"query": "test query"}'
```

## Next Steps

1. **Get API Key**: Sign up at [ref.tools](https://ref.tools) to get your API key
2. **Configure MCP**: Add Ref Tools to your Claude Code MCP configuration  
3. **Test Integration**: Run the basic search tests above
4. **Integrate Workflows**: Start using Ref Tools in your trading bot development

---

*Last Updated: 2025-08-22*
*Status: Ready for Integration*