# Multi-stage Dockerfile for Alpaca Trading Bot
# Stage 1: Base Python environment with dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    gcc \
    g++ \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r tradingbot && useradd -r -g tradingbot tradingbot

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-test.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Development environment
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir -r requirements-test.txt

# Install development tools
RUN pip install --no-cache-dir \
    debugpy \
    ipython \
    jupyter \
    black \
    flake8 \
    pytest \
    pytest-cov

# Create directories with proper permissions
RUN mkdir -p /app/{AUTH,ORDERS,logs,data,uploads} && \
    chown -R tradingbot:tradingbot /app

# Copy application code
COPY --chown=tradingbot:tradingbot . .

# Switch to non-root user
USER tradingbot

# Expose ports for Flask app and debugger
EXPOSE 9765 5678

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9765/api/bot/status || exit 1

# Default command for development with hot reload
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "flask_app.py"]

# Stage 3: Production environment
FROM base as production

# Copy only necessary application files
COPY --chown=tradingbot:tradingbot . .

# Create production directories
RUN mkdir -p /app/{AUTH,ORDERS,logs,data} && \
    chown -R tradingbot:tradingbot /app

# Switch to non-root user
USER tradingbot

# Expose only Flask port
EXPOSE 9765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9765/api/bot/status || exit 1

# Production command with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:9765", "--workers", "4", "--timeout", "120", "--keep-alive", "2", "--max-requests", "1000", "--max-requests-jitter", "100", "flask_app:app"]