#!/usr/bin/env bash
set -e

echo "==================================================="
echo "  OpsPilot - Starting Incident Command Center"
echo "==================================================="
echo ""

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "0. Releasing ports 8000, 8080, and 5173..."
python "$ROOT_DIR/scripts/free_ports.py" || true

echo "1. Starting ShopFlow Microservices on port 8000..."
(cd "$ROOT_DIR/shopflow-test" && python -m uvicorn services.api_gateway.main:app --port 8000 --host 127.0.0.1) &
SHOPFLOW_PID=$!

echo "2. Starting OpsPilot Backend on port 8080..."
(cd "$ROOT_DIR/backend" && python -m uvicorn app.main:app --port 8080 --host 127.0.0.1) &
BACKEND_PID=$!

echo "3. Starting OpsPilot React Console on port 5173..."
(cd "$ROOT_DIR/frontend" && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "All services launched!"
echo "  - ShopFlow:         http://127.0.0.1:8000"
echo "  - OpsPilot Backend: http://127.0.0.1:8080"
echo "  - OpsPilot Console: http://127.0.0.1:5173"
echo ""
echo "Press Ctrl+C to terminate all services."

trap "kill $SHOPFLOW_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM EXIT
wait
