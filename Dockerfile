FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and Chrome/Chromium for headless browsing
RUN apt-get update && apt-get install -y \
    gcc \
    wget \
    curl \
    chromium \
    chromium-driver \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create data directory for SQLite database
RUN mkdir -p /app/data

ENV PYTHONPATH=/app

CMD ["python", "src/main.py"]