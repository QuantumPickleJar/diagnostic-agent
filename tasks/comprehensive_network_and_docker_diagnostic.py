#!/usr/bin/env python3
"""
Comprehensive Network and Docker Diagnostic Task
Performs network troubleshooting, WireGuard analysis, and Docker networking diagnosis.

Hardware Requirements:
- Raspberry Pi 4 or equivalent ARM/x86 system
- Minimum 1GB RAM for Docker operations
- Network interfaces: WiFi capability (dual-interface setup supported)
- Optional: External WiFi adapter (Netgear A7000 or equivalent)

Package Requirements:
- Python 3.7+
- Standard library: subprocess, socket, json, os, time, shutil
- System packages: net-tools, iproute2, iputils-ping, iptables
- Optional: docker.io, wireguard-tools
- Optional: psutil for enhanced system monitoring

System Dependencies:
- /proc filesystem for network statistics
- /sys/class/net for interface information
- iptables for firewall rule analysis
- systemctl for service management
- Docker daemon (if Docker diagnostics needed)
- WireGuard kernel module (if VPN diagnostics needed)

Network Configuration Context:
- Built-in WiFi (wlan0): Typically used for WireGuard VPN tunnel
- External adapter (wlx*): Used for home network connectivity  
- Split tunneling configuration for maintaining local access
- Docker bridge networks requiring proper iptables configuration
"""

import json
import subprocess
import socket
import time
import os
import shutil
from datetime import datetime

def run_command(cmd, timeout=10, capture_output=True):
    """Run a command safely with timeout and error handling"""
    try:
        if isinstance(cmd, str):
            cmd = cmd.split()
        result = subprocess.run(cmd, capture_output=capture_output, text=True, timeout=timeout)
        return {
            "command": " ".join(cmd),
            "success": result.returncode == 0,
            "stdout": result.stdout.strip() if capture_output else "",
            "stderr": result.stderr.strip() if capture_output else "",
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "command": " ".join(cmd),
            "success": False,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "returncode": -1
        }
    except FileNotFoundError:
        return {
            "command": " ".join(cmd),
            "success": False,
            "stdout": "",
            "stderr": f"Command not found: {cmd[0]}",
            "returncode": -1
        }
    except Exception as e:
        return {
            "command": " ".join(cmd),
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }

def check_internet_connectivity():
    """Test internet connectivity using multiple methods"""
    targets = [
        ("1.1.1.1", 53),    # Cloudflare DNS
        ("8.8.8.8", 53),    # Google DNS
        ("9.9.9.9", 53),    # Quad9 DNS
    ]
    
    results = {}
    for host, port in targets:
        try:
            with socket.create_connection((host, port), timeout=3):
                results[f"{host}:{port}"] = {"reachable": True, "error": None}
        except Exception as e:
            results[f"{host}:{port}"] = {"reachable": False, "error": str(e)}
    
    # Also try ping if available
    ping_results = {}
    if shutil.which("ping"):
        for host, _ in targets:
            ping_result = run_command(["ping", "-c", "1", "-W", "3", host])
            ping_results[host] = {
                "success": ping_result["success"],
                "output": ping_result["stdout"]
            }
    
    return {
        "socket_connectivity": results,
        "ping_results": ping_results,
        "overall_connectivity": any(r["reachable"] for r in results.values())
    }

def analyze_network_interfaces():
    """Analyze all network interfaces and their status"""
    interfaces = {}
    
    # Get interface list
    ip_addr = run_command(["ip", "addr", "show"])
    ip_route = run_command(["ip", "route", "show"])
    
    # Parse interfaces from /sys/class/net
    net_dir = "/sys/class/net"
    if os.path.exists(net_dir):
        for iface in os.listdir(net_dir):
            if iface == "lo":  # Skip loopback
                continue
                
            iface_info = {
                "name": iface,
                "type": "unknown",
                "status": "unknown",
                "ip_addresses": [],
                "mac_address": None
            }
            
            # Determine interface type
            if iface.startswith("wlan"):
                iface_info["type"] = "wifi_builtin"
            elif iface.startswith("wlx"):
                iface_info["type"] = "wifi_external"
            elif iface.startswith("eth") or iface.startswith("end"):
                iface_info["type"] = "ethernet"
            elif iface.startswith("wg"):
                iface_info["type"] = "wireguard"
            elif iface.startswith("br-") or iface.startswith("docker"):
                iface_info["type"] = "docker_bridge"
            elif iface.startswith("veth"):
                iface_info["type"] = "docker_veth"
            
            # Get status
            operstate_file = f"{net_dir}/{iface}/operstate"
            if os.path.exists(operstate_file):
                with open(operstate_file) as f:
                    iface_info["status"] = f.read().strip()
            
            # Get MAC address
            address_file = f"{net_dir}/{iface}/address"
            if os.path.exists(address_file):
                with open(address_file) as f:
                    iface_info["mac_address"] = f.read().strip()
            
            interfaces[iface] = iface_info
    
    return {
        "interfaces": interfaces,
        "ip_addr_output": ip_addr["stdout"] if ip_addr["success"] else ip_addr["stderr"],
        "ip_route_output": ip_route["stdout"] if ip_route["success"] else ip_route["stderr"]
    }

