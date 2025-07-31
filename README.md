# Diagnostic Journalist Agent Blueprint

## Overview

This is the "Diagnostic Journalist" agent designed to run on a Raspberry Pi 4 with optional SSH bridge to a more capable development machine.

## Model Setup

### Sentence Transformer Model (Auto-downloaded)

- **Model**: `sentence-transformers/all-MiniLM-L6-v2` (~120MB)
- **Location**: Auto-downloaded to `/home/agent/.cache/sentence_transformers/` in container
- **Mount**: Handled by `model_cache` volume in docker-compose.yml
- **Purpose**: Semantic search and memory recall via FAISS embeddings

### TinyLlama Model (Optional Manual Download)

- **Model**: TinyLlama-1.1B-Chat-GGUF
- **Location**: Place in `./models/tinyllama.gguf`
- **Mount**: `./models:/app/models` in docker-compose.yml

To download TinyLlama:

```bash
mkdir -p models
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-GGUF/resolve/main/tinyllama-1.1b-chat.Q4_K_M.gguf -O ./models/tinyllama.gguf
```

## Deployment

### Quick Start

**Linux/Raspberry Pi:**
```bash
./deploy.sh
```

**Windows (PowerShell):**
```powershell
.\deploy.ps1
```

### Available Options

Both scripts support the same options:

```bash
# Normal deployment
./deploy.sh                # Linux/Pi
.\deploy.ps1               # Windows

# Clean deployment (removes old images/volumes)
./deploy.sh --clean        # Linux/Pi
.\deploy.ps1 -Clean        # Windows

# View logs
./deploy.sh --logs         # Linux/Pi
.\deploy.ps1 -Logs         # Windows

# Check status
./deploy.sh --status       # Linux/Pi
.\deploy.ps1 -Status       # Windows

# Stop service
./deploy.sh --stop         # Linux/Pi
.\deploy.ps1 -Stop         # Windows
```

# Check status
./deploy.sh --status

# Stop service
./deploy.sh --stop
```

### Manual Docker Commands

```bash
# Build and start
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Docker Compose Configuration

The system uses the following volume mounts:

- `agent_memory:/app/agent_memory` - Persistent memory and logs
- `./logs:/app/logs` - External log access
- `./models:/app/models` - TinyLlama and other local models
- `model_cache:/home/agent/.cache` - Sentence transformer cache

## CLI Interface

The diagnostic agent includes a powerful CLI interface (`cli_prompt.py`) that allows you to interact with a deployed agent from the command line. This is especially useful when the agent is deployed behind NGINX or on a remote server.

### Basic Usage

```bash
# Ask a single question
python3 cli_prompt.py "What is the system status?"

# Use the wrapper script (Linux/macOS)
./prompt.sh "Check network connectivity"

# Interactive mode
python3 cli_prompt.py --interactive

# Check agent status
python3 cli_prompt.py --status
```

### Remote Agent Access

When your diagnostic agent is deployed on a remote server (e.g., Raspberry Pi behind NGINX):

```bash
# Connect to remote agent
python3 cli_prompt.py --host your-pi.local --port 5000 "System health check"

# Using environment variables
export DIAGNOSTIC_AGENT_HOST="picklegate.ddns.net"
export DIAGNOSTIC_AGENT_PORT="5000"
python3 cli_prompt.py "Scan running processes"

# Via NGINX reverse proxy
python3 cli_prompt.py --host your-domain.com --port 80 "Network diagnostic"
```

### SSH Tunnel Access

For secure access over SSH (following the castlebravo setup):

```bash
# Set up SSH tunnel first
ssh -L 5000:localhost:5000 -p 2222 castlebravo@picklegate.ddns.net

# Then use CLI locally (in another terminal)
python3 cli_prompt.py --host localhost --port 5000 "What processes are running?"
```

### Advanced CLI Options

```bash
# All available options
python3 cli_prompt.py --help

# Common patterns
python3 cli_prompt.py --host 192.168.1.100 --verbose "Detailed system analysis"
python3 cli_prompt.py --activation-word PurpleTomato "Protected diagnostic"
python3 cli_prompt.py --output-format json "System status" | jq .
python3 cli_prompt.py --interactive --host remote-pi.local
```

