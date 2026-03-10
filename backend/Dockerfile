FROM python:3.11-slim

# Install system dependencies required by psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry 2.x
RUN pip install --no-cache-dir "poetry>=2.0.0,<3.0.0"

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml poetry.lock* ./

# Install dependencies without creating a virtualenv inside the container
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# Copy application source
COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
