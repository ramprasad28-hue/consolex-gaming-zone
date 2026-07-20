#!/usr/bin/env bash
# ─────────────────────────────────────────────
# File: build.sh
# Run by Railway / Render on every deploy
# ─────────────────────────────────────────────

set -e  # Exit on any error

echo "▶ Installing dependencies..."
pip install -r apps/requirements/production.txt

echo "▶ Collecting static files..."
python manage.py collectstatic --noinput

echo "▶ Running migrations..."
python manage.py migrate --noinput

echo "✅ Build complete."