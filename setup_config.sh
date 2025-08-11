#!/bin/bash
#
# Setup script for configuring connection information
# Run this script to set up your diagnostic agent configuration
#

set -e

echo "🔧 Diagnostic Agent Configuration Setup"
echo "======================================="
echo ""

# Check if routing config already exists
if [ -f "agent_memory/routing_config.json" ]; then
    echo "⚠️  Configuration file already exists at agent_memory/routing_config.json"
    read -p "Do you want to overwrite it? (y/N): " overwrite
    if [ "$overwrite" != "y" ] && [ "$overwrite" != "Y" ]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Create agent_memory directory
mkdir -p agent_memory

# Copy example configuration
echo "📋 Copying example configuration..."
cp routing_config_example.json agent_memory/routing_config.json

echo "✅ Configuration file created at agent_memory/routing_config.json"
echo ""
echo "📝 Next steps:"
echo "1. Edit agent_memory/routing_config.json with your actual values:"
echo "   - dev_machine_mac: Your dev machine's MAC address"
echo "   - dev_machine_ip: Your dev machine's IP address"
echo "   - dev_machine_user: SSH username for your dev machine"
echo "   - pi_user: Username on the Raspberry Pi"
echo ""
echo "2. Set up deployment scripts (optional):"
echo "   cp deploy_to_pi_example.ps1 deploy_to_pi.ps1"
echo "   cp deploy_agent_example.sh deploy_agent.sh"
echo ""
echo "3. Configure environment variables (alternative to config file):"
echo "   export DEV_MACHINE_MAC='AA:BB:CC:DD:EE:FF'"
echo "   export DEV_MACHINE_IP='192.168.1.100'"
echo "   export SSH_HOST='your-pi-hostname.local'"
echo ""
echo "📖 For more details, see CONFIG_SETUP.md"
