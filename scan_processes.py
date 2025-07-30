#!/usr/bin/env python3
import json
import os
import time
import subprocess

process_names = []
ports = []

try:
    import psutil
except ImportError:
    psutil = None

if psutil:
    for p in psutil.process_iter(['name']):
        name = p.info.get('name')
        if name:
            process_names.append(name)
    try:
        for conn in psutil.net_connections():
            if conn.status == getattr(psutil, 'CONN_LISTEN', 'LISTEN') and conn.laddr:
                ports.append({
                    'pid': conn.pid,
                    'address': conn.laddr.ip,
                    'port': conn.laddr.port,
                })
    except Exception:
        pass
else:
    # Fallback using subprocess
    try:
        out = subprocess.check_output(['ps', '-eo', 'comm'], text=True)
        for line in out.strip().splitlines()[1:]:
            if line:
                process_names.append(line.strip())
    except Exception:
        pass
    try:
        out = subprocess.check_output(['ss', '-tulpn'], text=True)
        for line in out.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 5:
                local = parts[4]
                if ':' in local:
                    addr, port = local.rsplit(':', 1)
                    ports.append({'address': addr, 'port': int(port) if port.isdigit() else port})
    except Exception:
        pass

output = {
    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'processes': process_names,
    'ports': ports,
}

os.makedirs('/agent_memory', exist_ok=True)
with open('/agent_memory/process_status.json', 'w') as f:
    json.dump(output, f, indent=2)
