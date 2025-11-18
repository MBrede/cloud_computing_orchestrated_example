#!/bin/bash

echo "======================================"
echo "  Stopping all services..."
echo "======================================"
echo ""

docker-compose down

echo ""
echo "✓ All services stopped"
echo ""
echo "To remove all data volumes, run:"
echo "  docker-compose down -v"
echo ""
