# Docker Build & Deploy Guide

## Quick Reference

### 🏃‍♂️ Fast Development (5-8 minutes)
```powershell
# Build and deploy fast variant
docker-compose -f docker-compose.fast.yml up --build -d
```

### 🏭 Production Build (15-20 minutes)
```powershell
# Build and deploy production variant
docker-compose -f docker-compose.yml up --build -d
```

### ⚡ Cross-Compilation (2-3 minutes on Pi!)
```powershell
# First time setup (run once)
.\setup_cross_compile.ps1

# Build on dev machine, deploy to Pi (fast!)
.\cross_compile_and_deploy.ps1

# Production cross-compile
.\cross_compile_and_deploy.ps1 -UseProduction
```

## File Structure

- **Dockerfile.fast** - Fast development builds with pre-built wheels
- **Dockerfile.production** - Full production builds with optimizations
- **docker-compose.fast.yml** - Fast development compose
- **docker-compose.yml** - Production compose
- **requirements.fast.txt** - Minimal requirements with ARM wheels

## Build Time Comparison

| Method | Dev Machine | Raspberry Pi 4 |
|--------|-------------|----------------|
| **Fast build** | N/A | 5-8 min |
| **Production** | N/A | 15-20 min |
| **Cross-compile** | 8-12 min | 2-3 min (deploy) |

## Cross-Compilation Requirements

### Dev Machine Setup:
1. **Docker Desktop** with buildx support
2. **Stable internet** (for downloading base images)
3. **PowerShell 5.1+** (Windows built-in)
4. **SSH access** to Pi

### Network Requirements:
- **Outbound HTTPS** (443) - Docker registry access
- **SSH** (port 2222) - Pi access
- **No static IP required** - uses Pi's dynamic DNS

## Troubleshooting

### "Could not find a version that satisfies the requirement packaging"
```powershell
# Use fast variant instead
docker-compose -f docker-compose.fast.yml up --build
```

### Cross-compilation fails
```powershell
# Recreate builder
docker buildx rm diagnostic-builder
.\setup_cross_compile.ps1 -SetupOnly
```

### Pi deployment fails
```powershell
# Check Pi connectivity
ssh -p 2222 your_pi_user@your_pi_host 'docker --version'
```
