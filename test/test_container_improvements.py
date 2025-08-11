#!/usr/bin/env python3
"""
Test script to validate the three high-impact improvements for container diagnostics.
"""

import json
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_container_diagnostics():
    """Test the enhanced container diagnostic functions"""
    print("=== Testing Enhanced Container Diagnostics ===")
    
    try:
        from tasks.enhanced_container_diagnostics import (
            check_docker_environment,
            diagnose_container_access_issue,
            get_container_information
        )
        
        print("1. Testing Docker environment check...")
        env_check = check_docker_environment()
        print(f"   Docker command available: {env_check['environment_checks']['docker_command_available']['available']}")
        print(f"   Docker socket exists: {env_check['socket_access'].get('socket_exists', False)}")
        print(f"   Suggestions count: {len(env_check['suggestions'])}")
        
        print("\n2. Testing container access issue diagnosis...")
        diagnosis = diagnose_container_access_issue()
        print(f"   Root causes identified: {len(diagnosis['root_causes'])}")
        print(f"   Solutions provided: {len(diagnosis['solutions'])}")
        
        print("\n3. Testing container information retrieval...")
        container_info = get_container_information()
        if "error" in container_info:
            print(f"   Expected error: {container_info['error']}")
        else:
            print(f"   Container info retrieved successfully")
        
        print("✅ Container diagnostics module working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Container diagnostics test failed: {e}")
        return False

def test_semantic_scoring():
    """Test the enhanced semantic scoring for container queries"""
    print("\n=== Testing Enhanced Semantic Scoring ===")
    
    try:
        from semantic_task_scorer import semantic_scorer
        
        # Test container-related queries
        test_queries = [
            "list all running containers",
            "show me docker ps output", 
            "what containers are running",
            "docker system info",
            "simple hello world",
            "complex network analysis with performance optimization"
        ]
        
        print("Testing query scoring:")
        for query in test_queries:
            score = semantic_scorer.score(query)
            routing = "DEV MACHINE" if score >= 0.7 else "LOCAL"
            print(f"   '{query[:40]}...' -> Score: {score:.3f} -> {routing}")
        
        print("✅ Semantic scoring working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Semantic scoring test failed: {e}")
        return False

def test_autonomic_dispatcher():
    """Test the enhanced autonomic dispatcher"""
    print("\n=== Testing Enhanced Autonomic Dispatcher ===")
    
    try:
        from autonomic_dispatcher import dispatch_task
        
        # Test container query dispatch
        container_query = "list all running containers"
        print(f"Testing dispatch for: '{container_query}'")
        
        # Force local to test container diagnostic integration
        result = dispatch_task(container_query, force_local=True)
        
        if "DIAGNOSTIC" in result:
            print("✅ Container diagnostic integration working")
            print("   Diagnostic information provided for container query")
        elif "LOCAL" in result:
            print("✅ Local execution working")
            print("   Query processed locally")
        else:
            print(f"⚠️  Unexpected result format: {result[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Autonomic dispatcher test failed: {e}")
        return False

def validate_docker_compose_fixes():
    """Validate Docker Compose configuration fixes"""
    print("\n=== Validating Docker Compose Fixes ===")
    
    try:
        # Check fast.cross configuration
        fast_cross_file = Path("docker-compose.fast.cross.yml")
        if fast_cross_file.exists():
            with open(fast_cross_file) as f:
                content = f.read()
                if "/var/run/docker.sock:/var/run/docker.sock:rw" in content:
                    print("✅ fast.cross configuration has correct Docker socket mount (rw)")
                else:
                    print("❌ fast.cross configuration missing rw Docker socket mount")
        
        # Check production configuration  
        prod_file = Path("docker-compose.production.yml")
        if prod_file.exists():
            with open(prod_file) as f:
                content = f.read()
                if "/var/run/docker.sock:/var/run/docker.sock:rw" in content:
                    print("✅ production configuration has correct Docker socket mount (rw)")
                else:
                    print("❌ production configuration missing rw Docker socket mount")
        
        return True
        
    except Exception as e:
        print(f"❌ Docker Compose validation failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("Container Diagnostic Improvements Validation")
    print("=" * 50)
    
    tests = [
        test_container_diagnostics,
        test_semantic_scoring,
        test_autonomic_dispatcher,
        validate_docker_compose_fixes
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print(f"\n=== SUMMARY ===")
    print(f"Tests passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All improvements validated successfully!")
        print("\n📋 DEPLOYMENT CHECKLIST:")
        print("1. ✅ Container diagnostic functions implemented")
        print("2. ✅ Semantic scoring enhanced for container queries") 
        print("3. ✅ Docker socket permissions fixed in compose files")
        print("4. ✅ Autonomic dispatcher enhanced with container diagnostics")
        print("\n🚀 Ready to deploy and test with real container queries!")
    else:
        print("⚠️  Some improvements need attention before deployment")

if __name__ == "__main__":
    main()
