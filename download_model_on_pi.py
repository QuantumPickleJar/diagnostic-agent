#!/usr/bin/env python3
"""
Download Sentence Transformers Model Directly on Pi
==================================================

This script downloads the sentence transformers model directly inside the container
to avoid transfer issues and ensure proper cache location.
"""
import os
import sys
from pathlib import Path

def download_sentence_transformers():
    """Download sentence transformers model to proper cache location"""
    print("🤖 Downloading sentence transformers model on Pi...")
    
    try:
        # Import inside the function to handle missing dependencies gracefully
        from sentence_transformers import SentenceTransformer
        
        print("📍 Setting up cache directory...")
        cache_dir = Path("/home/agent/.cache/sentence_transformers")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        print("📦 Downloading all-MiniLM-L6-v2 model (~120MB)...")
        print("This may take a few minutes depending on network speed...")
        
        # Set cache directory explicitly
        os.environ['SENTENCE_TRANSFORMERS_HOME'] = str(cache_dir)
        
        # Download the model - this will cache it properly
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        
        print("✅ Model downloaded successfully!")
        print(f"📁 Cached at: {cache_dir}")
        
        # Test the model to ensure it works
        print("🧪 Testing model...")
        test_sentences = ["Hello world", "Test sentence"]
        embeddings = model.encode(test_sentences)
        print(f"✅ Model test successful! Generated embeddings shape: {embeddings.shape}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install sentence-transformers")
        return False
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def main():
    """Main execution"""
    print("🚀 Sentence Transformers Model Downloader")
    print("=" * 50)
    
    success = download_sentence_transformers()
    
    if success:
        print("\n🎉 Download completed successfully!")
        print("The model is now cached and ready for use.")
    else:
        print("\n💥 Download failed. Check error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
