#!/usr/bin/env python3
"""
Dev Machine Performance Optimizer
================================

Provides recommendations for optimizing OpenHermes performance on the dev machine.
Analyzes response times and suggests configuration improvements.
"""

import time
import subprocess
import statistics
from pathlib import Path

def analyze_model_performance():
    """Test OpenHermes performance and provide optimization recommendations"""
    print("🔧 Analyzing OpenHermes Performance on Dev Machine")
    print("=" * 60)
    
    # Test queries of varying complexity
    test_queries = [
        "Hello, test query",
        "What is the current system status?",
        "Please analyze network performance and provide detailed optimization recommendations",
        "Generate a comprehensive security audit report with remediation strategies"
    ]
    
    response_times = []
    
    for i, query in enumerate(test_queries):
        print(f"\nTest {i+1}/4: {query[:50]}...")
        
        start_time = time.time()
        try:
            # Test the dev machine agent directly
            result = subprocess.run([
                "wsl", "python3", "~/diagnostic-agent/dev_machine_agent_optimized.py", query
            ], capture_output=True, text=True, timeout=60)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            response_times.append(response_time)
            
            print(f"  ✅ Response time: {response_time:.0f}ms")
            if response_time > 30000:
                print(f"  ⚠️  SLOW: > 30 seconds")
            elif response_time > 15000:
                print(f"  ⚠️  Moderate: > 15 seconds")
            
        except subprocess.TimeoutExpired:
            print(f"  ❌ TIMEOUT: > 60 seconds")
            response_times.append(60000)
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    
    # Analyze results
    if response_times:
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        
        print(f"\n📊 Performance Analysis:")
        print(f"  Average response time: {avg_time:.0f}ms")
        print(f"  Maximum response time: {max_time:.0f}ms")
        
        recommendations = []
        
        if avg_time > 30000:
            recommendations.extend([
                "🔧 CRITICAL: Reduce n_ctx from 8192 to 4096 or 2048",
                "🔧 CRITICAL: Reduce max_tokens from 768 to 512 or 256",
                "🔧 Consider using Q4_0 instead of Q5_0 quantization",
                "🔧 Reduce n_threads if CPU usage is maxed out"
            ])
        elif avg_time > 15000:
            recommendations.extend([
                "⚡ Reduce n_ctx from 8192 to 4096",
                "⚡ Reduce max_tokens if generating long responses",
                "⚡ Check if model is loading fresh each time (cache issue)"
            ])
        elif avg_time > 5000:
            recommendations.extend([
                "💡 Performance acceptable but could optimize n_ctx",
                "💡 Consider warming up model with a small query first"
            ])
        else:
            recommendations.append("✅ Performance is good!")
        
        # Memory usage recommendations
        recommendations.extend([
            "",
            "💾 Memory Optimization Tips:",
            "  - Use f16_kv=True (already set) ✅",
            "  - Use use_mlock=True (already set) ✅", 
            "  - Monitor WSL memory allocation in .wslconfig",
            "  - Consider increasing swap if needed"
        ])
        
        print(f"\n🎯 Optimization Recommendations:")
        for rec in recommendations:
            print(f"  {rec}")
        
        return avg_time < 20000
    
    return False

def suggest_model_config():
    """Suggest optimized model configuration"""
    print(f"\n⚙️  Suggested OpenHermes Configuration:")
    print("""
For FAST responses (< 10s):
    llm = Llama(
        model_path=model_path,
        n_ctx=2048,          # Reduced from 8192
        n_threads=4,         # Reduced from 6
        n_gpu_layers=0,      # CPU only
        n_batch=256,         # Reduced from 512
        f16_kv=True,
        use_mlock=True,
        verbose=False
    )
    
    response = llm(
        prompt,
        max_tokens=256,      # Reduced from 768
        temperature=0.7,
        top_p=0.9,
        repeat_penalty=1.1,
        stop=["<|im_end|>", "<|im_start|>"],
        echo=False
    )

For BALANCED responses (10-20s):
    n_ctx=4096           # Half of current
    max_tokens=512       # Reduced from 768
    n_batch=384          # Slightly reduced

For DETAILED responses (20-30s):
    # Keep current settings but add warming query
    """)

def main():
    """Run performance analysis and optimization"""
    print("🚀 Dev Machine Performance Analyzer")
    print("=" * 80)
    
    performance_ok = analyze_model_performance()
    suggest_model_config()
    
    print(f"\n" + "=" * 80)
    if performance_ok:
        print("✅ Dev machine performance is acceptable")
        print("   Delegation from Pi should improve overall response times")
    else:
        print("❌ Dev machine performance needs optimization")
        print("   Apply the recommended configuration changes")
        print("   Pi might currently be faster for complex queries")
    
    print(f"\n💡 Next Steps:")
    print(f"  1. Apply configuration changes to dev_machine_agent_optimized.py")
    print(f"  2. Test with: wsl python3 ~/diagnostic-agent/dev_machine_agent_optimized.py 'test'")
    print(f"  3. Monitor via statistics dashboard at http://localhost:5001/stats")
    print(f"  4. Adjust semantic scoring threshold if needed")

if __name__ == "__main__":
    main()
