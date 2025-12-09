#!/bin/bash

# Development helper script for AI Document Processing
# Runs all services: Backend (Docker), Frontend (React), and Marketing (Astro)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
}

# Print banner
echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║   AI Document Processing - Development Server     ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# Check dependencies
print_info "Checking dependencies..."

if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check for docker compose (v2 plugin) or docker-compose (standalone)
if ! docker compose version >/dev/null 2>&1 && ! command_exists docker-compose; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

if ! command_exists npm; then
    print_error "npm is not installed. Please install Node.js and npm first."
    exit 1
fi

print_success "All dependencies are installed"

# Check ports
print_info "Checking if required ports are available..."

if port_in_use 8000; then
    print_warning "Port 8000 is already in use (API). Stop the service or it will fail."
fi

if port_in_use 3002; then
    print_warning "Port 3002 is already in use (Frontend). Stop the service or it will fail."
fi

if port_in_use 4321; then
    print_warning "Port 4321 is already in use (Marketing). Stop the service or it will fail."
fi

# Parse command line arguments
SERVICE=${1:-all}

case $SERVICE in
    backend|api)
        print_info "Starting backend services (FastAPI + PostgreSQL + Redis)..."
        docker compose up
        ;;

    frontend|react)
        print_info "Starting React frontend..."
        cd frontend && npm run dev
        ;;

    marketing|astro)
        print_info "Starting Astro marketing site..."
        cd marketing && npm run dev
        ;;

    all)
        print_info "Starting all services..."
        print_info ""
        print_info "This will open 3 terminal tabs/windows:"
        print_info "  1. Backend (API, Database, Redis) - http://localhost:8000"
        print_info "  2. Frontend (React App) - http://localhost:3002"
        print_info "  3. Marketing (Astro Site) - http://localhost:4321"
        print_info ""

        # Detect terminal emulator and open tabs
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            osascript <<EOF
tell application "Terminal"
    activate

    -- Backend
    do script "cd \"$PWD\" && docker compose up"

    -- Frontend
    set frontendTab to do script "cd \"$PWD/frontend\" && npm run dev"

    -- Marketing
    set marketingTab to do script "cd \"$PWD/marketing\" && npm run dev"
end tell
EOF
            print_success "Opened 3 terminal tabs"
        else
            # Linux - try various terminal emulators
            if command_exists gnome-terminal; then
                gnome-terminal --tab -- bash -c "docker compose up; exec bash"
                gnome-terminal --tab -- bash -c "cd frontend && npm run dev; exec bash"
                gnome-terminal --tab -- bash -c "cd marketing && npm run dev; exec bash"
            elif command_exists konsole; then
                konsole --new-tab -e bash -c "docker compose up; exec bash"
                konsole --new-tab -e bash -c "cd frontend && npm run dev; exec bash"
                konsole --new-tab -e bash -c "cd marketing && npm run dev; exec bash"
            else
                print_warning "Automatic terminal tab opening not supported on this system."
                print_info "Please manually run these commands in separate terminals:"
                echo ""
                echo "  Terminal 1: docker compose up"
                echo "  Terminal 2: cd frontend && npm run dev"
                echo "  Terminal 3: cd marketing && npm run dev"
            fi
        fi
        ;;

    install)
        print_info "Installing dependencies for all services..."

        print_info "Installing frontend dependencies..."
        cd frontend && npm install && cd ..

        print_info "Installing marketing dependencies..."
        cd marketing && npm install && cd ..

        print_success "All dependencies installed"
        ;;

    *)
        echo "Usage: $0 [backend|frontend|marketing|all|install]"
        echo ""
        echo "Commands:"
        echo "  backend, api     - Start backend services only (Docker)"
        echo "  frontend, react  - Start React frontend only"
        echo "  marketing, astro - Start Astro marketing site only"
        echo "  all              - Start all services (default)"
        echo "  install          - Install all npm dependencies"
        echo ""
        echo "Examples:"
        echo "  $0                # Start all services"
        echo "  $0 backend        # Start only backend"
        echo "  $0 frontend       # Start only frontend"
        echo "  $0 install        # Install dependencies"
        exit 1
        ;;
esac
