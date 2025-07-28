# === Diagnostic Journalist Agent Blueprint ===

## SYSTEM DESIGN COMPONENTS
-------------------------
This file describes the structural design for the "Diagnostic Journalist" agent
running on a Raspberry Pi 4 with optional SSH bridge to a more capable dev machine.

# == CORE COMPONENTS ==

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
```

# [3] MEMORY WRITER (memory.py)

```py
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

# [4] MODEL FALLBACK WRAPPER (run_agent.sh)
```sh
#!/bin/bash

PI_MODEL="/home/pi/models/tinyllama.gguf"
DEV_IP="192.168.0.42"
PORT=22

if nc -z $DEV_IP $PORT; then
    echo "[+] Using remote model via SSH"
    open-interpreter --shell "ssh pi@$DEV_IP" --system "$(cat system_prompt.txt)"
else
    echo "[-] Fallback: Using local model on Pi"
    ./llama.cpp/main -m $PI_MODEL -p "$(cat system_prompt.txt)"
fi
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
    # Pipe the question into local model or Open Interpreter subprocess
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

- Implement FAISS journal embeddings
- Serve front-end with instructions
- Add REST endpoints for memory recall and config management
- Add systemd support for local deploy without Docker if needed
