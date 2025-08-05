import subprocess
import time
import socket
import os

DEV_MAC = "AA:BB:CC:DD:EE:FF"  # Replace with your dev machine's MAC
DEV_IP = "192.168.1.100"        # Replace with your dev machine's static IP
MAX_RETRIES = 10
RETRY_DELAY = 15  # seconds

def is_ssh_up(ip):
    try:
        subprocess.run(["ssh", "-o", "ConnectTimeout=5", f"vincent@{ip}", "echo ok"],
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
