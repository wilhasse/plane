#!/usr/bin/env python3
"""
Full AD to Plane Sync Script

This script runs inside the plane-api container and:
1. Fetches users from Active Directory using ldap3
2. Optionally outputs JSON for piping to plane_sync.py
3. Or directly syncs to Plane

Usage:
    python sync_full.py                    # List users
    python sync_full.py --output-json      # Output JSON for syncing
    python sync_full.py --list             # List users
    python sync_full.py --dry-run          # Show what would be synced
    python sync_full.py --group "Plane"    # Filter by AD group
"""

import os
import sys
import json
import argparse

# AD Configuration from environment
AD_SERVER = os.environ.get("AD_SERVER", "192.168.20.5")
AD_PORT = int(os.environ.get("AD_PORT", "389"))
AD_BASE_DN = os.environ.get("AD_BASE_DN", "DC=cslog,DC=local")
AD_USERS_OU = os.environ.get("AD_USERS_OU", "OU=Usuarios")
AD_BIND_USER = os.environ.get("AD_BIND_USER", "CN=infraestrutura,OU=Servicos,DC=cslog,DC=local")
AD_BIND_PASSWORD = os.environ.get("AD_BIND_PASSWORD", "")


def fetch_ad_users(group_filter=None):
    """Fetch users from Active Directory"""
    try:
        from ldap3 import Server, Connection, ALL, SUBTREE
    except ImportError:
        print("ERROR: ldap3 not installed. Run: pip install ldap3", file=sys.stderr)
        sys.exit(1)

    server = Server(AD_SERVER, port=AD_PORT, get_info=ALL)

    try:
        conn = Connection(server, user=AD_BIND_USER, password=AD_BIND_PASSWORD, auto_bind=True)
    except Exception as e:
        print(f"ERROR: Failed to connect to AD: {e}", file=sys.stderr)
        sys.exit(1)

    # Build search filter
    # Only active users with email addresses
    search_filter = "(&(objectClass=person)(mail=*)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"

    if group_filter:
        search_filter = f"(&{search_filter}(memberOf=CN={group_filter},OU=Grupos,{AD_BASE_DN}))"

    # Search for users
    search_base = f"{AD_USERS_OU},{AD_BASE_DN}"
    conn.search(
        search_base=search_base,
        search_filter=search_filter,
        search_scope=SUBTREE,
        attributes=["sAMAccountName", "mail", "displayName", "givenName", "sn"]
    )

    users = []
    for entry in conn.entries:
        user = {
            "username": str(entry.sAMAccountName) if hasattr(entry, "sAMAccountName") else "",
            "email": str(entry.mail).lower() if hasattr(entry, "mail") else "",
            "display_name": str(entry.displayName) if hasattr(entry, "displayName") else "",
            "first_name": str(entry.givenName) if hasattr(entry, "givenName") else "",
            "last_name": str(entry.sn) if hasattr(entry, "sn") else "",
        }
        if user["email"]:
            users.append(user)

    conn.unbind()
    return users


def main():
    parser = argparse.ArgumentParser(description="Sync AD users to Plane")
    parser.add_argument("--list", action="store_true", help="List AD users")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced")
    parser.add_argument("--output-json", action="store_true", help="Output JSON for piping")
    parser.add_argument("--group", type=str, help="Filter by AD group name")
    args = parser.parse_args()

    users = fetch_ad_users(group_filter=args.group)

    if args.output_json:
        # Output JSON only (for piping to plane_sync.py)
        print(json.dumps(users))
        return

    if args.list or args.dry_run:
        print(f"Found {len(users)} users in AD:")
        for u in users:
            print(f"  - {u['email']} ({u['display_name'] or u['username']})")

        if args.dry_run:
            print("\n[DRY RUN] Would sync these users to Plane")
        return

    # Default: list users
    print(f"Found {len(users)} users in AD")
    print("Use --output-json to get JSON for syncing")
    print("Use --list to see all users")


if __name__ == "__main__":
    main()
