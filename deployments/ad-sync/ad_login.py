#!/usr/bin/env python3
"""
AD Login Bridge for Plane

This script runs inside the plane-api container and provides a way to
authenticate users via AD and set their Plane password.

Usage:
    # Set password for a user (verify AD first, then set in Plane)
    echo '{"email":"user@example.com","password":"ADPassword123"}' | \
        docker exec -i plane-api-1 python manage.py shell -c "exec(open('/tmp/ad_login.py').read())"
"""

import json
import sys
import os

# This script is meant to be run via: python manage.py shell -c "exec(open('...').read())"

# AD Configuration from environment
AD_SERVER = os.environ.get("AD_SERVER", "192.168.20.5")
AD_PORT = int(os.environ.get("AD_PORT", "389"))
AD_DOMAIN = os.environ.get("LDAP_DOMAIN", "cslog.local")


def verify_ad_credentials(email, password):
    """Verify credentials against Active Directory"""
    from ldap3 import Server, Connection, ALL

    username = email.split('@')[0]
    server = Server(AD_SERVER, port=AD_PORT, get_info=ALL)

    # Try UPN format
    try:
        conn = Connection(server, user=f"{username}@{AD_DOMAIN}", password=password, auto_bind=True)
        conn.unbind()
        return True
    except Exception:
        pass

    # Try DOMAIN\user format
    try:
        domain_short = AD_DOMAIN.split(".")[0].upper()
        conn = Connection(server, user=f"{domain_short}\\{username}", password=password, auto_bind=True)
        conn.unbind()
        return True
    except Exception:
        pass

    return False


def set_plane_password(email, password):
    """Set the user's password in Plane"""
    from plane.db.models import User

    try:
        user = User.objects.get(email=email.lower())
        user.set_password(password)
        user.is_password_autoset = False
        user.save()
        return True, f"Password set for {email}"
    except User.DoesNotExist:
        return False, f"User {email} not found in Plane"
    except Exception as e:
        return False, str(e)


# Main execution
if __name__ == '__main__' or True:  # Always run when exec'd
    # Read credentials from stdin
    try:
        data = json.loads(sys.stdin.read())
        email = data.get('email', '').lower()
        password = data.get('password', '')

        if not email or not password:
            print(json.dumps({'success': False, 'error': 'Email and password required'}))
            sys.exit(1)

        # Verify AD credentials
        if not verify_ad_credentials(email, password):
            print(json.dumps({'success': False, 'error': 'Invalid AD credentials'}))
            sys.exit(1)

        # Set Plane password
        success, message = set_plane_password(email, password)
        print(json.dumps({'success': success, 'message': message}))

    except json.JSONDecodeError:
        print(json.dumps({'success': False, 'error': 'Invalid JSON input'}))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))