def analyze_wireguard():
    """Analyze WireGuard configuration and status"""
    wg_show = run_command(["wg", "show"])
    wg_configs = []
    
    # Look for config files
    config_paths = ["/etc/wireguard", "/home/diagnostic-agent/wireguard"]
    for config_dir in config_paths:
        if os.path.exists(config_dir):
            for file in os.listdir(config_dir):
                if file.endswith(".conf"):
                    config_path = os.path.join(config_dir, file)
                    try:
                        with open(config_path) as f:
                            # Don't read sensitive keys, just check structure
                            content = f.read()
                            wg_configs.append({
                                "file": config_path,
                                "has_interface": "[Interface]" in content,
                                "has_peer": "[Peer]" in content,
                                "lines": len(content.splitlines())
                            })
                    except Exception as e:
                        wg_configs.append({
                            "file": config_path,
                            "error": str(e)
                        })
    
    return {
        "wg_show": wg_show,
        "config_files": wg_configs,
        "wireguard_available": shutil.which("wg") is not None
    }

def analyze_docker_networking():
    """Analyze Docker networking configuration and issues"""
    docker_info = run_command(["docker", "info"])
    docker_ps = run_command(["docker", "ps", "-a"])
    docker_networks = run_command(["docker", "network", "ls"])
    
    # Check iptables for Docker rules
    iptables_nat = run_command(["iptables", "-t", "nat", "-L", "-n"])
    iptables_filter = run_command(["iptables", "-L", "-n"])
    
    # Check for common Docker networking issues
    issues = []
    
    # Check if Docker daemon is running
    if not docker_info["success"]:
        issues.append({
            "type": "docker_daemon",
            "severity": "high",
            "description": "Docker daemon is not running or accessible",
            "suggestion": "Check if Docker is installed and running: sudo systemctl status docker"
        })
    
    # Check for iptables issues
    if "DOCKER" not in iptables_filter.get("stdout", ""):
        issues.append({
            "type": "iptables_docker_chain",
            "severity": "medium", 
            "description": "Docker iptables chains may be missing",
            "suggestion": "Restart Docker daemon to recreate iptables rules"
        })
    
    return {
        "docker_info": docker_info,
        "docker_ps": docker_ps,
        "docker_networks": docker_networks,
        "iptables_nat": iptables_nat,
        "iptables_filter": iptables_filter,
        "issues": issues,
        "docker_available": shutil.which("docker") is not None
    }

def analyze_dns_configuration():
    """Analyze DNS configuration and resolution"""
    # Check resolv.conf
    resolv_conf = {"exists": False, "content": "", "nameservers": []}
    if os.path.exists("/etc/resolv.conf"):
        resolv_conf["exists"] = True
        try:
            with open("/etc/resolv.conf") as f:
                content = f.read()
                resolv_conf["content"] = content
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("nameserver"):
                        parts = line.split()
                        if len(parts) >= 2:
                            resolv_conf["nameservers"].append(parts[1])
        except Exception as e:
            resolv_conf["error"] = str(e)
    
    # Test DNS resolution
    dns_tests = {}
    test_domains = ["google.com", "github.com", "cloudflare.com"]
    
    for domain in test_domains:
        try:
            import socket
            result = socket.gethostbyname(domain)
            dns_tests[domain] = {"success": True, "ip": result}
        except Exception as e:
            dns_tests[domain] = {"success": False, "error": str(e)}
    
    # Test with nslookup if available
    nslookup_tests = {}
    if shutil.which("nslookup"):
        for domain in test_domains:
            nslookup_result = run_command(["nslookup", domain])
            nslookup_tests[domain] = nslookup_result
    
    return {
        "resolv_conf": resolv_conf,
        "dns_resolution_tests": dns_tests,
        "nslookup_tests": nslookup_tests
    }

