#!/usr/bin/env pwsh
#
# PowerShell script for deploying fixed diagnostic agent over Ethernet (wired Pi connection)
#
# Usage: .\deploy_image_over_eth.ps1 [Pi_IP]
# If Pi_IP is not provided, defaults to 10.42.0.1

param(
    [string]$PiIP = "10.42.0.1"
)

Write-Host "Deploying Fixed Diagnostic Agent over Ethernet" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

# Check if image exists
$imageExists = docker image inspect diagnostic-agent:fast-cross-fixed 2>$null
if (-not $imageExists) {
    Write-Host "Image 'diagnostic-agent:fast-cross-fixed' not found" -ForegroundColor Red
    Write-Host "Run: docker build -f Dockerfile.fast.cross -t diagnostic-agent:fast-cross-fixed ." -ForegroundColor Yellow
    exit 1
}

# Create tarball (uncompressed for Windows compatibility)
$tarFile = "diagnostic-agent_fast-cross-fixed.tar"
if (-not (Test-Path $tarFile)) {
    Write-Host "Creating deployment package..." -ForegroundColor Yellow
    docker save diagnostic-agent:fast-cross-fixed -o $tarFile
    
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
scp -P 2222 $tarFile castlebravo@${PiIP}:~/

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Transfer successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps on Pi:" -ForegroundColor Cyan
    Write-Host "1. SSH to Pi: ssh -p 2222 castlebravo@$PiIP" -ForegroundColor White
    Write-Host "2. Load image: docker load -i ~/$tarFile" -ForegroundColor White
    Write-Host "3. Update docker-compose to use new image" -ForegroundColor White
    Write-Host "4. Restart: docker-compose down && docker-compose up -d" -ForegroundColor White
} else {
    Write-Host "❌ Transfer failed" -ForegroundColor Red
    Write-Host "Check connection to $PiIP:2222" -ForegroundColor Yellow
}