### CLI Examples for Deployed Agent

```bash
# Quick system health check
python3 cli_prompt.py --host your-pi.local "What is the current system health?"

# Network diagnostics
python3 cli_prompt.py --host your-pi.local "Check internet connectivity and SSH tunnel status"

# Process monitoring
python3 cli_prompt.py --host your-pi.local "Show me running processes and open ports"

# Memory analysis
python3 cli_prompt.py --host your-pi.local "Analyze memory usage and system load"

# Historical data search
python3 cli_prompt.py --host your-pi.local "Find similar network issues from the past"

# Interactive troubleshooting session
python3 cli_prompt.py --interactive --host your-pi.local
```

### Integration with NGINX

If your diagnostic agent is behind an NGINX reverse proxy:

```nginx
# NGINX configuration example
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then access via CLI:

```bash
# Through NGINX proxy
python3 cli_prompt.py --host your-domain.com --port 80 "System diagnostic"

# With SSL (if configured)
# Note: CLI currently supports HTTP only, use SSH tunnel for secure access
```

### Output Formats

```bash
# Human-readable output (default)
python3 cli_prompt.py "System status"

# JSON output for scripting
python3 cli_prompt.py --output-format json "System status" | jq '.response'

# Verbose debugging
python3 cli_prompt.py --verbose "Debug network issues"
```

### Environment Configuration

Set these environment variables for convenience:

```bash
# In your ~/.bashrc or ~/.profile
export DIAGNOSTIC_AGENT_HOST="your-pi.local"
export DIAGNOSTIC_AGENT_PORT="5000"
export ACTIVATION_WORD="your_secret_word"

# Then use simplified commands
python3 cli_prompt.py "Quick system check"
```

### Testing Deployed Endpoints

Use the CLI to test your deployed diagnostic agent to ensure it's working correctly:

```bash
# Test basic connectivity and health
python3 cli_prompt.py --host your-domain.com --status

# Test through NGINX reverse proxy (port 80/443)
python3 cli_prompt.py --host your-domain.com --port 80 "System health check"

# Test with custom port (if not using standard ports)
python3 cli_prompt.py --host your-pi.local --port 5000 "Network connectivity test"

# Automated deployment verification script
python3 cli_prompt.py --output-format json --host your-domain.com "System status" | jq '.success'

# Test all major functions to verify deployment
python3 cli_prompt.py --host your-domain.com "What is the current system status?"
python3 cli_prompt.py --host your-domain.com "Check internet connectivity"
python3 cli_prompt.py --host your-domain.com "Show running processes"
python3 cli_prompt.py --host your-domain.com "Search memory for network issues"
```

**Deployment Testing Checklist:**
1. ✅ `--status` returns healthy status
2. ✅ Basic prompts receive responses
3. ✅ System info queries work (CPU, memory, processes)
4. ✅ Network connectivity checks function
5. ✅ Memory search/recall operates correctly
6. ✅ SSH bridge status (if configured)

**For CI/CD Integration:**
```bash
# Simple health check for automated deployment
if python3 cli_prompt.py --host $AGENT_HOST --status --output-format json | jq -e '.success'; then
    echo "✅ Diagnostic Agent deployment successful"
else
    echo "❌ Diagnostic Agent deployment failed"
    exit 1
fi
```

## System Architecture


# [1] PROMPT TEMPLATE (system_prompt.txt)
system_prompt = """
You are a diagnostic assistant called “Diagnostic Journalist.”
You run on a Raspberry Pi 4 in a low-resource environment with access to the local filesystem and shell.

---
Constraints:
- Time to reason: 10s to 30s
- Resource usage must be minimal
- Execute only permitted shell commands

---
Memory Access:
- Static facts stored in /agent_memory/static_config.json
- Diagnostic logs stored in /agent_memory/recall_log.jsonl
- Use Python scripts like lookup.py to retrieve memory facts

---
Behavior:
- Format all diagnostic outcomes as structured JSON
- Log each step to recall_log.jsonl
- If networked SSH bridge is available, you may delegate execution to the remote model

---
Fallback:
- If SSH target unreachable, use local LLM via llama.cpp with quantized model
- Confirm when fallback mode is engaged
"""

# [2] LOOKUP MODULE (lookup.py)
```py
import json
import sys

