#!/usr/bin/env powershell
<#
.SYNOPSIS
Set up cross-compilation environment for building ARM64 Docker images on Windows dev machine

.DESCRIPTION
This script prepares your Windows development machine for cross-compiling Docker images
to deploy to your Raspberry Pi. It installs Docker Desktop buildx and sets up the ARM64 platform.

.PARAMETER SetupOnly
Only sets up the environment without building
#>

param(
    [switch]$SetupOnly
)

$ErrorActionPreference = "Stop"

Write-Host "🔧 Setting up cross-compilation environment..." -ForegroundColor Cyan

# Check if Docker is installed
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found. Please install Docker Desktop first." -ForegroundColor Red
    Write-Host "Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# Check if buildx is available
try {
    docker buildx version | Out-Null
    Write-Host "✅ Docker Buildx available" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Buildx not available. Please update Docker Desktop." -ForegroundColor Red
    exit 1
}

# Create and use a new builder that supports ARM64
Write-Host "🏗️ Setting up multi-platform builder..." -ForegroundColor Yellow

try {
    # Remove existing builder if it exists
    docker buildx rm diagnostic-builder 2>$null
    
    # Create new builder
    docker buildx create --name diagnostic-builder --driver docker-container --platform linux/amd64,linux/arm64
    docker buildx use diagnostic-builder
    docker buildx inspect --bootstrap
    
    Write-Host "✅ Multi-platform builder 'diagnostic-builder' created" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create builder: $_" -ForegroundColor Red
    exit 1
}

# Verify platforms
Write-Host "🔍 Checking available platforms..." -ForegroundColor Yellow
$platforms = docker buildx inspect | Select-String "Platforms:"
Write-Host "Available platforms: $platforms" -ForegroundColor Cyan

if ($SetupOnly) {
    Write-Host "✅ Setup complete! You can now cross-compile ARM64 images." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Run: .\cross_compile_and_deploy.ps1" -ForegroundColor White
    Write-Host "  2. Or manually: docker buildx build --platform linux/arm64 -t diagnostic-agent:arm64 ." -ForegroundColor White
    exit 0
}

Write-Host "✅ Cross-compilation environment ready!" -ForegroundColor Green
