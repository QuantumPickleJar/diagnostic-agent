"""
ISA (Instruction Set Architecture) diagnostic tasks module.

This module contains diagnostic scripts that gather system information:
- collect_self_facts.py: System facts (hostname, IP, memory, CPU load)
- check_connectivity.py: Network connectivity and SSH tunnel status  
- scan_processes.py: Running processes and listening ports
- network_interface_scan.py: Detailed network interface analysis and dual-adapter detection
- network_troubleshooting.py: Network problem diagnosis and recommendations
- wireguard_analysis.py: WireGuard configuration analysis and tunnel insights

These scripts run periodically to update system state in /app/agent_memory/

Network Configuration Notes:
- Pi built-in antenna (wlan0): Used for WireGuard tunnel
- External Netgear A7000 (wlx*): Used for home network connectivity
- Split tunneling preferred for maintaining local network access
"""
