# MCP Trading Bot Integration Guide

## ✅ MCP Setup Complete

The MCP (Model Context Protocol) integration is now fully operational in your Alpaca StochRSI EMA Trading Bot project.

## 🚀 Current Status

### Active Swarm
- **Swarm ID**: `swarm_1756140584677_wp3cg7aqx`
- **Topology**: Mesh (optimal for distributed trading operations)
- **Active Agents**: 2
  - Market Analyst (`agent_1756140590460_2cwiod`)
  - Trading Coordinator (`agent_1756140595447_6liaqn`)

### Stored Configuration
- **Key**: `trading_bot_mcp_config`
- **Namespace**: `trading`
- **Storage**: Persistent SQLite with 24-hour TTL

## 📋 How to Use MCP in Your Trading Bot

### 1. Direct MCP Tool Usage (In Claude Code)

```javascript
// Initialize a new swarm
mcp__claude-flow__swarm_init {
  topology: "mesh",
  maxAgents: 8,
  strategy: "adaptive"
}

// Spawn trading agents
mcp__claude-flow__agent_spawn {
  type: "analyst",
  name: "Market Analyst",
  capabilities: ["market_analysis", "signal_generation"]
}

// Orchestrate tasks
mcp__claude-flow__task_orchestrate {
  task: "Analyze AAPL for trading signals",
  priority: "high",
  strategy: "adaptive"
}

// Store trading state
mcp__claude-flow__memory_usage {
  action: "store",
  key: "trading_positions",
  value: JSON.stringify(positions),
  namespace: "trading"
}
```

### 2. Python Integration

Use the provided `scripts/mcp_trading_integration.py` module:

```python
from scripts.mcp_trading_integration import TradingBotMCPEnhancement

# Initialize enhanced bot
bot = TradingBotMCPEnhancement()
await bot.initialize()

# Analyze market
analysis = await bot.analyze_market_conditions()

# Generate signals
signals = await bot.generate_trading_signals()

# Execute trades
execution = await bot.execute_trades(signals)
```

### 3. JavaScript Integration

Use the provided `scripts/mcp_trading_integration.js` module:

```javascript
const { 
  initializeTradingSwarm,
  orchestrateTradingTask,
  storeConfiguration 
} = require('./scripts/mcp_trading_integration');

// Initialize swarm
const swarmId = await initializeTradingSwarm();

// Orchestrate trading task
const taskId = await orchestrateTradingTask(
  "Generate trading signals for AAPL"
);
```

## 🔧 Integration Points with Your Trading Bot

### 1. Market Data Service (Port 9005)
- MCP agents can analyze live market data
- Coordinate data collection across multiple symbols
- Optimize data fetch patterns

### 2. Signal Processing (Port 9003)
- MCP orchestrates indicator calculations
- Distributes signal generation across agents
- Optimizes parameter tuning

### 3. Trading Execution (Port 9002)
- MCP coordinates order placement
- Manages position tracking
- Handles order routing optimization

### 4. Risk Management (Port 9004)
- MCP monitors risk metrics
- Coordinates stop-loss adjustments
- Generates risk alerts

### 5. AI Training Service (Port 9011)
- MCP manages neural network training
- Coordinates pattern recognition
- Optimizes trading strategies

## 📊 Available MCP Commands

### Swarm Management
```bash
# Check status
mcp__claude-flow__swarm_status

# Monitor in real-time
mcp__claude-flow__swarm_monitor { interval: 5 }

# List agents
mcp__claude-flow__agent_list

# Get metrics
mcp__claude-flow__agent_metrics { agentId: "agent_id" }
```

### Task Orchestration
```bash
# Create task
mcp__claude-flow__task_orchestrate {
  task: "Your trading task",
  priority: "high"
}

# Check status
mcp__claude-flow__task_status { taskId: "task_id" }

# Get results
mcp__claude-flow__task_results { taskId: "task_id" }
```

### Memory Management
```bash
# Store data
mcp__claude-flow__memory_usage {
  action: "store",
  key: "your_key",
  value: "your_data",
  namespace: "trading"
}

# Retrieve data
mcp__claude-flow__memory_usage {
  action: "retrieve",
  key: "your_key",
  namespace: "trading"
}

# Search memory
mcp__claude-flow__memory_search {
  pattern: "trading",
  namespace: "trading"
}
```

