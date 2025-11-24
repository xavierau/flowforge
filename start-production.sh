#!/bin/bash
# Production startup script with PM2 for AI Document Processing API

set -e

echo "🚀 Starting AI Document Processing API (Production Mode with PM2)..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create a .env file with your configuration."
    echo "See .env.example for reference."
    exit 1
fi

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    echo -e "${RED}Error: PM2 is not installed!${NC}"
    echo "Install PM2 globally with:"
    echo "  npm install -g pm2"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Create it with:"
    echo "  uv venv"
    exit 1
fi

# Check if PostgreSQL is accessible (local installation)
echo -e "${YELLOW}Checking PostgreSQL connection...${NC}"
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo -e "${RED}Error: PostgreSQL is not running on localhost:5432!${NC}"
    echo "Start it with:"
    echo "  sudo systemctl start postgresql"
    echo ""
    echo "Enable auto-start on boot:"
    echo "  sudo systemctl enable postgresql"
    exit 1
fi

# Check if Redis is accessible (local installation)
echo -e "${YELLOW}Checking Redis connection...${NC}"
if ! redis-cli -h localhost -p 6379 ping > /dev/null 2>&1; then
    echo -e "${RED}Error: Redis is not running on localhost:6379!${NC}"
    echo "Start it with:"
    echo "  sudo systemctl start redis-server"
    echo ""
    echo "Enable auto-start on boot:"
    echo "  sudo systemctl enable redis-server"
    exit 1
fi

# Extract database connection info from .env
echo -e "${YELLOW}Checking database configuration...${NC}"
source .venv/bin/activate

# Parse DATABASE_URL to extract connection details
DB_URL=$(grep "^DATABASE_URL=" .env | cut -d '=' -f2-)
# Extract database name from URL (last part after last /)
DB_NAME=$(echo "$DB_URL" | sed 's/.*\///')
# Extract host (after @ and before :port or /)
DB_HOST=$(echo "$DB_URL" | sed 's/.*@//' | sed 's/:.*//' | sed 's/\/.*//')
# Extract port (after :port and before /)
DB_PORT=$(echo "$DB_URL" | sed 's/.*://' | sed 's/\/.*//')
# Extract user (between :// and : before password)
DB_USER=$(echo "$DB_URL" | sed 's/.*:\/\///' | sed 's/:.*//')
# Extract password (between user: and @)
DB_PASS=$(echo "$DB_URL" | sed 's/.*:\/\/[^:]*://' | sed 's/@.*//')

echo "Database: $DB_NAME"
echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo "User: $DB_USER"

# Check if database exists, create if it doesn't
echo -e "${YELLOW}Checking if database exists...${NC}"
DB_EXISTS=$(PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME" && echo "yes" || echo "no")

if [ "$DB_EXISTS" = "no" ]; then
    echo -e "${YELLOW}Database '$DB_NAME' does not exist. Creating it...${NC}"
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;" postgres
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Database '$DB_NAME' created successfully!${NC}"
    else
        echo -e "${RED}Failed to create database '$DB_NAME'${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}Database '$DB_NAME' already exists.${NC}"
fi

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
alembic upgrade head

# Create storage and logs directories
mkdir -p storage/documents storage/pages logs

# Stop existing PM2 processes if running
echo -e "${YELLOW}Stopping existing PM2 processes...${NC}"
pm2 delete ecosystem.config.js 2>/dev/null || true

# Start with PM2
echo -e "${YELLOW}Starting services with PM2...${NC}"
pm2 start ecosystem.config.js

# Save PM2 process list
echo -e "${YELLOW}Saving PM2 process list...${NC}"
pm2 save

echo ""
echo -e "${GREEN}✅ All services started successfully with PM2!${NC}"
echo ""
echo "📊 Service URLs:"
echo "   API:     http://localhost:8000"
echo "   Docs:    http://localhost:8000/docs"
echo "   Health:  http://localhost:8000/health"
echo "   Flower:  http://localhost:5555 (Celery monitoring)"
echo ""
echo "📝 Useful PM2 commands:"
echo -e "   ${BLUE}pm2 status${NC}          - View all processes"
echo -e "   ${BLUE}pm2 logs${NC}            - View all logs"
echo -e "   ${BLUE}pm2 logs ai-doc-api${NC} - View API logs"
echo -e "   ${BLUE}pm2 logs ai-doc-worker${NC} - View worker logs"
echo -e "   ${BLUE}pm2 monit${NC}           - Monitor processes in real-time"
echo -e "   ${BLUE}pm2 restart all${NC}     - Restart all services"
echo -e "   ${BLUE}pm2 stop all${NC}        - Stop all services"
echo -e "   ${BLUE}pm2 delete all${NC}      - Remove all processes from PM2"
echo ""
echo "🔄 Auto-restart on system reboot:"
echo -e "   ${BLUE}pm2 startup${NC}         - Generate startup script (run once)"
echo -e "   ${BLUE}pm2 save${NC}            - Save current process list"
echo ""
echo "📊 View monitoring dashboard:"
echo -e "   ${BLUE}pm2 plus${NC}            - Connect to PM2+ cloud monitoring (optional)"
echo ""
