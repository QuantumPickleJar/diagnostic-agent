#!/bin/bash

# Diagnostic Agent Deployment Script
# For Linux and Raspberry Pi
# Windows users: use deploy.ps1
# Diagnostic Agent Deployment Script
# For Linux and Raspberry Pi
# Windows users: use deploy.ps1

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Diagnostic Agent Deployment${NC}"

# Function to check Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not installed. Install with:${NC}"
        echo "curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker not running. Please start Docker first.${NC}"
        exit 1
    fi

    # Prefer new 'docker compose' over legacy 'docker-compose'
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        echo -e "${RED}❌ Docker Compose not available.${NC}"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --clean     Clean deployment (removes old images and volumes)"
    echo "  --no-build  Skip Docker build step"
    echo "  --logs      Show container logs"
    echo "  --status    Show container status"
    echo "  --stop      Stop the container"
    echo "  --smart     Enable smart agent startup"
    echo "  --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                # Normal deployment"
    echo "  $0 --clean        # Clean deployment"
    echo "  $0 --smart        # Deploy with smart agent startup"
    echo "  $0 --no-build     # Skip build step"
    echo "  $0 --logs         # View logs"
    echo "  $0 --status       # Check status"
}

# Function to get local IP
get_local_ip() {
    # Try hostname -I first (works on most Linux systems including Pi)
    if command -v hostname &> /dev/null; then
        local ip=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [[ -n "$ip" ]]; then
            echo "$ip"
            return
        fi
    fi
    
    # Fallback to localhost
    echo "localhost"
}

# Function to show status
show_status() {
    echo -e "${BLUE}📊 Container Status:${NC}"
    $DOCKER_COMPOSE ps
    
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
SMART=false
NO_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --no-build)
            NO_BUILD=true
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
        --smart)
            SMART=true
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
    $DOCKER_COMPOSE down
    exit 0
fi

if [[ "$LOGS" == true ]]; then
    echo -e "${YELLOW}📋 Showing logs (Ctrl+C to exit):${NC}"
    $DOCKER_COMPOSE logs -f
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
    $DOCKER_COMPOSE down
    docker image prune -f || true
    docker volume prune -f || true
fi

# Stop existing containers
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
$DOCKER_COMPOSE down || true

# Build the image
echo -e "${YELLOW}🔨 Building diagnostic agent image...${NC}"
if [[ "$NO_BUILD" == true ]]; then
    echo -e "${GRAY}Skipping build step...${NC}"
elif [[ "$CLEAN" == true ]]; then
    $DOCKER_COMPOSE build --no-cache
else
    $DOCKER_COMPOSE build
fi

# Start the container
echo -e "${YELLOW}▶️  Starting diagnostic agent container...${NC}"
$DOCKER_COMPOSE up -d

# Wait for container to be healthy
echo -e "${YELLOW}⏳ Waiting for container to be healthy...${NC}"
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if $DOCKER_COMPOSE ps | grep -q "healthy"; then
        echo -e "${GREEN}✅ Diagnostic agent is running and healthy!${NC}"
        break
    fi
    
    if [ $attempt -eq $((max_attempts - 1)) ]; then
        echo -e "${RED}❌ Container failed to become healthy after $max_attempts attempts${NC}"
        echo -e "${YELLOW}📋 Checking logs...${NC}"
        $DOCKER_COMPOSE logs --tail=50
        exit 1
    fi
    
    echo -e "${GRAY}Attempt $((attempt + 1))/$max_attempts - waiting for health check...${NC}"
    sleep 10
    attempt=$((attempt + 1))
done

# Show final status
show_status

# Test smart agent if requested
if [[ "$SMART" == true ]]; then
    echo ""
    echo -e "${YELLOW}🤖 Testing Smart Agent functionality...${NC}"
    sleep 5  # Give the agent time to fully initialize
    
    # Test if CLI is available and working
    if command -v python3 &> /dev/null; then
        echo -e "${CYAN}Testing smart agent query...${NC}"
        if python3 cli_prompt.py --activation-word PurpleTomato "What model is powering your responses?" 2>/dev/null; then
            echo -e "${GREEN}✅ Smart agent is responding correctly${NC}"
        else
            echo -e "${YELLOW}⚠️  Smart agent test failed - agent may still be initializing${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Python3 not available for smart agent testing${NC}"
    fi
fi

echo ""
echo -e "${YELLOW}📋 Recent logs:${NC}"
$DOCKER_COMPOSE logs --tail=10

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GRAY}💡 Use '$0 --logs' to view logs${NC}"
echo -e "${GRAY}💡 Use '$0 --status' to check status${NC}"
echo -e "${GRAY}💡 Use '$0 --stop' to stop the service${NC}"
echo -e "${GRAY}💡 Use '$0 --clean' for clean deployment${NC}"
