#!/bin/bash

# Build and Deploy Script for AI Document Processing
# This script:
# 1. Pulls latest code from git
# 2. Builds frontend (if needed) using Node.js v20
# 3. Restarts services using PM2

set -e  # Exit on error

echo "==================================="
echo "AI Document Processing - Build Script"
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[*]${NC} $1"
}

# Create logs directory if it doesn't exist
mkdir -p logs

# 1. Pull latest code
print_status "Pulling latest code from git..."
git pull origin develop || print_warning "Git pull failed or no changes"

# 2. Install/update uv if needed
if ! command -v uv &> /dev/null; then
    print_status "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"
fi

# Ensure uv is in PATH
export PATH="$HOME/.local/bin:$PATH"

# 3. Create virtual environment and sync dependencies
print_status "Setting up Python virtual environment with uv..."
uv sync

print_status "Python environment ready at .venv/"

# Verify Python binary exists and show details
if [ -f ".venv/bin/python" ]; then
    print_status "Python binary found: .venv/bin/python"
    ls -lh .venv/bin/python
    file .venv/bin/python
    .venv/bin/python --version
    print_status "Absolute path: $(pwd)/.venv/bin/python"
elif [ -f ".venv/bin/python3" ]; then
    print_status "Python binary found: .venv/bin/python3"
    ls -lh .venv/bin/python3
    .venv/bin/python3 --version
else
    print_error "Warning: No Python binary found in .venv/bin/"
    print_warning "Contents of .venv/bin/:"
    ls -la .venv/bin/ || echo "Directory does not exist"
fi

# 4. Run database migrations
print_status "Running database migrations..."
if [ -f ".venv/bin/alembic" ]; then
    .venv/bin/alembic upgrade head
    print_status "Database migrations completed"
else
    print_warning "Alembic not found, skipping migrations"
fi

# 5. Check if frontend build is needed
SKIP_FRONTEND_BUILD=false
if [ "$1" == "--skip-frontend" ]; then
    SKIP_FRONTEND_BUILD=true
    print_warning "Skipping frontend build (dist folder will be used from git)"
fi

# 6. Build frontend if not skipped
if [ "$SKIP_FRONTEND_BUILD" = false ]; then
    print_status "Building frontend..."

# Load nvm
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    print_status "Loading nvm..."
    . "$NVM_DIR/nvm.sh"
else
    print_error "nvm not found at $NVM_DIR/nvm.sh"
    exit 1
fi

# Use Node.js v20
print_status "Switching to Node.js v20..."
nvm use 20 || {
    print_warning "Node.js v20 not installed, installing..."
    nvm install 20
    nvm use 20
}

# Verify Node version
NODE_VERSION=$(node -v)
print_status "Using Node.js version: $NODE_VERSION"

# Navigate to frontend directory and build
print_status "Building frontend..."
cd frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    print_status "Installing frontend dependencies..."
    pnpm install
fi

    # Build frontend
    # print_status "Running frontend build..."
    # pnpm run build

    cd ..
else
    print_warning "Using pre-built frontend from git (frontend/dist/)"
fi

# 7. Restart services using PM2
print_status "Restarting services with PM2..."

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    print_error "PM2 is not installed. Please install it with: npm install -g pm2"
    exit 1
fi

# Start or reload services using ecosystem file
pm2 startOrReload ecosystem.config.js

print_status "Deployment complete!"
echo ""
echo "==================================="
echo "Services Status:"
echo "==================================="
pm2 list
echo ""
echo "To view logs:"
echo "  pm2 logs uvicorn-api"
echo "  pm2 logs celery-worker"
echo "  pm2 logs"
echo ""
echo "To monitor services:"
echo "  pm2 monit"
echo ""
echo "To stop services:"
echo "  pm2 stop all"
echo "==================================="
