#!/usr/bin/env python3
"""
Simple script to download sentence transformers model in Docker container
"""

import os
import subprocess
import sys

def download_with_docker():
    """Use Docker to download the model"""
    print("📦 Using Docker to download sentence transformers model...")
    
    # Create a temporary container to download the model
    docker_cmd = [
        "docker", "run", "--rm", 
        "-v", f"{os.getcwd()}/temp_model_cache:/cache",
        "python:3.11-slim",
        "sh", "-c", 
        "pip install sentence-transformers && python -c \"from sentence_transformers import SentenceTransformer; model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); print('Model downloaded successfully!')\" && cp -r /root/.cache/sentence_transformers /cache/"
    ]
    
    try:
        # Create temp directory
        os.makedirs("temp_model_cache", exist_ok=True)
        
        # Run Docker command
        result = subprocess.run(docker_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Model downloaded successfully!")
            
            # Create tar file
            tar_cmd = ["tar", "-czf", "sentence_transformers_cache.tar.gz", "-C", "temp_model_cache", "sentence_transformers"]
            tar_result = subprocess.run(tar_cmd, capture_output=True, text=True)
            
            if tar_result.returncode == 0:
                print("✅ Model packaged for transfer")
                
                # Clean up temp directory
                import shutil
                shutil.rmtree("temp_model_cache")
                
                return True
            else:
                print(f"❌ Error creating tar: {tar_result.stderr}")
                return False
        else:
            print(f"❌ Docker command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🤖 Sentence Transformers Model Download (Docker Method)")
    print("=" * 55)
    
    if download_with_docker():
        print("\n🚀 Model ready for transfer!")
        print("Next steps:")
        print("1. scp -P 2222 sentence_transformers_cache.tar.gz your_pi_user@your_pi_host:~/")
        print("2. SSH to Pi and extract to Docker volume")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
