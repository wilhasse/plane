#!/bin/bash
#
# Set Plane password using AD credentials
#
# This script verifies your AD password and sets it as your Plane password.
# Users run this once to sync their AD password to Plane.
#
# Usage:
#   ./set-ad-password.sh user@example.com
#

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <email>"
    echo "Example: $0 user@example.com"
    exit 1
fi

EMAIL="$1"

echo "=== Sync AD Password to Plane ==="
echo "Email: $EMAIL"
echo ""
read -s -p "Enter your AD (Windows) password: " PASSWORD
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Copy the AD login script to container
docker cp "$SCRIPT_DIR/ad_login.py" plane-api-1:/tmp/ad_login.py

# Run the verification and password set
RESULT=$(echo "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | \
    docker exec -i plane-api-1 python manage.py shell -c "exec(open('/tmp/ad_login.py').read())" 2>/dev/null | tail -1)

# Parse result
if echo "$RESULT" | grep -q '"success": true'; then
    echo ""
    echo "SUCCESS! Your Plane password has been synced with your AD password."
    echo "You can now login to Plane using your AD credentials."
else
    ERROR=$(echo "$RESULT" | grep -oP '"error": "\K[^"]+' || echo "Unknown error")
    echo ""
    echo "FAILED: $ERROR"
    exit 1
fi
