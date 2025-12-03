#!/bin/bash
# Wait for MySQL to be ready before starting other services

DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-3306}
DB_USER=${DB_USER:-seerrbridge}
DB_PASSWORD=${DB_PASSWORD:-seerrbridge}
DB_NAME=${DB_NAME:-seerrbridge}
MAX_WAIT=${MAX_WAIT:-120}
WAITED=0

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Waiting for MySQL to be ready..."

while [ $WAITED -lt $MAX_WAIT ]; do
    # Try to connect using mysqladmin or mysql command
    if mysqladmin ping -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" --silent 2>/dev/null || \
       mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1" "$DB_NAME" >/dev/null 2>&1; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] MySQL is ready!"
        exit 0
    fi
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] MySQL not ready yet, waiting 2 seconds... (waited ${WAITED}/${MAX_WAIT}s)"
    sleep 2
    WAITED=$((WAITED + 2))
done

echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: MySQL did not become ready within ${MAX_WAIT} seconds"
exit 1

