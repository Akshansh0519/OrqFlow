FROM python:3.12-slim

WORKDIR /app

# Prevents Python from writing pyc files and buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies needed by asyncpg and bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caching — only reruns on requirements.txt change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .
RUN chmod +x /app/docker-entrypoint.sh

# All 4 Python services share this image — port depends on the service
# The CMD is overridden per-service in docker-compose.yml
EXPOSE 8000 8001 8002 8003

# Default: run the main FastAPI API server
# ${PORT:-8000}: use platform-provided PORT env var (Render sets this automatically),
# fall back to 8000 for local Docker Compose.
# NEVER hardcode a port here — that's how Render deployment silently fails.
CMD ["/app/docker-entrypoint.sh"]
