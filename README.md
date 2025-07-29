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

```bash
# Linux/macOS/Pi
./deploy.sh

# Windows (PowerShell)
.\deploy.ps1
```

### Available Options

```bash
# Normal deployment
./deploy.sh

# Clean deployment (removes old images/volumes)
./deploy.sh --clean

# View logs
./deploy.sh --logs

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

```

# [4] MODEL FALLBACK WRAPPER (run_agent.sh)
```sh


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
