# Environment Variables Reference

This document lists all the environment variables you can set to configure your diagnostic agent without editing code files.

## Connection Configuration

### Dev Machine (SSH Target)
```bash
export DEV_MACHINE_MAC="AA:BB:CC:DD:EE:FF"    # MAC address for Wake-on-LAN
export DEV_MACHINE_IP="192.168.1.100"         # IP address of dev machine
export DEV_MACHINE_PORT="2222"                # SSH port (default: 2222)
export DEV_MACHINE_USER="your_username"       # SSH username for dev machine
```

### Pi Configuration
```bash
export SSH_HOST="your-pi-hostname.local"      # Pi hostname or IP
export PI_USER="your_pi_username"             # Pi username
export PI_HOST="your-pi-hostname.local"       # Pi hostname (for deployment scripts)
export PI_CONFIG_URL="http://your-pi:5000/config/pi_snapshot"  # Pi config endpoint
```

### SSH Settings
```bash
export SSH_TIMEOUT="5"                        # SSH connection timeout in seconds
export SSH_MAX_RETRIES="10"                   # Maximum SSH retry attempts
export SSH_RETRY_DELAY="15"                   # Delay between SSH retries
export BRIDGE_CHECK_INTERVAL="300"            # Bridge status check interval
```

## Usage Examples

### PowerShell (Windows)
```powershell
$env:DEV_MACHINE_MAC = "AA:BB:CC:DD:EE:FF"
$env:DEV_MACHINE_IP = "192.168.1.100"
$env:PI_USER = "pi"
$env:PI_HOST = "raspberrypi.local"

# Then run deployment
.\cross_compile_fast.ps1
```

### Bash (Linux/macOS)
```bash
export DEV_MACHINE_MAC="AA:BB:CC:DD:EE:FF"
export DEV_MACHINE_IP="192.168.1.100"
export PI_USER="pi"
export PI_HOST="raspberrypi.local"

# Then run deployment
./deploy_agent.sh
```

### .env File (Alternative)
Create a `.env` file in the project root:
```ini
DEV_MACHINE_MAC=AA:BB:CC:DD:EE:FF
DEV_MACHINE_IP=192.168.1.100
DEV_MACHINE_USER=your_username
SSH_HOST=your-pi-hostname.local
PI_USER=your_pi_username
PI_HOST=your-pi-hostname.local
```

## Files That Use These Variables

### Python Files
- `bridge_status_monitor.py` - Bridge monitoring and Wake-on-LAN
- `tasks/bridge_checker.py` - Bridge connectivity checks
- `tasks/check_connectivity.py` - SSH connectivity tests
- `dev_machine_agent_optimized.py` - Pi configuration fetching

### Deployment Scripts
- `cross_compile_fast.ps1` - Fast cross-compilation deployment
- `cross_compile_and_deploy.ps1` - Full cross-compilation deployment
- `deploy_to_pi.ps1` - Pi deployment script
- `deploy_agent.sh` - Bash deployment script

## Security Notes

1. **Never commit these values to git** - They contain sensitive network information
2. **Use .env files** for local development (`.env` is gitignored)
3. **Set in CI/CD** for automated deployments
4. **Environment variables override** config file values
