# Multi-stage build for production - optimized for Railway Hobby plan
FROM python:3.11-slim AS base

# Install system dependencies with minimal footprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf ~/.cache/pip

# Remove build dependencies to reduce image size
RUN apt-get update && apt-get purge -y gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Create storage directory (will be mounted to /data on Railway)
RUN mkdir -p storage/videos

# Production stage
FROM base AS production

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Copy start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Run based on service name
CMD ["/app/start.sh"]
