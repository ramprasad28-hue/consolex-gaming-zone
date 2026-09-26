# Start command for managed platforms (Railway / Render / Heroku).
# PORT is injected by the platform; bind to it on all interfaces.
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 60