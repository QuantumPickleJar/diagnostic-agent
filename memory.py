import json, time

def log_event(task, result):
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task": task,
        "result": result
    }
    with open("/agent_memory/recall_log.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")