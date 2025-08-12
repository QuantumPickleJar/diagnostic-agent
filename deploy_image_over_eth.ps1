#!/usr/bin/env pwsh
#
# PowerShell script for deploying ARM64 diagnostic agent to Raspberry Pi over Ethernet
#
# Usage: .\deploy_image_over_eth.ps1 [Pi_IP]
# If Pi_IP is not provided, defaults to 10.42.0.1
#
# This script builds and deploys the ARM64 image for Pi deployment.
# 
# Deployment Modes:
# - Pi Production: docker compose -f docker-compose.production.yml up -d (ARM64, delegates to dev machine)
# - Dev Symbiote:  docker compose -f docker-compose.symbiote.yml up -d (x86_64, all local models)

param(
    [string]$PiIP = "10.42.0.1"
)

Write-Host "Deploying ARM64 Diagnostic Agent to Raspberry Pi" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

# Check if ARM64 Pi image exists
$imageExists = docker image inspect diagnostic-agent:pi-arm64 2>$null
if (-not $imageExists) {
    Write-Host "[ERR] Image 'diagnostic-agent:pi-arm64' not found" -ForegroundColor Red
    Write-Host "[INFO] Building ARM64 Pi image..." -ForegroundColor Yellow
    
    # Build the ARM64 Pi image using production compose
    docker compose -f docker-compose.production.yml build
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERR] Failed to build ARM64 image" -ForegroundColor Red
        exit 1
    }
    
    # Tag the built image for clarity
    docker tag diagnostic-agent:production-arm64 diagnostic-agent:pi-arm64
    Write-Host "[OK] ARM64 Pi image built successfully" -ForegroundColor Green
}

# Create tarball (uncompressed for Windows compatibility)
$tarFile = "diagnostic-agent_pi-arm64.tar"
if (-not (Test-Path $tarFile)) {
    Write-Host "Creating deployment package..." -ForegroundColor Yellow
    docker save diagnostic-agent:pi-arm64 -o $tarFile
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create Docker image tar" -ForegroundColor Red
        exit 1
    }
}

# Get file size
$fileSize = [math]::Round((Get-Item $tarFile).Length / 1MB, 1)
Write-Host "Deployment package: $tarFile ($fileSize MB)" -ForegroundColor Cyan

# Transfer to Pi over Ethernet
Write-Host "Transferring to Pi at $PiIP..." -ForegroundColor Yellow
scp -P 2222 $tarFile castlebravo@${PiIP}:/home/diagnostic-agent/

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Transfer successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps on Pi:" -ForegroundColor Cyan
    Write-Host "1. SSH to Pi: ssh -p 2222 castlebravo@$PiIP" -ForegroundColor White
    Write-Host "2. Load image: docker load -i /home/diagnostic-agent/$tarFile" -ForegroundColor White
    Write-Host "3. Check architecture compatibility:" -ForegroundColor White
    Write-Host "   docker image inspect diagnostic-agent:pi-arm64 | grep Architecture" -ForegroundColor Gray
    Write-Host "   # Should show 'arm64' for Pi, 'amd64' for x86 machines" -ForegroundColor DarkGray
    Write-Host "4. Tag the new image as latest:" -ForegroundColor White
    Write-Host "   docker tag diagnostic-agent:pi-arm64 diagnostic-agent:latest" -ForegroundColor Gray
    Write-Host "5. Optional - backup current image before replacement:" -ForegroundColor White
    Write-Host "   docker tag diagnostic-agent:latest diagnostic-agent:backup-$(date +%Y%m%d)" -ForegroundColor Gray
    Write-Host "6. Fix volume permissions for container user:" -ForegroundColor White
    Write-Host "   sudo chown -R 1000:1000 logs/ models/ temp/ agent_memory/" -ForegroundColor Gray
    Write-Host "7. Use production compose for Pi deployment:" -ForegroundColor White
    Write-Host "   docker compose -f docker-compose.production.yml up -d" -ForegroundColor Gray
    Write-Host "8. Verify deployment:" -ForegroundColor White
    Write-Host "   docker compose -f docker-compose.production.yml ps && docker logs diagnostic-journalist" -ForegroundColor Gray
    Write-Host "9. Test local LLM functionality:" -ForegroundColor White
    Write-Host "   curl 'http://localhost:5000/ask' -d 'query=test local model' -H 'Content-Type: application/x-www-form-urlencoded'" -ForegroundColor Gray
    Write-Host "10. Clean up old images (optional):" -ForegroundColor White
    Write-Host "   docker image prune -f" -ForegroundColor Gray
    Write-Host ""
    Write-Host "[INFO] Executing deployment on Pi..." -ForegroundColor Cyan
    
    # Execute deployment commands directly on Pi
    $deployCommands = @"
echo '[>>] Loading new image with stats functionality...'
docker load -i /home/diagnostic-agent/$tarFile

echo '[>>] Stopping existing diagnostic-agent containers...'
docker stop diagnostic-agent-container 2>/dev/null || true
docker rm diagnostic-agent-container 2>/dev/null || true

echo '[>>] Backing up current latest image (if exists)...'
docker tag diagnostic-agent:latest diagnostic-agent:backup-$(date +%Y%m%d-%H%M) 2>/dev/null || echo 'No existing latest image to backup'

echo '[>>] Tagging new image as latest...'
docker tag diagnostic-agent:pi-arm64 diagnostic-agent:latest

echo '[>>] Starting new container with stats functionality...'
docker run -d \
  --name diagnostic-agent-container \
  --restart unless-stopped \
  -p 5000:5000 \
  -v /home/castlebravo/agent_memory:/app/agent_memory \
  diagnostic-agent:latest

echo '[>>] Cleaning up old images (keeping backup and latest)...'
docker image prune -f

echo '[>>] Cleaning up deployment file...'
rm -f /home/diagnostic-agent/$tarFile

echo '[OK] Deployment complete! Stats functionality should now be available.'
echo '[INFO] Container status:'
docker ps | grep diagnostic-agent || echo 'Container not running - check logs'
echo '[INFO] Access interface at: http://$(hostname -I | awk '{print $1}'):5000'
"@

    ssh -p 2222 castlebravo@${PiIP} $deployCommands
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Deployment completed successfully!" -ForegroundColor Green
        Write-Host "[INFO] The Stats button should now be available in the web interface" -ForegroundColor Cyan
    } else {
        Write-Host "[WARN] Remote deployment may have encountered issues" -ForegroundColor Yellow
    }
    
    # Clean up local deployment file
    Write-Host "[>>] Cleaning up local deployment file..." -ForegroundColor Yellow
    Remove-Item $tarFile -Force -ErrorAction SilentlyContinue
    
} else {
    Write-Host "[ERR] Transfer failed" -ForegroundColor Red
    Write-Host "Check connection to $PiIP:2222" -ForegroundColor Yellow
}
