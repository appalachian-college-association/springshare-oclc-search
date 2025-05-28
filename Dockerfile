# Most secure option - Alpine Linux (Simplified)
FROM python:alpine

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV FLASK_APP=src/app.py
ENV PORT=8080

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -s /bin/sh -D appuser

# Install system dependencies (Alpine uses apk instead of apt-get)
RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
        build-base \
        curl \
        gcc \
        musl-dev \
        libffi-dev \
        && rm -rf /var/cache/apk/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf ~/.cache/pip/*

# Copy source code and set ownership
COPY src/ ./src/
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Use CMD directly instead of entrypoint script
CMD ["gunicorn", "--bind", ":8080", "--workers", "2", "--threads", "8", "--timeout", "30", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "--log-level", "info", "src.app:app"]