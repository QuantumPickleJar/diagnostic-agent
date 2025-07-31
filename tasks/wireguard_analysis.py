#!/usr/bin/env python3
"""
WireGuard Configuration Analyzer
Analyzes WireGuard configuration and provides insights about tunnel setup.

Hardware Requirements:
- Raspberry Pi 4 or compatible system with WiFi capability
- Built-in WiFi adapter dedicated to WireGuard tunnel
- External network adapter for local connectivity
- Minimum 512MB RAM for configuration parsing

Package Requirements:
- Python 3.7+
- WireGuard tools: wireguard-tools package
- System utilities: systemctl, ip
- File access to /etc/wireguard/ directory

System Dependencies:
- Linux kernel 5.6+ with WireGuard built-in OR
- WireGuard kernel module for older kernels
- iptables for firewall rule analysis
- systemd for service management
- sudo access for WireGuard commands
"""
import json
import os
import time
import subprocess
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

def parse_wireguard_config(config_path="/etc/wireguard/wg0.conf"):
    """Parse WireGuard configuration file"""
    config = {
        'interface': {},
        'peers': [],
        'file_exists': False,
        'readable': False
    }
    
    try:
        if os.path.exists(config_path):
            config['file_exists'] = True
            
            with open(config_path, 'r') as f:
                content = f.read()
                config['readable'] = True
                
                current_section = None
                current_peer = {}
                
                for line in content.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith('[') and line.endswith(']'):
                        if current_section == 'Peer' and current_peer:
                            config['peers'].append(current_peer)
                            current_peer = {}
                        current_section = line[1:-1]
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if current_section == 'Interface':
                            config['interface'][key] = value
                        elif current_section == 'Peer':
                            current_peer[key] = value
                
                # Don't forget the last peer
                if current_section == 'Peer' and current_peer:
                    config['peers'].append(current_peer)
    
    except PermissionError:
        config['error'] = 'Permission denied reading config file'
    except Exception as e:
        config['error'] = str(e)
    
    return config

def analyze_wireguard_config(config):
    """Analyze WireGuard configuration for common issues and insights"""
    analysis = {
        'tunnel_type': 'unknown',
        'routing_mode': 'unknown',
        'security_assessment': 'unknown',
        'recommendations': [],
        'warnings': [],
        'insights': []
    }
    
    if not config['file_exists']:
        analysis['warnings'].append("WireGuard configuration file not found")
        analysis['recommendations'].append("Create WireGuard configuration: sudo nano /etc/wireguard/wg0.conf")
        return analysis
    
    if not config['readable']:
        analysis['warnings'].append("Cannot read WireGuard configuration (permission denied)")
        analysis['recommendations'].append("Check file permissions: sudo chmod 600 /etc/wireguard/wg0.conf")
        return analysis
    
    interface = config['interface']
    peers = config['peers']
    
    # Analyze tunnel type based on allowed IPs
    if peers:
        allowed_ips = []
        for peer in peers:
            if 'AllowedIPs' in peer:
                allowed_ips.extend(peer['AllowedIPs'].split(','))
        
        allowed_ips = [ip.strip() for ip in allowed_ips]
        
        if '0.0.0.0/0' in allowed_ips or '::/0' in allowed_ips:
            analysis['tunnel_type'] = 'full_tunnel'
            analysis['routing_mode'] = 'all_traffic_through_vpn'
            analysis['insights'].append("Full tunnel configuration - all traffic routed through VPN")
        else:
            analysis['tunnel_type'] = 'split_tunnel'
            analysis['routing_mode'] = 'selective_routing'
            analysis['insights'].append(f"Split tunnel configuration - only specific networks routed: {', '.join(allowed_ips)}")
    
    # Security assessment
    if 'PrivateKey' in interface:
        analysis['security_assessment'] = 'configured'
        analysis['insights'].append("Private key configured (good)")
    else:
        analysis['warnings'].append("No private key found in interface configuration")
    
    if peers:
        for i, peer in enumerate(peers):
            if 'PublicKey' in peer:
                analysis['insights'].append(f"Peer {i+1}: Public key configured")
            if 'Endpoint' in peer:
                analysis['insights'].append(f"Peer {i+1}: Endpoint {peer['Endpoint']}")
            else:
                analysis['warnings'].append(f"Peer {i+1}: No endpoint configured (server mode?)")
    
    # Port analysis
    if 'ListenPort' in interface:
        port = interface['ListenPort']
        analysis['insights'].append(f"Listening on port {port}")
        if port == '51820':
            analysis['insights'].append("Using standard WireGuard port")
        else:
            analysis['insights'].append("Using non-standard port (good for security)")
    
    # Address analysis
    if 'Address' in interface:
        address = interface['Address']
        analysis['insights'].append(f"Interface address: {address}")
        
        # Determine network role
        if address.startswith('10.0.0.'):
            analysis['insights'].append("Using 10.0.0.x network (common for VPN)")
        elif address.startswith('192.168.'):
            analysis['insights'].append("Using 192.168.x.x network (typical home network range)")
    
    # PostUp/PostDown analysis
    if 'PostUp' in interface:
        analysis['insights'].append("PostUp commands configured")
        if 'iptables' in interface['PostUp']:
            analysis['insights'].append("iptables rules configured in PostUp")
    
    if 'PostDown' in interface:
        analysis['insights'].append("PostDown commands configured")
    
    # Recommendations based on Pi dual-adapter setup
    if analysis['tunnel_type'] == 'full_tunnel':
        analysis['recommendations'].append("Consider split tunneling to maintain local network access")
        analysis['recommendations'].append("Ensure home network traffic can still use external adapter")
    
    if len(peers) == 0:
        analysis['warnings'].append("No peers configured")
        analysis['recommendations'].append("Add peer configuration for VPN connection")
    elif len(peers) > 1:
        analysis['insights'].append(f"Multiple peers configured ({len(peers)})")
    
    return analysis

