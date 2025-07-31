import os
import json
import socket
import platform
from datetime import datetime
import argparse


MEMORY_PATH = "/app/agent_memory/system_facts.json"
LOG_PATH = "/app/logs/isa_trace.jsonl"


def get_hostname():
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def get_uptime():
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
        return int(uptime_seconds)
    except Exception:
        return None


def get_kernel_version():
    try:
        return platform.release()
    except Exception:
        return "unknown"


def get_cpu_arch():
    try:
        return platform.machine()
    except Exception:
        return "unknown"


def detect_container():
    containerized = False
    docker_id = None
    try:
        with open("/proc/self/cgroup", "r") as f:
            for line in f:
                if "docker" in line:
                    containerized = True
                    parts = line.strip().split('/')
                    if parts:
                        docker_id = parts[-1][:12]
                    break
    except Exception:
        pass
    return containerized, docker_id


def detect_virtualization():
    virt = "unknown"
    try:
        with open("/proc/cpuinfo", "r") as f:
            info = f.read().lower()
        if "qemu" in info:
            virt = "qemu"
        elif "hypervisor" in info:
            virt = "yes"
        else:
            virt = "no"
    except Exception:
        pass
    return virt


def get_model_status():
    path = os.environ.get("TINYLLAMA_MODEL_PATH")
    status = {"path": path, "available": False, "size_mb": None}
    if path:
        try:
            if os.path.exists(path) and os.access(path, os.R_OK):
                size_mb = round(os.path.getsize(path) / (1024 * 1024))
                status["available"] = True
                status["size_mb"] = size_mb
        except Exception:
            pass
    return status


def get_agent_version():
    try:
        with open("version.txt", "r") as f:
            return f.read().strip()
    except Exception:
        return "unknown"


def log_event(event: dict) -> None:
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass


def collect_facts() -> dict:
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    facts = {
        "hostname": get_hostname(),
        "uptime": get_uptime(),
        "current_time_utc": now,
        "kernel_version": get_kernel_version(),
        "cpu_architecture": get_cpu_arch(),
    }

    containerized, docker_id = detect_container()
    facts["containerized"] = containerized
    if docker_id:
        facts["docker_id"] = docker_id

    virt = detect_virtualization()
    facts["virtualized"] = virt

    facts["model_status"] = get_model_status()
    facts["agent_version"] = get_agent_version()
    facts["isa_last_run"] = now
    facts["ssh_bridge_status"] = "unknown"

    return facts


def write_memory(facts: dict) -> None:
    try:
        os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
        with open(MEMORY_PATH, "w") as f:
            json.dump(facts, f, indent=2)
    except Exception:
        pass


def main(ping: bool = False) -> None:
    start_event = {"timestamp": datetime.utcnow().isoformat() + "Z", "event": "start"}
    log_event(start_event)
    facts = collect_facts()
    write_memory(facts)
    result_event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": "result",
        "facts": facts,
    }
    log_event(result_event)
    if ping:
        print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ISA collector")
    parser.add_argument("--ping", action="store_true", help="collect and output system facts")
    args = parser.parse_args()
    main(ping=args.ping)
