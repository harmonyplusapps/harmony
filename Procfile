web: gunicorn harmony.wsgi:application
worker: celery -A harmony worker --loglevel=info
beat: celery -A harmony beat --loglevel=info
