# Multi-stage lightweight Python Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (build essentials for pgvector and psycopg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY skills/ ./skills/
COPY .env.example .env

ENV PYTHONUNBUFFERED=1
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
