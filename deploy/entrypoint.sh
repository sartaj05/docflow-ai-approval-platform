#!/bin/sh

set -e

echo "Waiting for PostgreSQL..."
python /app/deploy/wait_for_postgres.py

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting command: $@"
exec "$@"