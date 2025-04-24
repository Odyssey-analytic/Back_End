#!/bin/bash
python manage.py makemigrations
python manage.py migrate

# Start both Celery and Uvicorn in the background
celery -A backend worker -l info &
uvicorn backend.asgi:application --host 0.0.0.0 --port 8000