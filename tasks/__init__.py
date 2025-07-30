"""
ISA (Instruction Set Architecture) diagnostic tasks module.

This module contains diagnostic scripts that gather system information:
- collect_self_facts.py: System facts (hostname, IP, memory, CPU load)
- check_connectivity.py: Network connectivity and SSH tunnel status  
- scan_processes.py: Running processes and listening ports

These scripts run periodically to update system state in /app/agent_memory/
"""
