FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_NO_CACHE=1 \ 
    VIRTUAL_ENV=/app/.venv

# Change wd to app directory
WORKDIR /app

# Create virtual environment
RUN uv venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies using uv
COPY requirements.txt .
RUN cat requirements.txt
RUN uv --version
RUN uv pip install -r requirements.txt

# Copy script
COPY load_kiel_data.py .
RUN mkdir data
COPY data/* data/

# Run the data loader
CMD ["uv", "run", "load_kiel_data.py"]
