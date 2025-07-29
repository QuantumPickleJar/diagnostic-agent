import json
import time
import faiss_utils

LOG_PATH = "/agent_memory/recall_log.jsonl"

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