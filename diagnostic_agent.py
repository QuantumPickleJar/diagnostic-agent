#!/usr/bin/env python3
import subprocess
import json
import os
import time
import psutil
import socket
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DiagnosticAgent:
    """Diagnostic agent that performs actual system diagnostics"""
    
    def __init__(self, memory_dir="/app/agent_memory"):
        self.memory_dir = memory_dir
        self.hostname = socket.gethostname()
    
    def execute_diagnostic(self, query):
        """Execute diagnostic task(s) based on the query"""
        timestamp = datetime.now().isoformat()
        query_lower = query.lower()
        
        # Log the query
        self._log_event(f"User query: {query}", "Processing diagnostic request")
        
        try:
            # Container/Docker diagnostics
            if any(word in query_lower for word in ['container', 'docker', 'running']):
                return self._diagnose_containers(query, timestamp)
            
            # Network diagnostics
            elif any(word in query_lower for word in ['network', 'connection', 'ping', 'dns', 'connectivity']):
                return self._diagnose_network(query, timestamp)
            
            # System status
            elif any(word in query_lower for word in ['status', 'health', 'system', 'cpu', 'memory']):
                return self._diagnose_system(query, timestamp)
            
            # Process monitoring
            elif any(word in query_lower for word in ['process', 'service', 'port', 'listen']):
                return self._diagnose_processes(query, timestamp)
            
            # Log analysis
            elif any(word in query_lower for word in ['log', 'error', 'suspicious', 'problem']):
                return self._diagnose_logs(query, timestamp)
            
            # General diagnostic
            else:
                return self._general_diagnostic(query, timestamp)
                
        except Exception as e:
            logger.error(f"Diagnostic execution failed: {e}")
            error_response = f"""[{timestamp}] DIAGNOSTIC ERROR
Query: {query}

Error occurred during diagnostic execution: {str(e)}

Status: Diagnostic failed - please try a more specific query."""
            
            self._log_event(f"Diagnostic error: {query}", error_response)
            return error_response
    
    def _diagnose_containers(self, query, timestamp):
        """Diagnose Docker containers"""
        result = f"""[{timestamp}] CONTAINER DIAGNOSTIC MODE
Query: {query}

"""
        
        try:
            # Check if Docker is available
            docker_result = subprocess.run(['docker', '--version'], 
                                         capture_output=True, text=True, timeout=5)
            
            if docker_result.returncode == 0:
                # List running containers
                ps_result = subprocess.run(['docker', 'ps'], 
                                         capture_output=True, text=True, timeout=10)
                
                if ps_result.returncode == 0:
                    result += "🐳 Docker Containers (Running):\n"
                    lines = ps_result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        for line in lines:
                            result += f"   {line}\n"
                    else:
                        result += "   No running containers found\n"
                
                # List all containers (including stopped)
                all_result = subprocess.run(['docker', 'ps', '-a'], 
                                          capture_output=True, text=True, timeout=10)
                if all_result.returncode == 0:
                    result += "\n🔍 All Containers (including stopped):\n"
                    lines = all_result.stdout.strip().split('\n')
                    for line in lines:
                        result += f"   {line}\n"
            else:
                result += "ERR: Docker not available or not running\n"
                
        except subprocess.TimeoutExpired:
            result += "WARN:  Docker commands timed out\n"
        except FileNotFoundError:
            result += "ERR: Docker command not found\n"
        except Exception as e:
            result += f"ERR: Container diagnostic error: {str(e)}\n"
        
        result += f"\nStatus: Container diagnostic complete."
        self._log_event("Container diagnostic", result)
        return result
    
    def _diagnose_network(self, query, timestamp):
        """Diagnose network connectivity"""
        result = f"""[{timestamp}] NETWORK DIAGNOSTIC MODE
Query: {query}

"""
        
        try:
            # Read connectivity status from ISA scripts
            connectivity_file = os.path.join(self.memory_dir, 'connectivity.json')
            if os.path.exists(connectivity_file):
                with open(connectivity_file, 'r') as f:
                    connectivity_data = json.load(f)
                    result += f"Internet Connectivity: {'✅ UP' if connectivity_data.get('internet_reachable') else 'ERR: DOWN'}\n"
                    result += f"SSH Tunnel: {'OPEN' if connectivity_data.get('ssh_tunnel_open') else 'ERR: CLOSED'}\n"
                    result += f"Last Check: {connectivity_data.get('timestamp', 'Unknown')}\n"
            
            # Check network interfaces
            try:
                interfaces = psutil.net_if_addrs()
                result += "\n🖧 Network Interfaces:\n"
                for interface, addrs in interfaces.items():
                    for addr in addrs:
                        if addr.family == socket.AF_INET:
                            result += f"   {interface}: {addr.address}\n"
            except Exception as e:
                result += f"WARN: Could not read network interfaces: {e}\n"
            
            # Check listening ports
            try:
                connections = psutil.net_connections(kind='inet')
                listening_ports = [conn for conn in connections if conn.status == 'LISTEN']
                result += f"\n🔊 Listening Ports: {len(listening_ports)} active\n"
                for conn in listening_ports[:10]:  # Show first 10
                    result += f"   Port {conn.laddr.port} ({conn.laddr.ip})\n"
            except Exception as e:
                result += f"WARN: Could not read listening ports: {e}\n"
                
        except Exception as e:
            result += f"ERR: Network diagnostic error: {str(e)}\n"
        
        result += "\nRecommendations:\n"
        result += "1. Check cable connections if connectivity is down\n"
        result += "2. Verify firewall settings for blocked ports\n"
        result += "3. Test DNS resolution if internet issues persist\n"
        result += "\nStatus: Network diagnostic complete."
        
        self._log_event("Network diagnostic", result)
        return result
    
    def _diagnose_system(self, query, timestamp):
        """Diagnose system health"""
        result = f"""[{timestamp}] SYSTEM DIAGNOSTIC MODE
Query: {query}

"""
        
        try:
            # Read system facts from ISA scripts
            system_file = os.path.join(self.memory_dir, 'system_facts.json')
            if os.path.exists(system_file):
                with open(system_file, 'r') as f:
                    system_data = json.load(f)
                    result += f"Hostname: {system_data.get('hostname', 'Unknown')}\n"
                    result += f"IP Address: {system_data.get('ip_address', 'Unknown')}\n"
                    
                    memory_info = system_data.get('memory', {})
                    if memory_info:
                        total_gb = memory_info.get('total', 0) / (1024**3)
                        available_gb = memory_info.get('available', 0) / (1024**3)
                        percent = memory_info.get('percent', 0)
                        result += f"💾 Memory: {available_gb:.1f}GB free / {total_gb:.1f}GB total ({percent}% used)\n"
                    
                    result += f"CPU Load (1min): {system_data.get('cpu_load_1min', 'Unknown')}\n"
                    result += f"Last Update: {system_data.get('timestamp', 'Unknown')}\n"
            
            # Get current system stats
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                result += f"\n Current System Status:\n"
                result += f"   CPU Usage: {cpu_percent:.1f}%\n"
                result += f"   Memory Usage: {memory.percent:.1f}%\n"
                result += f"   Disk Usage: {(disk.used/disk.total)*100:.1f}%\n"
                
                # Check for high resource usage
                if cpu_percent > 80:
                    result += "WARN: HIGH CPU USAGE DETECTED\n"
                if memory.percent > 85:
                    result += "WARN: HIGH MEMORY USAGE DETECTED\n"
                if (disk.used/disk.total)*100 > 90:
                    result += "WARN: LOW DISK SPACE WARNING\n"
                    
            except Exception as e:
                result += f"WARN: Could not get current system stats: {e}\n"
                
        except Exception as e:
            result += f"ERR: System diagnostic error: {str(e)}\n"
        
        result += "\nStatus: System diagnostic complete."
        self._log_event("System diagnostic", result)
        return result
    
    def _diagnose_processes(self, query, timestamp):
        """Diagnose running processes"""
        result = f"""[{timestamp}] PROCESS DIAGNOSTIC MODE
Query: {query}

"""
        
        try:
            # Read process status from ISA scripts
            process_file = os.path.join(self.memory_dir, 'process_status.json')
            if os.path.exists(process_file):
                with open(process_file, 'r') as f:
                    process_data = json.load(f)
                    
                    processes = process_data.get('processes', [])
                    ports = process_data.get('ports', [])
                    
                    result += f"🔄 Running Processes: {len(processes)} detected\n"
                    
                    # Show interesting processes (common services and containers)
                    interesting = ['nginx', 'apache', 'docker', 'mysql', 'postgres', 'redis', 'node', 'python']
                    found_interesting = [p for p in processes if any(i in p.lower() for i in interesting)]
                    
                    if found_interesting:
                        result += "🎯 Key Processes Found:\n"
                        for proc in found_interesting[:10]:
                            result += f"   {proc}\n"
                    
                    result += f"\n🔊 Open Ports: {len(ports)}\n"
                    for port in ports[:10]:  # Show first 10
                        result += f"   {port.get('address', '?')}:{port.get('port', '?')}\n"
                    
                    result += f"\n📅 Last Scan: {process_data.get('timestamp', 'Unknown')}\n"
            
            # Get current high-CPU processes
            try:
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        proc.info['cpu_percent'] = proc.cpu_percent()
                        if proc.info['cpu_percent'] > 1.0:  # Show processes using >1% CPU
                            processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                if processes:
                    processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
                    result += "\n🔥 High CPU Processes:\n"
                    for proc in processes[:5]:
                        result += f"   PID {proc['pid']}: {proc['name']} ({proc['cpu_percent']:.1f}% CPU)\n"
                        
            except Exception as e:
                result += f"WARN:  Could not get process details: {e}\n"
                
        except Exception as e:
            result += f"ERR: Process diagnostic error: {str(e)}\n"
        
        result += "\nStatus: Process diagnostic complete."
        self._log_event("Process diagnostic", result)
        return result
    
    def _diagnose_logs(self, query, timestamp):
        """Analyze logs for issues"""
        result = f"""[{timestamp}] LOG ANALYSIS MODE
Query: {query}

"""
        
        try:
            # Check Docker logs if Docker is available and a container name is mentioned
            # Look for container names in the query and try to get their logs
            try:
                # Get list of all containers to see what's available
                ps_result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], 
                                         capture_output=True, text=True, timeout=5)
                if ps_result.returncode == 0:
                    available_containers = ps_result.stdout.strip().split('\n')
                    available_containers = [c for c in available_containers if c]  # Filter empty strings
                    
                    # Check if any container names are mentioned in the query
                    mentioned_containers = [c for c in available_containers if c.lower() in query.lower()]
                    
                    if mentioned_containers:
                        for container_name in mentioned_containers:
                            logs_result = subprocess.run(['docker', 'logs', '--tail', '30', container_name], 
                                                       capture_output=True, text=True, timeout=15)
                            if logs_result.returncode == 0:
                                result += f"📋 {container_name.title()} Container Logs (last 30 lines):\n"
                                log_lines = logs_result.stdout.strip().split('\n')
                                
                                # Look for errors and warnings
                                error_count = 0
                                warning_count = 0
                                for line in log_lines:
                                    if any(word in line.lower() for word in ['error', 'fail', 'exception', 'critical']):
                                        result += f"ERR: {line}\n"
                                        error_count += 1
                                    elif any(word in line.lower() for word in ['warn', 'warning']):
                                        result += f"WARN:  {line}\n"
                                        warning_count += 1
                                
                                if error_count == 0 and warning_count == 0:
                                    result += "✅ No obvious errors or warnings found in recent logs\n"
                                    # Show last few normal lines
                                    result += "\nRecent log entries:\n"
                                    for line in log_lines[-5:]:
                                        result += f"   {line}\n"
                                else:
                                    result += f"\n🚨 Found {error_count} errors and {warning_count} warnings in logs\n"
                                result += "\n"
                            else:
                                result += f"ERR: Could not read {container_name} logs\n"
                    else:
                        result += "💡 No specific container mentioned in query. Try mentioning a container name for targeted log analysis.\n"
                        if available_containers:
                            result += f"Available containers: {', '.join(available_containers)}\n"
            except (subprocess.TimeoutExpired, FileNotFoundError):
                result += "WARN:  Could not access Docker logs\n"
            
            # Check system logs
            try:
                # Look at our own logs
                debug_log = '/app/logs/debug.log'
                if os.path.exists(debug_log):
                    result += "\n📋 Agent Debug Log (last 10 lines):\n"
                    with open(debug_log, 'r') as f:
                        lines = f.readlines()
                        for line in lines[-10:]:
                            if 'ERROR' in line:
                                result += f"ERR: {line.strip()}\n"
                            elif 'WARN' in line:
                                result += f"WARN:  {line.strip()}\n"
                            else:
                                result += f"   {line.strip()}\n"
                                
            except Exception as e:
                result += f"WARN:  Could not read agent logs: {e}\n"
                
        except Exception as e:
            result += f"ERR: Log analysis error: {str(e)}\n"
        
        result += "\nStatus: Log analysis complete."
        self._log_event("Log analysis", result)
        return result
    
    def _general_diagnostic(self, query, timestamp):
        """General diagnostic with actual system checks"""
        result = f"""[{timestamp}] COMPREHENSIVE DIAGNOSTIC MODE
Query: {query}

"""
        
        try:
            # Quick system overview
            result += "🔍 System Overview:\n"
            result += f"   Hostname: {self.hostname}\n"
            
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            result += f"   CPU Usage: {cpu_percent:.1f}%\n"
            result += f"   Memory Usage: {memory.percent:.1f}%\n"
            
            # Disk space
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used/disk.total)*100
            result += f"   Disk Usage: {disk_percent:.1f}%\n"
            
            # Docker status
            try:
                docker_result = subprocess.run(['docker', 'ps', '--quiet'], 
                                             capture_output=True, text=True, timeout=5)
                if docker_result.returncode == 0:
                    container_count = len([l for l in docker_result.stdout.strip().split('\n') if l])
                    result += f" Docker Containers: {container_count} running\n"
                else:
                    result += " Docker: Not available\n"
            except:
                result += " Docker: Not available\n"
            
            # Network connectivity
            connectivity_file = os.path.join(self.memory_dir, 'connectivity.json')
            if os.path.exists(connectivity_file):
                with open(connectivity_file, 'r') as f:
                    conn_data = json.load(f)
                    result += f"   Internet: {'Connected' if conn_data.get('internet_reachable') else 'ERR: Disconnected'}\n"
            
            # System alerts
            alerts = []
            if cpu_percent > 80:
                alerts.append("High CPU usage")
            if memory.percent > 85:
                alerts.append("High memory usage")
            if disk_percent > 90:
                alerts.append("Low disk space")
            
            if alerts:
                result += f"\n System Alerts:\n"
                for alert in alerts:
                    result += f"WARN:  {alert}\n"
            else:
                result += "\nNo system alerts\n"
                
        except Exception as e:
            result += f"ERR: General diagnostic error: {str(e)}\n"
        
        result += f"\nStatus: Comprehensive diagnostic complete."
        result += f"\nFor specific diagnostics, try: 'network status', 'container logs', 'system health'"
        
        self._log_event("General diagnostic", result)
        return result
    
    def _log_event(self, task, result):
        """Log diagnostic events"""
        try:
            from memory import log_event
            log_event(task, result)
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
    
# Global instance
diagnostic_agent = DiagnosticAgent()

def execute_diagnostic(question):
    """Execute diagnostic task"""
    return diagnostic_agent.execute_diagnostic(question)
