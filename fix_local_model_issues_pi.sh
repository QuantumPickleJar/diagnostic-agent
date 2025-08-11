#!/bin/bash
#
# Fix Local Model Issues on Pi
# Run this script inside the diagnostic-agent container
#

set -e

echo "🔧 Fixing Local Model Issues"
echo "============================"

# Function to check if we're in the container
check_container() {
    if [ ! -f "/app/diagnostic_agent.py" ] && [ ! -f "/app/web_agent.py" ]; then
        echo "❌ This script should be run inside the diagnostic-agent container"
        echo "   Run: docker exec diagnostic-journalist bash ./fix_local_model_issues_pi.sh"
        exit 1
    fi
}

# Function to fix sentence transformers
fix_sentence_transformers() {
    echo ""
    echo "🔧 Fixing SentenceTransformers model..."
    
    # Remove any corrupted model directories
    echo "Removing corrupted models..."
    rm -rf /app/models/all-MiniLM-L6-v2 2>/dev/null || true
    rm -rf /home/agent/.cache/sentence_transformers 2>/dev/null || true
    rm -rf ~/.cache/sentence_transformers 2>/dev/null || true
    
    # Download fresh model
    echo "📥 Downloading fresh SentenceTransformers model..."
    python3 -c "
import os
from sentence_transformers import SentenceTransformer

print('Downloading sentence-transformers/all-MiniLM-L6-v2...')
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

print('Testing model...')
test_embeddings = model.encode(['Hello world', 'Test sentence'])
print(f'✅ Model working! Shape: {test_embeddings.shape}')
print(f'📁 Model cached successfully')
"
    
    if [ $? -eq 0 ]; then
        echo "✅ SentenceTransformers model fixed"
    else
        echo "❌ SentenceTransformers fix failed"
        return 1
    fi
}

# Function to test semantic scoring
test_semantic_scoring() {
    echo ""
    echo "🧪 Testing semantic scoring..."
    
    python3 -c "
import sys
sys.path.insert(0, '/app')

from semantic_task_scorer import semantic_scorer

print(f'Semantic Scorer Status:')
print(f'  Enabled: {semantic_scorer.enabled}')
print(f'  Threshold: {semantic_scorer.threshold}')  
print(f'  Embeddings OK: {semantic_scorer.embed_ok}')

if semantic_scorer.embed_ok:
    test_query = 'Please provide a comprehensive analysis of the system'
    score = semantic_scorer.score(test_query)
    print(f'  Test score: {score:.3f}')
    print('✅ Semantic scoring working')
else:
    print('❌ Semantic scoring not working')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        echo "✅ Semantic scoring test passed"
    else
        echo "❌ Semantic scoring test failed"
        return 1
    fi
}

# Function to test local model execution
test_local_execution() {
    echo ""
    echo "🧪 Testing local execution..."
    
    python3 -c "
import sys
import time
sys.path.insert(0, '/app')

print('Testing local query processing...')
start_time = time.time()

try:
    from autonomic_dispatcher import run_local
    
    test_query = 'Show system status and memory usage'
    result = run_local(test_query)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f'✅ Local execution completed in {duration:.2f} seconds')
    print(f'Response preview: {str(result)[:150]}...')
    
    if duration < 10:
        print('🚀 Response time is excellent (< 10 seconds)')
    elif duration < 20:
        print('⚠️  Response time is acceptable (10-20 seconds)')
    else:
        print('🐌 Response time is slow (> 20 seconds) - consider optimization')
    
    # Check if response contains error
    if 'ERROR' in str(result) or 'signal only works in main thread' in str(result):
        print('❌ Execution has errors')
        sys.exit(1)
    else:
        print('✅ Execution successful')
        
except Exception as e:
    print(f'❌ Local execution test failed: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        echo "✅ Local execution test passed"
    else
        echo "❌ Local execution test failed"
        return 1
    fi
}

# Function to check TinyLlama model
check_tinyllama() {
    echo ""
    echo "🔍 Checking TinyLlama model..."
    
    if [ -f "/app/models/tinyllama.gguf" ]; then
        size=$(du -h /app/models/tinyllama.gguf | cut -f1)
        echo "✅ TinyLlama model found: $size"
    else
        echo "⚠️  TinyLlama model not found at /app/models/tinyllama.gguf"
        echo "   This is optional - the agent can work without it"
        echo "   To add TinyLlama: place tinyllama.gguf in the ./models directory on host"
    fi
}

# Function to show final status
show_status() {
    echo ""
    echo "📊 System Status Check"
    echo "====================="
    
    python3 -c "
import sys
sys.path.insert(0, '/app')

try:
    from semantic_task_scorer import semantic_scorer
    from unified_smart_agent import smart_agent
    
    print(f'🔧 Semantic Scorer:')
    print(f'   Enabled: {semantic_scorer.enabled}')
    print(f'   Embeddings: {'✅ Working' if semantic_scorer.embed_ok else '❌ Failed'}')
    
    print(f'')
    print(f'🤖 Unified Smart Agent:')
    print(f'   Model Available: {'✅ Yes' if smart_agent.model_available else '❌ No'}')
    print(f'   Model Path: {smart_agent.model_path or 'Not found'}')
    
    # Test a simple query
    print(f'')
    print(f'🧪 Quick Test:')
    result = smart_agent.process_query('What is the current time?')
    if 'ERROR' in str(result):
        print(f'   ❌ Test failed: {str(result)[:100]}...')
    else:
        print(f'   ✅ Test passed: {str(result)[:100]}...')
        
except Exception as e:
    print(f'❌ Status check failed: {e}')
"
}

# Main execution
main() {
    check_container
    
    echo "Starting diagnostic fixes..."
    
    # Fix sentence transformers
    if fix_sentence_transformers; then
        echo "Step 1/4: ✅ SentenceTransformers fixed"
    else
        echo "Step 1/4: ❌ SentenceTransformers fix failed"
        exit 1
    fi
    
    # Test semantic scoring
    if test_semantic_scoring; then
        echo "Step 2/4: ✅ Semantic scoring verified"
    else
        echo "Step 2/4: ❌ Semantic scoring failed"
        exit 1
    fi
    
    # Test local execution
    if test_local_execution; then
        echo "Step 3/4: ✅ Local execution verified"
    else
        echo "Step 3/4: ❌ Local execution failed"
        exit 1
    fi
    
    # Check TinyLlama
    check_tinyllama
    echo "Step 4/4: ✅ TinyLlama check complete"
    
    # Show final status
    show_status
    
    echo ""
    echo "🎉 All fixes completed successfully!"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Test the web interface with a query"
    echo "2. Check response times (should be 5-15 seconds for local queries)"
    echo "3. Monitor logs for any remaining errors"
    echo ""
    echo "🔧 If issues persist:"
    echo "   - Restart the container: docker-compose restart"
    echo "   - Check container logs: docker-compose logs -f"
}

# Run main function
main "$@"
