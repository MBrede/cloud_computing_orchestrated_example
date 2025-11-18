#!/bin/bash

echo "======================================"
echo "  Kiel City Data Platform"
echo "  Starting all services..."
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
fi

echo "Starting Docker Compose services..."
echo ""

docker-compose up --build

echo ""
echo "======================================"
echo "  Shutdown complete"
echo "======================================"
