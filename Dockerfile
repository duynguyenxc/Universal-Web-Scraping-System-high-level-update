FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UWSS_THROTTLE_SEC=0.5 \
    UWSS_JITTER_SEC=0.2

WORKDIR /app

# System deps for cloud deployment
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    build-essential \
    libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data/files /app/data/export /app/logs

# Health check for cloud deployment
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# The application expects working dir root with config/ and data/ mounted
VOLUME ["/app/data", "/app/config", "/app/logs"]

# Default command prints CLI help; override with args, e.g.:
# docker run --rm -v $PWD/data:/app/data uwss:latest python -m src.uwss.cli stats --db data/uwss.sqlite
CMD ["python", "-m", "src.uwss.cli"]



