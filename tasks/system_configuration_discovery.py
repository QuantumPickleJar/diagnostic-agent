#!/usr/bin/env python3
"""
System Configuration Discovery Task
Documents the current system configuration for the agent's understanding.
Creates a knowledge base about hardware, networking, and service setup.

Hardware Requirements:
- Any system capable of running the diagnostic agent
- Access to system information in /proc and /sys
- Minimum 256MB RAM for configuration discovery

Package Requirements:
- Python 3.7+
- Standard system utilities: ps, systemctl, ip, lsusb (optional)
- Access to configuration files in /etc

System Dependencies:
- /proc filesystem for system information
- systemd for service management information
- Read access to network configuration files
"""
import json
import os
import time
import subprocess
import socket
import re
import glob
from pathlib import Path

def run_command(cmd, timeout=10):
    """Run system command safely"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip()
        }
    except:
        return {'success': False, 'stdout': '', 'stderr': ''}

def discover_hardware_configuration():
    """Discover and document hardware configuration"""
    hardware = {
        'timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        'system_type': 'unknown',
        'network_adapters': {},
        'specifications': {}
    }
    
    # Detect system type
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'Raspberry Pi' in cpuinfo:
                hardware['system_type'] = 'raspberry_pi'
                if 'Pi 4' in cpuinfo:
                    hardware['specifications']['model'] = 'Raspberry Pi 4'
                    hardware['specifications']['architecture'] = 'ARM64'
            elif 'ARM' in cpuinfo:
                hardware['system_type'] = 'arm_system'
            else:
                hardware['system_type'] = 'x86_system'
    except:
        pass
    
    # Memory information
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    kb = int(line.split()[1])
                    hardware['specifications']['total_memory_mb'] = kb // 1024
                    break
    except:
        pass
    
    # Network adapter discovery
    net_result = run_command("ip link show")
    if net_result['success']:
        for line in net_result['stdout'].split('\n'):
            if_match = re.match(r'^\d+:\s+([^:]+):', line)
            if if_match:
                if_name = if_match.group(1)
                adapter_info = {'interface': if_name, 'type': 'unknown', 'purpose': 'unknown'}
                
                # Classify adapter based on Pi networking strategy
                if if_name == 'wlan0':
                    adapter_info.update({
                        'type': 'builtin_wifi',
                        'purpose': 'dedicated_wireguard_tunnel',
                        'description': 'Built-in Pi WiFi reserved for WireGuard VPN tunnel'
                    })
                elif if_name.startswith('wlx'):
                    adapter_info.update({
                        'type': 'external_usb_wifi',
                        'purpose': 'home_network_connection',
                        'description': 'External USB WiFi adapter (e.g., Netgear A7000) for home network'
                    })
                elif if_name.startswith('wg'):
                    adapter_info.update({
                        'type': 'wireguard_interface',
                        'purpose': 'vpn_tunnel',
                        'description': 'WireGuard VPN tunnel interface'
                    })
                elif if_name.startswith('eth') or if_name.startswith('end'):
                    adapter_info.update({
                        'type': 'ethernet',
                        'purpose': 'wired_connection',
                        'description': 'Ethernet interface (typically unused on this Pi setup)'
                    })
                elif if_name.startswith('br-') or 'docker' in if_name:
                    adapter_info.update({
                        'type': 'docker_bridge',
                        'purpose': 'container_networking',
                        'description': 'Docker container bridge network'
                    })
                
                hardware['network_adapters'][if_name] = adapter_info
    
    return hardware

def discover_network_configuration():
    """Document current network configuration strategy"""
    network_config = {
        'timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        'strategy': 'unknown',
        'dns_configuration': {},
        'routing_strategy': {},
        'firewall_status': {}
    }
    
    # Determine networking strategy
    interfaces = run_command("ip addr show")
    if interfaces['success']:
        has_external_wifi = 'wlx' in interfaces['stdout']
        has_builtin_wifi = 'wlan0' in interfaces['stdout']
        has_wireguard = 'wg0' in interfaces['stdout']
        
        if has_external_wifi and has_builtin_wifi:
            network_config['strategy'] = 'dual_adapter_separation'
            network_config['description'] = 'Dual WiFi adapter setup: built-in for WireGuard, external for home network'
        elif has_external_wifi:
            network_config['strategy'] = 'external_adapter_primary'
        elif has_builtin_wifi:
            network_config['strategy'] = 'builtin_adapter_only'
    
    # DNS configuration
    try:
        with open('/etc/resolv.conf', 'r') as f:
            resolv_content = f.read()
            dns_servers = []
            for line in resolv_content.split('\n'):
                if line.startswith('nameserver'):
                    dns_servers.append(line.split()[1])
            network_config['dns_configuration']['servers'] = dns_servers
    except:
        pass
    
    # Routing analysis
    routes = run_command("ip route show default")
    if routes['success']:
        default_routes = routes['stdout'].split('\n')
        network_config['routing_strategy']['default_routes'] = default_routes
        
        # Analyze which interfaces handle default routing
        for route in default_routes:
            if 'wlan0' in route:
                network_config['routing_strategy']['builtin_wifi_default'] = True
            if 'wlx' in route:
                network_config['routing_strategy']['external_wifi_default'] = True
    
    # Firewall status
    ufw_status = run_command("ufw status")
    if ufw_status['success']:
        network_config['firewall_status']['ufw_active'] = 'Status: active' in ufw_status['stdout']
    
    return network_config

def discover_service_configuration():
    """Document running services and their configurations"""
    services = {
        'timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        'critical_services': {},
        'docker_services': {},
        'network_services': {}
    }
    
    # WireGuard service
    wg_status = run_command("systemctl is-active wg-quick@wg0")
    services['network_services']['wireguard'] = {
        'active': wg_status['success'] and wg_status['stdout'] == 'active',
        'purpose': 'VPN tunnel management'
    }
    
    # Docker service
    docker_status = run_command("systemctl is-active docker")
    services['critical_services']['docker'] = {
        'active': docker_status['success'] and docker_status['stdout'] == 'active',
        'purpose': 'Container orchestration for diagnostic agent'
    }
    
    # NetworkManager
    nm_status = run_command("systemctl is-active NetworkManager")
    services['network_services']['network_manager'] = {
        'active': nm_status['success'] and nm_status['stdout'] == 'active',
        'purpose': 'Network connection management'
    }
    
    # SSH service
    ssh_status = run_command("systemctl is-active ssh")
    services['critical_services']['ssh'] = {
        'active': ssh_status['success'] and ssh_status['stdout'] == 'active',
        'purpose': 'Remote access and management'
    }
    
    # Docker containers (if Docker is running)
    if services['critical_services']['docker']['active']:
        containers = run_command("docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'")
        if containers['success']:
            container_lines = containers['stdout'].split('\n')[1:]  # Skip header
            for line in container_lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        services['docker_services'][parts[0]] = {
                            'image': parts[1],
                            'status': parts[2],
                            'purpose': 'diagnostic-agent' if 'diagnostic' in parts[0] else 'container_service'
                        }
    
    return services

def generate_configuration_facts():
    """Generate key facts about the system configuration"""
    facts = {
        'timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        'system_identity': {
            'hostname': socket.gethostname(),
            'role': 'diagnostic_agent_host',
            'location': 'raspberry_pi_4'
        },
        'networking_facts': {},
        'service_facts': {},
        'configuration_recommendations': []
    }
    
    # Gather all configuration data
    hardware = discover_hardware_configuration()
    network = discover_network_configuration()
    services = discover_service_configuration()
    
    # Extract key networking facts
    active_adapters = [name for name, data in hardware['network_adapters'].items() 
                      if data['type'] in ['builtin_wifi', 'external_usb_wifi']]
    
    facts['networking_facts'] = {
        'dual_adapter_setup': len(active_adapters) >= 2,
        'adapter_separation_strategy': network['strategy'] == 'dual_adapter_separation',
        'external_adapter_present': any(name.startswith('wlx') for name in hardware['network_adapters']),
        'wireguard_capable': 'wlan0' in hardware['network_adapters'],
        'dns_servers': network['dns_configuration'].get('servers', [])
    }
    
    # Service facts
    facts['service_facts'] = {
        'docker_operational': services['critical_services']['docker']['active'],
        'wireguard_available': services['network_services']['wireguard']['active'],
        'remote_access_enabled': services['critical_services']['ssh']['active'],
        'agent_containers': len(services['docker_services'])
    }
    
    # Generate recommendations
    if not facts['networking_facts']['dual_adapter_setup']:
        facts['configuration_recommendations'].append(
            "Consider connecting external USB WiFi adapter for optimal dual-adapter setup"
        )
    
    if not facts['service_facts']['docker_operational']:
        facts['configuration_recommendations'].append(
            "Docker service required for diagnostic agent operation"
        )
    
    return facts, hardware, network, services

def main():
    """Main configuration discovery function"""
    print("Discovering system configuration...")
    
    # Run all discovery tasks
    facts, hardware, network, services = generate_configuration_facts()
    
    # Create comprehensive configuration document
    configuration_document = {
        'metadata': {
            'generated_at': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            'hostname': socket.gethostname(),
            'document_purpose': 'Agent system configuration knowledge base'
        },
        'system_facts': facts,
        'hardware_configuration': hardware,
        'network_configuration': network,
        'service_configuration': services
    }
    
    # Save configuration document
    os.makedirs('/app/agent_memory', exist_ok=True)
    with open('/app/agent_memory/system_configuration.json', 'w') as f:
        json.dump(configuration_document, f, indent=2)
    
    # Print summary
    print(f"\n=== SYSTEM CONFIGURATION DISCOVERY COMPLETE ===")
    print(f"System Type: {hardware['system_type']}")
    print(f"Networking Strategy: {network['strategy']}")
    print(f"Active Network Adapters: {len([a for a in hardware['network_adapters'].values() if a['type'] != 'unknown'])}")
    print(f"Docker Status: {'OPERATIONAL' if facts['service_facts']['docker_operational'] else 'INACTIVE'}")
    print(f"WireGuard Available: {'YES' if facts['service_facts']['wireguard_available'] else 'NO'}")
    
    if facts['configuration_recommendations']:
        print(f"\nConfiguration Recommendations:")
        for rec in facts['configuration_recommendations']:
            print(f"  • {rec}")
    
    print(f"\nConfiguration document saved to: /app/agent_memory/system_configuration.json")

if __name__ == "__main__":
    main()
