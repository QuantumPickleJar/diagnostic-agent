#!/usr/bin/env powershell
<#
.SYNOPSIS
Cross-compile ARM64 Docker image on dev machine and deploy to Raspberry Pi

.DESCRIPTION
This script builds the Docker image for ARM64 on your Windows dev machine (much faster than Pi),
then transfers and deploys it to your Raspberry Pi via SSH.

.PARAMETER UseProduction
Use production Dockerfile instead of fast variant

.PARAMETER SkipBuild
Skip building, just deploy existing image

.PARAMETER RestartService
Restart the service after deployment

.PARAMETER ShowLogs
Show container logs after deployment
#>

param(
    [switch]$UseProduction,
    [switch]$SkipBuild,
    [switch]$RestartService,
    [switch]$ShowLogs
)

$ErrorActionPreference = "Stop"

# Configuration
$PI_USER = "your_pi_user"
$PI_HOST = "your_pi_host.local"
$PI_PORT = "2222"
$IMAGE_NAME = "diagnostic-agent"
$CONTAINER_NAME = "diagnostic-journalist"

# Determine which Dockerfile to use
$DOCKERFILE = if ($UseProduction) { "Dockerfile.production" } else { "Dockerfile.fast" }
$BUILD_TAG = if ($UseProduction) { "production" } else { "fast" }
$FULL_IMAGE_NAME = "${IMAGE_NAME}:${BUILD_TAG}-arm64"

Write-Host "Cross-Compilation Deployment Pipeline" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "${Target: $PI_USER@$PI_HOST:$PI_PORT}" -ForegroundColor Yellow
Write-Host "Dockerfile: $DOCKERFILE" -ForegroundColor Yellow
Write-Host "Image: $FULL_IMAGE_NAME" -ForegroundColor Yellow
Write-Host ""

if (-not $SkipBuild) {
    Write-Host "Building ARM64 image on dev machine..." -ForegroundColor Yellow
    Write-Host "This will be much faster than building on Pi!" -ForegroundColor Green
    
    try {
        # Use buildx to create ARM64 image
        $buildCommand = @(
            "docker", "buildx", "build",
            "--platform", "linux/arm64",
            "--file", $DOCKERFILE,
            "--tag", $FULL_IMAGE_NAME,
            "--load",  # Load into local Docker for export
            "."
        )
        
        Write-Host "Running: $($buildCommand -join ' ')" -ForegroundColor Gray
        & $buildCommand[0] $buildCommand[1..($buildCommand.Length-1)]
        
        if ($LASTEXITCODE -ne 0) {
            throw "Build failed with exit code $LASTEXITCODE"
        }
        
        Write-Host "ARM64 image built successfully!" -ForegroundColor Green
    } catch {
        Write-Host "ERR: Build failed: $_" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "Exporting image for transfer..." -ForegroundColor Yellow
    
    # Export image to tar file
    $tarFile = "${IMAGE_NAME}_${BUILD_TAG}_arm64.tar"
    try {
        docker save $FULL_IMAGE_NAME -o $tarFile
        Write-Host "Image exported to $tarFile" -ForegroundColor Green
    } catch {
        Write-Host "ERR: Export failed: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Deploying to Raspberry Pi..." -ForegroundColor Yellow

try {
    if (-not $SkipBuild) {
        # Transfer tar file to Pi
        Write-Host "Transferring image to Pi..." -ForegroundColor Cyan
        $scpCommand = @("scp", "-P", $PI_PORT, $tarFile, "${PI_USER}@${PI_HOST}:~/")
        & $scpCommand[0] $scpCommand[1..($scpCommand.Length-1)]
        
        if ($LASTEXITCODE -ne 0) {
            throw "File transfer failed"
        }
        
        # Load image on Pi
        Write-Host "Loading image on Pi..." -ForegroundColor Cyan
        $sshLoadCommand = @(
            "ssh", "-p", $PI_PORT, "${PI_USER}@${PI_HOST}",
            "docker load -i ~/$tarFile && rm ~/$tarFile"
        )
        & $sshLoadCommand[0] $sshLoadCommand[1..($sshLoadCommand.Length-1)]
        
        if ($LASTEXITCODE -ne 0) {
            throw "Image load failed"
        }
    }
    
    # Deploy on Pi
    Write-Host "Deploying container on Pi..." -ForegroundColor Cyan
    
    $composeFile = if ($UseProduction) { "docker-compose.yml" } else { "docker-compose.fast.yml" }
    
    $deployCommands = @(
        "cd /home/diagnostic-agent",
        "docker-compose -f $composeFile down || true",
        "docker tag $FULL_IMAGE_NAME diagnostic-agent:latest",
        "docker-compose -f $composeFile up -d"
    )
    
    $deployScript = $deployCommands -join " && "
    
    $sshDeployCommand = @(
        "ssh", "-p", $PI_PORT, "${PI_USER}@${PI_HOST}",
        $deployScript
    )
    & $sshDeployCommand[0] $sshDeployCommand[1..($sshDeployCommand.Length-1)]
    
    if ($LASTEXITCODE -ne 0) {
        throw "Deployment failed"
    }
    
    Write-Host "Deployment successful!" -ForegroundColor Green
    
    # Clean up local tar file
    if (-not $SkipBuild -and (Test-Path $tarFile)) {
        Remove-Item $tarFile
        Write-Host "Cleaned up local tar file" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "ERR: Deployment failed: $_" -ForegroundColor Red
    exit 1
}

if ($ShowLogs) {
    Write-Host ""
    Write-Host "Container logs:" -ForegroundColor Yellow
    $logCommand = @(
        "ssh", "-p", $PI_PORT, "${PI_USER}@${PI_HOST}",
        "docker logs $CONTAINER_NAME --tail 20"
    )
    & $logCommand[0] $logCommand[1..($logCommand.Length-1)]
}

Write-Host ""
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "Access your diagnostic agent at: http://${PI_HOST}:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next commands:" -ForegroundColor Yellow
Write-Host "  View logs: ssh -p $PI_PORT $PI_USER@$PI_HOST 'docker logs $CONTAINER_NAME'" -ForegroundColor White
Write-Host "  Restart:   .\cross_compile_and_deploy.ps1 -SkipBuild -RestartService" -ForegroundColor White
Write-Host "  Monitor:   ssh -p $PI_PORT $PI_USER@$PI_HOST 'docker stats'" -ForegroundColor White
