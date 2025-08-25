# Claude Code Configuration - BMAD Development Environment

## 🚨 CRITICAL: CONCURRENT EXECUTION & FILE MANAGEMENT

**ABSOLUTE RULES**:
1. ALL operations MUST be concurrent/parallel in a single message
2. **NEVER save working files, text/mds and tests to the root folder**
3. ALWAYS organize files in appropriate subdirectories
4. **CONSISTENT PORT USAGE** - Frontend is on port 9100, microservices on 9000-9012

### ⚡ GOLDEN RULE: "1 MESSAGE = ALL RELATED OPERATIONS"

**MANDATORY PATTERNS:**
- **TodoWrite**: ALWAYS batch ALL todos in ONE call (5-10+ todos minimum)
- **Task tool**: ALWAYS spawn ALL agents in ONE message with full instructions
- **File operations**: ALWAYS batch ALL reads/writes/edits in ONE message
- **Bash commands**: ALWAYS batch ALL terminal operations in ONE message
- **Memory operations**: ALWAYS batch ALL memory store/retrieve in ONE message

### 📁 File Organization Rules

**NEVER save to root folder. Use these directories:**
- `/src` - Source code files
- `/tests` - Test files
- `/docs` - Documentation and markdown files
- `/config` - Configuration files
- `/scripts` - Utility scripts
- `/examples` - Example code

### 📚 Documentation Management (BMAD Method)

**CRITICAL DOCUMENTATION RULES:**
1. **ALWAYS check for existing documentation** before creating new files
2. **UPDATE existing docs** instead of creating duplicates
3. **Follow BMAD method**: Build → Measure → Analyze → Document
4. **NEVER create new docs** when an existing file covers the same topic

**Documentation Structure:**
```
/docs/
├── API/              # API specifications and endpoints
├── ARCHITECTURE/     # System design and architecture
├── DEPLOYMENT/       # Deployment guides and configs
├── EPICS/           # Epic-specific documentation
├── GUIDES/          # User and developer guides
├── IMPLEMENTATION/   # Implementation details
├── TESTING/         # Testing strategies and reports
└── README.md        # Main documentation index
```

**Before Creating ANY Documentation:**
1. Search existing docs with: `Grep -i "topic" docs/`
2. Check if topic exists in any current file
3. If exists → UPDATE that file
4. If new topic → Place in appropriate subfolder
5. NEVER duplicate information across files

### 🌳 Source Tree Maintenance

**CRITICAL: Keep `/docs/sourcetree.md` Updated**
1. **UPDATE sourcetree.md** whenever:
   - New directories are created
   - Major files are added or moved
   - Project structure changes
   - New modules/components are introduced
2. **ALWAYS check sourcetree.md** before asking about project structure
3. **Use sourcetree.md** as the single source of truth for project layout

## Project Overview

This project uses BMAD (Build, Measure, Analyze, Document) methodology with Claude-Flow orchestration for systematic iterative development and continuous improvement.

## 🏗️ Microservices Architecture (CRITICAL)

**PORT ALLOCATION:**
- **Frontend (Main):** 9100 - Primary React-based trading platform
- **API Gateway:** 9000 - Central routing and authentication
- **Position Management:** 9001 - Portfolio tracking
- **Trading Execution:** 9002 - Order execution and Alpaca API
- **Signal Processing:** 9003 - Technical indicators and signals
- **Risk Management:** 9004 - Risk controls and limits
- **Market Data:** 9005 - Live data feeds
- **Historical Data:** 9006 - Data storage and retrieval
- **Analytics:** 9007 - Performance metrics
- **Notification:** 9008 - Alerts and messaging
- **Configuration:** 9009 - System settings
- **Health Monitor:** 9010 - Service monitoring
- **Training Service:** 9011 - AI collaborative trading
- **Crypto Trading:** 9012 - 24/7 cryptocurrency trading (NEW)

**MAIN ENTRY POINTS:**
- **Primary:** http://localhost:9100/ (Frontend Service)
- **API Gateway:** http://localhost:9000/
- **Training AI:** http://localhost:9011/
- **Training Docs:** http://localhost:9011/docs
- **Crypto API:** http://localhost:9012/ - 24/7 cryptocurrency trading
- **Crypto Health:** http://localhost:9012/health

## 🪙 Crypto Trading Features (NEW)

