# Alpaca Trading Bot - Docker Development Makefile
# =================================================

.PHONY: help setup dev-up dev-down prod-up prod-down logs shell test lint format backup clean

# Default target
.DEFAULT_GOAL := help

# Variables
COMPOSE_FILE = docker-compose.yml
COMPOSE_PROD_FILE = docker-compose.prod.yml
CONTAINER_NAME = alpaca-trading-bot

# Colors for output
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

## Help target
help: ## Show this help message
	@echo "$(BLUE)Alpaca Trading Bot - Docker Commands$(NC)"
	@echo "=================================="
	@echo ""
	@echo "$(GREEN)Development Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -v "prod-" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Production Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep "prod-" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Utility Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(test|lint|format|backup|clean)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'

## Setup and Development
setup: ## Run the automated development setup
	@echo "$(BLUE)Running automated setup...$(NC)"
	./scripts/dev-setup.sh

dev-up: ## Start development environment
	@echo "$(BLUE)Starting development environment...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d --build
	@echo "$(GREEN)Development environment started!$(NC)"
	@echo "$(YELLOW)Trading Bot:$(NC) http://localhost:8765"
	@echo "$(YELLOW)Grafana:$(NC)     http://localhost:3000 (admin/admin123)"
	@echo "$(YELLOW)Jupyter:$(NC)     http://localhost:8888 (token: tradingbot123)"

dev-down: ## Stop development environment
	@echo "$(BLUE)Stopping development environment...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN)Development environment stopped!$(NC)"

dev-restart: ## Restart development environment
	@echo "$(BLUE)Restarting development environment...$(NC)"
	docker-compose -f $(COMPOSE_FILE) restart
	@echo "$(GREEN)Development environment restarted!$(NC)"

dev-rebuild: ## Rebuild and restart development environment
	@echo "$(BLUE)Rebuilding development environment...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d --build --force-recreate
	@echo "$(GREEN)Development environment rebuilt!$(NC)"

## Production
prod-up: ## Start production environment
	@echo "$(BLUE)Starting production environment...$(NC)"
	docker-compose -f $(COMPOSE_PROD_FILE) up -d --build
	@echo "$(GREEN)Production environment started!$(NC)"

prod-down: ## Stop production environment
	@echo "$(BLUE)Stopping production environment...$(NC)"
	docker-compose -f $(COMPOSE_PROD_FILE) down
	@echo "$(GREEN)Production environment stopped!$(NC)"

prod-restart: ## Restart production environment
	@echo "$(BLUE)Restarting production environment...$(NC)"
	docker-compose -f $(COMPOSE_PROD_FILE) restart
	@echo "$(GREEN)Production environment restarted!$(NC)"

prod-logs: ## View production logs
	@echo "$(BLUE)Viewing production logs...$(NC)"
	docker-compose -f $(COMPOSE_PROD_FILE) logs -f

## Logging and Monitoring
logs: ## View development logs
	@echo "$(BLUE)Viewing development logs...$(NC)"
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-app: ## View only trading bot logs
	@echo "$(BLUE)Viewing trading bot logs...$(NC)"
	docker-compose -f $(COMPOSE_FILE) logs -f trading-bot

logs-db: ## View database logs
	@echo "$(BLUE)Viewing database logs...$(NC)"
	docker-compose -f $(COMPOSE_FILE) logs -f postgres

logs-redis: ## View Redis logs
	@echo "$(BLUE)Viewing Redis logs...$(NC)"
	docker-compose -f $(COMPOSE_FILE) logs -f redis

status: ## Show container status
	@echo "$(BLUE)Container Status:$(NC)"
	docker-compose -f $(COMPOSE_FILE) ps

health: ## Check service health
	@echo "$(BLUE)Service Health Check:$(NC)"
	@echo "$(YELLOW)Trading Bot:$(NC)"
	@curl -s http://localhost:8765/api/bot/status | jq . || echo "$(RED)Service not available$(NC)"
	@echo "$(YELLOW)PostgreSQL:$(NC)"
	@docker-compose exec -T postgres pg_isready -U tradingbot || echo "$(RED)Database not available$(NC)"
	@echo "$(YELLOW)Redis:$(NC)"
	@docker-compose exec -T redis redis-cli ping || echo "$(RED)Redis not available$(NC)"

## Development Utilities
shell: ## Access trading bot container shell
	@echo "$(BLUE)Accessing trading bot shell...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot bash

shell-db: ## Access PostgreSQL shell
	@echo "$(BLUE)Accessing PostgreSQL shell...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec postgres psql -U tradingbot -d tradingbot_dev

shell-redis: ## Access Redis shell
	@echo "$(BLUE)Accessing Redis shell...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec redis redis-cli

## Testing and Code Quality
test: ## Run test suite
	@echo "$(BLUE)Running tests...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot python -m pytest tests/ -v --tb=short

test-coverage: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot python -m pytest tests/ -v --cov=. --cov-report=html

lint: ## Run code linting
	@echo "$(BLUE)Running linter...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot flake8 /app --exclude=venv,__pycache__,.git --max-line-length=120

format: ## Format code with Black
	@echo "$(BLUE)Formatting code...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot black /app --exclude=venv --line-length=120

format-check: ## Check code formatting
	@echo "$(BLUE)Checking code formatting...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot black /app --exclude=venv --line-length=120 --check

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot python -m mypy . --ignore-missing-imports

