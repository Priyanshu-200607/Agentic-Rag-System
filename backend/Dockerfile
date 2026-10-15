FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --default-timeout=1000 --retries=10 -r requirements.txt

# Pre-download models to cache them in the Docker image
COPY download_models.py .
RUN python download_models.py

# Copy backend application
COPY . .

# Expose API port
EXPOSE 8000

# Generate config at runtime, then run the FastAPI server
CMD ["/bin/bash", "-c", "python setup_hardware.py && uvicorn api:app --host 0.0.0.0 --port 8000"]
