#!/usr/bin/env python3
"""
Test routing decisions without actual execution
"""

import sys
from pathlib import Path

# Add the current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from semantic_task_scorer import semantic_scorer

def test_routing_decisions():
    """Test routing decisions for various queries"""
    print("🔍 Testing Routing Decisions")
    print("=" * 60)
    
    test_queries = [
        # Complex queries that should route to dev machine
        "Please provide a comprehensive analysis of network security vulnerabilities and generate detailed remediation strategies",
        "Analyze system performance bottlenecks across microservices architecture and optimize Docker container orchestration",
        "Research advanced monitoring strategies for Kubernetes deployments and implement sophisticated alerting mechanisms",
        "Develop comprehensive automation scripts for CI/CD pipelines with advanced error handling and rollback capabilities",
        "Generate detailed troubleshooting documentation for complex infrastructure issues including network and storage optimization",
        
        # Simple queries that should stay local
        "list files",
        "show status", 
        "check containers",
        "help",
        "echo hello",
        "test connection",
        "what time is it",
        
        # Medium complexity queries (interesting edge cases)
        "check system performance",
        "troubleshoot network issues",
        "show container logs",
        "restart service",
        "update configuration",
    ]
    
    print(f"Semantic Scorer: Enabled={semantic_scorer.enabled}, Threshold={semantic_scorer.threshold}")
    print(f"Embeddings Available: {semantic_scorer.embed_ok}")
    print()
    
    complex_routed_to_dev = 0
    simple_routed_local = 0
    total_complex = 0
    total_simple = 0
    
    for query in test_queries:
        score = semantic_scorer.score(query)
        will_route_to_dev = score >= semantic_scorer.threshold
        destination = "DEV MACHINE" if will_route_to_dev else "LOCAL"
        
        # Classify query type based on length and keywords
        is_complex = len(query.split()) > 8 or any(word in query.lower() for word in [
            'comprehensive', 'detailed', 'advanced', 'sophisticated', 'analyze', 
            'optimize', 'research', 'implement', 'generate', 'troubleshoot'
        ])
        
        if is_complex:
            total_complex += 1
            if will_route_to_dev:
                complex_routed_to_dev += 1
                status = "✅"
            else:
                status = "⚠️"
        else:
            total_simple += 1
            if not will_route_to_dev:
                simple_routed_local += 1
                status = "✅"
            else:
                status = "⚠️"
        
        complexity = "COMPLEX" if is_complex else "SIMPLE"
        print(f"{status} Score: {score:.3f} | Route: {destination:11} | Type: {complexity:7} | Query: {query[:50]}...")
    
    print()
    print("📊 Routing Analysis:")
    print(f"   Complex queries routed to dev: {complex_routed_to_dev}/{total_complex} ({complex_routed_to_dev/total_complex*100:.1f}%)")
    print(f"   Simple queries kept local: {simple_routed_local}/{total_simple} ({simple_routed_local/total_simple*100:.1f}%)")
    
    overall_accuracy = (complex_routed_to_dev + simple_routed_local) / (total_complex + total_simple)
    print(f"   Overall routing accuracy: {overall_accuracy*100:.1f}%")
    
    if overall_accuracy >= 0.8:
        print("✅ Routing logic appears to be working correctly!")
        return True
    else:
        print("❌ Routing logic needs adjustment")
        return False

def test_threshold_sensitivity():
    """Test how threshold changes affect routing"""
    print("\n🎛️  Testing Threshold Sensitivity")
    print("=" * 60)
    
    test_query = "Analyze system performance and provide comprehensive optimization recommendations"
    
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
    
    score = semantic_scorer.score(test_query)
    print(f"Test Query: {test_query}")
    print(f"Semantic Score: {score:.3f}")
    print()
    
    for threshold in thresholds:
        would_route = score >= threshold
        destination = "DEV MACHINE" if would_route else "LOCAL"
        print(f"Threshold {threshold:.1f}: Route to {destination}")
    
    print(f"\nCurrent threshold: {semantic_scorer.threshold}")
    current_routing = "DEV MACHINE" if score >= semantic_scorer.threshold else "LOCAL"
    print(f"Current routing: {current_routing}")

def main():
    """Run routing decision tests"""
    print("🧪 Testing Pi-to-Dev Routing Decisions")
    print("=" * 80)
    
    routing_test = test_routing_decisions()
    test_threshold_sensitivity()
    
    print("\n" + "=" * 80)
    if routing_test:
        print("✅ Routing decision logic is working correctly!")
        print("   Complex queries will be sent to OpenHermes on dev machine")
        print("   Simple queries will be handled locally on Pi")
        print("\nNext step: Deploy to Pi container to test full pipeline")
    else:
        print("❌ Routing decision logic needs adjustment")
        print("   Review semantic scoring thresholds and keyword weights")
    
    return routing_test

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
