FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Environment setup
ENV PYTHONUNBUFFERED=1
ENV TRANSCRIPTS_DIR=/app/transcripts

# Run the worker pipeline
CMD ["python", "worker_pipeline.py"]
