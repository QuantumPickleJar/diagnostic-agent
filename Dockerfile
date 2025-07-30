# Use Python 3.11 slim image for efficiency on Raspberry Pi
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and clean up in single layer to reduce image size
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libblas-dev \
    liblapack-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies with optimizations for Pi and ARM architecture
RUN pip install --no-cache-dir --upgrade pip && \
    # Install numpy first as it's a dependency for many packages
    pip install --no-cache-dir "numpy>=2.0.0" && \
    # Install FAISS with specific handling for ARM
    pip install --no-cache-dir "faiss-cpu>=1.9.0" --no-build-isolation || \
    pip install --no-cache-dir "faiss-cpu==1.7.4" --no-build-isolation || \
    echo "FAISS installation failed, will use fallback" && \
    # Install remaining requirements
    pip install --no-cache-dir "flask>=3.0.0" "sentence-transformers>=3.0.0" "requests>=2.31.0"

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

# Switch to agent user before downloading model to use correct cache location
USER agent

# Create cache directory structure
RUN mkdir -p /home/agent/.cache/sentence_transformers

# Copy download_model.py for runtime use (will check ./models first, then cache/download as needed)
COPY download_model.py .

# Copy the run_agent.py script into the container
COPY run_agent.py .

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
CMD ["python", "run_agent.py"]