def get_wireguard_runtime_status():
    """Get current WireGuard runtime status"""
    status = {
        'running': False,
        'interfaces': [],
        'stats': {}
    }
    
    # Check if WireGuard is running
    wg_result = run_command("wg show")
    if wg_result['success'] and wg_result['stdout']:
        status['running'] = True
        
        # Parse interface stats
        current_interface = None
        for line in wg_result['stdout'].split('\n'):
            if line.startswith('interface:'):
                current_interface = line.split(':', 1)[1].strip()
                status['interfaces'].append(current_interface)
                status['stats'][current_interface] = {'peers': []}
            elif line.startswith('peer:'):
                peer_key = line.split(':', 1)[1].strip()
                if current_interface:
                    status['stats'][current_interface]['peers'].append({
                        'public_key': peer_key[:16] + '...',  # Truncate for security
                        'allowed_ips': None,
                        'latest_handshake': None,
                        'transfer': None
                    })
            elif line.strip().startswith('allowed ips:') and current_interface:
                allowed_ips = line.split(':', 1)[1].strip()
                if status['stats'][current_interface]['peers']:
                    status['stats'][current_interface]['peers'][-1]['allowed_ips'] = allowed_ips
            elif line.strip().startswith('latest handshake:') and current_interface:
                handshake = line.split(':', 1)[1].strip()
                if status['stats'][current_interface]['peers']:
                    status['stats'][current_interface]['peers'][-1]['latest_handshake'] = handshake
            elif line.strip().startswith('transfer:') and current_interface:
                transfer = line.split(':', 1)[1].strip()
                if status['stats'][current_interface]['peers']:
                    status['stats'][current_interface]['peers'][-1]['transfer'] = transfer
    
    return status

def main():
    """Main function to analyze WireGuard configuration"""
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Parse and analyze configuration
    config = parse_wireguard_config()
    analysis = analyze_wireguard_config(config)
    runtime_status = get_wireguard_runtime_status()
    
    # Compile results
    results = {
        'timestamp': timestamp,
        'config_file': config,
        'analysis': analysis,
        'runtime_status': runtime_status,
        'recommendations_summary': analysis['recommendations'],
        'warnings_summary': analysis['warnings']
    }
    
    # Save results
    os.makedirs('/app/agent_memory', exist_ok=True)
    with open('/app/agent_memory/wireguard_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print(f"WireGuard analysis completed at {timestamp}")
    print(f"Configuration file exists: {config['file_exists']}")
    print(f"Runtime status: {'RUNNING' if runtime_status['running'] else 'STOPPED'}")
    print(f"Tunnel type: {analysis['tunnel_type']}")
    print(f"Warnings: {len(analysis['warnings'])}")
    print(f"Recommendations: {len(analysis['recommendations'])}")

if __name__ == "__main__":
    main()
