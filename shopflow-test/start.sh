#!/usr/bin/env bash
set -e

echo "=================================================="
echo " Starting ShopFlow E-Commerce Microservices Platform"
echo "=================================================="

# Check if docker is available
if command -v docker &> /dev/null && [ "$1" == "--docker" ]; then
    echo "Starting via Docker Compose..."
    docker compose up --build
else
    echo "Starting ShopFlow locally in Python..."
    export PYTHONPATH="$(pwd)"
    python -m uvicorn services.api_gateway.main:app --host 0.0.0.0 --port 8000 --reload
fi
