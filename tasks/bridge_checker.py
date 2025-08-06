import subprocess
import time
import socket
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DEV_MAC = os.getenv("DEV_MACHINE_MAC", "98:48:27:C6:51:05")
DEV_IP = os.getenv("DEV_MACHINE_IP", "192.168.1.213")
DEV_USER = os.getenv("DEV_MACHINE_USER", "vincent")
SSH_TIMEOUT = int(os.getenv("SSH_TIMEOUT", "5"))
MAX_RETRIES = int(os.getenv("SSH_MAX_RETRIES", "10"))
RETRY_DELAY = int(os.getenv("SSH_RETRY_DELAY", "15"))

def is_ssh_up(ip):
    try:
        subprocess.run(["ssh", "-o", f"ConnectTimeout={SSH_TIMEOUT}", f"{DEV_USER}@{ip}", "echo ok"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def send_magic_packet(mac):
    print("🔋 Sending magic packet to wake dev machine...")
    subprocess.run(["wakeonlan", mac])

def try_connect_or_wake():
    print(f"🔍 Checking SSH connectivity to {DEV_IP}...")
    if is_ssh_up(DEV_IP):
        print("✅ SSH is already up.")
        return True

    print("❌ SSH not available. Attempting to wake dev machine.")
    send_magic_packet(DEV_MAC)

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"⏳ Retry {attempt}/{MAX_RETRIES}...")
        time.sleep(RETRY_DELAY)
        if is_ssh_up(DEV_IP):
            print("✅ Dev machine is now online.")
            return True

    print("❌ Dev machine did not respond after all retries.")
    return False

if __name__ == "__main__":
    success = try_connect_or_wake()
    if not success:
        # Optional: trigger fallback mode
        print("⚠️  Activating local fallback mode...")
