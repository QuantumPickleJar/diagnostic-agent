import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

LOG_PATH = "/agent_memory/recall_log.jsonl"
INDEX_PATH = "/agent_memory/embeddings.faiss"
MAPPING_PATH = "/agent_memory/embeddings.json"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
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
    """Rebuild FAISS index from recall log.

    Returns True if any entries were indexed, otherwise False. In the empty case
    any existing index files are removed so search returns no results.
    """
    entries = _load_entries()
    texts = [f"{e.get('task','')} {e.get('result','')}" for e in entries]
    if not texts:
        if os.path.exists(INDEX_PATH):
            os.remove(INDEX_PATH)
        if os.path.exists(MAPPING_PATH):
            os.remove(MAPPING_PATH)
        return False
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype="float32")
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, INDEX_PATH)
    with open(MAPPING_PATH, "w") as f:
        json.dump(entries, f)
    return True

def search(query, top_k=5):
    if not os.path.exists(INDEX_PATH) or not os.path.exists(MAPPING_PATH):
        return []
    index = faiss.read_index(INDEX_PATH)
    with open(MAPPING_PATH) as f:
        entries = json.load(f)
    model = get_model()
    query_emb = model.encode([query], show_progress_bar=False)
    query_emb = np.array(query_emb, dtype='float32')
    D, I = index.search(query_emb, top_k)
    results = []
    for idx in I[0]:
        if 0 <= idx < len(entries):
            results.append(entries[idx])
    return results
