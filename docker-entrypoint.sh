#!/bin/bash
set -e

echo "🚀 Starting Diagnostic Agent Container"
echo "====================================="

# Function to wait for dependencies
wait_for_deps() {
    echo "⏳ Waiting for system to settle..."
    sleep 3
}

# Function to ensure proper permissions
fix_permissions() {
    echo "🔧 Fixing permissions..."
    
    # Ensure cache directories exist and have correct permissions
    mkdir -p /home/agent/.cache/sentence_transformers
    mkdir -p /home/agent/.cache/huggingface/hub
    
    # Fix ownership
    chown -R agent:agent /home/agent/.cache || true
    chmod -R 755 /home/agent/.cache || true
    
    # Ensure app directories have correct permissions
    chown -R agent:agent /app/agent_memory || true
    chown -R agent:agent /app/logs || true
    chown -R agent:agent /app/models || true
    chown -R agent:agent /app/temp || true
    
    echo "✅ Permissions fixed"
}

# Function to pre-download sentence transformers model
preload_models() {
    echo "📥 Pre-loading models..."
    
    # Switch to agent user for model downloads
    su - agent -c "cd /app && python3 -c '
import os
os.environ[\"TRANSFORMERS_CACHE\"] = \"/home/agent/.cache/huggingface\"
os.environ[\"SENTENCE_TRANSFORMERS_HOME\"] = \"/home/agent/.cache/sentence_transformers\"

try:
    from sentence_transformers import SentenceTransformer
    print(\"Downloading sentence-transformers/all-MiniLM-L6-v2...\")
    model = SentenceTransformer(\"sentence-transformers/all-MiniLM-L6-v2\")
    test = model.encode([\"startup test\"])
    print(f\"✅ Model loaded successfully! Shape: {test.shape}\")
except Exception as e:
    print(f\"❌ Model loading failed: {e}\")
    exit(1)
'"
    
    if [ $? -eq 0 ]; then
        echo "✅ Models pre-loaded successfully"
    else
        echo "❌ Model pre-loading failed, but continuing..."
    fi
}

# Function to test components
test_components() {
    echo "🧪 Testing components..."
    
    su - agent -c "cd /app && python3 -c '
import sys
sys.path.insert(0, \"/app\")

try:
    from semantic_task_scorer import semantic_scorer
    print(f\"Semantic scorer enabled: {semantic_scorer.enabled}\")
    print(f\"Embeddings OK: {semantic_scorer.embed_ok}\")
    
    if semantic_scorer.embed_ok:
        score = semantic_scorer.score(\"test query\")
        print(f\"Test score: {score:.3f}\")
        print(\"✅ Semantic scoring working\")
    else:
        print(\"❌ Semantic scoring not working\")
        
except Exception as e:
    print(f\"Component test error: {e}\")
'"
}

# Main startup sequence
main() {
    wait_for_deps
    fix_permissions
    preload_models
    test_components
    
    echo ""
    echo "🎉 Initialization complete!"
    echo "🌐 Starting web agent..."
    echo ""
    
    # Switch to agent user and start the application
    exec su - agent -c "cd /app && python3 web_agent.py"
}

# Run main function
main "$@"
