Copy# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY .env .env

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=src/app.py

# Expose port
EXPOSE 5000

# Use gunicorn as production server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "src.app:app"]