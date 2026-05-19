#!/usr/bin/env python3
"""
Plane User Sync Script - Runs inside the Plane API container
Syncs users from Active Directory to Plane via Django ORM

This script should be copied to and executed inside the plane-api container.
"""

import os
import sys
import json
import secrets

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plane.settings.production')

import django
django.setup()

from plane.db.models import Profile, User


def generate_temp_password():
    """Generate a secure temporary password"""
    return secrets.token_urlsafe(16)


def sync_user(user_data, dry_run=False):
    """Sync a single user to Plane"""
    email = user_data['email'].lower()

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

        if updated and not dry_run:
            user.save()
            Profile.objects.get_or_create(user=user)
            return {'status': 'updated', 'email': email, 'changes': changes}
        elif updated:
            return {'status': 'would_update', 'email': email, 'changes': changes}
        if not dry_run:
            Profile.objects.get_or_create(user=user)
        return {'status': 'unchanged', 'email': email}

    except User.DoesNotExist:
        if dry_run:
            return {'status': 'would_create', 'email': email}

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
        Profile.objects.create(user=user)

        return {
            'status': 'created',
            'email': email,
            'temp_password': temp_password
        }


def main():
    # Read user data from stdin or command line argument
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            users_data = json.load(f)
    else:
        users_data = json.load(sys.stdin)

    dry_run = os.environ.get('DRY_RUN', '0') == '1'

    if dry_run:
        print("[DRY RUN MODE]")

    results = {
        'created': [],
        'updated': [],
        'unchanged': [],
        'errors': []
    }

    for user_data in users_data:
        try:
            result = sync_user(user_data, dry_run)

            if result['status'] in ('created', 'would_create'):
                results['created'].append(result)
            elif result['status'] in ('updated', 'would_update'):
                results['updated'].append(result)
            else:
                results['unchanged'].append(result)

        except Exception as e:
            results['errors'].append({
                'email': user_data.get('email', 'unknown'),
                'error': str(e)
            })

    # Print summary
    print(f"\n=== Sync Summary ===")
    print(f"Created: {len(results['created'])}")
    print(f"Updated: {len(results['updated'])}")
    print(f"Unchanged: {len(results['unchanged'])}")
    print(f"Errors: {len(results['errors'])}")

    if results['created']:
        print(f"\n--- Created Users ---")
        for r in results['created']:
            if 'temp_password' in r:
                print(f"  {r['email']} (temp password: {r['temp_password']})")
            else:
                print(f"  {r['email']} (would create)")

    if results['updated']:
        print(f"\n--- Updated Users ---")
        for r in results['updated']:
            print(f"  {r['email']} ({', '.join(r.get('changes', []))})")

    if results['errors']:
        print(f"\n--- Errors ---")
        for r in results['errors']:
            print(f"  {r['email']}: {r['error']}")


if __name__ == '__main__':
    main()
