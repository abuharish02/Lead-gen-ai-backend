FROM python:3.11

# Set working directory
WORKDIR /app

# Ensure Python can import the `app` package regardless of CWD
ENV PYTHONPATH=/app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p data/uploads data/knowledge_base

# Copy application code
COPY . .

# Expose default Cloud Run port (doc only)
EXPOSE 8000

# FIXED: Use Python to handle PORT environment variable properly
CMD ["python", "-c", "import os; import uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))"]