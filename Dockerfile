# SolutionBridge Production-Style Multi-Service Container
FROM python:3.11-slim

# Prevent Python from writing .pyc and buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install OS dependencies for MySQL connectivity and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY app/ ./app/
COPY ml/ ./ml/
COPY dashboard/ ./dashboard/
COPY postman/ ./postman/
COPY scripts/ ./scripts/
COPY docs/ ./docs/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY README.md .

# Create directory for logs, reports, and persistent artifacts
RUN mkdir -p logs reports ml/artifacts

# Expose FastAPI backend and Streamlit dashboard ports
EXPOSE 8000 8501

# Default command launches backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
