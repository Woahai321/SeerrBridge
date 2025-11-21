#!/bin/bash

# Database Initialization Script
# This script ensures the database is properly initialized with all required tables and data

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DB_HOST=${DB_HOST:-mysql}
DB_PORT=${DB_PORT:-3306}
DB_NAME=${DB_NAME:-seerrbridge}
DB_USER=${DB_USER:-seerrbridge}
DB_PASSWORD=${DB_PASSWORD:-seerrbridge}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-seerrbridge_root}

echo -e "${GREEN}Starting database initialization...${NC}"

# Wait for MySQL to be ready
echo -e "${YELLOW}Waiting for MySQL to be ready...${NC}"
until mysqladmin ping -h"$DB_HOST" -P"$DB_PORT" -u"root" -p"$MYSQL_ROOT_PASSWORD" --silent; do
    echo "Waiting for MySQL to be ready..."
    sleep 2
done

echo -e "${GREEN}MySQL is ready!${NC}"

# Run the complete initialization script
echo -e "${YELLOW}Running database initialization script...${NC}"
mysql -h"$DB_HOST" -P"$DB_PORT" -u"root" -p"$MYSQL_ROOT_PASSWORD" < mysql-init/00-complete-init.sql

echo -e "${GREEN}Database initialization completed successfully!${NC}"

# Verify the database was created properly
echo -e "${YELLOW}Verifying database setup...${NC}"
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -D"$DB_NAME" -e "SHOW TABLES;" | grep -E "(unified_media|log_entries|notification_settings|system_config)" && echo -e "${GREEN}✓ Core tables verified${NC}" || echo -e "${RED}✗ Core tables missing${NC}"

echo -e "${GREEN}Database initialization script completed!${NC}"
