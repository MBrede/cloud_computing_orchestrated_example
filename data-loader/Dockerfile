FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy script
COPY load_kiel_data.py .

# Run the data loader
CMD ["python", "load_kiel_data.py"]
