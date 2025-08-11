#!/usr/bin/env python3
"""
Test semantic scoring on the Pi
"""

from semantic_task_scorer import semantic_scorer

print(f"Semantic Scorer Status:")
print(f"  Enabled: {semantic_scorer.enabled}")
print(f"  Threshold: {semantic_scorer.threshold}")
print(f"  Embeddings OK: {semantic_scorer.embed_ok}")
print()

# Test embeddings availability
try:
    import sentence_transformers
    print("sentence-transformers: Available")
except ImportError:
    print("sentence-transformers: NOT AVAILABLE")

print()

test_queries = [
    "Please provide a comprehensive analysis of the network configuration and troubleshoot any connectivity issues",
    "Analyze the system performance and optimize the database queries for better throughput", 
    "Generate a detailed security audit report with recommendations",
    "Research Docker orchestration best practices and implement them",
    "list files",
    "show status",
    "echo hello",
    "help"
]

print("Testing query scoring:")
print("-" * 80)

for query in test_queries:
    score = semantic_scorer.score(query)
    route = "DEV MACHINE" if score >= semantic_scorer.threshold else "LOCAL"
    print(f"Score: {score:.3f} | Route: {route:11} | Query: {query[:50]}...")

print("-" * 80)
