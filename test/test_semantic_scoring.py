#!/usr/bin/env python3
"""
Test script to evaluate semantic scoring behavior
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from semantic_task_scorer import semantic_scorer

def test_queries():
    """Test various query types to understand scoring behavior"""
    
    test_cases = [
        # Should score HIGH (>= 0.7) - complex queries for dev machine
        "Please provide a comprehensive analysis of the network configuration and troubleshoot any connectivity issues",
        "Analyze the system performance and optimize the database queries for better throughput",
        "Generate a detailed report on security vulnerabilities and implement fixes",
        "Research the best practices for Docker container orchestration and develop a deployment plan",
        "Perform comprehensive network diagnostics and troubleshoot routing issues",
        
        # Should score LOW (< 0.7) - simple queries for local execution  
        "list files",
        "show status",
        "echo hello",
        "help",
        "test connection",
        "simple check"
    ]
    
    print(f"Semantic Scorer Status:")
    print(f"  Enabled: {semantic_scorer.enabled}")
    print(f"  Threshold: {semantic_scorer.threshold}")
    print(f"  Embeddings OK: {semantic_scorer.embed_ok}")
    print()
    
    print("Testing query scoring:")
    print("-" * 80)
    
    for query in test_cases:
        score = semantic_scorer.score(query)
        route_to = "DEV MACHINE" if score >= semantic_scorer.threshold else "LOCAL"
        
        print(f"Score: {score:.3f} | Route: {route_to:11} | Query: {query[:60]}...")
        
        # Breakdown scoring components
        if hasattr(semantic_scorer, '_debug_score'):
            # Add debug scoring if we modify the scorer
            pass
    
    print("-" * 80)

def test_scoring_components():
    """Test individual scoring components"""
    
    test_query = "Please provide a comprehensive analysis of the network configuration and troubleshoot any connectivity issues"
    
    print(f"\nDetailed scoring for: '{test_query}'")
    print("-" * 80)
    
    # Length scoring
    length_norm = min(len(test_query) / 1000, 1.0)
    length_score = 0.3 * length_norm
    print(f"Length: {len(test_query)} chars -> norm: {length_norm:.3f} -> score: {length_score:.3f}")
    
    # Token scoring
    tokens = test_query.split()
    token_norm = min(len(tokens) / 200, 1.0)
    token_score = 0.3 * token_norm
    print(f"Tokens: {len(tokens)} words -> norm: {token_norm:.3f} -> score: {token_score:.3f}")
    
    # Keyword scoring
    text_lower = test_query.lower()
    heavy_keywords = [
        "optimize", "analyze", "summarize", "plan", "research",
        "implement", "generate", "build", "develop", "comprehensive",
        "detailed", "troubleshoot", "diagnostic", "configuration", 
        "investigate", "performance", "security", "vulnerability",
        "orchestration", "deployment", "architecture", "system"
    ]
    light_keywords = ["list", "show", "echo", "simple", "test", "example", "help", "check", "status"]
    
    heavy_found = [k for k in heavy_keywords if k in text_lower]
    light_found = [k for k in light_keywords if k in text_lower]
    
    keyword_score = 0.0
    if heavy_found:
        keyword_score += 0.2
    if light_found:
        keyword_score -= 0.2
        
    print(f"Heavy keywords found: {heavy_found} -> score: +{0.2 if heavy_found else 0}")
    print(f"Light keywords found: {light_found} -> score: {-0.2 if light_found else 0}")
    print(f"Keyword score: {keyword_score:.3f}")
    
    # Embedding scoring
    if semantic_scorer.embed_ok:
        print("Embeddings: Available")
        try:
            emb = semantic_scorer.model.encode([test_query])
            heavy_sim = float(semantic_scorer.util.cos_sim(emb, semantic_scorer.heavy_emb).max())
            light_sim = float(semantic_scorer.util.cos_sim(emb, semantic_scorer.light_emb).max())
            embedding_score = 0.2 * ((heavy_sim - light_sim + 1) / 2)
            print(f"Heavy similarity: {heavy_sim:.3f}")
            print(f"Light similarity: {light_sim:.3f}")
            print(f"Embedding score: {embedding_score:.3f}")
        except Exception as e:
            print(f"Embedding error: {e}")
    else:
        print("Embeddings: Not available")
        
    total_score = semantic_scorer.score(test_query)
    print(f"\nTotal score: {total_score:.3f}")
    print(f"Would route to: {'DEV MACHINE' if total_score >= semantic_scorer.threshold else 'LOCAL'}")

if __name__ == "__main__":
    test_queries()
    test_scoring_components()
