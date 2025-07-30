#!/usr/bin/env python3
import json
import subprocess
import socket
import time
import os

PING_TARGET = "1.1.1.1"
SSH_HOST = "192.168.0.153"
SSH_PORT = 2222

# Check internet connectivity with ping
ping_result = subprocess.run([
    "ping", "-c", "1", PING_TARGET
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

internet_ok = ping_result.returncode == 0

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

os.makedirs("/agent_memory", exist_ok=True)
with open("/agent_memory/connectivity.json", "w") as f:
    json.dump(output, f, indent=2)
