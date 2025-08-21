#!/usr/bin/env python3
"""
Setup script for local development with virtual environment
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def create_virtual_environment():
    """Create virtual environment"""
    print("🔧 Creating virtual environment...")
    
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("  ✅ Virtual environment already exists")
        return True
    
    try:
        # Create virtual environment
        result = subprocess.run([
            sys.executable, "-m", "venv", "venv"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✅ Virtual environment created")
            return True
        else:
            print(f"  ❌ Failed to create virtual environment: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error creating virtual environment: {e}")
        return False

def get_pip_command():
    """Get the correct pip command for the virtual environment"""
    if platform.system() == "Windows":
        return "venv\\Scripts\\pip"
    else:
        return "venv/bin/pip"

def get_python_command():
    """Get the correct python command for the virtual environment"""
    if platform.system() == "Windows":
        return "venv\\Scripts\\python"
    else:
        return "venv/bin/python"

def install_dependencies():
    """Install dependencies in virtual environment"""
    print("\n📦 Installing dependencies in virtual environment...")
    
    pip_cmd = get_pip_command()
    
    try:
        # Upgrade pip first
        result = subprocess.run([
            pip_cmd, "install", "--upgrade", "pip"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✅ Pip upgraded")
        else:
            print(f"  ⚠️  Pip upgrade failed: {result.stderr}")
        
        # Install requirements
        result = subprocess.run([
            pip_cmd, "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✅ Dependencies installed successfully")
            return True
        else:
            print(f"  ❌ Failed to install dependencies: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error installing dependencies: {e}")
        return False

def create_activation_scripts():
    """Create easy activation scripts"""
    print("\n📝 Creating activation scripts...")
    
    # Create activate script
    if platform.system() == "Windows":
        activate_content = '''@echo off
echo 🚀 Activating microservices environment...
call venv\\Scripts\\activate.bat
echo ✅ Environment activated
echo.
echo 🎯 Available commands:
echo   python start_all_services.py
echo   python start_position_service.py
echo   python start_trading_service.py
echo   python start_signal_service.py
echo   python start_risk_service.py
echo   python start_gateway.py
echo.
'''
        with open("activate.bat", "w") as f:
            f.write(activate_content)
        print("  ✅ Created activate.bat")
    else:
        activate_content = '''#!/bin/bash
echo "🚀 Activating microservices environment..."
source venv/bin/activate
echo "✅ Environment activated"
echo ""
echo "🎯 Available commands:"
echo "  python start_all_services.py"
echo "  python start_position_service.py"
echo "  python start_trading_service.py"
echo "  python start_signal_service.py"
echo "  python start_risk_service.py"
echo "  python start_gateway.py"
echo ""
'''
        with open("activate.sh", "w") as f:
            f.write(activate_content)
        os.chmod("activate.sh", 0o755)
        print("  ✅ Created activate.sh")

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    directories = [
        "data",
        "data/position-management",
        "data/trading-execution", 
        "data/signal-processing",
        "data/risk-management",
        "logs"
    ]
    
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"  ✅ Created {directory}")
        except Exception as e:
            print(f"  ❌ Failed to create {directory}: {e}")

def create_env_file():
    """Create .env file from template"""
    print("\n⚙️  Setting up environment...")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if env_example.exists():
        if not env_file.exists():
            try:
                with open(env_example) as src, open(env_file, 'w') as dst:
                    content = src.read()
                    dst.write(content)
                print("  ✅ Created .env from .env.example")
                print("  ⚠️  Please edit .env and add your Alpaca API keys")
            except Exception as e:
                print(f"  ❌ Failed to create .env: {e}")
        else:
            print("  ✅ .env file already exists")
    else:
        print("  ⚠️  .env.example not found")

def create_startup_scripts():
    """Create startup scripts using virtual environment"""
    print("\n📝 Creating startup scripts...")
    
    python_cmd = get_python_command()
    
    services = {
        "start_position_service.py": {
            "port": 8001,
            "module": "services.position-management.app.main:app",
            "name": "Position Management"
        },
        "start_trading_service.py": {
            "port": 8002, 
            "module": "services.trading-execution.app.main:app",
            "name": "Trading Execution"
        },
        "start_signal_service.py": {
            "port": 8003,
            "module": "services.signal-processing.app.main:app", 
            "name": "Signal Processing"
        },
        "start_risk_service.py": {
            "port": 8004,
            "module": "services.risk-management.app.main:app",
            "name": "Risk Management"
        },
        "start_gateway.py": {
            "port": 8000,
            "module": "services.api-gateway.app.main:app",
            "name": "API Gateway"
        }
    }
    
    for filename, config in services.items():
        script_content = f'''#!/usr/bin/env python3
"""
Start {config['name']} Service
"""

import os
import sys
import subprocess

# Set environment variables
os.environ["PORT"] = "{config['port']}"
os.environ["PYTHONPATH"] = os.getcwd()
os.environ["POSITION_SERVICE_URL"] = "http://localhost:8001"
os.environ["TRADING_SERVICE_URL"] = "http://localhost:8002"
os.environ["SIGNAL_SERVICE_URL"] = "http://localhost:8003"
os.environ["RISK_SERVICE_URL"] = "http://localhost:8004"

print("🚀 Starting {config['name']} on port {config['port']}...")
print("📍 Service URL: http://localhost:{config['port']}")
print("📖 API Docs: http://localhost:{config['port']}/docs")
print("❤️  Health: http://localhost:{config['port']}/health")
print()
print("Press Ctrl+C to stop")
print()

try:
    subprocess.run([
        "{python_cmd}", "-m", "uvicorn",
        "{config['module']}",
        "--host", "0.0.0.0",
        "--port", "{config['port']}",
        "--reload"
    ])
except KeyboardInterrupt:
    print("\\n👋 Service stopped")
'''
        
        try:
            with open(filename, 'w') as f:
                f.write(script_content)
            
            if platform.system() != 'Windows':
                os.chmod(filename, 0o755)
            
            print(f"  ✅ Created {filename}")
        except Exception as e:
            print(f"  ❌ Failed to create {filename}: {e}")

def update_start_all_services():
    """Update start_all_services.py to use virtual environment"""
    print("\n🔄 Updating start_all_services.py...")
    
    python_cmd = get_python_command()
    
    # Read the existing file
    with open("start_all_services.py", "r") as f:
        content = f.read()
    
    # Replace the python command
    content = content.replace('sys.executable', f'"{python_cmd}"')
    
    # Write back
    with open("start_all_services.py", "w") as f:
        f.write(content)
    
    print("  ✅ Updated start_all_services.py to use virtual environment")

def show_usage_instructions():
    """Show usage instructions"""
    print("\n" + "="*60)
    print("🎉 LOCAL DEVELOPMENT SETUP COMPLETE!")
    print("="*60)
    
    if platform.system() == "Windows":
        print("\n🚀 ACTIVATE ENVIRONMENT:")
        print("  activate.bat")
        print("\n🎯 OR DIRECTLY START ALL SERVICES:")
        print("  venv\\Scripts\\python start_all_services.py")
    else:
        print("\n🚀 ACTIVATE ENVIRONMENT:")
        print("  source activate.sh")
        print("\n🎯 OR DIRECTLY START ALL SERVICES:")
        print("  venv/bin/python start_all_services.py")
    
    print("\n🔧 START INDIVIDUAL SERVICES:")
    python_cmd = get_python_command()
    print(f"  {python_cmd} start_position_service.py    # Port 8001")
    print(f"  {python_cmd} start_trading_service.py     # Port 8002") 
    print(f"  {python_cmd} start_signal_service.py      # Port 8003")
    print(f"  {python_cmd} start_risk_service.py        # Port 8004")
    print(f"  {python_cmd} start_gateway.py             # Port 8000")
    
    print("\n📱 ACCESS POINTS:")
    print("  Main Dashboard: Open templates/unified_dashboard.html")
    print("  API Gateway: http://localhost:8000")
    print("  Health Check: http://localhost:8000/health")
    print("  API Docs: http://localhost:8000/docs")
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("  • Virtual environment isolates dependencies")
    print("  • No Docker required - pure Python/FastAPI")
    print("  • Each service runs independently")
    print("  • Services communicate via HTTP APIs")
    print("  • Data stored in local SQLite databases")
    print("  • Edit .env file to add your Alpaca API keys")
    
    print("\n🧪 QUICK TEST:")
    if platform.system() == "Windows":
        print("  1. venv\\Scripts\\python start_all_services.py")
    else:
        print("  1. venv/bin/python start_all_services.py")
    print("  2. curl http://localhost:8000/health")
    print("  3. Open templates/unified_dashboard.html in browser")

def main():
    """Main setup function"""
    print("🛠️  MICROSERVICES LOCAL SETUP (WITH VIRTUAL ENVIRONMENT)")
    print("="*70)
    
    # Create virtual environment
    if not create_virtual_environment():
        print("\n❌ Setup failed: Could not create virtual environment")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed: Could not install dependencies")
        sys.exit(1)
    
    # Create activation scripts
    create_activation_scripts()
    
    # Create directories
    create_directories()
    
    # Create environment file
    create_env_file()
    
    # Create startup scripts
    create_startup_scripts()
    
    # Update start_all_services.py
    update_start_all_services()
    
    # Show usage instructions
    show_usage_instructions()

if __name__ == "__main__":
    main()