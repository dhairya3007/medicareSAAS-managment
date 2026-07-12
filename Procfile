web: gunicorn medical_shop.wsgi --log-file - --bind 0.0.0.0:$PORT
worker: celery -A medical_shop worker -l info -P solo
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
