#!/usr/bin/env python3
"""
Enhanced Container Diagnostic Functions
Addresses the "docker command not found in container" issue and provides comprehensive container diagnostics.
"""

import subprocess
import json
import os
import shutil
from pathlib import Path

def check_docker_environment():
    """
    Comprehensive check of Docker environment and access within the container.
    This addresses the core issue where the agent can't execute Docker commands.
    """
    results = {
        "timestamp": str(subprocess.run(["date"], capture_output=True, text=True).stdout.strip()),
        "environment_checks": {},
        "docker_access": {},
        "socket_access": {},
        "permissions": {},
        "suggestions": []
    }
    
    # 1. Check if docker command exists
    docker_path = shutil.which("docker")
    results["environment_checks"]["docker_command_available"] = {
        "available": docker_path is not None,
        "path": docker_path
    }
    
    if not docker_path:
        results["suggestions"].append({
            "priority": "critical",
            "issue": "Docker CLI not found in container",
            "solution": "Install Docker CLI in container or ensure /usr/local/bin/docker exists"
        })
        return results
    
    # 2. Check Docker socket access
    socket_path = "/var/run/docker.sock"
    socket_exists = os.path.exists(socket_path)
    results["socket_access"]["socket_exists"] = socket_exists
    
    if socket_exists:
        socket_stat = os.stat(socket_path)
        results["socket_access"]["socket_permissions"] = oct(socket_stat.st_mode)[-3:]
        results["socket_access"]["socket_group"] = socket_stat.st_gid
        results["socket_access"]["socket_readable"] = os.access(socket_path, os.R_OK)
        results["socket_access"]["socket_writable"] = os.access(socket_path, os.W_OK)
    else:
        results["suggestions"].append({
            "priority": "critical", 
            "issue": "Docker socket not mounted",
            "solution": "Add volume mount: -v /var/run/docker.sock:/var/run/docker.sock:rw"
        })
    
    # 3. Check user permissions
    try:
        import pwd
        import grp
        current_user = pwd.getpwuid(os.getuid())
        results["permissions"]["current_user"] = current_user.pw_name
        results["permissions"]["current_uid"] = os.getuid()
        results["permissions"]["current_gid"] = os.getgid()
        
        # Check if user is in docker group
        try:
            docker_group = grp.getgrnam("docker")
            user_in_docker_group = current_user.pw_name in docker_group.gr_mem or docker_group.gr_gid == os.getgid()
            results["permissions"]["in_docker_group"] = user_in_docker_group
            
            if not user_in_docker_group:
                results["suggestions"].append({
                    "priority": "high",
                    "issue": "User not in docker group",
                    "solution": "Add user to docker group: usermod -aG docker <username>"
                })
        except KeyError:
            results["permissions"]["docker_group_exists"] = False
            results["suggestions"].append({
                "priority": "medium",
                "issue": "Docker group doesn't exist",
                "solution": "Create docker group: groupadd docker"
            })
            
    except Exception as e:
        results["permissions"]["error"] = str(e)
    
    # 4. Test actual Docker access
    try:
        docker_test = subprocess.run([docker_path, "version"], 
                                   capture_output=True, text=True, timeout=10)
        results["docker_access"]["version_check"] = {
            "success": docker_test.returncode == 0,
            "stdout": docker_test.stdout,
            "stderr": docker_test.stderr,
            "return_code": docker_test.returncode
        }
        
        if docker_test.returncode == 0:
            # Try to list containers
            ps_test = subprocess.run([docker_path, "ps"], 
                                   capture_output=True, text=True, timeout=10)
            results["docker_access"]["container_list"] = {
                "success": ps_test.returncode == 0,
                "stdout": ps_test.stdout,
                "stderr": ps_test.stderr,
                "return_code": ps_test.returncode
            }
        
    except Exception as e:
        results["docker_access"]["test_error"] = str(e)
        results["suggestions"].append({
            "priority": "high",
            "issue": f"Docker command execution failed: {e}",
            "solution": "Check Docker socket permissions and user group membership"
        })
    
    return results

