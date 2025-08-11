#!/usr/bin/env python3
"""
Enhanced diagnostic agent for dev machine
Receives tasks from Pi and processes them using OpenHermes via llama-cpp-python
Now includes Pi configuration awareness for better context
"""
import sys
import os
import subprocess
import json
import time
from pathlib import Path

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests not available, Pi config fetching disabled", file=sys.stderr)

# Pi configuration cache
pi_config_cache = None
pi_config_last_update = 0

def fetch_pi_configuration():
    """Fetch current Pi configuration for context awareness"""
    global pi_config_cache, pi_config_last_update
    
    if not REQUESTS_AVAILABLE:
        return {
            "pi_info": {"hostname": "unknown"},
            "routing_config": {},
            "available_tasks": [],
            "system_capabilities": {"local_model": "TinyLlama-1.1B"}
        }
    
    current_time = time.time()
    # Cache for 5 minutes
    if pi_config_cache and (current_time - pi_config_last_update) < 300:
        return pi_config_cache
    
    try:
        # Try to fetch from Pi (customize URL for your setup)
        pi_url = os.getenv("PI_CONFIG_URL", "http://your-pi-hostname.local:5000/config/pi_snapshot")
        response = requests.get(pi_url, timeout=5)
        
        if response.status_code == 200:
            pi_config_cache = response.json()
            pi_config_last_update = current_time
            return pi_config_cache
        else:
            print(f"Failed to fetch Pi config: HTTP {response.status_code}", file=sys.stderr)
    except Exception as e:
        print(f"Could not fetch Pi configuration: {e}", file=sys.stderr)
    
    # Return minimal fallback config
    return {
        "pi_info": {"hostname": "unknown"},
        "routing_config": {},
        "available_tasks": [],
        "system_capabilities": {"local_model": "TinyLlama-1.1B"}
    }

def find_model_path():
    """Find the OpenHermes model in various potential locations"""
    potential_paths = [
        # User's inference-server directory
        "~/inference-server/models/openhermes-2.5-mistral-7b.Q5_0.gguf",
        # Standard models directory
        "~/models/openhermes-2.5-mistral-7b.Q5_0.gguf",
        "./models/openhermes-2.5-mistral-7b.Q5_0.gguf",
        # Generic search patterns
        "~/models/*openhermes*.gguf",
        "~/inference-server/models/*openhermes*.gguf",
        "./models/*openhermes*.gguf"
    ]
    
    for path_pattern in potential_paths:
        path = Path(path_pattern).expanduser()
        if "*" in str(path):
            # Handle glob patterns
            parent = path.parent
            pattern = path.name
            if parent.exists():
                for model_file in parent.glob(pattern):
                    if model_file.is_file():
                        return str(model_file)
        else:
            # Handle direct paths
            if path.exists() and path.is_file():
                return str(path)
    
    return None

def process_with_openhermes(query):
    """Process query using OpenHermes via llama-cpp-python with Pi context awareness"""
    model_path = find_model_path()
    if not model_path:
        return "ERROR: OpenHermes model not found. Expected at ~/inference-server/models/openhermes-2.5-mistral-7b.Q5_0.gguf"
    
    # Fetch Pi configuration for context
    pi_config = fetch_pi_configuration()
    
    try:
        # Try to use llama-cpp-python directly
        from llama_cpp import Llama
        
        print(f"Loading OpenHermes model from: {model_path}", file=sys.stderr)
        
        # Initialize the model with optimized settings for 7B model on dev machine
        # Your WSL has 9.7GB RAM, so we can be more generous with settings
        llm = Llama(
            model_path=model_path, 
            n_ctx=8192,  # Much larger context window (25% of model's training context)
            n_threads=6,  # Use most of your CPU cores efficiently
            n_gpu_layers=0,  # CPU inference (increase if you have CUDA GPU)
            n_batch=512,  # Larger batch for better throughput
            f16_kv=True,  # Use FP16 for key-value cache (saves memory)
            use_mlock=True,  # Lock memory to prevent swapping
            verbose=False
        )
        
        # Build context-aware prompt with Pi information
        pi_context = f"""
Pi System Context:
- Hostname: {pi_config['pi_info'].get('hostname', 'unknown')}
- Local Model: {pi_config['system_capabilities'].get('local_model', 'TinyLlama-1.1B')}
- Available Tasks: {', '.join(pi_config.get('available_tasks', [])[:5])}
- Routing Threshold: {pi_config.get('routing_config', {}).get('routing', {}).get('delegation_threshold', 0.7)}

This query was delegated from the Pi because it requires advanced analysis beyond the Pi's TinyLlama capabilities.
"""
        
        # Create a proper ChatML prompt for OpenHermes with Pi context
        prompt = f"""<|im_start|>system
You are OpenHermes, a helpful AI assistant specialized in technical analysis, system diagnostics, and problem-solving. You are running on a dev machine and receive complex queries delegated from a Raspberry Pi diagnostic agent.

{pi_context}

Provide detailed, accurate responses with practical solutions. Consider the Pi's limited resources and provide recommendations that are appropriate for the Pi environment when relevant.
<|im_end|>
<|im_start|>user
{query}
<|im_end|>
<|im_start|>assistant
"""
        
        # Generate response with improved settings
        response = llm(
            prompt, 
            max_tokens=768,  # More tokens for detailed responses
            temperature=0.7,
            top_p=0.9,  # Better token selection
            repeat_penalty=1.1,  # Reduce repetition
            stop=["<|im_end|>", "<|im_start|>"], 
            echo=False
        )
        
        result = response["choices"][0]["text"].strip()
        print(f"Generated response length: {len(result)} chars", file=sys.stderr)
        
        # Add metadata about the processing
        metadata = f"\n\n[Processed on dev machine with OpenHermes-2.5-Mistral-7B | Pi Context: {pi_config['pi_info'].get('hostname', 'unknown')}]"
        return result + metadata
        
    except ImportError:
        return "ERROR: llama-cpp-python not available on dev machine"
    except Exception as e:
        return f"ERROR: Failed to process with OpenHermes: {str(e)}"

def main():
    """Main entry point for dev machine agent"""
    if len(sys.argv) < 2:
        print("Usage: python3 dev_machine_agent.py 'your query here'")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    print(f"Processing query: {query[:100]}...", file=sys.stderr)
    
    result = process_with_openhermes(query)
    print(result)

if __name__ == "__main__":
    main()
