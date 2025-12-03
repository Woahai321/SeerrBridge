#!/bin/bash
# Wait for Nuxt frontend to be ready before starting backend

# Try both ports (3777 is expected, but 3000 might be used if PORT env var isn't set)
FRONTEND_PORTS="3777 3000"
MAX_WAIT=${MAX_WAIT:-120}
WAITED=0

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Waiting for Nuxt frontend to be ready..."

while [ $WAITED -lt $MAX_WAIT ]; do
    for PORT in $FRONTEND_PORTS; do
        if curl -f -s "http://localhost:${PORT}/api/health" >/dev/null 2>&1 || \
           curl -f -s "http://localhost:${PORT}/api/setup-status" >/dev/null 2>&1; then
            echo "[$(date +'%Y-%m-%d %H:%M:%S')] Nuxt frontend is ready on port ${PORT}!"
            exit 0
        fi
    done
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Frontend not ready yet, waiting 2 seconds... (waited ${WAITED}/${MAX_WAIT}s)"
    sleep 2
    WAITED=$((WAITED + 2))
done

echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: Nuxt frontend did not become ready within ${MAX_WAIT} seconds"
exit 1

