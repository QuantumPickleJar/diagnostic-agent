# autonomic_dispatcher.py
# This module decides whether to execute tasks locally or dispatch them to a remote dev machine

import json
import subprocess
import time
import os
import logging
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Ensure agent_memory directory exists
memory_dir = Path("agent_memory")
memory_dir.mkdir(exist_ok=True)

# Load static config
config_path = memory_dir / "static_config.json"
try:
    with open(config_path) as f:
        config = json.load(f)
except FileNotFoundError:
    # Create default config if it doesn't exist
    config = {
        "delegation_threshold": 0.65,
        "dev_machine": {
            "host": "picklegate.ddns.net",
            "port": 2222,
            "user": "castlebravo"
        },
        "local_agent_enabled": True,
        "remote_agent_enabled": True
    }
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"Created default config at {config_path}")

THRESHOLD = config.get("delegation_threshold", 0.65)
DEV_HOST = config.get("dev_machine", {}).get("host", "picklegate.ddns.net")
DEV_PORT = config.get("dev_machine", {}).get("port", 2222)
DEV_USER = config.get("dev_machine", {}).get("user", "castlebravo")
LOCAL_ENABLED = config.get("local_agent_enabled", True)
REMOTE_ENABLED = config.get("remote_agent_enabled", True)


def score_task(task_text):
    """
    Score a task to determine if it should be executed locally or remotely.
    Returns a score between 0.0 and 1.0, where higher scores indicate 
    tasks better suited for the dev machine.
    """
    score = 0.0
    task_lower = task_text.lower()
    
    # Length-based scoring (longer tasks may benefit from more resources)
    if len(task_text) > 200:
        score += 0.3
    elif len(task_text) > 100:
        score += 0.1
    
    # Complexity indicators
    complexity_keywords = [
        "optimize", "analyze", "summarize", "plan", "generate", "create",
        "compile", "build", "complex", "detailed", "comprehensive"
    ]
    if any(kw in task_lower for kw in complexity_keywords):
        score += 0.4
    
    # Code-related tasks (may need dev environment)
    code_indicators = ["{", "}", ";", "def ", "class ", "import ", "function"]
    if any(indicator in task_text for indicator in code_indicators):
        score += 0.3
    
    # Development-specific tasks
    dev_keywords = [
        "debug", "refactor", "implement", "code review", "architecture",
        "design pattern", "algorithm", "performance", "benchmark"
    ]
    if any(kw in task_lower for kw in dev_keywords):
        score += 0.4
    
    # System-specific tasks (better suited for local execution)
    local_keywords = [
        "system status", "container", "docker", "network", "disk usage",
        "memory", "cpu", "temperature", "process", "service", "logs"
    ]
    if any(kw in task_lower for kw in local_keywords):
        score -= 0.3
    
    # Real-time monitoring tasks (should stay local)
    realtime_keywords = ["monitor", "watch", "real-time", "live", "current"]
    if any(kw in task_lower for kw in realtime_keywords):
        score -= 0.2
    
    return max(0.0, min(score, 1.0))


def dispatch_task(task_text, force_local=False, force_remote=False):
    """
    Main dispatch function that decides where to execute a task.
    
    Args:
        task_text (str): The task to execute
        force_local (bool): Force local execution regardless of score
        force_remote (bool): Force remote execution regardless of score
    
    Returns:
        str: The result of task execution
    """
    if force_local and force_remote:
        raise ValueError("Cannot force both local and remote execution")
    
    score = score_task(task_text)
    reason = f"Task score: {score:.2f} vs threshold: {THRESHOLD:.2f}"
    
    # Determine execution location
    if force_local:
        execute_remote = False
        reason = "Forced local execution"
    elif force_remote:
        execute_remote = True
        reason = "Forced remote execution"
    else:
        execute_remote = score >= THRESHOLD and REMOTE_ENABLED
    
    # Log the decision
    log_event("dispatch_decision", {
        "score": score, 
        "threshold": THRESHOLD, 
        "reason": reason,
        "execute_remote": execute_remote,
        "task_preview": task_text[:100] + "..." if len(task_text) > 100 else task_text
    })
    
    if execute_remote:
        return run_remote(task_text)
    else:
        return run_local(task_text)


