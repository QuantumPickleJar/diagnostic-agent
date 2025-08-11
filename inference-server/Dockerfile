# OpenHermes Inference Server
# High-performance local LLM server for development machine
FROM ollama/ollama:latest

# Install additional dependencies for model management
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create directory for custom scripts
RUN mkdir -p /opt/inference-server

# Copy any custom scripts or configurations
COPY scripts/ /opt/inference-server/ 2>/dev/null || echo "No scripts directory found"

# Set working directory
WORKDIR /root

# Expose Ollama port
EXPOSE 11434

# Health check to ensure Ollama is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:11434/api/tags || exit 1

# Default command - start Ollama server
CMD ["ollama", "serve"]
