#!/usr/bin/env bash
set -e

echo "==================================================="
echo "  OpsPilot - Resetting Demo to Clean Baseline"
echo "==================================================="
echo ""

echo "1. Resetting ShopFlow Chaos Engine..."
curl -s -X POST http://127.0.0.1:8000/api/chaos/reset || true
echo ""

echo "2. Clearing OpsPilot SQLite database..."
rm -f backend/opspilot.db opspilot.db

echo "Clean baseline restored successfully!"
echo "Ready for new demo run."
