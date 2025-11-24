#!/bin/bash
# Startup script for AI Document Processing API

set -e

echo "🚀 Starting AI Document Processing API..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create a .env file with your configuration."
    echo "See .env.example for reference."
    exit 1
fi

# Check if running in Docker or local mode
if [ "$1" == "docker" ]; then
    echo -e "${GREEN}Starting with Docker Compose...${NC}"
    echo ""

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not running!${NC}"
        echo "Please start Docker and try again."
        exit 1
    fi

    # Build and start containers
    echo -e "${YELLOW}Building containers...${NC}"
    docker-compose build

    echo -e "${YELLOW}Starting services...${NC}"
    docker-compose up -d

    # Wait for services to be healthy
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    sleep 5

    # Check if migrations need to be run
    echo -e "${YELLOW}Checking database migrations...${NC}"
    if ! docker-compose exec -T api alembic current > /dev/null 2>&1; then
        echo -e "${YELLOW}Running database migrations...${NC}"
        docker-compose exec -T api alembic upgrade head
    fi

    echo ""
    echo -e "${GREEN}✅ All services started successfully!${NC}"
    echo ""
    echo "📊 Service URLs:"
    echo "   API:     http://localhost:8000"
    echo "   Docs:    http://localhost:8000/docs"
    echo "   Health:  http://localhost:8000/health"
    echo ""
    echo "📝 View logs:"
    echo "   docker-compose logs -f api"
    echo "   docker-compose logs -f worker"
    echo ""
    echo "🛑 Stop services:"
    echo "   docker-compose down"

else
    echo -e "${GREEN}Starting in local development mode...${NC}"
    echo ""

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q -e ".[dev]"

    # Check if PostgreSQL is running
    echo -e "${YELLOW}Checking PostgreSQL connection...${NC}"
    if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
        echo -e "${RED}Warning: PostgreSQL not running on localhost:5432${NC}"
        echo "Starting PostgreSQL with Docker..."
        docker run -d --name doc_processing_pg \
            -p 5432:5432 \
            -e POSTGRES_PASSWORD=postgres \
            -e POSTGRES_DB=doc_processing \
            postgres:16-alpine
        sleep 3
    fi

    # Check if Redis is running
    echo -e "${YELLOW}Checking Redis connection...${NC}"
    if ! redis-cli -h localhost -p 6379 ping > /dev/null 2>&1; then
        echo -e "${RED}Warning: Redis not running on localhost:6379${NC}"
        echo "Starting Redis with Docker..."
        docker run -d --name doc_processing_redis \
            -p 6379:6379 \
            redis:7-alpine
        sleep 2
    fi

    # Run migrations
    echo -e "${YELLOW}Running database migrations...${NC}"
    alembic upgrade head

    # Create storage directory
    mkdir -p storage/documents storage/pages

    echo ""
    echo -e "${GREEN}✅ Setup complete!${NC}"
    echo ""
    echo "To start the services, run in separate terminals:"
    echo ""
    echo -e "${YELLOW}Terminal 1 - API Server:${NC}"
    echo "   source venv/bin/activate"
    echo "   uvicorn app.main:app --reload"
    echo ""
    echo -e "${YELLOW}Terminal 2 - Celery Worker:${NC}"
    echo "   source venv/bin/activate"
    echo "   celery -A app.tasks.celery_app worker --loglevel=info"
    echo ""
    echo -e "${YELLOW}Terminal 3 - Flower (Optional monitoring):${NC}"
    echo "   source venv/bin/activate"
    echo "   celery -A app.tasks.celery_app flower"
    echo ""
fi
