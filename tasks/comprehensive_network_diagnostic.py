#!/usr/bin/env python3
"""
Comprehensive Network Diagnostic Task
Performs complete network analysis for dual-adapter Pi systems with WireGuard.
Consolidates interface scanning, connectivity testing, and configuration analysis.

Hardware Requirements:
- Raspberry Pi 4 (recommended) with dual WiFi capability
- Built-in WiFi adapter (wlan0) - reserved for WireGuard tunnel
- External USB WiFi adapter (e.g., Netgear A7000, appears as wlx*) - for home network
- Minimum 1GB RAM for comprehensive diagnostics
- USB 3.0 ports recommended for external adapter performance

Package Requirements:
- Python 3.7+
- System utilities: ip, ping, nslookup, iptables, systemctl
- WireGuard tools: wg, wg-quick (wireguard-tools package)
- Docker tools: docker, docker-compose (if containerized services)
- Network utilities: ufw, netstat (optional but recommended)

System Dependencies:
- Linux kernel 5.6+ with WireGuard support OR WireGuard module
- iptables with NAT and filter table support
- systemd for service management
- /proc and /sys filesystems mounted
- sudo access for privileged network commands
"""
import json
import os
import time
import subprocess
import socket
import re
from pathlib import Path

def run_command(cmd, timeout=10, ignore_errors=False):
    """Run shell command with timeout and comprehensive error handling"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {
            'success': result.returncode == 0 or ignore_errors,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'returncode': result.returncode,
            'command': cmd
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Command timeout', 'stdout': '', 'stderr': '', 'command': cmd}
    except Exception as e:
        return {'success': False, 'error': str(e), 'stdout': '', 'stderr': '', 'command': cmd}

def detect_system_architecture():
    """Detect the system architecture and networking setup"""
    architecture = {
        'hostname': socket.gethostname(),
        'timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        'interfaces': {},
        'routing': {},
        'services': {},
        'configuration': {}
    }
    
    # Detect network interfaces and their roles
    interfaces_result = run_command("ip addr show")
    if interfaces_result['success']:
        current_interface = None
        for line in interfaces_result['stdout'].split('\n'):
            if_match = re.match(r'^(\d+):\s+([^:]+):\s+<([^>]+)>', line)
            if if_match:
                if_name = if_match.group(2).strip()
                flags = if_match.group(3).split(',')
                
                # Determine interface role based on Pi networking strategy
                role = 'unknown'
                purpose = 'Unknown interface'
                
                if if_name == 'wlan0':
                    role = 'builtin_wifi'
                    purpose = 'Built-in Pi WiFi - Reserved for WireGuard tunnel'
                elif if_name.startswith('wlx'):
                    role = 'external_wifi_adapter'
                    purpose = 'External USB WiFi adapter (Netgear A7000) - Home network connection'
                elif if_name.startswith('wg'):
                    role = 'wireguard_tunnel'
                    purpose = 'WireGuard VPN tunnel interface'
                elif if_name.startswith('eth') or if_name.startswith('end'):
                    role = 'ethernet'
                    purpose = 'Ethernet interface (typically unused on this Pi)'
                elif if_name.startswith('br-') or 'docker' in if_name:
                    role = 'docker_bridge'
                    purpose = 'Docker container bridge network'
                elif if_name == 'lo':
                    role = 'loopback'
                    purpose = 'System loopback interface'
                
                architecture['interfaces'][if_name] = {
                    'role': role,
                    'purpose': purpose,
                    'state': 'UP' if 'UP' in flags else 'DOWN',
                    'flags': flags,
                    'addresses': []
                }
                current_interface = if_name
            elif current_interface and 'inet' in line:
                addr_match = re.search(r'inet6?\s+([^\s]+)', line)
                if addr_match:
                    architecture['interfaces'][current_interface]['addresses'].append(addr_match.group(1))
    
    # Analyze routing configuration
    routes_result = run_command("ip route show")
    if routes_result['success']:
        architecture['routing']['ipv4'] = routes_result['stdout'].split('\n')
        
        # Identify key routes
        for route in architecture['routing']['ipv4']:
            if route.startswith('default'):
                if 'wlan0' in route:
                    architecture['routing']['default_via_builtin'] = route
                elif 'wlx' in route:
                    architecture['routing']['default_via_external'] = route
    
    # Check WireGuard status
    wg_result = run_command("wg show")
    architecture['services']['wireguard'] = {
        'active': wg_result['success'] and bool(wg_result['stdout']),
        'output': wg_result['stdout'] if wg_result['success'] else None
    }
    
    # Check Docker status
    docker_result = run_command("docker ps")
    architecture['services']['docker'] = {
        'active': docker_result['success'],
        'containers': len(docker_result['stdout'].split('\n')) - 1 if docker_result['success'] else 0
    }
    
    return architecture

def diagnose_connectivity_issues():
    """Comprehensive connectivity diagnostic"""
    connectivity = {
        'timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        'dns_tests': {},
        'ping_tests': {},
        'service_tests': {},
        'issues': [],
        'recommendations': []
    }
    
    # Test DNS resolution
    dns_servers = [
        ('system_default', ''),
        ('google_dns', '8.8.8.8'),
        ('cloudflare_dns', '1.1.1.1'),
        ('local_router', '192.168.0.1')
    ]
    
    for name, server in dns_servers:
        cmd = f"nslookup github.com {server}" if server else "nslookup github.com"
        result = run_command(cmd, timeout=5)
        
        connectivity['dns_tests'][name] = {
            'server': server or 'system default',
            'success': result['success'],
            'response': result['stdout']
        }
        
        # Check for DNS hijacking
        if result['success'] and '10.0.0.2' in result['stdout']:
            connectivity['issues'].append(f"DNS hijacking detected on {name} - github.com resolving to VPN peer IP")
            connectivity['recommendations'].append("Check /etc/hosts file and DNS configuration")
    
    # Test ping connectivity
    ping_targets = [
        ('local_gateway', '192.168.0.1'),
        ('google_dns', '8.8.8.8'),
        ('cloudflare_dns', '1.1.1.1'),
        ('github_ip', '140.82.114.3')
    ]
    
    for name, target in ping_targets:
        result = run_command(f"ping -c 2 -W 3 {target}", timeout=10)
        connectivity['ping_tests'][name] = {
            'target': target,
            'success': result['success'],
            'output': result['stdout'][:200] if result['success'] else result['stderr'][:200]
        }
    
    # Test service connectivity
    services = [
        ('github_https', 'github.com', 443),
        ('local_ssh', '192.168.0.1', 22),
        ('dns_service', '8.8.8.8', 53)
    ]
    
    for name, host, port in services:
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            connectivity['service_tests'][name] = {'success': True, 'host': host, 'port': port}
        except Exception as e:
            connectivity['service_tests'][name] = {'success': False, 'host': host, 'port': port, 'error': str(e)}
    
    return connectivity

def analyze_wireguard_configuration():
    """Analyze WireGuard setup and configuration"""
    wg_analysis = {
        'timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        'config_exists': False,
        'config_readable': False,
        'runtime_status': {},
        'analysis': {},
        'recommendations': []
    }
    
    config_path = '/etc/wireguard/wg0.conf'
    
    # Check if config file exists
    if os.path.exists(config_path):
        wg_analysis['config_exists'] = True
        
        try:
            with open(config_path, 'r') as f:
                content = f.read()
                wg_analysis['config_readable'] = True
                
                # Basic config analysis
                if '[Interface]' in content:
                    wg_analysis['analysis']['has_interface_section'] = True
                if '[Peer]' in content:
                    wg_analysis['analysis']['has_peer_section'] = True
                if 'AllowedIPs = 0.0.0.0/0' in content:
                    wg_analysis['analysis']['tunnel_type'] = 'full_tunnel'
                    wg_analysis['recommendations'].append("Consider split tunneling for better local network access")
                elif 'AllowedIPs' in content:
                    wg_analysis['analysis']['tunnel_type'] = 'split_tunnel'
                
        except PermissionError:
            wg_analysis['recommendations'].append("Cannot read WireGuard config - check permissions")
    else:
        wg_analysis['recommendations'].append("WireGuard configuration not found - create /etc/wireguard/wg0.conf")
    
    # Check runtime status
    wg_result = run_command("wg show")
    wg_analysis['runtime_status'] = {
        'active': wg_result['success'] and bool(wg_result['stdout']),
        'output': wg_result['stdout'] if wg_result['success'] else None
    }
    
    return wg_analysis

def check_docker_networking():
    """Check Docker networking setup and potential conflicts"""
    docker_net = {
        'timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        'docker_active': False,
        'networks': [],
        'iptables_status': {},
        'potential_conflicts': []
    }
    
    # Check if Docker is running
    docker_ps = run_command("docker ps")
    docker_net['docker_active'] = docker_ps['success']
    
    if docker_net['docker_active']:
        # List Docker networks
        networks_result = run_command("docker network ls")
        if networks_result['success']:
            for line in networks_result['stdout'].split('\n')[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        docker_net['networks'].append({
                            'id': parts[0],
                            'name': parts[1],
                            'driver': parts[2]
                        })
    
    # Check iptables Docker chains
    iptables_chains = ['DOCKER', 'DOCKER-USER', 'DOCKER-ISOLATION-STAGE-1']
    for chain in iptables_chains:
        result = run_command(f"iptables -L {chain} -n", ignore_errors=True)
        docker_net['iptables_status'][chain] = result['success']
    
    return docker_net

def generate_system_insights():
    """Generate insights about the current network configuration"""
    insights = {
        'timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        'system_health': 'unknown',
        'configuration_status': 'unknown',
        'key_findings': [],
        'action_items': [],
        'user_questions': []
    }
    
    # Load all diagnostic data
    architecture = detect_system_architecture()
    connectivity = diagnose_connectivity_issues()
    wireguard = analyze_wireguard_configuration()
    docker = check_docker_networking()
    
    # Analyze system health
    active_interfaces = len([i for i in architecture['interfaces'].values() if i['state'] == 'UP'])
    successful_pings = len([p for p in connectivity['ping_tests'].values() if p['success']])
    
    if successful_pings >= 3 and active_interfaces >= 2:
        insights['system_health'] = 'good'
    elif successful_pings >= 2:
        insights['system_health'] = 'fair'
    else:
        insights['system_health'] = 'poor'
    
    # Key findings
    if architecture['services']['wireguard']['active']:
        insights['key_findings'].append("WireGuard tunnel is active")
    else:
        insights['key_findings'].append("WireGuard tunnel is inactive")
        insights['action_items'].append("Consider activating WireGuard if VPN access needed")
    
    if docker['docker_active']:
        insights['key_findings'].append(f"Docker is running with {len(docker['networks'])} networks")
    
    # Configuration analysis
    external_adapters = [name for name, data in architecture['interfaces'].items() 
                        if data['role'] == 'external_wifi_adapter' and data['state'] == 'UP']
    builtin_wifi = [name for name, data in architecture['interfaces'].items() 
                   if data['role'] == 'builtin_wifi' and data['state'] == 'UP']
    
    if external_adapters and builtin_wifi:
        insights['configuration_status'] = 'dual_adapter_active'
        insights['key_findings'].append("Dual-adapter configuration detected and active")
    elif external_adapters:
        insights['configuration_status'] = 'external_only'
        insights['key_findings'].append("Only external WiFi adapter active")
    else:
        insights['configuration_status'] = 'limited'
        insights['action_items'].append("Check external WiFi adapter connection")
    
    # Generate user questions
    insights['user_questions'] = [
        "Is the external Netgear A7000 WiFi adapter properly connected?",
        "Should WireGuard be running for your current use case?",
        "Are you experiencing any specific network connectivity issues?",
        "Do you need help configuring split tunneling for WireGuard?",
        "Should the built-in WiFi be reserved exclusively for WireGuard?"
    ]
    
    return insights, architecture, connectivity, wireguard, docker

def main():
    """Main comprehensive diagnostic function"""
    print("Starting comprehensive network diagnostic...")
    
    # Run all diagnostics
    insights, architecture, connectivity, wireguard, docker = generate_system_insights()
    
    # Compile complete diagnostic report
    report = {
        'metadata': {
            'generated_at': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            'hostname': socket.gethostname(),
            'diagnostic_version': '1.0'
        },
        'system_insights': insights,
        'architecture': architecture,
        'connectivity': connectivity,
        'wireguard': wireguard,
        'docker_networking': docker
    }
    
    # Save comprehensive report
    os.makedirs('/app/agent_memory', exist_ok=True)
    with open('/app/agent_memory/comprehensive_network_diagnostic.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print executive summary
    print(f"\n=== COMPREHENSIVE NETWORK DIAGNOSTIC COMPLETE ===")
    print(f"System Health: {insights['system_health'].upper()}")
    print(f"Configuration: {insights['configuration_status']}")
    print(f"Active Interfaces: {len([i for i in architecture['interfaces'].values() if i['state'] == 'UP'])}")
    print(f"WireGuard Status: {'ACTIVE' if architecture['services']['wireguard']['active'] else 'INACTIVE'}")
    print(f"Docker Status: {'ACTIVE' if docker['docker_active'] else 'INACTIVE'}")
    
    if insights['key_findings']:
        print(f"\nKey Findings:")
        for finding in insights['key_findings'][:3]:
            print(f"  • {finding}")
    
    if insights['action_items']:
        print(f"\nRecommended Actions:")
        for action in insights['action_items'][:3]:
            print(f"  • {action}")
    
    print(f"\nFull report saved to: /app/agent_memory/comprehensive_network_diagnostic.json")

if __name__ == "__main__":
    main()
