# PDF Bot Dockerfile
# Optimized for Railway deployment with Ghostscript

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Ghostscript
RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Verify Ghostscript installation
RUN gs --version

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Create temp directory for file processing
RUN mkdir -p /tmp/pdf_processing

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/ || exit 1

# Expose port for health checks
EXPOSE 8001

# Run the application
CMD ["python", "main.py"]
