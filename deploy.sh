#!/bin/bash

# Universal Deployment Script for Diagnostic Agent
# Works on Linux (including Raspberry Pi) and macOS
# For Windows, use deploy.ps1

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Detect platform
PLATFORM="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
    # Check if it's a Raspberry Pi
    if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        PLATFORM="pi"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
fi

echo -e "${GREEN}🚀 Diagnostic Agent Deployment Script${NC}"
echo -e "${GRAY}Platform detected: $PLATFORM${NC}"

# Function to check if Docker is installed and running
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed.${NC}"
        if [[ "$PLATFORM" == "pi" || "$PLATFORM" == "linux" ]]; then
            echo "Install with: curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
        elif [[ "$PLATFORM" == "macos" ]]; then
            echo "Install Docker Desktop from: https://www.docker.com/products/docker-desktop"
        fi
        exit 1
    fi

    # Check if Docker is running
    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not available.${NC}"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --clean     Clean deployment (removes old images and volumes)"
    echo "  --logs      Show container logs"
    echo "  --status    Show container status"
    echo "  --stop      Stop the container"
    echo "  --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                # Normal deployment"
    echo "  $0 --clean        # Clean deployment"
    echo "  $0 --logs         # View logs"
    echo "  $0 --status       # Check status"
}

# Function to get local IP
get_local_ip() {
    if [[ "$PLATFORM" == "pi" || "$PLATFORM" == "linux" ]]; then
        hostname -I | awk '{print $1}'
    elif [[ "$PLATFORM" == "macos" ]]; then
        ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1
    else
        echo "localhost"
    fi
}

# Function to show status
show_status() {
    echo -e "${BLUE}📊 Container Status:${NC}"
    docker-compose ps
    
    echo ""
    echo -e "${BLUE}🌐 Endpoints:${NC}"
    local_ip=$(get_local_ip)
    echo -e "   Main interface: ${CYAN}http://${local_ip}:5000${NC}"
    echo -e "   Health check:   ${CYAN}http://${local_ip}:5000/health${NC}"
    echo -e "   Status:         ${CYAN}http://${local_ip}:5000/status${NC}"
    
    # Test health endpoint
    echo ""
    echo -e "${YELLOW}🔍 Testing health endpoint...${NC}"
    if curl -sf "http://localhost:5000/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Service is healthy${NC}"
    else
        echo -e "${RED}❌ Service is not responding${NC}"
    fi
}

# Parse command line arguments
CLEAN=false
LOGS=false
STATUS=false
STOP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --logs)
            LOGS=true
            shift
            ;;
        --status)
            STATUS=true
            shift
            ;;
        --stop)
            STOP=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# Check Docker
check_docker

# Handle different operations
if [[ "$STOP" == true ]]; then
    echo -e "${YELLOW}🛑 Stopping Diagnostic Agent...${NC}"
    docker-compose down
    exit 0
fi

if [[ "$LOGS" == true ]]; then
    echo -e "${YELLOW}📋 Showing logs (Ctrl+C to exit):${NC}"
    docker-compose logs -f
    exit 0
fi

if [[ "$STATUS" == true ]]; then
    show_status
    exit 0
fi

# Main deployment process
echo -e "${YELLOW}🔧 Starting deployment process...${NC}"

# Create necessary directories
mkdir -p logs
mkdir -p models

# Clean deployment if requested
if [[ "$CLEAN" == true ]]; then
    echo -e "${YELLOW}🧹 Performing clean deployment...${NC}"
    docker-compose down
    docker image prune -f || true
    if [[ "$PLATFORM" == "pi" ]]; then
        # On Pi, also clean up volumes to free space
        docker volume prune -f || true
    fi
fi

# Stop existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down || true

# Build the image
echo -e "${YELLOW}🔨 Building diagnostic agent image...${NC}"
if [[ "$CLEAN" == true ]]; then
    docker-compose build --no-cache
else
    docker-compose build
fi

# Start the container
echo -e "${YELLOW}▶️  Starting diagnostic agent container...${NC}"
docker-compose up -d

# Wait for container to be healthy
echo -e "${YELLOW}⏳ Waiting for container to be healthy...${NC}"
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose ps | grep -q "healthy"; then
        echo -e "${GREEN}✅ Diagnostic agent is running and healthy!${NC}"
        break
    fi
    
    if [ $attempt -eq $((max_attempts - 1)) ]; then
        echo -e "${RED}❌ Container failed to become healthy after $max_attempts attempts${NC}"
        echo -e "${YELLOW}📋 Checking logs...${NC}"
        docker-compose logs --tail=50
        exit 1
    fi
    
    echo -e "${GRAY}Attempt $((attempt + 1))/$max_attempts - waiting for health check...${NC}"
    sleep 10
    attempt=$((attempt + 1))
done

# Show final status
show_status

echo ""
echo -e "${YELLOW}📋 Recent logs:${NC}"
docker-compose logs --tail=10

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GRAY}💡 Use '$0 --logs' to view logs${NC}"
echo -e "${GRAY}💡 Use '$0 --status' to check status${NC}"
echo -e "${GRAY}💡 Use '$0 --stop' to stop the service${NC}"
echo -e "${GRAY}💡 Use '$0 --clean' for clean deployment${NC}"
