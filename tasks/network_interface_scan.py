#!/usr/bin/env python3
"""
Network Interface Scanner
Collects detailed information about all network interfaces, routing, and connectivity.
Designed to understand dual-adapter setups (Pi antenna for WireGuard, external adapter for home network).

Hardware Requirements:
- Raspberry Pi 4 or compatible ARM64/x86_64 system
- Multiple network interfaces (built-in + external adapters)
- USB ports for external WiFi adapters
- Minimum 512MB RAM for interface scanning

Package Requirements:
- Python 3.7+
- iproute2 package (ip command)
- iputils-ping for connectivity testing
- net-tools (optional, for legacy ifconfig)
- WireGuard tools if VPN analysis needed

System Dependencies:
- Linux kernel with network namespace support
- sysfs mounted at /sys
- procfs mounted at /proc
- Network interface drivers loaded
"""
import json
import os
import time
import subprocess
import socket
import re

def run_command(cmd, timeout=10):
    """Run shell command with timeout and error handling"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Command timeout', 'stdout': '', 'stderr': ''}
    except Exception as e:
        return {'success': False, 'error': str(e), 'stdout': '', 'stderr': ''}

def get_network_interfaces():
    """Get detailed network interface information"""
    interfaces = {}
    
    # Get interface details with ip command
    cmd_result = run_command("ip addr show")
    if cmd_result['success']:
        current_interface = None
        for line in cmd_result['stdout'].split('\n'):
            # Parse interface header (e.g., "3: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP>")
            if_match = re.match(r'^(\d+):\s+([^:]+):\s+<([^>]+)>', line)
            if if_match:
                if_name = if_match.group(2).strip()
                flags = if_match.group(3).split(',')
                interfaces[if_name] = {
                    'name': if_name,
                    'index': int(if_match.group(1)),
                    'flags': flags,
                    'state': 'UP' if 'UP' in flags else 'DOWN',
                    'addresses': []
                }
                current_interface = if_name
            # Parse IP addresses
            elif current_interface and 'inet' in line:
                addr_match = re.search(r'inet6?\s+([^\s]+)', line)
                if addr_match:
                    interfaces[current_interface]['addresses'].append(addr_match.group(1))
    
    # Get additional interface statistics
    cmd_result = run_command("ip -s link show")
    if cmd_result['success']:
        # Parse interface statistics if needed
        pass
    
    return interfaces

def get_routing_table():
    """Get routing table information"""
    routes = {'ipv4': [], 'ipv6': []}
    
    # IPv4 routes
    cmd_result = run_command("ip route show")
    if cmd_result['success']:
        for line in cmd_result['stdout'].split('\n'):
            if line.strip():
                routes['ipv4'].append(line.strip())
    
    # IPv6 routes
    cmd_result = run_command("ip -6 route show")
    if cmd_result['success']:
        for line in cmd_result['stdout'].split('\n'):
            if line.strip():
                routes['ipv6'].append(line.strip())
    
    return routes

def get_wireguard_status():
    """Get WireGuard tunnel information"""
    wg_status = {'active': False, 'interfaces': []}
    
    cmd_result = run_command("wg show")
    if cmd_result['success'] and cmd_result['stdout']:
        wg_status['active'] = True
        current_interface = None
        interface_data = {}
        
        for line in cmd_result['stdout'].split('\n'):
            if line.startswith('interface:'):
                if current_interface and interface_data:
                    wg_status['interfaces'].append(interface_data)
                current_interface = line.split(':', 1)[1].strip()
                interface_data = {'name': current_interface, 'peers': []}
            elif line.startswith('peer:'):
                peer_key = line.split(':', 1)[1].strip()
                interface_data['peers'].append({'public_key': peer_key})
            elif line.strip().startswith('allowed ips:'):
                if interface_data['peers']:
                    interface_data['peers'][-1]['allowed_ips'] = line.split(':', 1)[1].strip()
        
        if current_interface and interface_data:
            wg_status['interfaces'].append(interface_data)
    
    return wg_status

def get_dns_configuration():
    """Get DNS configuration"""
    dns_config = {'resolv_conf': [], 'systemd_resolved': False}
    
    # Read /etc/resolv.conf
    try:
        with open('/etc/resolv.conf', 'r') as f:
            dns_config['resolv_conf'] = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        pass
    
    # Check systemd-resolved status
    cmd_result = run_command("systemctl is-active systemd-resolved")
    dns_config['systemd_resolved'] = cmd_result['success'] and cmd_result['stdout'] == 'active'
    
    return dns_config

def test_connectivity():
    """Test basic connectivity to various endpoints"""
    test_targets = [
        {'name': 'Local Gateway', 'host': '192.168.0.1', 'port': None},
        {'name': 'Google DNS', 'host': '8.8.8.8', 'port': 53},
        {'name': 'Cloudflare DNS', 'host': '1.1.1.1', 'port': 53},
        {'name': 'GitHub', 'host': 'github.com', 'port': 443},
    ]
    
    connectivity = []
    for target in test_targets:
        result = {'name': target['name'], 'host': target['host']}
        
        if target['port']:
            # Test TCP connectivity
            try:
                sock = socket.create_connection((target['host'], target['port']), timeout=5)
                sock.close()
                result['tcp_reachable'] = True
            except Exception:
                result['tcp_reachable'] = False
        
        # Test ping
        ping_result = run_command(f"ping -c 2 -W 3 {target['host']}")
        result['ping_reachable'] = ping_result['success']
        
        connectivity.append(result)
    
    return connectivity

def analyze_interface_roles():
    """Analyze which interfaces are used for what purposes"""
    interfaces = get_network_interfaces()
    analysis = {}
    
    for if_name, if_data in interfaces.items():
        role = 'unknown'
        details = {}
        
        if if_name.startswith('wlan'):
            if 'wlx' in if_name:
                role = 'external_wifi_adapter'
                details['description'] = 'External WiFi adapter (likely Netgear A7000)'
            else:
                role = 'builtin_wifi'
                details['description'] = 'Built-in Pi WiFi (likely used for WireGuard)'
        elif if_name.startswith('wg'):
            role = 'wireguard_tunnel'
            details['description'] = 'WireGuard VPN tunnel interface'
        elif if_name.startswith('eth') or if_name.startswith('end'):
            role = 'ethernet'
            details['description'] = 'Ethernet interface'
        elif if_name.startswith('br-') or 'docker' in if_name:
            role = 'docker_bridge'
            details['description'] = 'Docker bridge network'
        elif if_name == 'lo':
            role = 'loopback'
            details['description'] = 'Loopback interface'
        
        analysis[if_name] = {
            'role': role,
            'state': if_data['state'],
            'addresses': if_data['addresses'],
            **details
        }
    
    return analysis

def main():
    """Main function to collect all network diagnostic information"""
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Collect all network information
    network_data = {
        'timestamp': timestamp,
        'hostname': socket.gethostname(),
        'interfaces': get_network_interfaces(),
        'interface_analysis': analyze_interface_roles(),
        'routing': get_routing_table(),
        'wireguard': get_wireguard_status(),
        'dns': get_dns_configuration(),
        'connectivity': test_connectivity(),
    }
    
    # Save to agent memory
    os.makedirs('/app/agent_memory', exist_ok=True)
    with open('/app/agent_memory/network_scan.json', 'w') as f:
        json.dump(network_data, f, indent=2)
    
    # Print summary for agent logs
    print(f"Network scan completed at {timestamp}")
    print(f"Active interfaces: {len([i for i in network_data['interfaces'].values() if i['state'] == 'UP'])}")
    print(f"WireGuard active: {network_data['wireguard']['active']}")
    print(f"Connectivity tests passed: {len([t for t in network_data['connectivity'] if t.get('ping_reachable', False)])}/{len(network_data['connectivity'])}")

if __name__ == "__main__":
    main()
