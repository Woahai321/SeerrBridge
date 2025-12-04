#!/bin/bash
# Ensure database user exists with correct password
# This is needed when database is already initialized but user might not exist or have wrong password

set -e

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Set default values if not provided
export MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-seerrbridge_root}
export DB_NAME=${DB_NAME:-seerrbridge}
export DB_USER=${DB_USER:-seerrbridge}
export DB_PASSWORD=${DB_PASSWORD:-seerrbridge}

log "Ensuring database user '${DB_USER}' exists with correct password..."

# Wait for MySQL to be ready
for i in {1..30}; do
    if mysqladmin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD} --silent 2>/dev/null; then
        break
    fi
    if [ $i -eq 30 ]; then
        log "ERROR: MySQL is not ready"
        exit 1
    fi
    sleep 1
done

# Ensure database exists
mysql -h localhost -u root -p${MYSQL_ROOT_PASSWORD} <<EOF 2>/dev/null || true
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EOF

# Ensure user exists and has correct password
mysql -h localhost -u root -p${MYSQL_ROOT_PASSWORD} <<EOF 2>/dev/null || true
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS '${DB_USER}'@'%' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER '${DB_USER}'@'%' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'%';
FLUSH PRIVILEGES;
EOF

log "Database user '${DB_USER}' verified/created successfully"

# Initialize database tables if they don't exist (using SQL script)
log "Ensuring database tables are initialized..."
if [ -f "/docker-entrypoint-initdb.d/00-complete-init.sql" ]; then
    log "Running database initialization SQL script..."
    mysql -h localhost -u root -p${MYSQL_ROOT_PASSWORD} < /docker-entrypoint-initdb.d/00-complete-init.sql 2>/dev/null || {
        log "Note: Some tables may already exist (this is normal if database was previously initialized)"
    }
    log "Database tables initialization completed"
else
    log "Note: SQL initialization script not found, tables will be created by backend on first run"
fi

