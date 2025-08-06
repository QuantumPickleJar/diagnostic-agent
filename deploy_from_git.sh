#!/bin/bash

# Git-based deployment script for Raspberry Pi
# Run this ON the Pi to pull latest code and rebuild

set -e

echo "🚀 Deploying Diagnostic Agent from Git..."

# Configuration
REPO_DIR="/home/castlebravo/diagnostic-agent"
BRANCH="main"  # or whatever branch you want to deploy

# Change to repo directory
cd "$REPO_DIR"

# Pull latest changes
echo "📥 Pulling latest changes from Git..."
git fetch origin
git reset --hard origin/$BRANCH
git clean -fd

# Stop current containers
echo "🛑 Stopping current containers..."
docker-compose -f docker-compose.production.yml down 2>/dev/null || true

# Build new image
echo "🔨 Building new image..."
if [ -f "Dockerfile.fast.cross" ]; then
    # Use the fast cross-compile dockerfile for Pi
    docker build -f Dockerfile.fast.cross -t diagnostic-agent:latest .
elif [ -f "Dockerfile.production" ]; then
    # Use production dockerfile
    docker build -f Dockerfile.production -t diagnostic-agent:latest .
else
    # Use default dockerfile
    docker build -t diagnostic-agent:latest .
fi

# Update docker-compose to use latest tag
echo "🔄 Updating docker-compose configuration..."
if [ -f "docker-compose.production.yml" ]; then
    # Temporarily update the image tag in docker-compose
    sed -i 's/diagnostic-agent:[a-zA-Z0-9_-]*/diagnostic-agent:latest/g' docker-compose.production.yml
    
    # Start containers with new image
    echo "▶️ Starting containers..."
    docker-compose -f docker-compose.production.yml up -d
else
    # Fallback to simple docker run
    echo "▶️ Starting container..."
    docker run -d --name diagnostic-journalist \
        -p 5000:5000 \
        -v $(pwd)/agent_memory:/app/agent_memory \
        --restart unless-stopped \
        diagnostic-agent:latest
fi

# Check status
echo "📊 Checking container status..."
sleep 5
if docker ps | grep -q diagnostic; then
    echo "✅ Deployment successful!"
    docker logs diagnostic-journalist --tail 10
else
    echo "❌ Deployment failed!"
    docker logs diagnostic-journalist --tail 20
    exit 1
fi

echo "🎉 Git-based deployment complete!"
echo "🌐 Agent should be available at: http://$(hostname -I | awk '{print $1}'):5000"
