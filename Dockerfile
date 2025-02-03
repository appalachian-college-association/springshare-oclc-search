# Use official Python image with smaller footprint
FROM python:3.11-slim-bullseye

# Set environment variables before any other operations
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    FLASK_APP=src/app.py \
    PORT=8080

# Set working directory
WORKDIR /app

# Install only required system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (exclude .env from production image)
COPY src/ src/

# Expose Cloud Run default port
EXPOSE 8080

# Use gunicorn with appropriate settings
CMD exec gunicorn --bind :$PORT --workers 2 --threads 8 --timeout 0 src.app:app