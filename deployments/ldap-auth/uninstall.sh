#!/bin/bash
#
# Uninstall LDAP Authentication - restore original Plane authentication
#

set -e

echo "=== Uninstalling LDAP Authentication ==="

# Restore backup
echo "Restoring original authentication file..."
docker exec plane-api-1 cp \
    /code/plane/authentication/provider/credentials/email.py.bak \
    /code/plane/authentication/provider/credentials/email.py

# Restore in workers too
for container in plane-worker-1 plane-beat-worker-1; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        docker exec $container cp \
            /code/plane/authentication/provider/credentials/email.py.bak \
            /code/plane/authentication/provider/credentials/email.py 2>/dev/null || true
    fi
done

# Restart
echo "Restarting Plane API..."
docker restart plane-api-1

echo ""
echo "LDAP authentication removed. Original password auth restored."
