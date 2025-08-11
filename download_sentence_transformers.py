#!/usr/bin/env python3
"""
Download Sentence Transformers Model for Pi Deployment
====================================================

This script downloads the sentence transformers model locally and packages it
for transfer to the Pi to avoid repeated downloads.
"""

import os
import sys
import tarfile
import shutil
from pathlib import Path

def download_sentence_transformers_model():
    """Download the sentence transformers model locally"""
    print("📦 Downloading sentence transformers model...")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        # Download the model to local cache
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        print("✅ Model downloaded successfully!")
        
        # Get the model cache directory
        cache_dir = Path.home() / ".cache" / "sentence_transformers"
        
        if cache_dir.exists():
            print(f"📂 Model cache location: {cache_dir}")
            return cache_dir
        else:
            print("❌ Model cache directory not found!")
            return None
            
    except ImportError:
        print("❌ sentence_transformers not installed!")
        print("Run: pip install sentence-transformers")
        return None
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        return None

def package_model_for_transfer(cache_dir):
    """Package the model cache for transfer to Pi"""
    print("📦 Packaging model for transfer...")
    
    tar_path = "sentence_transformers_cache.tar.gz"
    
    try:
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(cache_dir, arcname="sentence_transformers")
        
        size_mb = os.path.getsize(tar_path) / (1024 * 1024)
        print(f"✅ Model packaged: {tar_path} ({size_mb:.1f} MB)")
        return tar_path
        
    except Exception as e:
        print(f"❌ Error packaging model: {e}")
        return None

def main():
    print("🤖 Sentence Transformers Model Transfer Utility")
    print("=" * 50)
    
    # Download model
    cache_dir = download_sentence_transformers_model()
    if not cache_dir:
        return 1
    
    # Package for transfer
    tar_path = package_model_for_transfer(cache_dir)
    if not tar_path:
        return 1
    
    print("\n🚀 Next steps:")
    print(f"1. Transfer to Pi: scp -P 2222 {tar_path} your_pi_user@your_pi_host:~/")
    print("2. On Pi, extract to Docker volume:")
    print("   ssh -p 2222 your_pi_user@your_pi_host")
    print("   docker run --rm -v diagnostic-agent_model_cache:/cache -v ~/sentence_transformers_cache.tar.gz:/tmp/cache.tar.gz alpine:latest sh -c 'cd /cache && tar -xzf /tmp/cache.tar.gz'")
    print("3. Restart container to use cached model")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
