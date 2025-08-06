# Multi-stage build for dramatic size and time reduction
# ====================================================

# Stage 1: Build dependencies (this layer gets cached)
FROM python:3.11-slim as builder

# Install build dependencies in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libblas-dev \
    liblapack-dev \
    gfortran \
    cmake \
    pkg-config \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements and install Python packages
COPY requirements.txt /tmp/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    # Build wheels with dependencies for better compatibility
    pip wheel --no-cache-dir --wheel-dir /wheels \
    -r /tmp/requirements.txt

# Stage 2: Runtime image (much smaller)
FROM python:3.11-slim

# Install only runtime dependencies (no build tools!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iputils-ping \
    net-tools \
    iproute2 \
    procps \
    dnsutils \
    ca-certificates \
    wakeonlan \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Docker CLI separately (much faster than full Docker installation)
RUN curl -fsSL https://download.docker.com/linux/static/stable/$(uname -m)/docker-20.10.24.tgz | \
    tar -xzf - --strip-components=1 -C /usr/local/bin docker/docker && \
    chmod +x /usr/local/bin/docker

# Copy pre-built wheels from builder stage
COPY --from=builder /wheels /wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --no-index --find-links /wheels \
    /wheels/*.whl && \
    rm -rf /wheels

# Create non-root user early
RUN useradd -m -u 1000 agent && \
    groupadd -f docker && \
    usermod -aG docker agent

# Set working directory and switch user
WORKDIR /app
USER agent

# Create necessary directories
RUN mkdir -p /home/agent/.cache/sentence_transformers \
    /app/agent_memory \
    /app/agent_memory/archived_sessions \
    /app/logs

# Copy application files (this layer changes most often, so put it last)
COPY --chown=agent:agent . .

# Create default config if it doesn't exist
RUN if [ ! -f /app/agent_memory/static_config.json ]; then \
    echo '{"mode":"local","local_model_path":"/app/models/tinyllama.gguf","system_prompt_file":"system_prompt.txt","remote_dev":{"user":"user","ip":"192.168.1.100","port":22},"logging":{"level":"INFO","max_log_size_mb":50,"max_log_days":30},"memory":{"faiss_index_path":"/app/agent_memory/embeddings.faiss","recall_log_path":"/app/agent_memory/recall_log.jsonl"},"system_info":{"hostname":"diagnostic-agent","platform":"raspberry-pi","last_updated":"2025-07-30T00:00:00Z"}}' > /app/agent_memory/static_config.json; \
    fi

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

EXPOSE 5000
CMD ["python", "web_agent.py"]
