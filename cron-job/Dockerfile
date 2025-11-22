FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_NO_CACHE=1 \
    VIRTUAL_ENV=/app/.venv

# Install cron
RUN apt-get update && apt-get install -y cron \
    && rm -rf /var/lib/apt/lists/*

# Change wd to app directory
WORKDIR /app

# Create virtual environment
RUN uv venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies using uv
COPY requirements.txt .
RUN uv pip install -r requirements.txt

# Copy application files
COPY fetch_bikes.py .
COPY crontab /etc/cron.d/bike-sync

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/bike-sync

# Create the log file
RUN touch /var/log/cron.log

# Apply cron job
RUN crontab /etc/cron.d/bike-sync

# Run initial sync and then start cron
CMD python /app/fetch_bikes.py && cron && tail -f /var/log/cron.log
