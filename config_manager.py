#!/usr/bin/env python3
"""
Configuration Sync Module
Allows the dev machine to understand Pi configuration for better task delegation
"""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime

class ConfigurationManager:
    """Manages configuration sync between Pi and dev machine"""
    
    def __init__(self, agent_memory_dir=None):
        self.agent_memory_dir = Path(agent_memory_dir or Path(__file__).parent / "agent_memory")
        self.config_file = self.agent_memory_dir / "pi_config_snapshot.json"
        
    def generate_pi_config_snapshot(self):
        """Generate a configuration snapshot of the Pi system"""
        try:
            config = {
                "timestamp": datetime.now().isoformat(),
                "system_info": self._get_system_info(),
                "container_info": self._get_container_info(),
                "network_info": self._get_network_info(),
                "agent_config": self._get_agent_config(),
                "capabilities": self._get_capabilities()
            }
            
            # Save to agent_memory
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return config
            
        except Exception as e:
            return {"error": f"Failed to generate config snapshot: {e}"}
    
    def _get_system_info(self):
        """Get basic system information"""
        info = {}
        
        try:
            # CPU info
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                if 'Raspberry Pi' in cpuinfo:
                    info['hardware'] = 'Raspberry Pi'
                    if 'BCM2711' in cpuinfo:
                        info['model'] = 'Pi 4'
                    elif 'BCM2837' in cpuinfo:
                        info['model'] = 'Pi 3'
        except:
            pass
        
        try:
            # Memory info
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        info['total_memory_kb'] = int(line.split()[1])
                        break
        except:
            pass
        
        try:
            # Load average
            info['load_average'] = os.getloadavg()[0]
        except:
            pass
        
        return info
    
    def _get_container_info(self):
        """Get container and Docker information"""
        info = {}
        
        try:
            # Check if running in container
            with open('/proc/1/cgroup', 'r') as f:
                if 'docker' in f.read():
                    info['running_in_container'] = True
        except:
            info['running_in_container'] = False
        
        try:
            # Get container environment variables
            env_vars = {}
            for key, value in os.environ.items():
                if key.startswith(('DIAGNOSTIC_', 'AGENT_', 'MODEL_')):
                    env_vars[key] = value
            info['environment'] = env_vars
        except:
            pass
        
        return info
    
    def _get_network_info(self):
        """Get network configuration"""
        info = {}
        
        try:
            # Check network interfaces
            result = subprocess.run(['ip', 'addr', 'show'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                interfaces = []
                for line in result.stdout.split('\n'):
                    if 'inet ' in line and '127.0.0.1' not in line:
                        interfaces.append(line.strip())
                info['interfaces'] = interfaces
        except:
            pass
        
        try:
            # Check if WireGuard is available
            result = subprocess.run(['which', 'wg'], 
                                  capture_output=True, text=True, timeout=2)
            info['wireguard_available'] = result.returncode == 0
        except:
            info['wireguard_available'] = False
        
        return info
    
    def _get_agent_config(self):
        """Get current agent configuration"""
        config = {}
        
        try:
            # Load routing config
            routing_file = self.agent_memory_dir / "routing_config.json"
            if routing_file.exists():
                with open(routing_file, 'r') as f:
                    config['routing'] = json.load(f)
        except:
            pass
        
        try:
            # Load semantic config
            semantic_file = self.agent_memory_dir / "semantic_config.json"
            if semantic_file.exists():
                with open(semantic_file, 'r') as f:
                    config['semantic'] = json.load(f)
        except:
            pass
        
        try:
            # Load static config
            static_file = self.agent_memory_dir / "static_config.json"
            if static_file.exists():
                with open(static_file, 'r') as f:
                    config['static'] = json.load(f)
        except:
            pass
        
        return config
    
    def _get_capabilities(self):
        """Get agent capabilities and available tools"""
        capabilities = []
        
        try:
            # Check if diagnostic tools are available
            tools = ['docker', 'systemctl', 'ps', 'netstat', 'ss', 'iptables']
            for tool in tools:
                result = subprocess.run(['which', tool], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    capabilities.append(tool)
        except:
            pass
        
        try:
            # Check Python packages
            packages = ['sentence_transformers', 'llama_cpp', 'psutil', 'docker']
            available_packages = []
            for package in packages:
                try:
                    __import__(package)
                    available_packages.append(package)
                except ImportError:
                    pass
            capabilities.append(f"python_packages: {available_packages}")
        except:
            pass
        
        return capabilities
    
    def get_config_for_dev_machine(self):
        """Get configuration formatted for dev machine consumption"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                # Add helpful context for dev machine
                context = {
                    "pi_config": config,
                    "context_for_delegation": {
                        "hardware_limitations": self._get_hardware_context(config),
                        "available_tools": config.get("capabilities", []),
                        "routing_preferences": config.get("agent_config", {}).get("routing", {}),
                        "network_setup": config.get("network_info", {})
                    }
                }
                return context
            else:
                return {"error": "No Pi configuration snapshot available"}
        except Exception as e:
            return {"error": f"Failed to load config: {e}"}
    
    def _get_hardware_context(self, config):
        """Generate hardware context for dev machine"""
        context = []
        
        system_info = config.get("system_info", {})
        if system_info.get("hardware") == "Raspberry Pi":
            context.append("Running on Raspberry Pi - prefer lightweight operations")
            
            total_mem = system_info.get("total_memory_kb", 0)
            if total_mem < 2 * 1024 * 1024:  # Less than 2GB
                context.append("Limited memory - avoid memory-intensive tasks")
            elif total_mem < 4 * 1024 * 1024:  # Less than 4GB
                context.append("Moderate memory - be cautious with large datasets")
        
        load_avg = system_info.get("load_average", 0)
        if load_avg > 2.0:
            context.append("High system load - consider deferring CPU-intensive tasks")
        
        return context

# Global instance
config_manager = ConfigurationManager()
