#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Set default values if not provided
export MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-seerrbridge_root}
export DB_NAME=${DB_NAME:-seerrbridge}
export DB_USER=${DB_USER:-seerrbridge}
export DB_PASSWORD=${DB_PASSWORD:-seerrbridge}
export DB_HOST=${DB_HOST:-localhost}
export DB_PORT=${DB_PORT:-3306}

log "Starting SeerrBridge Unified Container..."
log "Database: ${DB_NAME} | User: ${DB_USER} | Host: ${DB_HOST}:${DB_PORT}"

# ==============================================================================
# Step 0: Restore data files if volume mount is empty
# ==============================================================================
log "Step 0/6: Checking data files..."

# Check if unified.json exists in mounted data directory
if [ ! -f "/app/data/unified.json" ]; then
    # Volume mount is empty or file doesn't exist
    if [ -f "/app/data-default/unified.json" ]; then
        log "Restoring data files from image backup..."
        # Copy all JSON files from backup to data directory
        # Only copy if destination doesn't exist (preserve user's files)
        for json_file in /app/data-default/*.json; do
            if [ -f "$json_file" ]; then
                filename=$(basename "$json_file")
                if [ ! -f "/app/data/$filename" ]; then
                    cp "$json_file" "/app/data/$filename"
                    log "Restored: $filename"
                fi
            fi
        done
        
        # Restore images directory if it doesn't exist or is empty
        if [ ! -d "/app/data/images" ] || [ -z "$(ls -A /app/data/images 2>/dev/null)" ]; then
            if [ -d "/app/data-default/images" ] && [ -n "$(ls -A /app/data-default/images 2>/dev/null)" ]; then
                log "Restoring images from image backup..."
                mkdir -p /app/data/images
                cp -r /app/data-default/images/* /app/data/images/ 2>/dev/null || true
                log "Images restored successfully"
            fi
        else
            log "Images directory already exists in mounted volume"
        fi
        
        chmod -R 755 /app/data
        log "Data files restored successfully"
    else
        log_warn "No data files found in image backup. Collections feature may not work."
    fi
else
    log "Data files already present in mounted volume"
    # Still check if images need to be restored even if JSON files exist
    if [ ! -d "/app/data/images" ] || [ -z "$(ls -A /app/data/images 2>/dev/null)" ]; then
        if [ -d "/app/data-default/images" ] && [ -n "$(ls -A /app/data-default/images 2>/dev/null)" ]; then
            log "Restoring images from image backup..."
            mkdir -p /app/data/images
            cp -r /app/data-default/images/* /app/data/images/ 2>/dev/null || true
            chmod -R 755 /app/data/images
            log "Images restored successfully"
        fi
    fi
fi

# ==============================================================================
# Step 1: Initialize MariaDB
# ==============================================================================
log "Step 1/6: Initializing MariaDB..."

# Check if database is already initialized by checking if data directory exists
# If it exists, we assume it's already initialized and skip setup
if [ -d "/var/lib/mysql/mysql" ] && [ "$(ls -A /var/lib/mysql/mysql 2>/dev/null)" ]; then
    log "MariaDB data directory already exists and contains data, skipping initialization..."
    log "Database is already initialized, proceeding to start services..."
    log "Note: Database user will be verified/created after MySQL starts via ensure-db-user.sh"
else
    log "MariaDB data directory doesn't exist or is empty, initializing..."
    # Create MariaDB data directory if it doesn't exist
    if [ ! -d "/var/lib/mysql/mysql" ]; then
        log "Initializing MariaDB data directory..."
        # Try mariadb-install-db first (MariaDB 10.5+), fallback to mysql_install_db
        if command -v mariadb-install-db >/dev/null 2>&1; then
            mariadb-install-db --user=mysql --datadir=/var/lib/mysql --skip-test-db
        elif command -v mysql_install_db >/dev/null 2>&1; then
            mysql_install_db --user=mysql --datadir=/var/lib/mysql
        else
            log_warn "No MariaDB initialization tool found, MariaDB will initialize on first start"
        fi
    fi

    # Ensure proper permissions
    chown -R mysql:mysql /var/lib/mysql /var/run/mysqld
    chmod 755 /var/lib/mysql /var/run/mysqld

    # Start MariaDB temporarily to initialize database
    log "Starting MariaDB for initialization..."
    # Use mariadbd-safe if available, fallback to mysqld_safe
    if command -v mariadbd-safe >/dev/null 2>&1; then
        mariadbd-safe --default-authentication-plugin=mysql_native_password \
            --datadir=/var/lib/mysql \
            --user=mysql \
            --skip-networking \
            --socket=/var/run/mysqld/mysqld.sock &
    else
        mysqld_safe --default-authentication-plugin=mysql_native_password \
            --datadir=/var/lib/mysql \
            --user=mysql \
            --skip-networking \
            --socket=/var/run/mysqld/mysqld.sock &
    fi
    MYSQL_PID=$!

    # Wait for MariaDB to be ready
    log "Waiting for MariaDB to be ready..."
    for i in {1..30}; do
        if mysqladmin ping --socket=/var/run/mysqld/mysqld.sock --silent 2>/dev/null; then
            log "MariaDB is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "MariaDB failed to start within 30 seconds"
            exit 1
        fi
        sleep 1
    done

    # Set root password and create database/user (only if not already set)
    log "Setting up MariaDB database and user..."
    mysql --socket=/var/run/mysqld/mysqld.sock <<EOF
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS '${DB_USER}'@'%' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'%';
FLUSH PRIVILEGES;
EOF

    # Run initialization scripts (only on first run)
    if [ -d "/docker-entrypoint-initdb.d" ]; then
        log "Running database initialization scripts..."
        for f in /docker-entrypoint-initdb.d/*.sql; do
            if [ -f "$f" ]; then
                log "Executing $f..."
                mysql --socket=/var/run/mysqld/mysqld.sock -u root -p${MYSQL_ROOT_PASSWORD} < "$f" 2>/dev/null || \
                mysql --socket=/var/run/mysqld/mysqld.sock -u root < "$f" 2>/dev/null || true
            fi
        done
    fi

    # Stop temporary MariaDB instance
    log "Stopping temporary MariaDB instance..."
    # Try graceful shutdown first using mysqladmin (with root password)
    if mysqladmin --socket=/var/run/mysqld/mysqld.sock ping >/dev/null 2>&1; then
        mysqladmin --socket=/var/run/mysqld/mysqld.sock -u root -p${MYSQL_ROOT_PASSWORD} shutdown 2>/dev/null || \
        mysqladmin --socket=/var/run/mysqld/mysqld.sock -u root shutdown 2>/dev/null || true
        log "Sent shutdown signal to MariaDB"
    else
        log_warn "MariaDB not responding to ping, may already be stopped"
    fi

    # Wait for process to stop (with timeout)
    TIMEOUT=15
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ]; do
        # Check if the process is still running
        if ! kill -0 $MYSQL_PID 2>/dev/null; then
            log "MariaDB stopped gracefully"
            break
        fi
        sleep 1
        ELAPSED=$((ELAPSED + 1))
        if [ $((ELAPSED % 5)) -eq 0 ]; then
            log "Still waiting for MariaDB to stop... (${ELAPSED}/${TIMEOUT}s)"
        fi
    done

    # If still running, force kill
    if kill -0 $MYSQL_PID 2>/dev/null; then
        log_warn "MariaDB didn't stop gracefully, forcing shutdown..."
        kill -9 $MYSQL_PID 2>/dev/null || true
        sleep 2
    fi

    # Clean up any remaining MariaDB processes (but don't kill supervisor's instance)
    pkill -f "mysqld_safe.*skip-networking" 2>/dev/null || true
    pkill -f "mariadbd.*skip-networking" 2>/dev/null || true
    sleep 1
    log "MariaDB initialization completed"
fi

# ==============================================================================
# Step 2: Start Supervisor (which will manage all services)
# ==============================================================================
log "Step 2/6: Starting Supervisor process manager..."

# Create log directory
mkdir -p /app/logs
chmod 755 /app/logs

# Wait a moment for MySQL to fully stop
sleep 2

# Start supervisor (which will start MySQL, then frontend, then backend)
log "Starting all services via Supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf

