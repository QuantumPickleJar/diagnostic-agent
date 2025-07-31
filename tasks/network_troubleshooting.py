#!/usr/bin/env python3
"""
Network Troubleshooting Task
Diagnoses common network issues and provides actionable recommendations.
Focuses on dual-adapter Pi setup with WireGuard tunneling.

Hardware Requirements:
- Raspberry Pi 4 (recommended) or similar ARM64/x86_64 system
- Built-in WiFi adapter for WireGuard tunnel (wlan0)
- External USB WiFi adapter (e.g., Netgear A7000, appears as wlx*) for home network
- Minimum 1GB RAM, 2GB+ recommended for full diagnostics
- USB 3.0 ports recommended for external adapter performance

Package Requirements:
- Python 3.7+
- Standard system tools: ping, nslookup, ip, iptables
- WireGuard tools: wg, wg-quick (wireguard-tools package)
- Network utilities: systemctl, ufw (optional)
- Docker (if running containerized services)

System Dependencies:
- Linux kernel with WireGuard support (5.6+ or module)
- iptables with NAT support
- systemd for service management
- /proc and /sys filesystems for network interface information
- sudo access for privileged network commands

Network Architecture Notes:
- wlan0 (Pi built-in antenna): Dedicated to WireGuard tunnel traffic
- wlx* (External Netgear A7000): Used for local network connectivity
- Split tunneling configuration: Only specific traffic routed through VPN
- Local services remain accessible through home network adapter
"""
import json
import os
import time
import subprocess
import socket

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

def diagnose_dns_issues():
    """Diagnose DNS resolution problems"""
    issues = []
    recommendations = []
    
    # Test DNS servers
    dns_servers = ['8.8.8.8', '1.1.1.1', '192.168.0.1']
    working_dns = []
    
    for dns_server in dns_servers:
        result = run_command(f"nslookup github.com {dns_server}")
        if result['success'] and 'github.com' in result['stdout']:
            working_dns.append(dns_server)
    
    if not working_dns:
        issues.append("No DNS servers are responding")
        recommendations.append("Check network connectivity and firewall rules")
    elif len(working_dns) < len(dns_servers):
        issues.append(f"Some DNS servers not responding: {set(dns_servers) - set(working_dns)}")
        recommendations.append(f"Consider using working DNS servers: {working_dns}")
    
    # Check for DNS hijacking
    result = run_command("nslookup github.com")
    if result['success'] and '10.0.0.2' in result['stdout']:
        issues.append("DNS appears to be hijacked - github.com resolving to VPN peer IP")
        recommendations.append("Check /etc/hosts file and DNS configuration")
    
    return {
        'issues': issues,
        'recommendations': recommendations,
        'working_dns_servers': working_dns
    }

def diagnose_routing_issues():
    """Diagnose routing and gateway problems"""
    issues = []
    recommendations = []
    
    # Check default routes
    result = run_command("ip route show default")
    if not result['success'] or not result['stdout']:
        issues.append("No default route found")
        recommendations.append("Configure default gateway")
    else:
        # Parse default routes
        default_routes = result['stdout'].split('\n')
        if len(default_routes) > 2:
            issues.append(f"Multiple default routes detected: {len(default_routes)}")
            recommendations.append("Consider consolidating or prioritizing routes")
    
    # Test gateway connectivity
    gateway_result = run_command("ping -c 2 192.168.0.1")
    if not gateway_result['success']:
        issues.append("Cannot reach default gateway (192.168.0.1)")
        recommendations.append("Check physical network connection and gateway configuration")
    
    return {
        'issues': issues,
        'recommendations': recommendations
    }

def diagnose_wireguard_issues():
    """Diagnose WireGuard tunnel problems"""
    issues = []
    recommendations = []
    
    # Check WireGuard status
    wg_result = run_command("wg show")
    if not wg_result['success'] or not wg_result['stdout']:
        issues.append("WireGuard is not running")
        recommendations.append("Start WireGuard with: sudo wg-quick up wg0")
    else:
        # Check if peer is configured
        if 'peer:' not in wg_result['stdout']:
            issues.append("No WireGuard peers configured")
            recommendations.append("Check WireGuard configuration file")
        
        # Check allowed IPs
        if '10.0.0.2/32' in wg_result['stdout']:
            # This is split tunneling - good
            pass
        elif '0.0.0.0/0' in wg_result['stdout']:
            issues.append("WireGuard routing all traffic through VPN")
            recommendations.append("Consider split tunneling for local network access")
    
    # Test VPN connectivity
    wg_ping = run_command("ping -c 2 10.0.0.2")
    if not wg_ping['success']:
        issues.append("Cannot reach WireGuard peer")
        recommendations.append("Check WireGuard configuration and network connectivity")
    
    return {
        'issues': issues,
        'recommendations': recommendations
    }

def diagnose_firewall_issues():
    """Diagnose firewall and iptables problems"""
    issues = []
    recommendations = []
    
    # Check UFW status
    ufw_result = run_command("sudo ufw status")
    if ufw_result['success'] and 'Status: active' in ufw_result['stdout']:
        # Check for overly restrictive rules
        if 'DENY OUT' in ufw_result['stdout']:
            issues.append("UFW is blocking outbound connections")
            recommendations.append("Review UFW rules: sudo ufw status verbose")
    
    # Check for Docker iptables conflicts
    iptables_result = run_command("sudo iptables -L DOCKER")
    if not iptables_result['success']:
        issues.append("Docker iptables chain missing")
        recommendations.append("Restart Docker service or rebuild iptables chains")
    
    return {
        'issues': issues,
        'recommendations': recommendations
    }

def diagnose_interface_issues():
    """Diagnose network interface problems"""
    issues = []
    recommendations = []
    
    # Load previous network scan
    try:
        with open('/app/agent_memory/network_scan.json', 'r') as f:
            network_data = json.load(f)
        
        interface_analysis = network_data.get('interface_analysis', {})
        
        # Check for expected interfaces
        expected_roles = ['external_wifi_adapter', 'builtin_wifi', 'wireguard_tunnel']
        found_roles = [data['role'] for data in interface_analysis.values()]
        
        for role in expected_roles:
            if role not in found_roles:
                if role == 'external_wifi_adapter':
                    issues.append("External WiFi adapter (Netgear A7000) not detected")
                    recommendations.append("Check USB connection and driver installation")
                elif role == 'wireguard_tunnel':
                    issues.append("WireGuard tunnel interface not active")
                    recommendations.append("Start WireGuard: sudo wg-quick up wg0")
        
        # Check interface states
        for if_name, data in interface_analysis.items():
            if data['role'] in expected_roles and data['state'] == 'DOWN':
                issues.append(f"Expected interface {if_name} ({data['role']}) is DOWN")
                recommendations.append(f"Bring up interface: sudo ip link set {if_name} up")
    
    except FileNotFoundError:
        issues.append("Network scan data not available")
        recommendations.append("Run network interface scan first")
    
    return {
        'issues': issues,
        'recommendations': recommendations
    }

def generate_user_questions():
    """Generate questions for the user to help with troubleshooting"""
    questions = [
        "Is the external Netgear A7000 WiFi adapter connected and powered?",
        "Are you currently connected to your home WiFi network?",
        "Should WireGuard be running? (yes/no)",
        "Are you experiencing issues with specific services or general internet connectivity?",
        "Have you made any recent network configuration changes?",
        "Is the Pi's built-in WiFi antenna visible/accessible for WireGuard use?",
        "What is the expected IP range for your home network? (e.g., 192.168.0.x, 192.168.1.x)",
        "Do you need split tunneling (some traffic through VPN, some direct) or full tunneling?",
    ]
    return questions

def main():
    """Main troubleshooting function"""
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Run all diagnostic checks
    diagnostics = {
        'timestamp': timestamp,
        'hostname': socket.gethostname(),
        'dns': diagnose_dns_issues(),
        'routing': diagnose_routing_issues(),
        'wireguard': diagnose_wireguard_issues(),
        'firewall': diagnose_firewall_issues(),
        'interfaces': diagnose_interface_issues(),
        'user_questions': generate_user_questions()
    }
    
    # Compile overall assessment
    all_issues = []
    all_recommendations = []
    
    for category, data in diagnostics.items():
        if isinstance(data, dict) and 'issues' in data:
            all_issues.extend([f"[{category.upper()}] {issue}" for issue in data['issues']])
            all_recommendations.extend([f"[{category.upper()}] {rec}" for rec in data['recommendations']])
    
    diagnostics['summary'] = {
        'total_issues': len(all_issues),
        'all_issues': all_issues,
        'all_recommendations': all_recommendations,
        'severity': 'HIGH' if len(all_issues) > 5 else 'MEDIUM' if len(all_issues) > 2 else 'LOW'
    }
    
    # Save results
    os.makedirs('/app/agent_memory', exist_ok=True)
    with open('/app/agent_memory/network_troubleshooting.json', 'w') as f:
        json.dump(diagnostics, f, indent=2)
    
    # Print summary
    print(f"Network troubleshooting completed at {timestamp}")
    print(f"Issues found: {len(all_issues)}")
    print(f"Severity: {diagnostics['summary']['severity']}")
    
    if all_issues:
        print("\nTop Issues:")
        for issue in all_issues[:3]:
            print(f"  - {issue}")
    
    if all_recommendations:
        print("\nTop Recommendations:")
        for rec in all_recommendations[:3]:
            print(f"  - {rec}")

if __name__ == "__main__":
    main()
