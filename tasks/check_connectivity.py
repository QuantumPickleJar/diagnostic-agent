#!/usr/bin/env python3
"""
Basic Connectivity Checker
Tests internet connectivity and SSH tunnel accessibility.

Hardware Requirements:
- Any network-capable device (Pi, x86, ARM)
- Active network interface with internet access
- Minimum 128MB RAM for basic connectivity tests

Package Requirements:
- Python 3.6+
- Standard library only (socket, subprocess, json, os, time)
- Optional: iputils-ping package for ping command
- Optional: psutil for enhanced system monitoring

System Dependencies:
- Network stack configured and active
- DNS resolution working (fallback methods included)
- Socket support in kernel
- /proc filesystem for system information access
"""
import json
import subprocess
import socket
import time
import os
import shutil

PING_TARGET = "1.1.1.1"
SSH_HOST = "picklegate.ddns.net"
SSH_PORT = 2222

# Check internet connectivity with ping (with fallback if ping not available)
internet_ok = False
try:
    # First check if ping command exists
    ping_cmd = shutil.which("ping")
    if ping_cmd:
        ping_result = subprocess.run([
            ping_cmd, "-c", "1", PING_TARGET
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        internet_ok = ping_result.returncode == 0
    else:
        # Fallback: try to connect to a reliable service
        try:
            with socket.create_connection(("8.8.8.8", 53), timeout=3):
                internet_ok = True
        except Exception:
            internet_ok = False
except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
    # Fallback: try to connect to a reliable service
    try:
        with socket.create_connection(("8.8.8.8", 53), timeout=3):
            internet_ok = True
    except Exception:
        internet_ok = False

# Attempt to open SSH tunnel port
ssh_ok = False
try:
    with socket.create_connection((SSH_HOST, SSH_PORT), timeout=3):
        ssh_ok = True
except Exception:
    ssh_ok = False

output = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "internet_reachable": internet_ok,
    "ssh_tunnel_open": ssh_ok,
}

os.makedirs('/app/agent_memory', exist_ok=True)
with open('/app/agent_memory/connectivity.json', 'w') as f:
    json.dump(output, f, indent=2)
