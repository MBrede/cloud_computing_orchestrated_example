FROM python:3.11-slim

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies using uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

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
