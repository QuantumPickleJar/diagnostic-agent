# PowerShell Deployment Script for Diagnostic Agent
# Universal script for Windows (and cross-platform PowerShell)

param(
    [switch]$Clean,
    [switch]$Logs,
    [switch]$Status,
    [switch]$Stop,
    [switch]$Help
)

# Function to show usage
function Show-Usage {
    Write-Host "Diagnostic Agent Deployment Script" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\deploy.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -Clean      Clean deployment (removes old images and volumes)" -ForegroundColor Gray
    Write-Host "  -Logs       Show container logs" -ForegroundColor Gray
    Write-Host "  -Status     Show container status" -ForegroundColor Gray
    Write-Host "  -Stop       Stop the container" -ForegroundColor Gray
    Write-Host "  -Help       Show this help message" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\deploy.ps1           # Normal deployment" -ForegroundColor Gray
    Write-Host "  .\deploy.ps1 -Clean    # Clean deployment" -ForegroundColor Gray
    Write-Host "  .\deploy.ps1 -Logs     # View logs" -ForegroundColor Gray
    Write-Host "  .\deploy.ps1 -Status   # Check status" -ForegroundColor Gray
}

# Function to check if Docker is running
function Test-DockerRunning {
    try {
        docker info | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to get local IP address
function Get-LocalIP {
    try {
        $ip = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "Ethernet*" | Where-Object {$_.IPAddress -notlike "169.254.*"})[0].IPAddress
        if (-not $ip) { 
            $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*"})[0].IPAddress
        }
        if (-not $ip) { $ip = "localhost" }
        return $ip
    }
    catch {
        return "localhost"
    }
}

# Function to display status
function Show-Status {
    Write-Host "📊 Container Status:" -ForegroundColor Yellow
    docker-compose ps
    
    Write-Host "`n🌐 Endpoints:" -ForegroundColor Yellow
    $ip = Get-LocalIP
    
    Write-Host "   Main interface: http://${ip}:5000" -ForegroundColor Cyan
    Write-Host "   Health check:   http://${ip}:5000/health" -ForegroundColor Cyan
    Write-Host "   Status:         http://${ip}:5000/status" -ForegroundColor Cyan
    
    # Test health endpoint
    Write-Host "`n🔍 Testing health endpoint..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Service is healthy" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "❌ Service is not responding" -ForegroundColor Red
    }
}

# Show help if requested
if ($Help) {
    Show-Usage
    exit 0
}

Write-Host "🚀 Diagnostic Agent Deployment Script" -ForegroundColor Green
Write-Host "Platform: Windows (PowerShell)" -ForegroundColor Gray

# Check Docker
if (-not (Test-DockerRunning)) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Handle different operations
if ($Stop) {
    Write-Host "🛑 Stopping Diagnostic Agent..." -ForegroundColor Yellow
    docker-compose down
    exit 0
}

if ($Logs) {
    Write-Host "📋 Showing logs (Ctrl+C to exit):" -ForegroundColor Yellow
    docker-compose logs -f
    exit 0
}

if ($Status) {
    Show-Status
    exit 0
}

# Main deployment process
Write-Host "🔧 Starting deployment process..." -ForegroundColor Yellow

# Create necessary directories
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}
if (-not (Test-Path "models")) {
    New-Item -ItemType Directory -Path "models" | Out-Null
}

# Clean deployment if requested
if ($Clean) {
    Write-Host "🧹 Performing clean deployment..." -ForegroundColor Yellow
    docker-compose down
    docker image prune -f
    docker volume prune -f
}

# Stop existing containers
Write-Host "🛑 Stopping existing containers..." -ForegroundColor Yellow
docker-compose down

# Build the image
Write-Host "🔨 Building diagnostic agent image..." -ForegroundColor Yellow
if ($Clean) {
    docker-compose build --no-cache
} else {
    docker-compose build
}

# Start the container
Write-Host "▶️  Starting diagnostic agent container..." -ForegroundColor Yellow
docker-compose up -d

# Wait for container to be healthy
Write-Host "⏳ Waiting for container to be healthy..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

do {
    Start-Sleep -Seconds 5
    $attempt++
    
    try {
        $containerStatus = docker-compose ps --format "table {{.State}}" | Select-String "healthy"
        
        if ($containerStatus) {
            Write-Host "✅ Diagnostic agent is running and healthy!" -ForegroundColor Green
            break
        }
    }
    catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "❌ Container failed to become healthy after $maxAttempts attempts" -ForegroundColor Red
        Write-Host "📋 Checking logs..." -ForegroundColor Yellow
        docker-compose logs --tail=50
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - waiting for health check..." -ForegroundColor Gray
} while ($attempt -lt $maxAttempts)

# Show final status
Show-Status

Write-Host "`n📋 Recent logs:" -ForegroundColor Yellow
docker-compose logs --tail=10

Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
Write-Host "💡 Use '.\deploy.ps1 -Logs' to view logs" -ForegroundColor Gray
Write-Host "💡 Use '.\deploy.ps1 -Status' to check status" -ForegroundColor Gray
Write-Host "💡 Use '.\deploy.ps1 -Stop' to stop the service" -ForegroundColor Gray
Write-Host "💡 Use '.\deploy.ps1 -Clean' for clean deployment" -ForegroundColor Gray
