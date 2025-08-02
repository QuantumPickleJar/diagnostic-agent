# Diagnostic Agent Deployment Script for Windows
# For Linux/Pi users: use deploy.sh

param(
    [switch]$Clean,
    [switch]$Logs,
    [switch]$Status,
    [switch]$Stop,
    [switch]$Help
)

# Function to show usage
function Show-Usage {
    Write-Host "Diagnostic Agent Deployment" -ForegroundColor Green
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
}

# Function to check Docker
function Test-Docker {
    try {
        docker info | Out-Null
        return $true
    }
    catch {
        Write-Host "ERR: Docker not running. Please start Docker Desktop first." -ForegroundColor Red
        exit 1
    }
}

# Function to get Docker Compose command
function Get-DockerCompose {
    try {
        docker compose version | Out-Null
        return "docker compose"
    }
    catch {
        try {
            docker-compose version | Out-Null
            return "docker-compose"
        }
        catch {
            Write-Host "ERR: Docker Compose not available." -ForegroundColor Red
            exit 1
        }
    }
}

# Function to get local IP
function Get-LocalIP {
    try {
        $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
            $_.IPAddress -notlike "127.*" -and 
            $_.IPAddress -notlike "169.254.*" -and
            $_.InterfaceAlias -notlike "*Loopback*"
        })[0].IPAddress
        if ($ip) { return $ip } else { return "localhost" }
    }
    catch {
        return "localhost"
    }
}

# Function to show status
function Show-Status {
    Write-Host "Container Status:" -ForegroundColor Blue
    & $DockerCompose ps
    
    Write-Host ""
    Write-Host "Endpoints:" -ForegroundColor Blue
    $localIP = Get-LocalIP
    Write-Host "   Main interface: http://$localIP:5000" -ForegroundColor Cyan
    Write-Host "   Health check:   http://$localIP:5000/health" -ForegroundColor Cyan
    Write-Host "   Status:         http://$localIP:5000/status" -ForegroundColor Cyan
    
    Write-Host ""
    Write-Host "Testing health endpoint..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "Service is healthy" -ForegroundColor Green
        } else {
            Write-Host "ERR: Service returned status: $($response.StatusCode)" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "ERR: Service is not responding" -ForegroundColor Red
    }
}

# Show help if requested
if ($Help) {
    Show-Usage
    exit 0
}

# Check Docker
Write-Host "Diagnostic Agent Deployment" -ForegroundColor Green
Test-Docker | Out-Null
$DockerCompose = Get-DockerCompose

# Handle different operations
if ($Stop) {
    Write-Host "Stopping Diagnostic Agent..." -ForegroundColor Yellow
    & $DockerCompose down
    exit 0
}

if ($Logs) {
    Write-Host "Showing logs (Ctrl+C to exit):" -ForegroundColor Yellow
    & $DockerCompose logs -f
    exit 0
}

if ($Status) {
    Show-Status
    exit 0
}

# Main deployment process
Write-Host "Starting deployment process..." -ForegroundColor Yellow

# Create necessary directories
if (!(Test-Path "logs")) { New-Item -ItemType Directory -Name "logs" | Out-Null }
if (!(Test-Path "models")) { New-Item -ItemType Directory -Name "models" | Out-Null }

# Clean deployment if requested
if ($Clean) {
    Write-Host "Performing clean deployment..." -ForegroundColor Yellow
    & $DockerCompose down
    docker image prune -f
    docker volume prune -f
}

# Stop existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
& $DockerCompose down

# Build the image
Write-Host "Building diagnostic agent image..." -ForegroundColor Yellow
if ($Clean) {
    & $DockerCompose build --no-cache
} else {
    & $DockerCompose build
}

# Start the container
Write-Host "Starting diagnostic agent container..." -ForegroundColor Yellow
& $DockerCompose up -d

# Wait for container to be healthy
Write-Host "Waiting for container to be healthy..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

do {
    Start-Sleep -Seconds 10
    $attempt++
    
    try {
        $containerStatus = & $DockerCompose ps --format "table {{.State}}" | Select-String "healthy"
        
        if ($containerStatus) {
            Write-Host "Diagnostic agent is running and healthy!" -ForegroundColor Green
            break
        }
    }
    catch {
        # Continue waiting
    }
    
    if ($attempt -eq $maxAttempts) {
        Write-Host "ERR: Container failed to become healthy after $maxAttempts attempts" -ForegroundColor Red
        Write-Host "Checking logs..." -ForegroundColor Yellow
        & $DockerCompose logs --tail=50
        exit 1
    }
    
    Write-Host "Attempt $attempt/$maxAttempts - waiting for health check..." -ForegroundColor Gray
} while ($attempt -lt $maxAttempts)

# Show final status
Show-Status

Write-Host ""
Write-Host "Recent logs:" -ForegroundColor Yellow
& $DockerCompose logs --tail=10

Write-Host ""
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "Use '.\deploy.ps1 -Logs' to view logs" -ForegroundColor Gray
Write-Host "Use '.\deploy.ps1 -Status' to check status" -ForegroundColor Gray
Write-Host "Use '.\deploy.ps1 -Stop' to stop the service" -ForegroundColor Gray
Write-Host "Use '.\deploy.ps1 -Clean' for clean deployment" -ForegroundColor Gray
