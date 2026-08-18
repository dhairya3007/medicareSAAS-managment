#!/bin/bash
echo "Running migrations..."
python manage.py migrate --noinput
python manage.py create_superuser_if_not_exists

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Celery worker in the background..."
celery -A medical_shop worker -l info --concurrency 1 &

echo "Starting Gunicorn server..."
# Koyeb provides the PORT environment variable (defaults to 8000)
gunicorn medical_shop.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
