# Model Storage and Deployment Guide

## Model Locations and Mounting

### 1. Sentence Transformer Model
- **Auto-downloaded** by `sentence-transformers` library on first use
- **Container location**: `/home/agent/.cache/sentence_transformers/`
- **Docker mount**: `model_cache:/home/agent/.cache` (named volume)
- **Purpose**: FAISS semantic search and memory recall
- **Size**: ~120MB
- **No manual setup required** - downloads automatically

### 2. TinyLlama Model (Optional)
- **Manual download required** if you want to use it
- **Host location**: `./models/tinyllama.gguf` (in project directory)
- **Container location**: `/app/models/tinyllama.gguf`
- **Docker mount**: `./models:/app/models` (bind mount)
- **Purpose**: Future local LLM inference
- **Size**: ~600MB

## Volume Mounts Explained

The `docker-compose.yml` includes these mounts:

```yaml
volumes:
  # Persistent agent memory and logs
  - agent_memory:/app/agent_memory
  
  # External log access for monitoring
  - ./logs:/app/logs
  
  # TinyLlama and other local models (create ./models directory first)
  - ./models:/app/models
  
  # Sentence transformer cache (speeds up restarts)
  - model_cache:/home/agent/.cache
```

## To Answer Your Question

**Do you need to bind the models to mounts?**

- **Sentence transformer**: Already handled via `model_cache` volume - no action needed
- **TinyLlama**: Only if you want to use it - create `./models/` directory and download the model there

## Quick Setup

For basic operation (diagnostic agent only):
```bash
# No model setup needed - sentence transformer downloads automatically
./deploy.sh
```

For full setup with TinyLlama:
```bash
# Create models directory and download TinyLlama
mkdir -p models
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-GGUF/resolve/main/tinyllama-1.1b-chat.Q4_K_M.gguf -O ./models/tinyllama.gguf

# Deploy
./deploy.sh
```

The sentence transformer model cache persists between container restarts via the named volume, so it only downloads once.