def generate_iptables_fix_script():
    """Generate a script to fix common Docker iptables issues"""
    script_content = """#!/bin/bash
# Docker IPTables Fix Script
# This script repairs common Docker networking issues

echo "=== Docker IPTables Diagnostic and Repair ==="
echo "Date: $(date)"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)" 
   exit 1
fi

echo "Stopping Docker daemon..."
systemctl stop docker

echo "Cleaning up Docker iptables rules..."
# Remove Docker chains
iptables -t nat -F DOCKER 2>/dev/null || true
iptables -t nat -X DOCKER 2>/dev/null || true
iptables -t filter -F DOCKER 2>/dev/null || true
iptables -t filter -X DOCKER 2>/dev/null || true
iptables -t filter -F DOCKER-ISOLATION-STAGE-1 2>/dev/null || true
iptables -t filter -X DOCKER-ISOLATION-STAGE-1 2>/dev/null || true
iptables -t filter -F DOCKER-ISOLATION-STAGE-2 2>/dev/null || true
iptables -t filter -X DOCKER-ISOLATION-STAGE-2 2>/dev/null || true
iptables -t filter -F DOCKER-USER 2>/dev/null || true
iptables -t filter -X DOCKER-USER 2>/dev/null || true

echo "Restarting Docker daemon..."
systemctl start docker

echo "Waiting for Docker to initialize..."
sleep 5

echo "Testing Docker functionality..."
if docker ps > /dev/null 2>&1; then
    echo "✅ Docker is working correctly"
else
    echo "❌ Docker still has issues"
    exit 1
fi

echo "Testing Docker networking..."
if docker network ls > /dev/null 2>&1; then
    echo "✅ Docker networking is working"
else
    echo "❌ Docker networking still has issues"
    exit 1
fi

echo ""
echo "=== Repair Complete ==="
echo "Docker IPTables rules have been reset and recreated."
echo "You can now try running your containers again."

# Self-delete the script
echo "Cleaning up fix script..."
rm -f "$0"
"""
    
    return script_content

def main():
    """Main diagnostic function"""
    print("🔍 Starting comprehensive network and Docker diagnostic...")
    
    timestamp = datetime.now().isoformat()
    
    # Gather all diagnostic information
    diagnostic_data = {
        "timestamp": timestamp,
        "hostname": socket.gethostname(),
        "internet_connectivity": check_internet_connectivity(),
        "network_interfaces": analyze_network_interfaces(),
        "wireguard_analysis": analyze_wireguard(),
        "docker_networking": analyze_docker_networking(),
        "dns_configuration": analyze_dns_configuration()
    }
    
    # Generate recommendations
    recommendations = []
    
    # Internet connectivity recommendations
    if not diagnostic_data["internet_connectivity"]["overall_connectivity"]:
        recommendations.append({
            "category": "connectivity",
            "priority": "high",
            "issue": "No internet connectivity detected",
            "action": "Check physical connections and network configuration"
        })
    
    # Docker recommendations
    docker_issues = diagnostic_data["docker_networking"]["issues"]
    if docker_issues:
        for issue in docker_issues:
            if issue["type"] == "iptables_docker_chain":
                recommendations.append({
                    "category": "docker",
                    "priority": "medium",
                    "issue": "Docker iptables chains missing",
                    "action": "Run the generated iptables fix script",
                    "script_available": True
                })
    
    # WireGuard recommendations
    wg_data = diagnostic_data["wireguard_analysis"]
    if wg_data["wireguard_available"] and not wg_data["wg_show"]["success"]:
        recommendations.append({
            "category": "wireguard",
            "priority": "medium", 
            "issue": "WireGuard not running despite being available",
            "action": "Check WireGuard configuration and start if needed"
        })
    
    diagnostic_data["recommendations"] = recommendations
    
    # Create output directory
    os.makedirs('/app/agent_memory', exist_ok=True)
    
    # Save comprehensive diagnostic results
    with open('/app/agent_memory/comprehensive_network_diagnostic.json', 'w') as f:
        json.dump(diagnostic_data, f, indent=2)
    
    # Generate and save IPTables fix script if needed
    if any(r.get("script_available") for r in recommendations):
        fix_script = generate_iptables_fix_script()
        with open('/app/agent_memory/docker_iptables_fix.sh', 'w') as f:
            f.write(fix_script)
        os.chmod('/app/agent_memory/docker_iptables_fix.sh', 0o755)
        print("📝 Generated Docker IPTables fix script: /app/agent_memory/docker_iptables_fix.sh")
    
    print("✅ Comprehensive network diagnostic complete")
    print(f"📊 Results saved to: /app/agent_memory/comprehensive_network_diagnostic.json")
    
    # Print summary
    print("\n=== DIAGNOSTIC SUMMARY ===")
    print(f"Internet Connectivity: {'✅ OK' if diagnostic_data['internet_connectivity']['overall_connectivity'] else '❌ FAILED'}")
    print(f"Docker Available: {'✅ YES' if diagnostic_data['docker_networking']['docker_available'] else '❌ NO'}")
    print(f"WireGuard Available: {'✅ YES' if diagnostic_data['wireguard_analysis']['wireguard_available'] else '❌ NO'}")
    print(f"DNS Resolution: {'✅ OK' if any(t['success'] for t in diagnostic_data['dns_configuration']['dns_resolution_tests'].values()) else '❌ FAILED'}")
    
    if recommendations:
        print(f"\n⚠️  {len(recommendations)} recommendations generated")
        for rec in recommendations:
            print(f"   {rec['category'].upper()}: {rec['issue']}")
    else:
        print("\n✅ No critical issues detected")

if __name__ == "__main__":
    main()
