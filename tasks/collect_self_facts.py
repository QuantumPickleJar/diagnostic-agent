#!/usr/bin/env python3
"""
System Facts Collector
Gathers basic system information including hostname, memory usage, and CPU load.

Hardware Requirements:
- Any system with Python support (Pi, x86, ARM)
- Minimum 64MB RAM for fact collection
- CPU with basic load monitoring capability

Package Requirements:
- Python 3.6+
- Standard library: socket, os, time, json
- Optional: psutil for enhanced memory/CPU statistics
- Fallback to /proc filesystem parsing if psutil unavailable

System Dependencies:
- /proc filesystem mounted (Linux systems)
- /proc/meminfo readable for memory statistics
- /proc/loadavg readable for CPU load information
- hostname resolution working
"""
import json
import socket
import os
import time


# Gather hostname
hostname = socket.gethostname()

# Determine IP address
try:
    ip_address = socket.gethostbyname(hostname)
except Exception:
    ip_address = "unknown"

# Get memory usage
mem_info = {}
try:
    import psutil
    vm = psutil.virtual_memory()
    mem_info = {
        "total": vm.total,
        "available": vm.available,
        "percent": vm.percent,
    }
except Exception:
    # Fallback to /proc/meminfo parsing
    info = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    value = int(parts[1]) * 1024
                    info[key] = value
        total = info.get("MemTotal", 0)
        free = info.get("MemFree", 0) + info.get("Buffers", 0) + info.get("Cached", 0)
        mem_info = {
            "total": total,
            "available": free,
            "percent": round((total - free) / total * 100, 2) if total else 0,
        }
    except FileNotFoundError:
        mem_info = {}

# CPU load (1 minute average)
try:
    load1, _, _ = os.getloadavg()
except OSError:
    load1 = 0.0

output = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "hostname": hostname,
    "ip_address": ip_address,
    "memory": mem_info,
    "cpu_load_1min": load1,
}

os.makedirs('/app/agent_memory', exist_ok=True)
with open('/app/agent_memory/system_facts.json', 'w') as f:
    json.dump(output, f, indent=2)
