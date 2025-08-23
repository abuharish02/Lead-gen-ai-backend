# Dockerfile
FROM python:3.11

# Set working directory
WORKDIR /app

# Ensure Python can import the app package regardless of CWD
ENV PYTHONPATH=/app

# No extra OS packages to simplify build in Cloud Build

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p data/uploads data/knowledge_base

# Copy application code
COPY . .

# Run as root (simpler for Cloud Build/Run). Consider non-root later if needed.

# Expose default Cloud Run port (doc only)
EXPOSE 8000

# Note: Cloud Run manages health internally; no container HEALTHCHECK needed

# Command to run the application; honor Cloud Run PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]