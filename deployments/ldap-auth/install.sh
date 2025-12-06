#!/bin/bash
#
# Install LDAP Authentication for Plane
#
# This script patches Plane to authenticate users against LDAP/Active Directory
# instead of (or in addition to) the local password database.
#
# Usage:
#   ./install.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "=== Installing LDAP Authentication for Plane ==="
echo ""

# 1. Backup original file
echo "1. Backing up original authentication file..."
docker exec plane-api-1 cp \
    /code/plane/authentication/provider/credentials/email.py \
    /code/plane/authentication/provider/credentials/email.py.bak

# 2. Install ldap3 library
echo "2. Installing ldap3 library..."
docker exec plane-api-1 pip install --quiet ldap3

# 3. Copy our modified file
echo "3. Installing LDAP authentication module..."
docker cp "$SCRIPT_DIR/email_ldap.py" \
    plane-api-1:/code/plane/authentication/provider/credentials/email.py

# 4. Also install in worker containers
echo "4. Installing in worker containers..."
for container in plane-worker-1 plane-beat-worker-1; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        docker exec $container pip install --quiet ldap3 2>/dev/null || true
        docker cp "$SCRIPT_DIR/email_ldap.py" \
            $container:/code/plane/authentication/provider/credentials/email.py 2>/dev/null || true
    fi
done

# 5. Restart API to apply changes
echo "5. Restarting Plane API..."
docker restart plane-api-1

echo ""
echo "=== Installation Complete ==="
echo ""
echo "LDAP Configuration (via environment variables):"
echo "  LDAP_ENABLED=1          (enable LDAP auth)"
echo "  LDAP_SERVER=192.168.20.5"
echo "  LDAP_PORT=389"
echo "  LDAP_DOMAIN=cslog.local"
echo ""
echo "To change these, add to your .env file and restart:"
echo "  docker compose down && docker compose up -d"
echo ""
echo "Users can now login with their AD credentials!"