def run_local(task_text):
    """Execute task locally on the Pi using the unified smart agent"""
    logger.info("[LOCAL] Executing task on Pi...")
    
    try:
        # Import and use the local smart agent
        from unified_smart_agent import smart_agent
        result = smart_agent.process_query(task_text)
        
        log_event("local_execution", {
            "task": task_text[:100] + "..." if len(task_text) > 100 else task_text,
            "success": True,
            "result_length": len(result)
        })
        
        return f"[LOCAL] {result}"
        
    except Exception as e:
        error_msg = f"Local execution failed: {str(e)}"
        logger.error(error_msg)
        log_event("local_execution_error", {
            "task": task_text,
            "error": str(e)
        })
        return f"[LOCAL ERROR] {error_msg}"


def run_remote(task_text):
    """Execute task remotely on the dev machine"""
    logger.info("[REMOTE] Sending task to dev machine...")
    
    if not REMOTE_ENABLED:
        return run_local(task_text)  # Fallback to local
    
    try:
        # Use SSH to execute on the dev machine
        # Assume the dev machine has a similar agent setup
        ssh_command = [
            "ssh", 
            "-p", str(DEV_PORT),
            f"{DEV_USER}@{DEV_HOST}",
            f"cd ~/diagnostic-agent && python3 -c \"from unified_smart_agent import smart_agent; print(smart_agent.process_query('{task_text.replace('\"', '\\\"')}'))\""
        ]
        
        result = subprocess.run(
            ssh_command, 
            capture_output=True, 
            text=True, 
            timeout=30  # 30 second timeout for remote execution
        )
        
        if result.returncode == 0:
            log_event("remote_execution", {
                "task": task_text[:100] + "..." if len(task_text) > 100 else task_text,
                "success": True,
                "result_length": len(result.stdout)
            })
            return f"[REMOTE] {result.stdout.strip()}"
        else:
            error_msg = f"Remote execution failed: {result.stderr}"
            log_event("remote_execution_error", {
                "task": task_text,
                "error": error_msg
            })
            # Fallback to local execution
            logger.warning("Remote execution failed, falling back to local")
            return run_local(task_text)
            
    except subprocess.TimeoutExpired:
        error_msg = "Remote execution timed out"
        logger.error(error_msg)
        log_event("remote_execution_timeout", {
            "task": task_text,
            "timeout": 30
        })
        # Fallback to local execution
        return run_local(task_text)
        
    except Exception as e:
        error_msg = f"Could not reach dev machine: {str(e)}"
        logger.error(error_msg)
        log_event("remote_dispatch_error", {
            "task": task_text,
            "error": str(e)
        })
        # Fallback to local execution
        return run_local(task_text)


def log_event(event_type, data):
    """Log events to the recall log for analysis and debugging"""
    try:
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event_type": event_type,
            "data": data
        }
        
        log_file = memory_dir / "recall_log.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
            
    except Exception as e:
        logger.error(f"Failed to log event: {e}")


def test_connectivity():
    """Test connectivity to the remote dev machine"""
    if not REMOTE_ENABLED:
        return False, "Remote execution disabled in config"
    
    try:
        result = subprocess.run([
            "ssh", 
            "-p", str(DEV_PORT),
            "-o", "ConnectTimeout=5",
            f"{DEV_USER}@{DEV_HOST}",
            "echo 'connectivity_test'"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return True, "Remote connection successful"
        else:
            return False, f"SSH failed: {result.stderr}"
            
    except Exception as e:
        return False, f"Connection test failed: {str(e)}"


def get_dispatch_stats():
    """Get statistics about task dispatch decisions"""
    try:
        log_file = memory_dir / "recall_log.jsonl"
        if not log_file.exists():
            return {"total": 0, "local": 0, "remote": 0, "errors": 0}
        
        stats = {"total": 0, "local": 0, "remote": 0, "errors": 0}
        
        with open(log_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("event_type") == "dispatch_decision":
                        stats["total"] += 1
                        if entry.get("data", {}).get("execute_remote"):
                            stats["remote"] += 1
                        else:
                            stats["local"] += 1
                    elif "error" in entry.get("event_type", ""):
                        stats["errors"] += 1
                except json.JSONDecodeError:
                    continue
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get dispatch stats: {e}")
        return {"error": str(e)}


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 autonomic_dispatcher.py 'your question here'")
        print("       python3 autonomic_dispatcher.py --test-connectivity")
        print("       python3 autonomic_dispatcher.py --stats")
        exit(1)
    
    if sys.argv[1] == "--test-connectivity":
        success, message = test_connectivity()
        print(f"Connectivity test: {'PASS' if success else 'FAIL'}")
        print(f"Message: {message}")
        exit(0 if success else 1)
    
    if sys.argv[1] == "--stats":
        stats = get_dispatch_stats()
        print("Dispatch Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        exit(0)
    
    task = ' '.join(sys.argv[1:])
    print(dispatch_task(task))
