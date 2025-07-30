import os
from sentence_transformers import SentenceTransformer

def download_model():
    """Download sentence transformer model with caching support"""
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    cache_dir = "/home/agent/.cache/sentence_transformers"
    
    print(f"Checking for cached model in: {cache_dir}")
    
    # Check if model is already cached
    if os.path.exists(cache_dir) and os.listdir(cache_dir):
        print("Model already cached, skipping download")
        print(f"Cache contents: {os.listdir(cache_dir)}")
        return True
    
    try:
        print("Model not found in cache, downloading...")
        print(f"Downloading: {model_name}")
        
        # This will download to the cache directory automatically
        model = SentenceTransformer(model_name)
        
        print("Model downloaded successfully")
        
        # Verify the cache was created
        if os.path.exists(cache_dir):
            print(f"Model cached in: {cache_dir}")
            print(f"Cache contents: {os.listdir(cache_dir)}")
        else:
            print("Cache directory not found after download")
        
        return True
        
    except Exception as e:
        print(f"Model download failed: {e}")
        print("Model will be downloaded at runtime instead")
        return False

if __name__ == "__main__":
    download_model()