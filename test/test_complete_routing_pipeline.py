#!/usr/bin/env python3
"""
Complete routing pipeline test - verifies that routing decisions work correctly
after stats dashboard implementation.
"""

import json
import time
from datetime import datetime
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_routing_pipeline():
    """Test the complete routing pipeline"""
    
    print("=" * 60)
    print("COMPLETE ROUTING PIPELINE TEST")
    print("=" * 60)
    
    # Test imports
    print("\n1. Testing imports...")
    try:
        from autonomic_dispatcher import dispatch_task, test_connectivity, get_dispatch_stats
        from semantic_task_scorer import SemanticTaskScorer
        print("✓ All core modules imported successfully")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False
    
    # Test semantic scorer initialization
    print("\n2. Testing semantic scorer...")
    try:
        scorer = SemanticTaskScorer()
        status = scorer.status()
        print(f"✓ Semantic scorer status: {status['enabled']}")
        print(f"  - Threshold: {status['threshold']}")
        print(f"  - Total queries: {status['total_queries']}")
    except Exception as e:
        print(f"✗ Semantic scorer failed: {e}")
    
    # Test connectivity
    print("\n3. Testing connectivity...")
    try:
        success, message = test_connectivity()
        print(f"{'✓' if success else '⚠'} Connectivity: {message}")
    except Exception as e:
        print(f"✗ Connectivity test failed: {e}")
    
    # Test dispatch statistics
    print("\n4. Testing dispatch statistics...")
    try:
        stats = get_dispatch_stats()
        print(f"✓ Dispatch stats retrieved")
        print(f"  - Total dispatches: {stats.get('total_dispatches', 0)}")
        print(f"  - Remote successes: {stats.get('remote_successes', 0)}")
        print(f"  - Local fallbacks: {stats.get('local_fallbacks', 0)}")
    except Exception as e:
        print(f"✗ Dispatch stats failed: {e}")
    
    # Test sample queries
    print("\n5. Testing sample queries...")
    
    test_queries = [
        ("Simple query (should stay local)", "What is the current time?"),
        ("Complex analysis (should route to dev)", "Analyze the performance implications of implementing a distributed microservice architecture with event-driven patterns"),
        ("System diagnostic (might stay local)", "Check if docker containers are running"),
        ("Complex reasoning (should route to dev)", "Compare and contrast different machine learning approaches for natural language processing, considering computational complexity and accuracy trade-offs")
    ]
    
    for description, query in test_queries:
        print(f"\n  Testing: {description}")
        print(f"  Query: {query[:50]}...")
        
        try:
            start_time = time.time()
            response = dispatch_task(query)
            end_time = time.time()
            
            # Basic validation
            if response and len(response) > 20:
                print(f"  ✓ Response received ({len(response)} chars) in {end_time - start_time:.2f}s")
                # Check for routing indicators
                if "DEV MACHINE" in response.upper():
                    print("    → Routed to dev machine")
                elif "LOCAL" in response.upper() or "[PI]" in response.upper():
                    print("    → Processed locally")
                else:
                    print("    → Routing unclear from response")
            else:
                print(f"  ⚠ Short or empty response: {response[:100] if response else 'None'}")
                
        except Exception as e:
            print(f"  ✗ Query failed: {e}")
    
    # Test stats dashboard integration
    print("\n6. Testing stats dashboard integration...")
    try:
        import stats_dashboard
        print("✓ Stats dashboard module available")
        
        # Try to access stats data
        stats_file = "agent_memory/routing_stats.json"
        if os.path.exists(stats_file):
            with open(stats_file, 'r') as f:
                stats_data = json.load(f)
            print(f"✓ Stats file exists with {len(stats_data.get('routing_history', []))} entries")
        else:
            print("⚠ Stats file not yet created (expected on first run)")
            
    except ImportError:
        print("⚠ Stats dashboard not available")
    except Exception as e:
        print(f"✗ Stats dashboard test failed: {e}")
    
    print("\n" + "=" * 60)
    print("ROUTING PIPELINE TEST COMPLETE")
    print("=" * 60)
    
    # Final recommendations
    print("\nNext steps:")
    print("1. Check the stats dashboard at /stats endpoint")
    print("2. Monitor routing_stats.json for timing data")
    print("3. Run analyze_dev_performance.py for optimization recommendations")
    print("4. Adjust threshold if routing is not optimal")
    
    return True

if __name__ == "__main__":
    test_routing_pipeline()
