#!/usr/bin/env python3
"""
Setup script for local development without Docker
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def check_python_version():
    """Check Python version"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    
    if version.major == 3 and version.minor >= 8:
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro} (compatible)")
        return True
    else:
        print(f"  ❌ Python {version.major}.{version.minor}.{version.micro} (requires Python 3.8+)")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("  ❌ requirements.txt not found")
        return False
    
    try:
        # Install dependencies
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
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
                # Copy .env.example to .env
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

def check_service_files():
    """Check that all service files exist"""
    print("\n🔍 Checking service files...")
    
    services = [
        "services/position-management/app/main.py",
        "services/trading-execution/app/main.py",
        "services/signal-processing/app/main.py", 
        "services/risk-management/app/main.py",
        "services/api-gateway/app/main.py"
    ]
    
    all_exist = True
    for service_file in services:
        if Path(service_file).exists():
            print(f"  ✅ {service_file}")
        else:
            print(f"  ❌ {service_file}")
            all_exist = False
    
    return all_exist

def create_startup_scripts():
    """Create individual startup scripts"""
    print("\n📝 Creating startup scripts...")
    
    # Python startup scripts for each service
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
        sys.executable, "-m", "uvicorn",
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
            
            # Make executable on Unix systems
            if platform.system() != 'Windows':
                os.chmod(filename, 0o755)
            
            print(f"  ✅ Created {filename}")
        except Exception as e:
            print(f"  ❌ Failed to create {filename}: {e}")

def show_usage_instructions():
    """Show usage instructions"""
    print("\n" + "="*60)
    print("🎉 LOCAL DEVELOPMENT SETUP COMPLETE!")
    print("="*60)
    
    print("\n🚀 START ALL SERVICES:")
    print("  python start_all_services.py")
    
    print("\n🔧 START INDIVIDUAL SERVICES:")
    print("  python start_position_service.py    # Port 8001")
    print("  python start_trading_service.py     # Port 8002") 
    print("  python start_signal_service.py      # Port 8003")
    print("  python start_risk_service.py        # Port 8004")
    print("  python start_gateway.py             # Port 8000")
    
    print("\n🌐 ALTERNATIVE (using shell script):")
    print("  ./start_service.sh position-management")
    print("  ./start_service.sh trading-execution")
    print("  ./start_service.sh signal-processing")
    print("  ./start_service.sh risk-management")
    print("  ./start_service.sh api-gateway")
    
    print("\n📱 ACCESS POINTS:")
    print("  Main Dashboard: Use your existing unified_dashboard.html")
    print("  API Gateway: http://localhost:8000")
    print("  Health Check: http://localhost:8000/health")
    print("  API Docs: http://localhost:8000/docs")
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("  • No Docker required - pure Python/FastAPI")
    print("  • Each service runs independently")
    print("  • Services communicate via HTTP APIs")
    print("  • Data stored in local SQLite databases")
    print("  • Edit .env file to add your Alpaca API keys")
    
    print("\n🧪 QUICK TEST:")
    print("  1. python start_all_services.py")
    print("  2. curl http://localhost:8000/health")
    print("  3. Open unified_dashboard.html in browser")

def main():
    """Main setup function"""
    print("🛠️  MICROSERVICES LOCAL SETUP")
    print("="*60)
    print("Setting up microservices for local development (no Docker)")
    
    # Check Python version
    if not check_python_version():
        print("\n❌ Setup failed: Python version incompatible")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed: Could not install dependencies")
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Create environment file
    create_env_file()
    
    # Check service files
    if not check_service_files():
        print("\n⚠️  Some service files are missing, but continuing...")
    
    # Create startup scripts
    create_startup_scripts()
    
    # Show usage instructions
    show_usage_instructions()

if __name__ == "__main__":
    main()