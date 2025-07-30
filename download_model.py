import os
from sentence_transformers import SentenceTransformer

def download_model():
    """Download sentence transformer model with caching support, or use manually downloaded model if present."""
    import sys
    import time
    import logging
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    manual_model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "models", "all-MiniLM-L6-v2"))
    cache_dir = "/home/agent/.cache/sentence_transformers"

    print(f"[INFO] Python version: {sys.version}")
    print(f"[INFO] Platform: {sys.platform}")
    print(f"[INFO] Checking for manually downloaded model in: {manual_model_dir}")
    if os.path.exists(manual_model_dir) and os.listdir(manual_model_dir):
        print(f"[SUCCESS] Found manually downloaded model in {manual_model_dir}. Skipping download.")
        return True

    print(f"[INFO] Checking for cached model in: {cache_dir}")
    if os.path.exists(cache_dir) and os.listdir(cache_dir):
        print("[SUCCESS] Model already cached, skipping download")
        print(f"[INFO] Cache contents: {os.listdir(cache_dir)}")
        return True

    try:
        print("[INFO] Model not found in cache or ./models, starting download...")
        print(f"[INFO] Downloading: {model_name}")

        # Set up logging for transformers/huggingface_hub
        try:
            import transformers
            transformers.logging.set_verbosity_info()
            print("[INFO] Set transformers logging to INFO level.")
        except Exception as e:
            print(f"[WARN] Could not set transformers logging: {e}")
        try:
            import huggingface_hub
            huggingface_hub.logging.set_verbosity_info()
            print("[INFO] Set huggingface_hub logging to INFO level.")
        except Exception as e:
            print(f"[WARN] Could not set transformers logging: {e}")

        # Set environment variables for better download progress visibility
        os.environ["HF_HUB_VERBOSITY"] = "info"
        os.environ["TRANSFORMERS_VERBOSITY"] = "info"

        # This will download to the cache directory automatically
        start = time.time()
        print("[INFO] Starting model download... (this may take several minutes)")
        model = SentenceTransformer(model_name)
        elapsed = time.time() - start
        print(f"[SUCCESS] Model downloaded successfully in {elapsed:.2f} seconds.")

        # Verify the cache was created
        if os.path.exists(cache_dir):
            print(f"[INFO] Model cached in: {cache_dir}")
            print(f"[INFO] Cache contents: {os.listdir(cache_dir)}")
        else:
            print("[WARN] Cache directory not found after download")

        return True

    except Exception as e:
        print(f"[ERROR] Model download failed: {e}")
        print("[WARN] Model will be downloaded at runtime instead")
        return False

if __name__ == "__main__":
    download_model()