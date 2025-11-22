FROM python:3.11-slim

WORKDIR /app

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies using uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy script
COPY load_kiel_data.py .

# Run the data loader
CMD ["python", "load_kiel_data.py"]
