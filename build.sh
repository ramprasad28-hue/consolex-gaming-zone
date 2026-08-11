#!/usr/bin/env bash
# ─────────────────────────────────────────────
# File: build.sh
# Run by Railway / Render on every deploy
# ─────────────────────────────────────────────

set -e  # Exit on any error

# Force production settings unless the platform explicitly overrides it.
# Prevents a deploy from silently running with DEBUG=True / dev settings.
export DJANGO_ENV="${DJANGO_ENV:-production}"

echo "▶ Installing dependencies..."
pip install -r requirements/base.txt
pip install -r requirements/production.txt

echo "▶ Collecting static files..."
python manage.py collectstatic --noinput

echo "▶ Running migrations..."
python manage.py migrate --noinput

echo "✅ Build complete."