**24/7 Cryptocurrency Trading:**
- **Supported Pairs:** BTC/USD, ETH/USD, LTC/USD, BCH/USD, LINK/USD, UNI/USD, AAVE/USD, MKR/USD, MATIC/USD, AVAX/USD, BTC/USDT, ETH/USDT, BTC/USDC, ETH/USDC
- **Trading Hours:** 24/7 - Never closes (crypto markets are always open)
- **Order Types:** Market, Limit orders with fractional support
- **Min Order:** 0.0001 (fractional orders)
- **Max Order:** $200,000 per order
- **Settlement:** T+0 (instant settlement)
- **Margin:** Not allowed for crypto
- **Shorting:** Not allowed for crypto
- **Real-time:** WebSocket streaming for live quotes and data
- **API Endpoints:**
  - `/api/crypto/assets` - Available crypto assets
  - `/api/crypto/positions` - Current crypto positions
  - `/api/crypto/orders` - Submit crypto orders
  - `/api/crypto/quotes/{symbol}` - Real-time crypto quotes
  - `/api/crypto/bars/{symbol}` - Historical crypto price data
  - `/api/crypto/signals/{symbol}` - Crypto trading signals
  - `/api/crypto/account` - Crypto account information
  - `/crypto/stream` - WebSocket for real-time data

## BMAD Commands

### Core Commands
- `npx claude-flow bmad build "<feature>"` - Build new features or components
- `npx claude-flow bmad measure "<metrics>"` - Measure performance and quality
- `npx claude-flow bmad analyze "<data>"` - Analyze results and patterns
- `npx claude-flow bmad document "<topic>"` - Document findings and implementations

### Workflow Commands
- `npx claude-flow bmad cycle "<task>"` - Run complete BMAD cycle
- `npx claude-flow bmad iterate "<feature>"` - Iterative improvement
- `npx claude-flow bmad optimize "<component>"` - Performance optimization

### Build Commands
- `npm run build` - Build project
- `npm run test` - Run tests
- `npm run lint` - Linting
- `npm run typecheck` - Type checking

## BMAD Workflow Phases

1. **Build** - Rapid prototyping and feature implementation
2. **Measure** - Performance metrics, test coverage, quality indicators
3. **Analyze** - Data analysis, bottleneck identification, pattern recognition
4. **Document** - Update docs, capture learnings, maintain knowledge base

## Code Style & Best Practices

- **Modular Design**: Files under 500 lines
- **Environment Safety**: Never hardcode secrets
- **Test-First**: Write tests before implementation
- **Clean Architecture**: Separate concerns
- **Documentation**: Keep updated

## 🚀 Available Agents (54 Total)

### Core Development
`coder`, `reviewer`, `tester`, `planner`, `researcher`

### Swarm Coordination
`hierarchical-coordinator`, `mesh-coordinator`, `adaptive-coordinator`, `collective-intelligence-coordinator`, `swarm-memory-manager`

### Consensus & Distributed
`byzantine-coordinator`, `raft-manager`, `gossip-coordinator`, `consensus-builder`, `crdt-synchronizer`, `quorum-manager`, `security-manager`

### Performance & Optimization
`perf-analyzer`, `performance-benchmarker`, `task-orchestrator`, `memory-coordinator`, `smart-agent`

### GitHub & Repository
`github-modes`, `pr-manager`, `code-review-swarm`, `issue-tracker`, `release-manager`, `workflow-automation`, `project-board-sync`, `repo-architect`, `multi-repo-swarm`

### BMAD Methodology
`bmad-builder`, `bmad-measurer`, `bmad-analyzer`, `bmad-documenter`, `iteration-coordinator`

### Specialized Development
`backend-dev`, `mobile-dev`, `ml-developer`, `cicd-engineer`, `api-docs`, `system-architect`, `code-analyzer`, `base-template-generator`

### Testing & Validation
`tdd-london-swarm`, `production-validator`

### Migration & Planning
`migration-planner`, `swarm-init`

## 🎯 Claude Code vs MCP Tools

### Claude Code Handles ALL:
- File operations (Read, Write, Edit, MultiEdit, Glob, Grep)
- Code generation and programming
- Bash commands and system operations
- Implementation work
- Project navigation and analysis
- TodoWrite and task management
- Git operations
- Package management
- Testing and debugging

### MCP Tools ONLY:
- Coordination and planning
- Memory management
- Neural features
- Performance tracking
- Swarm orchestration
- GitHub integration

