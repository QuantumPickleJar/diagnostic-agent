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