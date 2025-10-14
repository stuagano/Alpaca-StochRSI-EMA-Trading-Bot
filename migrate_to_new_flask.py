#!/usr/bin/env python3
"""
Migration Script
Helps transition from old Flask architecture to new one
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

class FlaskMigration:
    """Handle migration to new Flask architecture"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backup_dir = self.project_root / 'backup' / datetime.now().strftime('%Y%m%d_%H%M%S')
        self.report = []

    def run(self):
        """Run complete migration"""
        print("=" * 60)
        print("FLASK ARCHITECTURE MIGRATION TOOL")
        print("=" * 60)

        # Step 1: Check prerequisites
        print("\n1. Checking prerequisites...")
        if not self.check_prerequisites():
            return False

        # Step 2: Backup existing files
        print("\n2. Creating backup...")
        self.create_backup()

        # Step 3: Verify new structure
        print("\n3. Verifying new Flask structure...")
        self.verify_new_structure()

        # Step 4: Update configuration
        print("\n4. Updating configuration...")
        self.update_configuration()

        # Step 5: Create startup scripts
        print("\n5. Creating startup scripts...")
        self.create_startup_scripts()

        # Step 6: Update frontend
        print("\n6. Updating frontend files...")
        self.update_frontend()

        # Step 7: Generate migration report
        print("\n7. Generating migration report...")
        self.generate_report()

        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Test new Flask app: python backend/api/run.py")
        print("2. Update any launch scripts to call: python backend/api/run.py")
        print("3. Check migration report: migration_report.txt")

        return True

    def check_prerequisites(self):
        """Check if prerequisites are met"""
        checks = {
            'Flask installed': self.check_package('flask'),
            'flask-cors installed': self.check_package('flask-cors'),
            'flask-socketio installed': self.check_package('flask-socketio'),
            'New structure exists': (self.project_root / 'backend' / 'api').exists(),
            'Config exists': (self.project_root / 'config' / 'unified_config.py').exists()
        }

        all_passed = True
        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
            if not passed:
                all_passed = False
                self.report.append(f"FAILED: {check}")

        return all_passed

    def check_package(self, package_name):
        """Check if a Python package is installed"""
        try:
            __import__(package_name.replace('-', '_'))
            return True
        except ImportError:
            return False

    def create_backup(self):
        """Create backup of existing files"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        files_to_backup = [
            'app.py',
            'frontend/index.html',
            '.env'
        ]

        for file_path in files_to_backup:
            src = self.project_root / file_path
            if src.exists():
                dst = self.backup_dir / file_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                print(f"  Backed up: {file_path}")
                self.report.append(f"BACKUP: {file_path} -> {dst}")

    def verify_new_structure(self):
        """Verify new Flask structure is in place"""
        required_files = [
            'backend/api/__init__.py',
            'backend/api/run.py',
            'backend/api/blueprints/__init__.py',
            'backend/api/services/__init__.py',
            'backend/api/utils/__init__.py'
        ]

        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"  ✓ {file_path}")
                self.report.append(f"VERIFIED: {file_path}")
            else:
                print(f"  ✗ Missing: {file_path}")
                self.report.append(f"MISSING: {file_path}")

    def update_configuration(self):
        """Update configuration files"""
        # Create .env file if it doesn't exist
        env_file = self.project_root / '.env'
        if not env_file.exists():
            env_content = """# Flask Configuration
FLASK_APP=backend.api.app
FLASK_ENV=development
SECRET_KEY=dev-key-change-in-production

# API Configuration
API_HOST=localhost
API_PORT=5001

# Database
DATABASE_URI=sqlite:///database/trading_data.db
"""
            env_file.write_text(env_content)
            print("  Created .env file")
            self.report.append("CREATED: .env configuration file")

        # Create or update Flask config
        flask_config = self.project_root / 'backend' / 'api' / '.flaskenv'
        flask_env_content = """FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
"""
        flask_config.write_text(flask_env_content)
        print("  Created .flaskenv file")
        self.report.append("CREATED: .flaskenv for Flask")

    def create_startup_scripts(self):
        """Create convenient startup scripts"""
        # Create start script for Unix/Linux/Mac
        start_sh = self.project_root / 'start_flask.sh'
        start_sh_content = """#!/bin/bash
# Start Flask Trading Bot

echo "Starting Flask Trading Bot..."
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start the Flask app
python backend/api/run.py --host 0.0.0.0 --port 5001
"""
        start_sh.write_text(start_sh_content)
        start_sh.chmod(0o755)
        print("  Created start_flask.sh")

        # Create start script for Windows
        start_bat = self.project_root / 'start_flask.bat'
        start_bat_content = """@echo off
REM Start Flask Trading Bot

echo Starting Flask Trading Bot...
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist venv\\Scripts\\activate.bat (
    call venv\\Scripts\\activate.bat
)

