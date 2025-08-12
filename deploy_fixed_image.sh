#!/bin/bash
#
# Quick deployment script for the fixed diagnostic agent
#

echo "Deploying Fixed Diagnostic Agent"
echo "=================================="

# Check if image exists
if ! docker image inspect diagnostic-agent:fast-cross-fixed >/dev/null 2>&1; then
    echo "Image 'diagnostic-agent:fast-cross-fixed' not found"
    echo "Run: docker build -f Dockerfile.fast.cross -t diagnostic-agent:fast-cross-fixed ."
    exit 1
fi

# Create tarball if it doesn't exist
if [ ! -f "diagnostic-agent_fast-cross-fixed.tar.gz" ]; then
    echo "Creating deployment tarball..."
    docker save diagnostic-agent:fast-cross-fixed | gzip > diagnostic-agent_fast-cross-fixed.tar.gz
fi

# Get file size
size=$(du -h diagnostic-agent_fast-cross-fixed.tar.gz | cut -f1)
echo "Deployment package: diagnostic-agent_fast-cross-fixed.tar.gz ($size)"

# Transfer to Pi
echo "Transferring to Pi..."
scp -P 2222 diagnostic-agent_fast-cross-fixed.tar.gz castlebravo@picklegate.ddns.net:~/

if [ $? -eq 0 ]; then
    echo "Transfer successful!"
    
    # Deploy on Pi
    echo "Deploying on Pi..."
    ssh -p 2222 castlebravo@picklegate.ddns.net '
        echo "Loading new image..."
        docker load -i ~/diagnostic-agent_fast-cross-fixed.tar.gz
        
        echo "Stopping current container..."
        cd /home/diagnostic-agent
        docker-compose down
        
        echo "Updating docker-compose to use new image..."
        # Create backup of current compose file
        cp docker-compose.fast.cross.yml docker-compose.fast.cross.yml.backup
        
        # Update image name in compose file
        sed -i "s/image: diagnostic-agent:fast-cross/image: diagnostic-agent:fast-cross-fixed/" docker-compose.fast.cross.yml
        
        echo "Starting with new image..."
        docker compose -f docker-compose.fast.cross.yml up -d
        
        echo "Deployment complete!"
        echo "Checking container status..."
        docker compose -f docker-compose.fast.cross.yml ps

        echo ""
        echo "To monitor startup:"
        echo "  docker compose -f docker-compose.fast.cross.yml logs -f"
    '
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "Deployment successful!"
        echo "The fixed image includes:"
        echo "  Fixed libgomp.so.1 dependency"
        echo "  Proper cache directory permissions"
        echo "  Automatic model pre-loading"
        echo "  Component testing on startup"
        echo ""
        echo "Monitor the deployment:"
        echo "  ssh -p 2222 castlebravo@picklegate.ddns.net"
        echo "  cd /home/diagnostic-agent"
        echo "  docker compose -f docker-compose.fast.cross.yml logs -f"
    else
        echo "❌ Deployment failed!"
    fi
else
    echo "❌ Transfer failed!"
fi
