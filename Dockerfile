# Use Python 3.13 slim image as base (matches .python-version and requires-python)
FROM python:3.13-slim

# Set working directory in container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -r pyproject.toml

# Copy source code
COPY src/ ./src/

# Create necessary directories
RUN mkdir -p logs data downloads

# Copy data files (conditionally)
RUN mkdir -p data
COPY data ./data

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Create a non-root user
RUN useradd --create-home --shell /bin/bash ringobot && \
    chown -R ringobot:ringobot /app

USER ringobot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the bot
CMD ["python", "src/main.py"]