## Database Operations
db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot python /app/scripts/migrate.py --action migrate

db-init: ## Initialize database schema
	@echo "$(BLUE)Initializing database...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot python /app/scripts/migrate.py --action init

db-backup: ## Create database backup
	@echo "$(BLUE)Creating database backup...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot python /app/scripts/migrate.py --action backup

db-verify: ## Verify database integrity
	@echo "$(BLUE)Verifying database integrity...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot python /app/scripts/migrate.py --action verify

db-reset: ## Reset database (WARNING: destroys data)
	@echo "$(RED)WARNING: This will destroy all database data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo; \
		echo "$(BLUE)Resetting database...$(NC)"; \
		docker-compose -f $(COMPOSE_FILE) down -v; \
		docker-compose -f $(COMPOSE_FILE) up -d postgres redis; \
		sleep 5; \
		docker-compose -f $(COMPOSE_FILE) up -d trading-bot; \
		$(MAKE) db-init; \
		echo "$(GREEN)Database reset complete!$(NC)"; \
	else \
		echo; \
		echo "$(YELLOW)Database reset cancelled.$(NC)"; \
	fi

## Cleanup and Maintenance
clean: ## Clean up Docker resources
	@echo "$(BLUE)Cleaning up Docker resources...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v --remove-orphans
	docker system prune -f
	docker volume prune -f
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-all: ## Clean up everything including images
	@echo "$(BLUE)Cleaning up all Docker resources...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down -v --remove-orphans --rmi all
	docker system prune -a -f
	docker volume prune -f
	@echo "$(GREEN)Complete cleanup finished!$(NC)"

backup: ## Create full backup
	@echo "$(BLUE)Creating full backup...$(NC)"
	mkdir -p backups/$(shell date +%Y%m%d_%H%M%S)
	$(MAKE) db-backup
	docker-compose -f $(COMPOSE_FILE) exec trading-bot tar -czf /app/backups/$(shell date +%Y%m%d_%H%M%S)/data_backup.tar.gz /app/data /app/logs /app/AUTH /app/ORDERS
	@echo "$(GREEN)Backup created in backups/$(shell date +%Y%m%d_%H%M%S)/$(NC)"

## Environment Management
env-setup: ## Setup environment files
	@echo "$(BLUE)Setting up environment files...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)Created .env from .env.example$(NC)"; \
		echo "$(YELLOW)Please edit .env with your API credentials$(NC)"; \
	else \
		echo "$(YELLOW).env file already exists$(NC)"; \
	fi

env-validate: ## Validate environment configuration
	@echo "$(BLUE)Validating environment configuration...$(NC)"
	@if [ -f .env ]; then \
		echo "$(GREEN)✓ .env file exists$(NC)"; \
		if grep -q "your_alpaca_api_key_here" .env; then \
			echo "$(RED)✗ Please update ALPACA_API_KEY in .env$(NC)"; \
		else \
			echo "$(GREEN)✓ ALPACA_API_KEY configured$(NC)"; \
		fi; \
		if grep -q "your_alpaca_secret_key_here" .env; then \
			echo "$(RED)✗ Please update ALPACA_SECRET_KEY in .env$(NC)"; \
		else \
			echo "$(GREEN)✓ ALPACA_SECRET_KEY configured$(NC)"; \
		fi; \
	else \
		echo "$(RED)✗ .env file missing - run 'make env-setup'$(NC)"; \
	fi

## Performance and Monitoring
perf-stats: ## Show performance statistics
	@echo "$(BLUE)Performance Statistics:$(NC)"
	docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

cache-clear: ## Clear Redis cache
	@echo "$(BLUE)Clearing Redis cache...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec redis redis-cli FLUSHALL
	@echo "$(GREEN)Cache cleared!$(NC)"

cache-stats: ## Show cache statistics
	@echo "$(BLUE)Cache Statistics:$(NC)"
	@curl -s http://localhost:8765/api/performance/cache | jq . || echo "$(RED)Service not available$(NC)"

## Quick Commands
quick-start: env-setup dev-up ## Quick start for new users
	@echo "$(GREEN)Quick start complete!$(NC)"
	@echo "$(YELLOW)Don't forget to edit .env with your API credentials!$(NC)"

quick-stop: dev-down ## Quick stop
	@echo "$(GREEN)Services stopped!$(NC)"

quick-restart: dev-restart ## Quick restart
	@echo "$(GREEN)Services restarted!$(NC)"

## Development Workflow
dev: dev-up logs ## Start development and show logs

debug: ## Start development with debugging enabled
	@echo "$(BLUE)Starting development with debugging...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d --build
	@echo "$(GREEN)Ready for debugging!$(NC)"
	@echo "$(YELLOW)VS Code: Use 'Python: Trading Bot (Docker)' debug configuration$(NC)"
	@echo "$(YELLOW)Debug port: 5678$(NC)"

work: ## Full development workflow (format, lint, test)
	@echo "$(BLUE)Running full development workflow...$(NC)"
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test
	@echo "$(GREEN)Development workflow complete!$(NC)"

## Security
security-scan: ## Run security scan
	@echo "$(BLUE)Running security scan...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot python -m bandit -r /app -x /app/venv,/app/tests

audit: ## Audit Python dependencies
	@echo "$(BLUE)Auditing Python dependencies...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec trading-bot pip-audit