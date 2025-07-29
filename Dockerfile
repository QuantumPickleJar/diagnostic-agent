# Use Python 3.11 slim image for efficiency on Raspberry Pi
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and clean up in single layer to reduce image size
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies with optimizations for Pi
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create agent_memory directory with proper permissions and structure
RUN mkdir -p /app/agent_memory && \
    mkdir -p /app/agent_memory/archived_sessions && \
    mkdir -p /app/logs && \
    chmod 755 /app/agent_memory && \
    chmod 755 /app/logs

# Create a non-root user for security
RUN useradd -m -u 1000 agent && \
    chown -R agent:agent /app

# Switch to non-root user
USER agent

# Pre-download the sentence transformer model to avoid first-run delays
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" || echo "Model download failed, will retry at runtime"

# Expose port 5000
EXPOSE 5000

# Health check for container orchestration with better reliability
HEALTHCHECK --interval=30s --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Environment variables for container optimization
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV PYTHONDONTWRITEBYTECODE=1

# Run the application
CMD ["python", "web_agent.py"]
