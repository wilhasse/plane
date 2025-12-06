#!/bin/bash
#
# AD to Plane User Sync - Docker Edition
# Runs the sync entirely within Docker containers
#
# Usage:
#   ./docker-sync.sh                    # Sync all users
#   ./docker-sync.sh --dry-run          # Show what would be synced
#   ./docker-sync.sh --group "Plane"    # Sync only users from "Plane" AD group
#   ./docker-sync.sh --list             # List AD users without syncing
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Load environment variables from .env
if [ -f .env ]; then
    export $(grep -E "^AD_" .env | xargs)
fi

# Parse arguments
ARGS="$@"

# Detect API container name (handles different docker compose project names)
API_CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "(plane-api-1|api-1)" | head -1)
if [ -z "$API_CONTAINER" ]; then
    echo "Error: Could not find API container"
    exit 1
fi
echo "Using container: $API_CONTAINER"

# First, ensure ldap3 is installed in the api container
echo "Installing ldap3 in $API_CONTAINER..."
docker exec "$API_CONTAINER" pip install --quiet ldap3 2>/dev/null || true

# Copy sync scripts to container
docker cp "$SCRIPT_DIR/sync_full.py" "$API_CONTAINER:/tmp/sync_full.py"
docker cp "$SCRIPT_DIR/plane_sync.py" "$API_CONTAINER:/tmp/plane_sync.py"

# Build docker exec env flags for AD settings
AD_ENV_FLAGS="-e AD_SERVER=$AD_SERVER -e AD_PORT=$AD_PORT -e AD_BASE_DN=$AD_BASE_DN -e AD_USERS_OU=$AD_USERS_OU -e AD_BIND_USER=$AD_BIND_USER -e AD_BIND_PASSWORD=$AD_BIND_PASSWORD"

# Run the full sync
if [[ "$ARGS" == *"--list"* ]] || [[ "$ARGS" == *"--dry-run"* ]]; then
    # Just list or dry-run - run sync_full.py directly
    docker exec $AD_ENV_FLAGS "$API_CONTAINER" python /tmp/sync_full.py $ARGS
else
    # Full sync - fetch from AD then sync to Plane
    echo "Fetching users from AD..."
    USERS_JSON=$(docker exec $AD_ENV_FLAGS "$API_CONTAINER" python /tmp/sync_full.py --output-json $ARGS 2>/dev/null | tail -1)

    if [ -z "$USERS_JSON" ] || [ "$USERS_JSON" == "[]" ]; then
        echo "No users found to sync"
        exit 0
    fi

    echo "Syncing users to Plane..."
    echo "$USERS_JSON" | docker exec -i "$API_CONTAINER" python manage.py shell -c "
import json
import sys
import secrets

# Read user data from stdin
users_data = json.loads(sys.stdin.read())

from plane.db.models import User

def generate_temp_password():
    return secrets.token_urlsafe(16)

results = {'created': [], 'updated': [], 'unchanged': [], 'errors': []}

for user_data in users_data:
    email = user_data['email'].lower()
    try:
        try:
            user = User.objects.get(email=email)
            # Update existing user
            updated = False
            changes = []
            if user_data.get('first_name') and user.first_name != user_data['first_name']:
                user.first_name = user_data['first_name']
                updated = True
                changes.append('first_name')
            if user_data.get('last_name') and user.last_name != user_data['last_name']:
                user.last_name = user_data['last_name']
                updated = True
                changes.append('last_name')
            if user_data.get('display_name') and user.display_name != user_data['display_name']:
                user.display_name = user_data['display_name']
                updated = True
                changes.append('display_name')
            if updated:
                user.save()
                results['updated'].append({'email': email, 'changes': changes})
            else:
                results['unchanged'].append({'email': email})
        except User.DoesNotExist:
            # Create new user
            temp_password = generate_temp_password()
            user = User.objects.create(
                email=email,
                username=email,
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                display_name=user_data.get('display_name') or email.split('@')[0],
                is_active=True,
                is_email_verified=True,
                is_password_autoset=True,
            )
            user.set_password(temp_password)
            user.save()
            results['created'].append({'email': email, 'temp_password': temp_password})
    except Exception as e:
        results['errors'].append({'email': email, 'error': str(e)})

# Print summary
print(f'\\n=== Sync Summary ===')
print(f'Created: {len(results[\"created\"])}')
print(f'Updated: {len(results[\"updated\"])}')
print(f'Unchanged: {len(results[\"unchanged\"])}')
print(f'Errors: {len(results[\"errors\"])}')

if results['created']:
    print(f'\\n--- Created Users ---')
    for r in results['created']:
        print(f'  {r[\"email\"]} (temp password: {r[\"temp_password\"]})')

if results['updated']:
    print(f'\\n--- Updated Users ---')
    for r in results['updated']:
        print(f'  {r[\"email\"]} ({\", \".join(r.get(\"changes\", []))})')

if results['errors']:
    print(f'\\n--- Errors ---')
    for r in results['errors']:
        print(f'  {r[\"email\"]}: {r[\"error\"]}')
"
fi

echo ""
echo "Done!"