def diagnose_container_access_issue():
    """
    Specific diagnostic for the 'docker command not found in container' issue.
    This function directly addresses the user's reported problem.
    """
    diagnosis = {
        "issue_description": "Docker command not found in container",
        "analysis": {},
        "root_causes": [],
        "solutions": []
    }
    
    # Run comprehensive environment check
    env_check = check_docker_environment()
    diagnosis["analysis"] = env_check
    
    # Analyze specific failure patterns
    if not env_check["environment_checks"]["docker_command_available"]["available"]:
        diagnosis["root_causes"].append({
            "cause": "Docker CLI not installed in container",
            "evidence": "which docker returns null",
            "fix_priority": 1
        })
        diagnosis["solutions"].append({
            "solution": "Install Docker CLI in Dockerfile",
            "implementation": "RUN curl -fsSL https://download.docker.com/linux/static/stable/$(uname -m)/docker-20.10.24.tgz | tar -xzf - --strip-components=1 -C /usr/local/bin docker/docker",
            "priority": "critical"
        })
    
    if not env_check["socket_access"].get("socket_exists", False):
        diagnosis["root_causes"].append({
            "cause": "Docker socket not mounted in container",
            "evidence": "/var/run/docker.sock does not exist",
            "fix_priority": 1
        })
        diagnosis["solutions"].append({
            "solution": "Mount Docker socket in docker-compose.yml",
            "implementation": "volumes: - /var/run/docker.sock:/var/run/docker.sock:rw",
            "priority": "critical"
        })
    
    elif not env_check["socket_access"].get("socket_writable", False):
        diagnosis["root_causes"].append({
            "cause": "Docker socket not writable",
            "evidence": f"Socket permissions: {env_check['socket_access'].get('socket_permissions', 'unknown')}",
            "fix_priority": 2
        })
        diagnosis["solutions"].append({
            "solution": "Fix socket permissions or add user to docker group",
            "implementation": "usermod -aG docker agent && chmod 666 /var/run/docker.sock",
            "priority": "high"
        })
    
    return diagnosis

def get_container_information():
    """
    Provide actual container information when Docker is accessible.
    This replaces generic responses with real data.
    """
    # First check if we can access Docker
    docker_check = check_docker_environment()
    
    if not docker_check["environment_checks"]["docker_command_available"]["available"]:
        return {
            "error": "Docker CLI not available in container",
            "diagnostic": diagnose_container_access_issue()
        }
    
    if not docker_check["socket_access"].get("socket_exists", False):
        return {
            "error": "Docker socket not accessible", 
            "diagnostic": diagnose_container_access_issue()
        }
    
    # If Docker is accessible, get real container information
    container_info = {}
    
    try:
        # Get running containers
        ps_result = subprocess.run(["docker", "ps", "--format", "json"], 
                                 capture_output=True, text=True, timeout=15)
        if ps_result.returncode == 0:
            containers = []
            for line in ps_result.stdout.strip().split('\n'):
                if line:
                    try:
                        containers.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            container_info["running_containers"] = containers
        
        # Get all containers
        ps_all_result = subprocess.run(["docker", "ps", "-a", "--format", "json"], 
                                     capture_output=True, text=True, timeout=15)
        if ps_all_result.returncode == 0:
            all_containers = []
            for line in ps_all_result.stdout.strip().split('\n'):
                if line:
                    try:
                        all_containers.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            container_info["all_containers"] = all_containers
        
        # Get Docker system info
        info_result = subprocess.run(["docker", "system", "info", "--format", "json"], 
                                   capture_output=True, text=True, timeout=15)
        if info_result.returncode == 0:
            try:
                container_info["system_info"] = json.loads(info_result.stdout)
            except json.JSONDecodeError:
                container_info["system_info"] = {"raw": info_result.stdout}
        
        # Get current container ID (if running inside Docker)
        hostname_result = subprocess.run(["hostname"], capture_output=True, text=True)
        if hostname_result.returncode == 0:
            hostname = hostname_result.stdout.strip()
            container_info["current_hostname"] = hostname
            
            # Try to find our own container
            for container in container_info.get("all_containers", []):
                if container.get("Names", "").replace("/", "") == hostname or \
                   container.get("ID", "").startswith(hostname):
                    container_info["current_container"] = container
                    break
        
    except Exception as e:
        container_info["error"] = f"Failed to get container information: {e}"
    
    return container_info

if __name__ == "__main__":
    print("=== Docker Environment Diagnostic ===")
    env_check = check_docker_environment()
    print(json.dumps(env_check, indent=2))
    
    print("\n=== Container Access Issue Diagnosis ===")
    diagnosis = diagnose_container_access_issue()
    print(json.dumps(diagnosis, indent=2))
    
    print("\n=== Container Information ===")
    container_info = get_container_information()
    print(json.dumps(container_info, indent=2))