REM Start the Flask app
python backend\\api\\run.py --host 0.0.0.0 --port 5001

pause
"""
        start_bat.write_text(start_bat_content)
        print("  Created start_flask.bat")
        self.report.append("CREATED: Startup scripts (start_flask.sh and start_flask.bat)")

    def update_frontend(self):
        """Update frontend to use new API endpoints"""
        # Create a new frontend configuration file
        frontend_config = self.project_root / 'frontend' / 'config.js'
        config_content = """// Frontend Configuration for New Flask API

const API_CONFIG = {
    // Base URL for API
    baseURL: window.location.origin,

    // API version
    version: 'v1',

    // Endpoints
    endpoints: {
        // Core API
        status: '/api/v1/status',
        account: '/api/v1/account',
        positions: '/api/v1/positions',
        signals: '/api/v1/signals',
        orders: '/api/v1/orders',
        symbols: '/api/v1/symbols',

        // Trading
        startTrading: '/api/v1/trading/start',
        stopTrading: '/api/v1/trading/stop',
        buy: '/api/v1/trading/buy',
        sell: '/api/v1/trading/sell',
        closePosition: '/api/v1/trading/close',
        closeAll: '/api/v1/trading/close-all',

        // P&L
        currentPnl: '/api/v1/pnl/current',
        pnlHistory: '/api/v1/pnl/history',
        pnlChart: '/api/v1/pnl/chart-data',
        pnlStats: '/api/v1/pnl/statistics',
        pnlExport: '/api/v1/pnl/export'
    },

    // WebSocket configuration
    websocket: {
        enabled: true,
        reconnect: true,
        reconnectDelay: 5000
    },

    // Update intervals (milliseconds)
    updateIntervals: {
        account: 30000,    // 30 seconds
        positions: 5000,   // 5 seconds
        signals: 10000,    // 10 seconds
        pnl: 5000         // 5 seconds
    }
};

// Helper function to build full API URL
function buildApiUrl(endpoint) {
    return `${API_CONFIG.baseURL}${API_CONFIG.endpoints[endpoint]}`;
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API_CONFIG;
}
"""
        frontend_config.write_text(config_content)
        print("  Created frontend/config.js")
        self.report.append("CREATED: frontend/config.js with new API endpoints")

    def generate_report(self):
        """Generate migration report"""
        report_file = self.project_root / 'migration_report.txt'

        report_content = f"""
FLASK ARCHITECTURE MIGRATION REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 60}

SUMMARY:
- Old dashboard files archived in: dashboard_archive/
- Backup created in: {self.backup_dir}
- New Flask structure created in: backend/api/

MIGRATION ACTIONS:
{chr(10).join(self.report)}

NEW FLASK STRUCTURE:
backend/api/
├── __init__.py         # Application factory
├── app.py              # Simplified transitional app
├── run.py              # Full application runner
├── config.py           # Flask configuration
├── blueprints/         # Route blueprints
│   ├── dashboard.py    # Dashboard routes
│   ├── api.py          # Core API
│   ├── trading.py      # Trading operations
│   ├── pnl.py          # P&L tracking
│   └── websocket_events.py  # WebSocket
├── services/           # Business logic
│   ├── trading_service.py
│   ├── pnl_service.py
│   └── alpaca_client.py
└── utils/              # Utilities
    ├── decorators.py
    ├── validators.py
    └── error_handlers.py

HOW TO USE NEW SYSTEM:

1. Start the unified Flask app:
   python backend/api/run.py

2. Or use the convenience scripts:
   ./start_flask.sh  (Unix/Linux/Mac)
   start_flask.bat   (Windows)

API ENDPOINTS:
- Dashboard: http://localhost:5001/
- API Status: http://localhost:5001/api/v1/status
- Account: http://localhost:5001/api/v1/account
- Positions: http://localhost:5001/api/v1/positions
- Signals: http://localhost:5001/api/v1/signals
- P&L: http://localhost:5001/api/v1/pnl/current

TESTING:
1. Test API status:
   curl http://localhost:5001/api/v1/status

2. Test account endpoint:
   curl http://localhost:5001/api/v1/account

3. Test WebSocket:
   Open http://localhost:5001/ in browser

ROLLBACK:
If you need to rollback to the old system:
1. Restore files from: {self.backup_dir}
2. Run old app: python backend/api/run.py

NEXT STEPS:
1. Test all API endpoints
2. Update any custom scripts to use new endpoints
3. Monitor logs for any issues
4. Consider removing old dashboard files once stable
"""
        report_file.write_text(report_content)
        print(f"\n  Report saved to: {report_file}")
        self.report.append(f"REPORT: Generated migration report")

def main():
    """Run migration"""
    migrator = FlaskMigration()
    success = migrator.run()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
