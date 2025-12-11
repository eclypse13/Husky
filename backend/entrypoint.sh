#!/bin/bash
set -e

echo "Waiting for MongoDB to be ready..."

MAX_RETRIES=30
RETRY_COUNT=0

until nc -z mongodb 27017 || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
  echo "MongoDB is unavailable - sleeping (attempt $RETRY_COUNT/$MAX_RETRIES)"
  RETRY_COUNT=$((RETRY_COUNT+1))
  sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "ERROR: MongoDB did not become ready in time"
  exit 1
fi

echo "MongoDB is ready!"
sleep 3

echo "Testing Django configuration..."
python manage.py check || {
    echo "ERROR: Django check failed!"
    exit 1
}

echo "Running Django migrations..."
python manage.py migrate --noinput || true

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Starting application..."
exec "$@"