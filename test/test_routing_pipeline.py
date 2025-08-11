#!/usr/bin/env python3
"""
Comprehensive Pi-to-Dev routing test script
"""

import sys
import time
import subprocess
from pathlib import Path

# Add the current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from semantic_task_scorer import semantic_scorer
from autonomic_dispatcher import dispatch_task, test_connectivity, get_dispatch_stats

def test_semantic_scoring():
    """Test semantic scoring with various query types"""
    print("🔍 Testing Semantic Scoring")
    print("=" * 60)
    
    test_cases = [
        # HIGH complexity - should route to dev machine (score >= 0.7)
        ("Please provide a comprehensive analysis of network security vulnerabilities", True),
        ("Analyze system performance bottlenecks and optimize Docker container orchestration", True),
        ("Generate detailed troubleshooting recommendations for complex infrastructure issues", True),
        ("Research and implement advanced monitoring strategies for microservices", True),
        ("Develop sophisticated automation scripts for deployment pipelines", True),
        
        # MEDIUM complexity - borderline cases
        ("Check system performance and memory usage", False),
        ("Troubleshoot network connectivity problems", False),
        ("Show container status and logs", False),
        
        # LOW complexity - should stay local (score < 0.7)
        ("list files", False),
        ("show status", False),
        ("echo hello", False),
        ("help me", False),
        ("test connection", False),
    ]
    
    print(f"Scorer Config: Enabled={semantic_scorer.enabled}, Threshold={semantic_scorer.threshold}")
    print(f"Embeddings Available: {semantic_scorer.embed_ok}")
    print()
    
    correct_predictions = 0
    total_tests = len(test_cases)
    
    for query, expected_route_to_dev in test_cases:
        score = semantic_scorer.score(query)
        actual_route_to_dev = score >= semantic_scorer.threshold
        
        status = "✅" if actual_route_to_dev == expected_route_to_dev else "❌"
        destination = "DEV" if actual_route_to_dev else "LOCAL"
        expected_dest = "DEV" if expected_route_to_dev else "LOCAL"
        
        print(f"{status} Score: {score:.3f} | Route: {destination:5} | Expected: {expected_dest:5} | Query: {query[:50]}...")
        
        if actual_route_to_dev == expected_route_to_dev:
            correct_predictions += 1
    
    accuracy = (correct_predictions / total_tests) * 100
    print()
    print(f"📊 Scoring Accuracy: {correct_predictions}/{total_tests} ({accuracy:.1f}%)")
    return accuracy >= 80  # 80% accuracy threshold

def test_connectivity():
    """Test SSH connectivity to dev machine"""
    print("\n🌐 Testing Dev Machine Connectivity")
    print("=" * 60)
    
    success, message = test_connectivity()
    print(f"SSH Connectivity: {'✅ PASS' if success else '❌ FAIL'}")
    print(f"Message: {message}")
    
    return success

def test_dev_machine_agent():
    """Test dev machine agent directly"""
    print("\n🤖 Testing Dev Machine Agent")
    print("=" * 60)
    
    test_query = "Analyze this routing test and confirm OpenHermes is working correctly"
    
    try:
        cmd = [
            'wsl', 'python3', '~/diagnostic-agent/dev_machine_agent_optimized.py', 
            test_query
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            response = result.stdout.strip()
            print(f"✅ Dev Machine Response ({len(response)} chars):")
            print(f"   {response[:200]}...")
            return True
        else:
            print(f"❌ Dev Machine Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Dev machine agent timed out")
        return False
    except Exception as e:
        print(f"❌ Dev machine test failed: {e}")
        return False

def test_full_routing_pipeline():
    """Test complete routing from semantic scoring to execution"""
    print("\n🚀 Testing Full Routing Pipeline")
    print("=" * 60)
    
    test_queries = [
        # Should route to dev machine
        ("Provide comprehensive analysis of Docker orchestration best practices", True),
        
        # Should stay local  
        ("show system status", False),
    ]
    
    results = []
    
    for query, should_route_to_dev in test_queries:
        print(f"\n📤 Testing: {query}")
        
        # Check semantic score
        score = semantic_scorer.score(query)
        will_route = score >= semantic_scorer.threshold
        
        print(f"   Semantic Score: {score:.3f}")
        print(f"   Will Route To: {'DEV' if will_route else 'LOCAL'}")
        print(f"   Expected: {'DEV' if should_route_to_dev else 'LOCAL'}")
        
        # Test actual dispatch (this will execute the query)
        try:
            start_time = time.time()
            response = dispatch_task(query)
            execution_time = time.time() - start_time
            
            executed_on_dev = response.startswith("[REMOTE]")
            executed_locally = response.startswith("[LOCAL]")
            
            print(f"   Execution Time: {execution_time:.2f}s")
            print(f"   Executed On: {'DEV' if executed_on_dev else 'LOCAL' if executed_locally else 'UNKNOWN'}")
            print(f"   Response Length: {len(response)} chars")
            
            # Check if routing worked as expected
            if should_route_to_dev and executed_on_dev:
                print("   ✅ Correctly routed to dev machine")
                results.append(True)
            elif not should_route_to_dev and executed_locally:
                print("   ✅ Correctly executed locally")
                results.append(True)
            else:
                print("   ❌ Incorrect routing")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ Dispatch failed: {e}")
            results.append(False)
    
    success_rate = sum(results) / len(results) if results else 0
    print(f"\n📊 Pipeline Success Rate: {sum(results)}/{len(results)} ({success_rate*100:.1f}%)")
    
    return success_rate >= 0.8

def test_dispatch_stats():
    """Show dispatch statistics"""
    print("\n📊 Dispatch Statistics")
    print("=" * 60)
    
    stats = get_dispatch_stats()
    
    if "error" in stats:
        print(f"❌ Error getting stats: {stats['error']}")
        return False
    
    print(f"Total Dispatches: {stats.get('total', 0)}")
    print(f"Local Executions: {stats.get('local', 0)}")
    print(f"Remote Executions: {stats.get('remote', 0)}")
    print(f"Errors: {stats.get('errors', 0)}")
    
    if stats.get('total', 0) > 0:
        remote_ratio = stats.get('remote', 0) / stats['total']
        print(f"Remote Routing Rate: {remote_ratio*100:.1f}%")
    
    return True

def main():
    """Run comprehensive routing tests"""
    print("🧪 Comprehensive Pi-to-Dev Routing Tests")
    print("=" * 80)
    
    test_results = {
        "Semantic Scoring": test_semantic_scoring(),
        "Dev Machine Agent": test_dev_machine_agent(),
        "Dispatch Statistics": test_dispatch_stats(),
        "Full Pipeline": test_full_routing_pipeline(),
    }
    
    print("\n" + "=" * 80)
    print("📋 Test Results Summary")
    print("=" * 80)
    
    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(test_results.values())
    overall = "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"
    
    print(f"\nOverall: {overall}")
    
    if all_passed:
        print("\n🎉 Pi-to-Dev routing pipeline is working correctly!")
        print("   Complex queries will be routed to OpenHermes on dev machine")
        print("   Simple queries will be handled locally on Pi")
    else:
        print("\n🔧 Issues detected in routing pipeline")
        print("   Check failed tests above for troubleshooting")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
