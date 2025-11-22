FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_NO_CACHE=1 \
    VIRTUAL_ENV=/app/.venv

# Install cron + curl for healthcheck
RUN apt-get update && apt-get install -y cron \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Change wd to app directory
WORKDIR /app

# Create virtual environment
RUN uv venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies using uv
COPY requirements.txt .
RUN uv pip install -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
