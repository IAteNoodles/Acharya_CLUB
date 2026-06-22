#!/bin/sh
set -e

echo "Running Alembic migrations..."
if alembic upgrade head; then
    echo "Migrations complete."
else
    echo "WARNING: Alembic migrations failed. Check DATABASE_URL / DB_PASSWORD."
    echo "The app will start but the database schema may be out of date."
fi

exec "$@"
