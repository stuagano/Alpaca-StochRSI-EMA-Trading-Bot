#!/bin/bash

# Ref Tools MCP Configuration Script for Claude Code
# This script helps configure Ref Tools MCP for efficient documentation search

echo "🔧 Ref Tools MCP Configuration for Trading Bot Project"
echo "===================================================="
echo ""

# Your API Key (already provided)
API_KEY="ref-8524f3d9b07eaa536507"
echo "✅ API Key: ${API_KEY:0:10}..."
echo ""

echo "📋 Configuration Options:"
echo ""

echo "Option 1: Add via Claude CLI (Recommended)"
echo "----------------------------------------"
echo "Run this command in your terminal:"
echo ""
echo "claude mcp add ref-tools \"https://api.ref.tools/mcp?apiKey=${API_KEY}\""
echo ""

echo "Option 2: Manual Configuration in Claude Code Settings"
echo "-----------------------------------------------------"
echo "Add this to your Claude Code MCP configuration:"
echo ""
cat << EOF
{
  "Ref": {
    "type": "http",
    "url": "https://api.ref.tools/mcp?apiKey=${API_KEY}"
  }
}
EOF
echo ""

echo "Option 3: Local stdio Server"
echo "----------------------------"
echo "For local development, add this configuration:"
echo ""
cat << EOF
{
  "Ref": {
    "command": "npx",
    "args": ["ref-tools-mcp@latest"],
    "env": {
      "REF_API_KEY": "${API_KEY}"
    }
  }
}
EOF
echo ""

echo "📝 Usage Examples After Configuration:"
echo "======================================"
echo ""

echo "1. Search Alpaca API Documentation:"
echo '   ref_search_documentation("Alpaca Trading API place market order Python example")'
echo ""

echo "2. Read Specific Documentation:"
echo '   ref_read_url("https://alpaca.markets/docs/api-references/trading-api/orders/")'
echo ""

echo "3. Search TradingView Documentation:"
echo '   ref_search_documentation("TradingView Lightweight Charts real-time data streaming")'
echo ""

echo "4. Combined with Claude Flow:"
echo '   # Initialize swarm'
echo '   mcp__claude-flow__swarm_init({ topology: "mesh", maxAgents: 5 })'
echo '   '
echo '   # Search documentation'
echo '   ref_search_documentation("Alpaca API WebSocket streaming market data")'
echo '   '
echo '   # Store findings'
echo '   mcp__claude-flow__memory_usage({'
echo '     action: "store",'
echo '     key: "alpaca_streaming_docs",'
echo '     value: "documentation findings",'
echo '     namespace: "trading_bot"'
echo '   })'
echo ""

echo "🧪 Test Commands:"
echo "================="
echo ""
echo "After configuration, test with these queries:"
echo ""

# Common trading bot documentation searches
test_queries=(
    "Alpaca API authentication setup Python SDK examples"
    "Alpaca market data streaming WebSocket real-time quotes"
    "Alpaca order management place cancel modify order status"
    "TradingView Lightweight Charts candlestick chart real-time updates"
    "Python algorithmic trading risk management position sizing"
    "FastAPI microservices authentication middleware Docker"
    "Playwright testing financial dashboard automation"
    "Stochastic RSI EMA crossover trading strategy implementation"
)

for i in "${!test_queries[@]}"; do
    echo "$((i+1)). ref_search_documentation(\"${test_queries[i]}\")"
done

echo ""
echo "💡 Benefits for Your Trading Bot Project:"
echo "========================================"
echo ""
echo "• 🎯 Efficient API documentation lookup (Alpaca, TradingView)"
echo "• 💰 58% cost reduction in documentation context usage"
echo "• 🧠 Better model performance with focused, relevant content"
echo "• 🔄 Session-aware search that avoids duplicate results"
echo "• 📚 Access to 5k+ tokens of highly relevant documentation per query"
echo "• 🔗 Seamless integration with your existing Claude Flow MCP setup"
echo ""

echo "📋 Next Steps:"
echo "=============="
echo "1. Run the Claude CLI command above to add Ref Tools MCP"
echo "2. Restart Claude Code to load the new MCP server"
echo "3. Test with a simple query: ref_search_documentation(\"Alpaca API\")"
echo "4. Start using efficient documentation search in your development workflow"
echo ""

echo "✅ Configuration guide complete!"
echo "   For questions, see: docs/REF_TOOLS_MCP_SETUP.md"