### Performance Analysis
```bash
# Run benchmarks
mcp__claude-flow__benchmark_run { type: "all" }

# Generate report
mcp__claude-flow__performance_report {
  format: "detailed",
  timeframe: "24h"
}

# Analyze bottlenecks
mcp__claude-flow__bottleneck_analyze {
  component: "trading_execution"
}
```

## 🎯 Trading-Specific Workflows

### 1. Morning Market Analysis
```javascript
// 1. Initialize swarm for the day
mcp__claude-flow__swarm_init { topology: "hierarchical" }

// 2. Spawn analysis agents
mcp__claude-flow__agent_spawn { type: "analyst", name: "Pre-Market Analyst" }

// 3. Orchestrate market scan
mcp__claude-flow__task_orchestrate {
  task: "Scan pre-market movers and analyze overnight news",
  priority: "high"
}
```

### 2. Signal Generation
```javascript
// Orchestrate signal generation across symbols
mcp__claude-flow__task_orchestrate {
  task: "Calculate StochRSI and EMA for watchlist symbols",
  strategy: "parallel",
  maxAgents: 4
}
```

### 3. Position Management
```javascript
// Store positions
mcp__claude-flow__memory_usage {
  action: "store",
  key: "open_positions",
  value: JSON.stringify(positions),
  namespace: "trading"
}

// Monitor positions
mcp__claude-flow__task_orchestrate {
  task: "Monitor open positions and adjust stop-loss levels",
  priority: "critical"
}
```

### 4. End-of-Day Analysis
```javascript
// Generate reports
mcp__claude-flow__task_orchestrate {
  task: "Generate daily P&L report and performance metrics",
  priority: "medium"
}

// Store daily results
mcp__claude-flow__memory_usage {
  action: "store",
  key: `daily_results_${date}`,
  value: JSON.stringify(results),
  namespace: "trading"
}
```

## 🚦 Testing MCP Integration

### Quick Test Commands
```bash
# Test swarm status
mcp__claude-flow__swarm_status

# Test memory storage
mcp__claude-flow__memory_usage {
  action: "store",
  key: "test_key",
  value: "test_value",
  namespace: "trading"
}

# Test task orchestration
mcp__claude-flow__task_orchestrate {
  task: "Test task execution",
  priority: "low"
}
```

### Full Integration Test
```bash
# Run Python test
python scripts/mcp_trading_integration.py

# Run JavaScript test (when MCP server is properly configured)
node scripts/mcp_trading_integration.js
```

## 📈 Benefits of MCP Integration

1. **Parallel Processing**: Execute multiple trading operations simultaneously
2. **Intelligent Coordination**: AI agents work together on complex tasks
3. **Persistent Memory**: Store and retrieve trading state across sessions
4. **Performance Optimization**: Identify and resolve bottlenecks
5. **Adaptive Strategies**: Self-adjusting algorithms based on market conditions
6. **Risk Management**: Coordinated risk monitoring across all positions
7. **Scalability**: Easy to add more agents as trading volume grows

## 🔗 Related Documentation

- [MCP Setup Guide](./MCP_SETUP.md)
- [MCP Workflow Examples](./MCP_WORKFLOW_EXAMPLES.md)
- [CLAUDE.md Configuration](../CLAUDE.md)
- [Microservices Architecture](./MICROSERVICES_ARCHITECTURE.md)

## 💡 Next Steps

1. **Customize Agents**: Modify agent capabilities for your specific trading strategies
2. **Enhance Memory**: Store more detailed trading state and historical data
3. **Optimize Performance**: Use benchmarking tools to improve execution speed
4. **Add Neural Training**: Implement machine learning for signal generation
5. **Scale Operations**: Add more agents for handling increased trading volume

## 🆘 Troubleshooting

### Issue: MCP tools not responding
**Solution**: Restart Claude Code and re-initialize the swarm

### Issue: Memory not persisting
**Solution**: Check namespace parameter and TTL settings

### Issue: Tasks not completing
**Solution**: Monitor task status with `task_status` and check agent availability

### Issue: Performance degradation
**Solution**: Run `bottleneck_analyze` to identify issues

## 📞 Support

For MCP-specific issues:
- [Claude Flow GitHub](https://github.com/ruvnet/claude-flow)
- [MCP Documentation](https://github.com/anthropics/mcp)

For trading bot issues:
- Check logs in `/logs` directory
- Review microservice status at http://localhost:9010
- Monitor swarm health with `swarm_monitor`

---

**Status**: ✅ MCP Integration Complete and Operational
**Last Updated**: 2025-08-25
**Swarm ID**: `swarm_1756140584677_wp3cg7aqx`