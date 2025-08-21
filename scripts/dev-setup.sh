#!/bin/bash

# =============================================================================
# ALPACA TRADING BOT - DEVELOPMENT SETUP SCRIPT
# =============================================================================
# This script sets up the development environment with hot-reload capabilities

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    log_info "Checking Docker..."
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    log_success "Docker is running"
}

# Check if Docker Compose is available
check_docker_compose() {
    log_info "Checking Docker Compose..."
    if ! command -v docker-compose >/dev/null 2>&1; then
        log_error "Docker Compose is not installed. Please install Docker Compose and try again."
        exit 1
    fi
    log_success "Docker Compose is available"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    directories=(
        "data"
        "logs" 
        "AUTH"
        "ORDERS"
        "docker/ssl"
        "docker/grafana/dashboards"
        "docker/grafana/datasources"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
    
    log_success "All directories created"
}

# Setup environment files
setup_environment() {
    log_info "Setting up environment files..."
    
    # Copy .env.example to .env if it doesn't exist
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success "Created .env from .env.example"
            log_warning "Please edit .env file with your actual API keys and credentials"
        else
            log_error ".env.example not found. Cannot create .env file."
            exit 1
        fi
    else
        log_info ".env file already exists"
    fi
    
    # Copy development environment
    if [ ! -f ".env.local" ]; then
        if [ -f ".env.development" ]; then
            cp .env.development .env.local
            log_success "Created .env.local from .env.development"
        fi
    fi
}

# Generate SSL certificates for development
generate_ssl_certs() {
    log_info "Generating SSL certificates for development..."
    
    if [ ! -f "docker/ssl/cert.pem" ] || [ ! -f "docker/ssl/key.pem" ]; then
        mkdir -p docker/ssl
        
        # Generate self-signed certificate
        openssl req -x509 -newkey rsa:4096 -keyout docker/ssl/key.pem -out docker/ssl/cert.pem -days 365 -nodes \
            -subj "/C=US/ST=Development/L=Local/O=TradingBot/CN=localhost" >/dev/null 2>&1
        
        log_success "SSL certificates generated"
    else
        log_info "SSL certificates already exist"
    fi
}

# Setup Grafana configuration
setup_grafana() {
    log_info "Setting up Grafana configuration..."
    
    # Create Grafana datasource configuration
    cat > docker/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

    # Create basic dashboard configuration
    cat > docker/grafana/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

    log_success "Grafana configuration created"
}

# Setup Prometheus configuration
setup_prometheus() {
    log_info "Setting up Prometheus configuration..."
    
    cat > docker/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'trading-bot'
    static_configs:
      - targets: ['trading-bot:8765']
    metrics_path: '/api/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
EOF

    log_success "Prometheus configuration created"
}

# Build and start development environment
start_development() {
    log_info "Building and starting development environment..."
    
    # Build the images
    log_info "Building Docker images..."
    docker-compose build --no-cache
    
    # Start the services
    log_info "Starting Docker services..."
    docker-compose up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    check_services_health
}

# Check service health
check_services_health() {
    log_info "Checking service health..."
    
    services=(
        "postgres:5432"
        "redis:6379"
        "trading-bot:8765"
    )
    
    for service in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service"
        
        if docker-compose exec -T "$name" timeout 5 bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null; then
            log_success "$name service is healthy"
        else
            log_warning "$name service might not be ready yet"
        fi
    done
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Wait for postgres to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    timeout=60
    while ! docker-compose exec -T postgres pg_isready -U tradingbot -d tradingbot_dev >/dev/null 2>&1; do
        timeout=$((timeout - 1))
        if [ $timeout -eq 0 ]; then
            log_error "PostgreSQL did not become ready in time"
            exit 1
        fi
        sleep 1
    done
    
    # Run migration script
    if docker-compose exec -T trading-bot python /app/scripts/migrate.py --action init; then
        log_success "Database migrations completed"
    else
        log_warning "Database migrations may have failed, but continuing..."
    fi
}

# Setup hot-reload configuration
setup_hot_reload() {
    log_info "Setting up hot-reload configuration..."
    
    # Create a watchdog script for hot-reload
    cat > scripts/hot-reload.py << 'EOF'
#!/usr/bin/env python3
"""
Hot-reload script for development
Watches for file changes and restarts the Flask application
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FlaskReloadHandler(FileSystemEventHandler):
    def __init__(self, process):
        self.process = process
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Only reload for Python files
        if event.src_path.endswith('.py'):
            print(f"File changed: {event.src_path}")
            print("Restarting Flask application...")
            self.restart_process()
    
    def restart_process(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
        
        self.process = subprocess.Popen([
            sys.executable, 'flask_app.py'
        ], env=os.environ.copy())

def main():
    # Start Flask process
    process = subprocess.Popen([
        sys.executable, 'flask_app.py'
    ], env=os.environ.copy())
    
    # Setup file watcher
    event_handler = FlaskReloadHandler(process)
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if process:
            process.terminate()
    
    observer.join()

if __name__ == "__main__":
    main()
EOF

    chmod +x scripts/hot-reload.py
    log_success "Hot-reload script created"
}

# Print success message and next steps
print_success_message() {
    log_success "Development environment setup completed!"
    echo ""
    echo -e "${GREEN}====================================================${NC}"
    echo -e "${GREEN}           ALPACA TRADING BOT - READY!             ${NC}"
    echo -e "${GREEN}====================================================${NC}"
    echo ""
    echo -e "${BLUE}Services:${NC}"
    echo "  🚀 Trading Bot:     http://localhost:8765"
    echo "  📊 Grafana:         http://localhost:3000 (admin/admin123)"
    echo "  📈 Prometheus:      http://localhost:9090"
    echo "  📓 Jupyter:         http://localhost:8888 (token: tradingbot123)"
    echo "  🗄️  PostgreSQL:      localhost:5432"
    echo "  🗃️  Redis:           localhost:6379"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  📋 View logs:        docker-compose logs -f"
    echo "  🔧 Restart services: docker-compose restart"
    echo "  🛑 Stop services:    docker-compose down"
    echo "  🏗️  Rebuild:          docker-compose up -d --build"
    echo "  🐚 Shell access:     docker-compose exec trading-bot bash"
    echo ""
    echo -e "${BLUE}VS Code:${NC}"
    echo "  🐛 Debug: Use 'Python: Trading Bot (Docker)' configuration"
    echo "  📂 Open: code ."
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Edit .env file with your Alpaca API credentials"
    echo "  2. Open VS Code and start debugging"
    echo "  3. Visit http://localhost:8765 to see the dashboard"
    echo ""
    echo -e "${RED}Important:${NC} Make sure to set your Alpaca API keys in .env file!"
    echo ""
}

# Main function
main() {
    echo -e "${BLUE}"
    echo "====================================================="
    echo "     ALPACA TRADING BOT - DEVELOPMENT SETUP        "
    echo "====================================================="
    echo -e "${NC}"
    
    # Run setup steps
    check_docker
    check_docker_compose
    create_directories
    setup_environment
    generate_ssl_certs
    setup_grafana
    setup_prometheus
    setup_hot_reload
    start_development
    run_migrations
    
    # Print success message
    print_success_message
}

# Handle script interruption
trap 'log_error "Setup interrupted"; exit 1' INT TERM

# Run main function
main "$@"