**KEY**: MCP coordinates, Claude Code executes.

## 🚀 Quick Setup

```bash
# Add Claude Flow MCP server
claude mcp add claude-flow npx claude-flow@alpha mcp start
```

## MCP Tool Categories

### Coordination
`swarm_init`, `agent_spawn`, `task_orchestrate`

### Monitoring
`swarm_status`, `agent_list`, `agent_metrics`, `task_status`, `task_results`

### Memory & Neural
`memory_usage`, `neural_status`, `neural_train`, `neural_patterns`

### GitHub Integration
`github_swarm`, `repo_analyze`, `pr_enhance`, `issue_triage`, `code_review`

### System
`benchmark_run`, `features_detect`, `swarm_monitor`

## 📋 Agent Coordination Protocol

### Every Agent MUST:

**1️⃣ BEFORE Work:**
```bash
npx claude-flow@alpha hooks pre-task --description "[task]"
npx claude-flow@alpha hooks session-restore --session-id "swarm-[id]"
```

**2️⃣ DURING Work:**
```bash
npx claude-flow@alpha hooks post-edit --file "[file]" --memory-key "swarm/[agent]/[step]"
npx claude-flow@alpha hooks notify --message "[what was done]"
```

**3️⃣ AFTER Work:**
```bash
npx claude-flow@alpha hooks post-task --task-id "[task]"
npx claude-flow@alpha hooks session-end --export-metrics true
```

## 🎯 Concurrent Execution Examples

### ✅ CORRECT (Single Message):
```javascript
[BatchTool]:
  // Initialize swarm
  mcp__claude-flow__swarm_init { topology: "mesh", maxAgents: 6 }
  mcp__claude-flow__agent_spawn { type: "researcher" }
  mcp__claude-flow__agent_spawn { type: "coder" }
  mcp__claude-flow__agent_spawn { type: "tester" }
  
  // Spawn agents with Task tool
  Task("Research agent: Analyze requirements...")
  Task("Coder agent: Implement features...")
  Task("Tester agent: Create test suite...")
  
  // Batch todos
  TodoWrite { todos: [
    {id: "1", content: "Research", status: "in_progress", priority: "high"},
    {id: "2", content: "Design", status: "pending", priority: "high"},
    {id: "3", content: "Implement", status: "pending", priority: "high"},
    {id: "4", content: "Test", status: "pending", priority: "medium"},
    {id: "5", content: "Document", status: "pending", priority: "low"}
  ]}
  
  // File operations
  Bash "mkdir -p app/{src,tests,docs}"
  Write "app/src/index.js"
  Write "app/tests/index.test.js"
  Write "app/docs/README.md"
```

### ❌ WRONG (Multiple Messages):
```javascript
Message 1: mcp__claude-flow__swarm_init
Message 2: Task("agent 1")
Message 3: TodoWrite { todos: [single todo] }
Message 4: Write "file.js"
// This breaks parallel coordination!
```

## Performance Benefits

- **84.8% SWE-Bench solve rate**
- **32.3% token reduction**
- **2.8-4.4x speed improvement**
- **27+ neural models**

## Hooks Integration

### Pre-Operation
- Auto-assign agents by file type
- Validate commands for safety
- Prepare resources automatically
- Optimize topology by complexity
- Cache searches

### Post-Operation
- Auto-format code
- Train neural patterns
- Update memory
- Analyze performance
- Track token usage

### Session Management
- Generate summaries
- Persist state
- Track metrics
- Restore context
- Export workflows

## Advanced Features (v2.0.0)

- 🚀 Automatic Topology Selection
- ⚡ Parallel Execution (2.8-4.4x speed)
- 🧠 Neural Training
- 📊 Bottleneck Analysis
- 🤖 Smart Auto-Spawning
- 🛡️ Self-Healing Workflows
- 💾 Cross-Session Memory
- 🔗 GitHub Integration

## Integration Tips

1. Start with basic swarm init
2. Scale agents gradually
3. Use memory for context
4. Monitor progress regularly
5. Train patterns from success
6. Enable hooks automation
7. Use GitHub tools first

## Support

- Documentation: https://github.com/ruvnet/claude-flow
- Issues: https://github.com/ruvnet/claude-flow/issues

---

Remember: **Claude Flow coordinates, Claude Code creates!**

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
Never save working files, text/mds and tests to the root folder.
