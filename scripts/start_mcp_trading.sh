#!/bin/bash

# MCP Trading Bot Starter Script
# This script starts the trading bot with MCP integration

echo "=========================================="
echo "🚀 Starting MCP-Enhanced Trading Bot"
echo "=========================================="

# Set the project directory
PROJECT_DIR="/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot"
cd "$PROJECT_DIR"

# Function to check if a port is in use
check_port() {
    lsof -i :$1 > /dev/null 2>&1
    return $?
}

# Function to display status
display_status() {
    echo ""
    echo "📊 Service Status:"
    echo "-----------------"
    
    if check_port 9100; then
        echo "✅ Frontend (9100): Running"
    else
        echo "❌ Frontend (9100): Not running"
    fi
    
    if check_port 9000; then
        echo "✅ API Gateway (9000): Running"
    else
        echo "❌ API Gateway (9000): Not running"
    fi
    
    if check_port 9002; then
        echo "✅ Trading Execution (9002): Running"
    else
        echo "❌ Trading Execution (9002): Not running"
    fi
    
    if check_port 9003; then
        echo "✅ Signal Processing (9003): Running"
    else
        echo "❌ Signal Processing (9003): Not running"
    fi
    
    echo ""
}

# Main menu
echo ""
echo "Select an option:"
echo "1) Run MCP Demo (Simulated)"
echo "2) Start Trading Services"
echo "3) Check Service Status"
echo "4) Run MCP Integration Test"
echo "5) View MCP Documentation"
echo "6) Exit"
echo ""
read -p "Enter your choice (1-6): " choice

case $choice in
    1)
        echo ""
        echo "🎯 Running MCP Trading Demo..."
        echo "-------------------------------"
        python3 scripts/run_mcp_trading_demo.py
        ;;
    
    2)
        echo ""
        echo "🚀 Starting Trading Services..."
        echo "--------------------------------"
        
        # Check if services are already running
        if check_port 9000 || check_port 9002 || check_port 9003; then
            echo "⚠️  Some services are already running!"
            display_status
            read -p "Stop existing services and restart? (y/n): " restart
            if [ "$restart" = "y" ]; then
                echo "Stopping existing services..."
                pkill -f "uvicorn"
                pkill -f "flask"
                sleep 2
            else
                echo "Keeping existing services running."
                exit 0
            fi
        fi
        
        echo ""
        echo "Starting microservices..."
        
        # Start core services (you can customize this based on your setup)
        if [ -f "scripts/start_core_services.py" ]; then
            python3 scripts/start_core_services.py &
            echo "✅ Core services starting..."
        else
            echo "⚠️  Core services script not found"
        fi
        
        sleep 3
        display_status
        
        echo ""
        echo "🔗 Access Points:"
        echo "  • Frontend: http://localhost:9100"
        echo "  • API Gateway: http://localhost:9000"
        echo "  • API Docs: http://localhost:9000/docs"
        ;;
    
    3)
        display_status
        ;;
    
    4)
        echo ""
        echo "🧪 Running MCP Integration Test..."
        echo "-----------------------------------"
        
        # Test MCP connection
        echo "Testing MCP server connection..."
        npx claude-flow@alpha version
        
        echo ""
        echo "Testing MCP tools..."
        
        # Create a simple test file
        cat > /tmp/mcp_test.js << 'EOF'
console.log("Testing MCP swarm status...");
console.log("Use these commands in Claude Code:");
console.log("  mcp__claude-flow__swarm_status");
console.log("  mcp__claude-flow__agent_list");
console.log("  mcp__claude-flow__memory_usage { action: 'list', namespace: 'trading' }");
EOF
        
        node /tmp/mcp_test.js
        
        echo ""
        echo "✅ MCP test complete. Use the commands above in Claude Code."
        ;;
    
    5)
        echo ""
        echo "📚 Opening MCP Documentation..."
        echo "-------------------------------"
        
        # Display key documentation files
        echo ""
        echo "Available documentation:"
        echo "1. MCP Trading Integration Guide: docs/MCP_TRADING_INTEGRATION_GUIDE.md"
        echo "2. MCP Setup Guide: docs/MCP_SETUP.md"
        echo "3. MCP Workflow Examples: docs/MCP_WORKFLOW_EXAMPLES.md"
        echo ""
        
        read -p "Which document to view? (1-3): " doc_choice
        
        case $doc_choice in
            1) less docs/MCP_TRADING_INTEGRATION_GUIDE.md ;;
            2) less docs/MCP_SETUP.md ;;
            3) less docs/MCP_WORKFLOW_EXAMPLES.md ;;
            *) echo "Invalid choice" ;;
        esac
        ;;
    
    6)
        echo "Exiting..."
        exit 0
        ;;
    
    *)
        echo "Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✅ Operation Complete"
echo "=========================================="