# Configuration Setup

This guide helps you set up your connection configuration securely.

## Initial Setup

1. **Copy the example configuration:**
   ```bash
   cp routing_config_example.json agent_memory/routing_config.json
   ```

2. **Edit the configuration with your actual values:**
   ```bash
   nano agent_memory/routing_config.json
   ```

   Update these values:
   - `dev_machine_mac`: Your dev machine's MAC address (for Wake-on-LAN)
   - `dev_machine_ip`: Your dev machine's IP address
   - `dev_machine_user`: SSH username for your dev machine
   - `pi_user`: Username on the Raspberry Pi

## Environment Variables (Alternative)

You can also set these values using environment variables instead of the config file:

```bash
export DEV_MACHINE_MAC="AA:BB:CC:DD:EE:FF"
export DEV_MACHINE_IP="192.168.1.100"
export DEV_MACHINE_USER="your_username"
export SSH_HOST="your-pi-hostname.local"
export PI_CONFIG_URL="http://your-pi-hostname.local:5000/config/pi_snapshot"
```

## Security Notes

- The `routing_config.json` file is automatically ignored by git
- Never commit actual MAC addresses or IP addresses to the repository
- Use environment variables in production deployments
- The example file provides safe placeholder values

## File Locations

- **Example config:** `routing_config_example.json` (committed to git)
- **Actual config:** `agent_memory/routing_config.json` (ignored by git)
- **Application usage:** The app automatically loads from `agent_memory/routing_config.json`

## Deployment Scripts

The following deployment scripts contain connection information and are ignored by git:
- `deploy_to_pi.ps1`
- `deploy_agent.sh` 
- `deploy_fixed.ps1`
- `cross_compile_and_deploy.ps1`
- `cross_compile_fast.ps1`

Example templates are provided:
- `deploy_to_pi_example.ps1` - Template for PowerShell deployment

To set up deployment:
1. Copy the example script: `cp deploy_to_pi_example.ps1 deploy_to_pi.ps1`
2. Configure your connection settings in the copied script
3. Implement the deployment logic for your environment