with open("/agent_memory/static_config.json") as f:
    config = json.load(f)

def get_fact(key):
    keys = key.split(".")
    val = config
    for k in keys:
        val = val.get(k)
        if val is None:
            print("[!] Not found")
            exit(1)
    print(val)

if __name__ == '__main__':
    get_fact(sys.argv[1])

# [3] MEMORY WRITER (memory.py)
import json, time

def log_event(task, result):
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task": task,
        "result": result
    }
    with open("/agent_memory/recall_log.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
```

# [3] MEMORY WRITER (memory.py)

```py
import json
import time
import faiss_utils

LOG_PATH = "/app/agent_memory/recall_log.jsonl"

def log_event(task, result):
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task": task,
        "result": result
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    # update embeddings after logging
    faiss_utils.reindex()
```

# [4] MODEL SELECTION WRAPPER (run_agent.py)
```sh
import json
import subprocess
import socket
import argparse
from datetime import datetime
from pathlib import Path

CONFIG_PATH = "/app/agent_memory/static_config.json"


def log_decision(mode: str, selected: str, action: str) -> None:
    """Print a structured JSON decision log."""
    log = {
        "mode": mode,
        "selected": selected,
        "action": action,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    print(json.dumps(log))


def check_ssh(host: str, port: int) -> bool:
    """Return True if SSH server is reachable."""
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except OSError:
        return False


def run_local(model_path: str, prompt: str, mode: str) -> None:
    action = f"./llama.cpp/main -m {model_path} -p '{prompt}'"
    print("[-] Fallback: Using local model")
    log_decision(mode, "local", action)
    subprocess.run(["./llama.cpp/main", "-m", model_path, "-p", prompt])


def run_remote(user: str, host: str, port: int, prompt: str, mode: str) -> None:
    ssh_cmd = f"ssh -p {port} {user}@{host}"
    action = f"open-interpreter --shell \"{ssh_cmd}\" --system PROMPT"
    print("[+] Using remote model via SSH")
    log_decision(mode, "remote", action)
    subprocess.run(["open-interpreter", "--shell", ssh_cmd, "--system", prompt])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Diagnostic Journalist agent")
    parser.add_argument(
        "--mode",
        choices=["auto", "local", "remote", "hybrid"],
        help="Override mode from config",
    )
    args = parser.parse_args()

    config_path = Path(CONFIG_PATH)
    with config_path.open() as f:
        config = json.load(f)

    mode = args.mode or config.get("mode", "auto")
    local_model_path = config.get("local_model_path")
    remote_dev = config.get("remote_dev", {})
    user = remote_dev.get("user")
    host = remote_dev.get("ip")
    port = remote_dev.get("port", 22)
    prompt_file = Path(config.get("system_prompt_file", "system_prompt.txt"))

    with prompt_file.open() as f:
        prompt = f.read()

    if mode == "local":
        run_local(local_model_path, prompt, mode)
    elif mode == "remote":
        run_remote(user, host, port, prompt, mode)
    elif mode == "hybrid":
        log_decision(mode, "none", "Hybrid mode not yet supported")
        print("[!] Hybrid mode not yet supported")
    else:  # auto mode
        if check_ssh(host, port):
            run_remote(user, host, port, prompt, mode)
        else:
            run_local(local_model_path, prompt, mode)


if __name__ == "__main__":
    main()
```

# == WEB FRONTEND SERVER ==
You can integrate this with Flask to expose a web API:

# [5] WEB SERVER ENTRYPOINT (web_agent.py)

```py
from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route("/ask", methods=["POST"])
def ask():
    question = request.json.get("question")
    output = subprocess.run(["python3", "agent_cli.py", question], capture_output=True, text=True)
    return jsonify({"response": output.stdout})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
```

# == REMOTE MODEL OPTION ==
You can use the same prompt via Open Interpreter with SSH bridging
to a stronger model hosted on your dev machine:
`open-interpreter --shell "ssh pi@192.168.0.149" --system "$(cat system_prompt.txt)"`

# == DOCKER DEPLOYMENT SETUP ==

You can containerize this agent using Docker Compose:

## [6] docker-compose.yml

```
version: '3.8'
services:
  diagnostic_journalist:
    build: .
    volumes:
      - ./agent_memory:/app/agent_memory
      - ./models:/app/models
    ports:
      - "5000:5000"
    environment:
      - MODEL_PATH=/app/models/tinyllama.gguf
      - PROMPT_PATH=/app/system_prompt.txt
    deploy:
      resources:
        limits:
          cpus: '1.5'
          memory: '3G'
    restart: unless-stopped
```

# [7] Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install flask faiss-cpu
CMD ["python3", "web_agent.py"]
```
This setup allows persistent memory across restarts and logs to be retained for FAISS embedding.

Use `docker-compose up --build` to deploy.

== STALE LOOKUP HANDLING ==
Agent should timestamp last config load. If older than X mins or if lookup fails:

- Prompt user to re-verify fact

- Flag entry as outdated in log

- Optionally store a `last_verified` key per config item

== CLI-THEMED FRONTEND ==
 To be served via Flask/static directory:

- static/index.html (mocked after ChatGPT with terminal font, dark theme, and monospaced output)

Will include: input box, streamed output area, scrollback, and FAISS search button

== TODO ==

- Serve front-end with instructions
- Add REST endpoints for memory recall and config management
- Add systemd support for local deploy without Docker if needed

== FAISS JOURNAL EMBEDDINGS ==
FAISS is used for semantic recall of past log entries. Each `task` and `result` line from `recall_log.jsonl` is embedded with SentenceTransformer and stored in the index. Install the dependencies with `pip install sentence-transformers faiss-cpu`. The first call will download the small `all-MiniLM-L6-v2` model
(~120MB). If you are offline, pre-download this model on another machine and place it under the `~/.cache/sentence_transformers/` directory on the Pi.

Run `python3 index_memory.py` to build `/agent_memory/embeddings.faiss` from `recall_log.jsonl`. If the log file is empty the script simply prints "No log entries found" and no index is created. The Flask server exposes `/search` for nearest-neighbor lookup and `/reindex` to rebuild the index. Embeddings are automatically refreshed every five minutes while the server is running.


# == STALE LOOKUP HANDLING ==
- Timestamp fact verification in static_config.json:
- Prompt user to re-verify fact if older than defined interval (e.g., 1 week)
- Flag entry as outdated in recall_log.jsonl

# == TODO ==
- Implement FAISS journal embeddings
- Serve front-end with instructions
- Add REST endpoints for memory recall and config management
- Add systemd support for local deploy without Docker if needed

## Quick Reference

### CLI Commands Cheat Sheet

```bash
# Single question to local agent
python3 cli_prompt.py "System status"

# Single question to remote agent
python3 cli_prompt.py --host your-pi.local "Network check"

# Interactive mode
python3 cli_prompt.py --interactive

# Status check
python3 cli_prompt.py --status

# With SSH tunnel (secure)
# ssh -L 5000:localhost:5000 -p 2222 castlebravo@picklegate.ddns.net
ssh -L 5000:localhost:5000 -p 2222 castlebravo@picklegate.ddns.net%%
python3 cli_prompt.py "Secure diagnostic"

# JSON output for automation
python3 cli_prompt.py --output-format json "System info" | jq '.response'
```

### Common Diagnostic Questions

```bash
# System Health
"What is the current system health?"
"Show memory usage and CPU load"
"Check disk space and system temperature"

# Network Diagnostics  
"Check internet connectivity"
"Test SSH tunnel status"
"Scan network interfaces and routing"

# Process Monitoring
"Show running processes"
"List open ports and listening services"
"Check for suspicious processes"

# Historical Analysis
"Find similar network issues from the past"
"Search for previous system errors"
"Show recent diagnostic activities"
```

### Environment Setup

```bash
# Add to ~/.bashrc for convenience
export DIAGNOSTIC_AGENT_HOST="your-pi.local"
export DIAGNOSTIC_AGENT_PORT="5000"
export ACTIVATION_WORD="your_secret"
```
