#!/bin/bash
# Database setup script for AI Document Processing
# This script creates the database if it doesn't exist

set -e

echo "🗄️  Database Setup for AI Document Processing"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create a .env file with DATABASE_URL configured."
    exit 1
fi

# Extract database connection info from .env
echo -e "${YELLOW}Reading database configuration from .env...${NC}"
DB_URL=$(grep "^DATABASE_URL=" .env | cut -d '=' -f2-)

if [ -z "$DB_URL" ]; then
    echo -e "${RED}Error: DATABASE_URL not found in .env file!${NC}"
    exit 1
fi

# Parse DATABASE_URL to extract connection details
# Format: postgresql+psycopg://user:password@host:port/database
# or: postgresql://user:password@host:port/database

# Extract database name (last part after last /)
DB_NAME=$(echo "$DB_URL" | sed 's/.*\///')

# Extract host (after @ and before :port)
DB_HOST=$(echo "$DB_URL" | sed 's/.*@//' | sed 's/:.*//')

# Extract port (after :port and before /)
DB_PORT=$(echo "$DB_URL" | grep -oP ':\d+/' | tr -d ':/' || echo "5432")
if [ -z "$DB_PORT" ]; then
    DB_PORT="5432"
fi

# Extract user (between :// and : before password)
DB_USER=$(echo "$DB_URL" | sed 's/.*:\/\///' | sed 's/+.*//' | sed 's/:.*//')

# Extract password (between user: and @)
DB_PASS=$(echo "$DB_URL" | sed 's/.*:\/\/[^:]*://' | sed 's/@.*//')

echo ""
echo "Database Configuration:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  User: $DB_USER"
echo "  Database: $DB_NAME"
echo ""

# Check if PostgreSQL is accessible
echo -e "${YELLOW}Checking PostgreSQL connection...${NC}"
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
    echo -e "${RED}Error: Cannot connect to PostgreSQL at $DB_HOST:$DB_PORT${NC}"
    echo "Please ensure PostgreSQL is running:"
    echo "  sudo systemctl start postgresql"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL is running${NC}"

# Check if database exists
echo -e "${YELLOW}Checking if database '$DB_NAME' exists...${NC}"
DB_EXISTS=$(PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$DB_NAME" && echo "yes" || echo "no")

if [ "$DB_EXISTS" = "no" ]; then
    echo -e "${YELLOW}Database '$DB_NAME' does not exist.${NC}"
    echo -e "${YELLOW}Creating database...${NC}"

    # Create database
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;" postgres 2>/dev/null

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Database '$DB_NAME' created successfully!${NC}"
    else
        echo -e "${RED}✗ Failed to create database '$DB_NAME'${NC}"
        echo ""
        echo "You may need to create it manually:"
        echo "  sudo -u postgres psql"
        echo "  CREATE DATABASE $DB_NAME;"
        echo "  GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
        echo "  \\q"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Database '$DB_NAME' already exists${NC}"
fi

# Test connection to the database
echo -e "${YELLOW}Testing database connection...${NC}"
if PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Successfully connected to database '$DB_NAME'${NC}"
else
    echo -e "${RED}✗ Failed to connect to database '$DB_NAME'${NC}"
    echo ""
    echo "Please check your DATABASE_URL configuration in .env"
    exit 1
fi

# Ask if user wants to run migrations
echo ""
read -p "Do you want to run database migrations now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ ! -d ".venv" ]; then
        echo -e "${RED}Error: Virtual environment not found!${NC}"
        echo "Please create it first:"
        echo "  python3 -m venv .venv"
        echo "  source .venv/bin/activate"
        echo "  pip install -e ."
        exit 1
    fi

    echo -e "${YELLOW}Running migrations...${NC}"
    source .venv/bin/activate
    alembic upgrade head

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Migrations completed successfully!${NC}"
    else
        echo -e "${RED}✗ Migration failed${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}✅ Database setup complete!${NC}"
echo ""
echo "Your database is ready to use:"
echo "  Database: $DB_NAME"
echo "  Host: $DB_HOST:$DB_PORT"
echo ""
