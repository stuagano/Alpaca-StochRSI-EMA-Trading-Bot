# MCP Claude Flow Setup Guide

## Overview
This document provides the complete setup and configuration for Claude Flow MCP (Model Context Protocol) server integration in the Alpaca Trading Bot project.

## Installation Status
✅ **MCP Claude Flow is fully configured and operational**

### Verified Components
- ✅ Node.js v22.16.0
- ✅ npm v11.5.1
- ✅ Claude CLI v1.0.70
- ✅ Claude Flow v2.0.0-alpha.88 (globally installed)
- ✅ MCP server integration working
- ✅ Swarm initialization successful
- ✅ Agent spawning functional
- ✅ Task orchestration working
- ✅ Memory management operational
- ✅ All test cases passing

## Quick Start Commands

### 1. Initialize Swarm
```bash
# Using MCP tools directly in Claude Code
mcp__claude-flow__swarm_init { topology: "mesh", maxAgents: 5 }
```

### 2. Spawn Agents
```bash
# Spawn specialized agents
mcp__claude-flow__agent_spawn { type: "researcher" }
mcp__claude-flow__agent_spawn { type: "coder" }
mcp__claude-flow__agent_spawn { type: "tester" }
```

### 3. BMAD Commands
```bash
# Build new features
npx claude-flow@alpha bmad build "<feature>"

# Measure performance
npx claude-flow@alpha bmad measure "<metrics>"

# Analyze results
npx claude-flow@alpha bmad analyze "<data>"

# Document findings
npx claude-flow@alpha bmad document "<topic>"

# Run complete cycle
npx claude-flow@alpha bmad cycle "<task>"
```

## Test Workflow
A test script is available to validate MCP functionality:

```bash
node scripts/test_mcp_workflow.js
```

## Installation Instructions

### Global Installation (Completed)
```bash
# Claude Flow is already installed globally
npm install -g claude-flow@alpha

# Verify installation
claude-flow --version  # Should show: v2.0.0-alpha.88
```

### MCP Server Configuration
The MCP server is configured to work with Claude Code through the MCP protocol. 
Claude Flow acts as an MCP server that Claude Code can communicate with.

## Current Swarm Status
- **Latest Swarm ID**: swarm_1755881324350_ddsssuv5k
- **Topology**: Hierarchical
- **Max Agents**: 8
- **Strategy**: Adaptive
- **Active Agents**: 1 (MasterCoordinator)

## Available MCP Tools

### Core Coordination (Claude Flow)
- `swarm_init` - Initialize swarm with topology
- `agent_spawn` - Create specialized agents
- `task_orchestrate` - Orchestrate complex tasks
- `swarm_status` - Check swarm health

### Memory & Neural (Claude Flow)
- `memory_usage` - Store/retrieve persistent memory
- `neural_status` - Check neural network status
- `neural_train` - Train patterns with WASM SIMD
- `neural_patterns` - Analyze cognitive patterns

### Performance (Claude Flow)
- `benchmark_run` - Run performance benchmarks
- `performance_report` - Generate performance reports
- `bottleneck_analyze` - Identify bottlenecks

### GitHub Integration (Claude Flow)
- `github_repo_analyze` - Analyze repositories
- `github_pr_manage` - Manage pull requests
- `github_code_review` - Automated code review

### Documentation Search (Ref Tools MCP)
- `ref_search_documentation` - AI-powered search for technical documentation
- `ref_read_url` - Fetch and convert web pages to markdown for detailed reading

## Project Integration

### Current Tasks
The MCP system has been integrated with the following project components:
1. Trading bot core functionality
2. Risk management system
3. API endpoints
4. Dashboard interfaces
5. Testing frameworks

### Memory Storage
Project setup information has been stored in MCP memory:
- **Key**: project_setup
- **Namespace**: default
- **Content**: MCP Claude Flow setup complete for Alpaca Trading Bot project

## Troubleshooting

### Common Issues and Solutions

1. **MCP server already exists error**
   - This is normal if Claude Flow was previously configured
   - The server is already available for use

2. **Command not found errors**
   - Ensure Node.js is installed: `node --version`
   - Verify npm is available: `npm --version`
   - Check Claude CLI: `claude --version`

3. **Swarm initialization fails**
   - Restart Claude Code
   - Re-run the MCP add command: `claude mcp add claude-flow npx claude-flow@alpha mcp start`

## Best Practices

1. **Always use concurrent operations** - Batch multiple MCP calls in a single message
2. **Initialize swarm at start** - Begin sessions with swarm_init
3. **Monitor performance** - Use swarm_status regularly
4. **Store context in memory** - Use memory_usage for persistence
5. **Clean shutdown** - Use swarm_destroy when finished

## Resources
- [Claude Flow Documentation](https://github.com/ruvnet/claude-flow)
- [MCP Protocol Spec](https://github.com/anthropics/mcp)
- [Project CLAUDE.md](./CLAUDE.md)

## MCP Server Configuration

### Current Servers
1. **Claude Flow** - Swarm coordination and task orchestration
2. **Ref Tools** - Documentation search and web content fetching (see [REF_TOOLS_MCP_SETUP.md](./REF_TOOLS_MCP_SETUP.md))

### Adding Ref Tools MCP
To add Ref Tools for documentation search capabilities:

```bash
# Get API key from ref.tools first, then add to Claude Code:
claude mcp add ref-tools https://api.ref.tools/mcp?apiKey=YOUR_API_KEY
```

Or configure manually in Claude Code settings:
```json
{
  "Ref": {
    "type": "http", 
    "url": "https://api.ref.tools/mcp?apiKey=YOUR_API_KEY"
  }
}
```

## Next Steps
1. **Set up Ref Tools MCP** - Get API key and configure documentation search
2. Run the test workflow: `node scripts/test_mcp_workflow.js`
3. Explore BMAD methodology with live tasks
4. Integrate swarm agents into development workflow
5. Enable GitHub integration for automated PR management
6. Use Ref Tools for efficient Alpaca API and TradingView documentation lookup

---

*Last Updated: 2025-08-22*
*Status: Fully Operational*