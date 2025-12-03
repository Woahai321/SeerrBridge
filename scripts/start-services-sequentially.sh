#!/bin/bash
# Start services in sequence: MySQL -> Frontend -> Backend

set -e

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Wait for supervisor to be ready
sleep 3

# Step 1: Wait for MySQL to be running
log "Waiting for MySQL to be running..."
for i in {1..30}; do
    if supervisorctl status mysql | grep -q "RUNNING"; then
        log "MySQL is running!"
        break
    fi
    if [ $i -eq 30 ]; then
        log "ERROR: MySQL failed to start"
        exit 1
    fi
    sleep 1
done

# Additional wait to ensure MySQL is fully ready
log "Waiting for MySQL to be fully ready..."
/app/scripts/wait-for-mysql.sh

# Step 2: Start frontend
log "Starting Nuxt frontend..."
supervisorctl start nuxt-frontend

# Wait for frontend to be running
log "Waiting for Nuxt frontend to be running..."
for i in {1..60}; do
    if supervisorctl status nuxt-frontend | grep -q "RUNNING"; then
        log "Nuxt frontend is running!"
        break
    fi
    if [ $i -eq 60 ]; then
        log "ERROR: Nuxt frontend failed to start"
        exit 1
    fi
    sleep 1
done

# Additional wait to ensure frontend is fully ready
log "Waiting for Nuxt frontend to be fully ready..."
/app/scripts/wait-for-frontend.sh

# Step 3: Start backend
log "Starting SeerrBridge backend..."
supervisorctl start seerrbridge-backend

log "All services started in sequence!"

# Keep script running (supervisor will keep it alive)
while true; do
    sleep 60
    # Optional: Check service health periodically
    if ! supervisorctl status mysql | grep -q "RUNNING"; then
        log "WARNING: MySQL is not running!"
    fi
    if ! supervisorctl status nuxt-frontend | grep -q "RUNNING"; then
        log "WARNING: Nuxt frontend is not running!"
    fi
    if ! supervisorctl status seerrbridge-backend | grep -q "RUNNING"; then
        log "WARNING: SeerrBridge backend is not running!"
    fi
done

