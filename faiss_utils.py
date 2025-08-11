import os
import json
import numpy as np

# Try to import FAISS with fallback
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    print("FAISS not available, using fallback similarity search")
    FAISS_AVAILABLE = False

# SentenceTransformer downloads the embedding model on first use.
# The default model works well on a Raspberry Pi and is around ~120MB.
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("SentenceTransformers not available, similarity search disabled")
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Use relative paths that work in both development and container environments
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(BASE_DIR, "agent_memory")
LOG_PATH = os.path.join(MEMORY_DIR, "recall_log.jsonl")
INDEX_PATH = os.path.join(MEMORY_DIR, "embeddings.faiss")
MAPPING_PATH = os.path.join(MEMORY_DIR, "embeddings.json")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Ensure the memory directory exists
os.makedirs(MEMORY_DIR, exist_ok=True)

_model = None

def get_model():
    global _model
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        return None
    if _model is None:
        try:
            # Check for locally available model first (user has this at /home/diagnostic-agent/models/)
            local_model_paths = [
                "/home/diagnostic-agent/models/all-MiniLM-L6-v2",
                os.path.abspath(os.path.join(BASE_DIR, "models", "all-MiniLM-L6-v2")),
                os.path.abspath(os.path.join(BASE_DIR, "..", "models", "all-MiniLM-L6-v2"))
            ]
            
            for model_path in local_model_paths:
                if os.path.exists(model_path) and os.listdir(model_path):
                    # Check if this is a valid sentence transformer model
                    config_path = os.path.join(model_path, "config.json")
                    if os.path.exists(config_path):
                        print(f"Loading local model from {model_path}")
                        _model = SentenceTransformer(model_path)
                        print("Local model loaded successfully")
                        return _model
                    else:
                        print(f"Skipping incomplete model at {model_path} (no config.json)")
            
            # Check if model is already cached
            cache_dir = os.path.expanduser("~/.cache/sentence_transformers")
            model_cache_exists = os.path.exists(cache_dir) and os.listdir(cache_dir)
            
            if model_cache_exists:
                print(f"Loading cached model from {cache_dir}")
            else:
                print("Model not cached, downloading...")
            
            _model = SentenceTransformer(MODEL_NAME)
            print("Model loaded successfully")
        except Exception as e:
            print(f"Failed to load SentenceTransformer model: {e}")
            return None
    return _model

def _load_entries():
    if not os.path.exists(LOG_PATH):
        return []
    entries = []
    with open(LOG_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries

def reindex():
    """(Re)build the FAISS index from ``recall_log.jsonl``.

    The SentenceTransformer embedding model is loaded (and downloaded if
    necessary) on the first call. Returns the number of entries indexed. If no
    log entries exist the index files are removed so search simply returns an
    empty list.
    """
    # Check if dependencies are available
    if not SENTENCE_TRANSFORMERS_AVAILABLE or not FAISS_AVAILABLE:
        print("FAISS or SentenceTransformers not available, skipping indexing")
        return 0
        
    # ensure the embedding model downloads on first run
    model = get_model()
    if model is None:
        print("Could not load embedding model, skipping indexing")
        return 0
        
    entries = _load_entries()
    texts = [f"{e.get('task','')} {e.get('result','')}" for e in entries]
    if not texts:
        for path in (INDEX_PATH, MAPPING_PATH):
            if os.path.exists(path):
                os.remove(path)
        return 0
    
    try:
        embeddings = model.encode(texts, show_progress_bar=False)
        embeddings = np.array(embeddings, dtype='float32')
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, INDEX_PATH)
        with open(MAPPING_PATH, 'w') as f:
            json.dump(entries, f)
        return len(entries)
    except Exception as e:
        print(f"Error during indexing: {e}")
        return 0

def search(query, top_k=5):
    """Search for similar entries using FAISS index.
    
    Returns a list of matching entries. If FAISS or SentenceTransformers
    are not available, returns an empty list.
    """
    if not SENTENCE_TRANSFORMERS_AVAILABLE or not FAISS_AVAILABLE:
        return []
        
    if not os.path.exists(INDEX_PATH) or not os.path.exists(MAPPING_PATH):
        return []
        
    try:
        index = faiss.read_index(INDEX_PATH)
        with open(MAPPING_PATH) as f:
            entries = json.load(f)
        model = get_model()
        if model is None:
            return []
            
        query_emb = model.encode([query], show_progress_bar=False)
        query_emb = np.array(query_emb, dtype='float32')
        D, I = index.search(query_emb, top_k)
        results = []
        for idx in I[0]:
            if 0 <= idx < len(entries):
                results.append(entries[idx])
        return results
    except Exception as e:
        print(f"Error during search: {e}")
        return []