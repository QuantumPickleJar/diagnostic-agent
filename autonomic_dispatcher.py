# autonomic_dispatcher.py
# This module decides whether to execute tasks locally or dispatch them to a remote dev machine

import json
import subprocess
import time
import os
import logging
import socket
from pathlib import Path
from semantic_task_scorer import semantic_scorer

# Configure logging
logger = logging.getLogger(__name__)

# Ensure agent_memory directory exists
memory_dir = Path("agent_memory")
memory_dir.mkdir(exist_ok=True)

# Load static config for SSH details
config_path = memory_dir / "static_config.json"
try:
    with open(config_path) as f:
        config = json.load(f)
except FileNotFoundError:
    config = {
        "dev_machine": {
            "host": "192.168.1.100",
            "port": 22,
            "user": "pi"
        },
        "local_agent_enabled": True,
        "remote_agent_enabled": True
    }
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    logger.info(f"Created default config at {config_path}")

# Routing configuration (reachability/WOL)
routing_config_path = memory_dir / "routing_config.json"
default_routing = {
    "routing": {
        "delegation_threshold": 0.7,
        "wake_on_lan_enabled": True,
        "dev_machine_mac": "A1:B2:C3:D4:E5:F6",
        "dev_machine_ip": "192.168.1.100",
        "dev_machine_port": 22
    }
}
try:
    with open(routing_config_path) as f:
        routing_config = json.load(f)
except FileNotFoundError:
    routing_config = default_routing
    with open(routing_config_path, 'w') as f:
        json.dump(routing_config, f, indent=2)

routing = routing_config.get("routing", {})
DEV_HOST = routing.get("dev_machine_ip", config.get("dev_machine", {}).get("host", "192.168.1.100"))
DEV_PORT = routing.get("dev_machine_port", config.get("dev_machine", {}).get("port", 22))
DEV_USER = config.get("dev_machine", {}).get("user", "pi")
LOCAL_ENABLED = config.get("local_agent_enabled", True)
REMOTE_ENABLED = config.get("remote_agent_enabled", True)
WAKE_ON_LAN_ENABLED = routing.get("wake_on_lan_enabled", True)
DEV_MAC = routing.get("dev_machine_mac", "")

BRIDGE_STATUS = {
    "connected": False,
    "last_ping_time": None,
    "fallback_used": False,
    "failure_count": 0,
    "disabled_until": 0
}


def save_routing_config():
    """Persist routing configuration to disk."""
    routing_config["routing"] = {
        "delegation_threshold": routing.get("delegation_threshold", semantic_scorer.threshold),
        "wake_on_lan_enabled": WAKE_ON_LAN_ENABLED,
        "dev_machine_mac": DEV_MAC,
        "dev_machine_ip": DEV_HOST,
        "dev_machine_port": DEV_PORT
    }
    with open(routing_config_path, 'w') as f:
        json.dump(routing_config, f, indent=2)


def set_wake_on_lan(enabled: bool):
    """Enable or disable Wake-on-LAN attempts."""
    global WAKE_ON_LAN_ENABLED
    WAKE_ON_LAN_ENABLED = bool(enabled)
    save_routing_config()
    return WAKE_ON_LAN_ENABLED


def is_dev_machine_reachable(ip: str, port: int) -> bool:
    """Check if the dev machine is reachable via TCP."""
    try:
        with socket.create_connection((ip, port), timeout=3):
            return True
    except Exception:
        return False


def send_magic_packet(mac_address: str):
    """Send a Wake-on-LAN magic packet."""
    try:
        mac_bytes = bytes.fromhex(mac_address.replace(":", ""))
        packet = b"\xff" * 6 + mac_bytes * 16
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(packet, ("<broadcast>", 9))
    except Exception as e:
        logger.error(f"Failed to send magic packet: {e}")


def attempt_wake_and_retry() -> bool:
    """Attempt to wake the dev machine then re-check reachability."""
    if not DEV_MAC:
        return False
    send_magic_packet(DEV_MAC)
    time.sleep(45)
    return is_dev_machine_reachable(DEV_HOST, DEV_PORT)


def get_bridge_status():
    """Return current bridge status information."""
    last_ping = None
    if BRIDGE_STATUS["last_ping_time"]:
        last_ping = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(BRIDGE_STATUS["last_ping_time"]))
    return {
        "status": "connected" if BRIDGE_STATUS["connected"] else "disconnected",
        "last_ping_time": last_ping,
        "fallback_used": BRIDGE_STATUS["fallback_used"],
        "wake_on_lan_enabled": WAKE_ON_LAN_ENABLED,
        "disabled_until": BRIDGE_STATUS["disabled_until"]
    }


def score_task(task_text):
    """Proxy to the semantic task scorer"""
    return semantic_scorer.score(task_text)


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

    threshold = semantic_scorer.threshold
    score = score_task(task_text)
    reason = f"Task score: {score:.2f} vs threshold: {threshold:.2f}"
    
    # Determine execution location
    if force_local:
        execute_remote = False
        reason = "Forced local execution"
    elif force_remote:
        execute_remote = True
        reason = "Forced remote execution"
    else:
        execute_remote = score >= threshold and REMOTE_ENABLED
        if BRIDGE_STATUS["disabled_until"] > time.time():
            execute_remote = False
            reason = "Remote delegation temporarily disabled"
    
    # Log the decision
    log_event("dispatch_decision", {
        "score": score,
        "threshold": threshold,
        "reason": reason,
        "execute_remote": execute_remote,
        "task_preview": task_text[:100] + "..." if len(task_text) > 100 else task_text
    })

    semantic_scorer.log_result(
        task_text,
        score,
        "dev" if execute_remote else "local"
    )
    
    if execute_remote:
        if is_dev_machine_reachable(DEV_HOST, DEV_PORT):
            BRIDGE_STATUS.update({
                "connected": True,
                "last_ping_time": time.time(),
                "fallback_used": False,
                "failure_count": 0
            })
            return run_remote(task_text)

        BRIDGE_STATUS.update({
            "connected": False,
            "last_ping_time": time.time(),
            "fallback_used": True,
            "failure_count": BRIDGE_STATUS["failure_count"] + 1
        })
        log_event("bridge_unreachable", {"ip": DEV_HOST, "port": DEV_PORT})

        if WAKE_ON_LAN_ENABLED and attempt_wake_and_retry():
            BRIDGE_STATUS.update({
                "connected": True,
                "fallback_used": False,
                "failure_count": 0
            })
            return run_remote(task_text)

        if BRIDGE_STATUS["failure_count"] >= 3:
            BRIDGE_STATUS["disabled_until"] = time.time() + 600
            log_event("bridge_auto_disabled", {"for_seconds": 600})
        log_event("fallback", "Dev machine unreachable, executing locally")
        return run_local(task_text)
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

    reachable = is_dev_machine_reachable(DEV_HOST, DEV_PORT)
    BRIDGE_STATUS.update({
        "connected": reachable,
        "last_ping_time": time.time(),
        "fallback_used": False
    })
    return reachable, "Remote connection successful" if reachable else "Dev machine unreachable"


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
