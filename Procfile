web: gunicorn medical_shop.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120
worker: celery -A medical_shop worker -l info --concurrency 1
