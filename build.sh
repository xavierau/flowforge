#!/bin/bash

# Build and Restart Script for AI Document Processing
# This script:
# 1. Restarts Python web server (uvicorn)
# 2. Restarts Celery worker
# 3. Builds frontend using Node.js v20

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

# 1. Stop existing Python web server (uvicorn)
print_status "Stopping existing uvicorn process..."
pkill -f "uvicorn app.main:app" || print_warning "No uvicorn process found"

# 2. Stop existing Celery worker
print_status "Stopping existing Celery worker..."
pkill -f "celery -A app.tasks.celery_app worker" || print_warning "No Celery worker found"

# Wait for processes to fully terminate
sleep 2

# 3. Start uvicorn in background
print_status "Starting uvicorn web server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &
UVICORN_PID=$!
print_status "Uvicorn started (PID: $UVICORN_PID)"

# 4. Start Celery worker in background
print_status "Starting Celery worker..."
celery -A app.tasks.celery_app worker --loglevel=info > logs/celery.log 2>&1 &
CELERY_PID=$!
print_status "Celery worker started (PID: $CELERY_PID)"

# 5. Build frontend using Node.js v20
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
    npm install
fi

# Build frontend
print_status "Running frontend build..."
npm run build

cd ..

# 6. Save PIDs to file for later reference
mkdir -p logs
echo "$UVICORN_PID" > logs/uvicorn.pid
echo "$CELERY_PID" > logs/celery.pid

print_status "Build complete!"
echo ""
echo "==================================="
echo "Services Status:"
echo "==================================="
echo "Uvicorn PID: $UVICORN_PID (logs/uvicorn.log)"
echo "Celery PID:  $CELERY_PID (logs/celery.log)"
echo ""
echo "Frontend built successfully!"
echo ""
echo "To view logs:"
echo "  tail -f logs/uvicorn.log"
echo "  tail -f logs/celery.log"
echo ""
echo "To stop services:"
echo "  kill $UVICORN_PID $CELERY_PID"
echo "==================================="
