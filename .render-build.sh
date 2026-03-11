pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser --noinput || true
python manage.py collectstatic --noinput
