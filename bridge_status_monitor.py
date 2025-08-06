#!/usr/bin/env python3
"""
Bridge Status Monitor
Integrates with autonomic dispatcher to provide SSH bridge monitoring
"""

import subprocess
import time
import socket
import os
import json
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class BridgeStatusMonitor:
    def __init__(self, memory_dir="agent_memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self.config_file = self.memory_dir / "routing_config.json"
        self.status_file = self.memory_dir / "bridge_status.json"
        
        # Configuration from environment variables with fallbacks
        self.config = {
            "dev_machine_mac": os.getenv("DEV_MACHINE_MAC", "98:48:27:C6:51:05"),
            "dev_machine_ip": os.getenv("DEV_MACHINE_IP", "192.168.1.213"),
            "dev_machine_port": int(os.getenv("DEV_MACHINE_PORT", "22")),
            "dev_machine_user": os.getenv("DEV_MACHINE_USER", "vincent"),
            "check_interval": int(os.getenv("BRIDGE_CHECK_INTERVAL", "300")),
            "wake_retries": int(os.getenv("SSH_MAX_RETRIES", "3")),
            "retry_delay": int(os.getenv("SSH_RETRY_DELAY", "15")),
            "ssh_timeout": int(os.getenv("SSH_TIMEOUT", "5"))
        }
        
        # Load any additional config from routing_config.json (legacy support)
        self.load_config()
        self.status = {
            "connected": False,
            "last_check": None,
            "last_successful_connection": None,
            "wake_attempts": 0,
            "errors": [],
            "uptime_percentage": 0.0
        }
        
        self.running = False
        self.monitor_thread = None
        
    def load_config(self):
        """Load additional configuration from routing_config.json (legacy support)"""
        try:
            if self.config_file.exists():
                with open(self.config_file) as f:
                    routing_config = json.load(f)
                    
                # Extract bridge-specific config and merge with env vars (env vars take precedence)
                routing = routing_config.get("routing", {})
                legacy_config = {
                    "dev_machine_mac": routing.get("dev_machine_mac", self.config["dev_machine_mac"]),
                    "dev_machine_ip": routing.get("dev_machine_ip", self.config["dev_machine_ip"]),
                    "dev_machine_port": routing.get("dev_machine_port", self.config["dev_machine_port"])
                }
                
                # Only update if env vars weren't set (preserving environment variable precedence)
                for key, value in legacy_config.items():
                    if key in self.config and self.config[key] in [
                        "98:48:27:C6:51:05", "192.168.1.213", 22, "vincent"  # Default values
                    ]:
                        self.config[key] = value
                        
                logger.info("Bridge monitor config merged from routing_config.json")
        except Exception as e:
            logger.warning(f"Could not load routing config: {e}")
            
    def is_ssh_reachable(self, ip=None, port=None, user=None, timeout=None):
        """Test SSH connectivity using configured values"""
        ip = ip or self.config["dev_machine_ip"]
        port = port or self.config["dev_machine_port"]
        user = user or self.config["dev_machine_user"]
        timeout = timeout or self.config["ssh_timeout"]
        try:
            if user:
                cmd = ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", f"{user}@{ip}", "echo", "ok"]
            else:
                # Just test port connectivity
                with socket.create_connection((ip, port), timeout=timeout):
                    return True
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"SSH check failed: {e}")
            return False
    
    def send_wake_on_lan(self, mac_address):
        """Send Wake-on-LAN magic packet"""
        try:
            # Try using wakeonlan command first
            result = subprocess.run(["wakeonlan", mac_address], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"WOL packet sent via wakeonlan to {mac_address}")
                return True
                
            # Fallback to manual packet creation
            mac_bytes = bytes.fromhex(mac_address.replace(":", ""))
            packet = b"\xff" * 6 + mac_bytes * 16
            
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.sendto(packet, ("<broadcast>", 9))
                logger.info(f"WOL packet sent manually to {mac_address}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send WOL packet: {e}")
            return False
    
    def attempt_wake_and_connect(self):
        """Attempt to wake the dev machine and verify connection"""
        ip = self.config["dev_machine_ip"]
        port = self.config["dev_machine_port"]
        mac = self.config["dev_machine_mac"]
        user = self.config["dev_machine_user"]
        
        # Check if already connected
        if self.is_ssh_reachable(ip, port, user):
            return True
            
        logger.info("SSH bridge down, attempting to wake dev machine...")
        
        # Send WOL packet
        if not self.send_wake_on_lan(mac):
            return False
            
        # Wait and retry connection
        for attempt in range(self.config["wake_retries"]):
            logger.info(f"Wake attempt {attempt + 1}/{self.config['wake_retries']}, waiting {self.config['retry_delay']}s...")
            time.sleep(self.config["retry_delay"])
            
            if self.is_ssh_reachable(ip, port, user):
                logger.info("✅ Dev machine is now online!")
                return True
                
        logger.warning("❌ Dev machine did not respond after all wake attempts")
        return False
    
    def check_bridge_status(self):
        """Perform a single bridge status check"""
        now = datetime.now()
        
        try:
            connected = self.attempt_wake_and_connect()
            
            # Update status
            self.status.update({
                "connected": connected,
                "last_check": now.isoformat(),
                "errors": self.status["errors"][-10:]  # Keep last 10 errors
            })
            
            if connected:
                self.status["last_successful_connection"] = now.isoformat()
                self.status["wake_attempts"] = 0
            else:
                self.status["wake_attempts"] += 1
                error_msg = f"Bridge check failed at {now.isoformat()}"
                self.status["errors"].append(error_msg)
                
            # Calculate uptime percentage (last 24 hours)
            self.calculate_uptime_percentage()
            
            # Save status to file
            self.save_status()
            
            return connected
            
        except Exception as e:
            logger.error(f"Bridge status check error: {e}")
            self.status["errors"].append(f"Check error at {now.isoformat()}: {str(e)}")
            return False
    
    def calculate_uptime_percentage(self):
        """Calculate uptime percentage based on recent checks"""
        # Simple implementation - can be enhanced with historical data
        if self.status["connected"]:
            # If currently connected, assume good uptime
            self.status["uptime_percentage"] = max(self.status.get("uptime_percentage", 0), 80.0)
        else:
            # Reduce uptime percentage
            current = self.status.get("uptime_percentage", 100.0)
            self.status["uptime_percentage"] = max(current - 5.0, 0.0)
    
    def save_status(self):
        """Save current status to file"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.status, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save bridge status: {e}")
    
    def load_status(self):
        """Load status from file"""
        try:
            if self.status_file.exists():
                with open(self.status_file) as f:
                    saved_status = json.load(f)
                    self.status.update(saved_status)
        except Exception as e:
            logger.warning(f"Could not load bridge status: {e}")
    
    def get_status_summary(self):
        """Get current status summary for API"""
        return {
            "bridge_connected": self.status["connected"],
            "last_check": self.status["last_check"],
            "last_successful_connection": self.status["last_successful_connection"],
            "uptime_percentage": self.status["uptime_percentage"],
            "wake_attempts": self.status["wake_attempts"],
            "error_count": len(self.status["errors"]),
            "monitoring_active": self.running
        }
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Bridge status monitor started")
        
        while self.running:
            try:
                self.check_bridge_status()
                time.sleep(self.config["check_interval"])
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(60)  # Wait a minute before retry
                
        logger.info("Bridge status monitor stopped")
    
    def start_monitoring(self):
        """Start the background monitoring thread"""
        if self.running:
            return False
            
        self.load_status()
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Bridge status monitoring started")
        return True
    
    def stop_monitoring(self):
        """Stop the background monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Bridge status monitoring stopped")
    
    def force_check_now(self):
        """Force an immediate bridge status check"""
        return self.check_bridge_status()


# Global instance
bridge_monitor = BridgeStatusMonitor()

def start_bridge_monitoring():
    """Start bridge monitoring - called from web_agent.py"""
    return bridge_monitor.start_monitoring()

def stop_bridge_monitoring():
    """Stop bridge monitoring"""
    bridge_monitor.stop_monitoring()

def get_bridge_status():
    """Get current bridge status - API endpoint"""
    return bridge_monitor.get_status_summary()

def force_bridge_check():
    """Force immediate bridge check - API endpoint"""
    return bridge_monitor.force_check_now()
