# Plane Deployment with LDAP/Active Directory Integration

This directory contains deployment configurations for Plane with LDAP/Active Directory integration.

## Features

- **Direct LDAP Authentication**: Users can login with their AD credentials directly
- **AD User Sync**: Automatically sync users from Active Directory to Plane
- **Authelia OIDC** (Optional): Use Authelia as an OIDC provider for SSO

## Quick Start

### 1. Configure Environment

```bash
cd deployments
cp .env.ldap.example .env

# Edit .env with your settings:
# - APP_DOMAIN
# - LDAP_SERVER, LDAP_DOMAIN
# - AD_* settings for user sync
# - SECRET_KEY (generate with: openssl rand -hex 32)
```

### 2. Start Plane

```bash
docker compose -f docker-compose.ldap.yml up -d
```

### 3. Enable LDAP Authentication

```bash
bash ldap-auth/install.sh
```

### 4. Sync AD Users (Optional)

```bash
bash ad-sync/docker-sync.sh
```

## Directory Structure

```
deployments/
├── README.md                    # This file
├── docker-compose.ldap.yml      # Docker Compose with LDAP support
├── .env.ldap.example            # Environment template
│
├── ldap-auth/                   # Direct LDAP authentication
│   ├── README.md
│   ├── email_ldap.py            # Modified authentication module
│   ├── install.sh               # Installation script
│   └── uninstall.sh             # Uninstallation script
│
├── ad-sync/                     # AD user synchronization
│   ├── README.md
│   ├── docker-sync.sh           # Main sync script
│   ├── sync_full.py             # Fetch users from AD
│   ├── plane_sync.py            # Create users in Plane
│   ├── ad_login.py              # AD credential verification
│   └── set-ad-password.sh       # Manual password sync
│
└── authelia/                    # Authelia OIDC provider (optional)
    ├── README.md
    └── config/
        └── configuration.yml.example
```

## Authentication Options

### Option 1: Direct LDAP Authentication (Recommended)

Users login with email + AD password. Plane verifies credentials directly against AD.

```
User → Plane Login → LDAP/AD Server → Success/Fail
```

**Setup:**
1. Start Plane with `docker-compose.ldap.yml`
2. Run `ldap-auth/install.sh`
3. Sync users with `ad-sync/docker-sync.sh`

### Option 2: Authelia OIDC

Users click "Login with OIDC" and are redirected to Authelia for authentication.

```
User → Plane → Authelia → AD → Authelia → Plane
```

**Setup:**
1. Configure `authelia/config/configuration.yml`
2. Start Plane with Authelia
3. Configure OIDC in Plane's admin panel

## Upgrading Plane

When upgrading Plane to a new version:

```bash
# Pull new images
docker compose -f docker-compose.ldap.yml pull

# Restart
docker compose -f docker-compose.ldap.yml down
docker compose -f docker-compose.ldap.yml up -d

# Wait for API to be ready
sleep 30

# Re-apply LDAP authentication
bash ldap-auth/install.sh
```

## Troubleshooting

### Check if LDAP is working

```bash
docker exec plane-api-1 head -20 /code/plane/authentication/provider/credentials/email.py
```

### View logs

```bash
docker logs plane-api-1 --tail 100 | grep -i "ldap\|auth"
```

### Test AD connection

```bash
docker exec plane-api-1 python -c "
from ldap3 import Server, Connection, ALL
server = Server('YOUR_AD_SERVER', port=389, get_info=ALL)
conn = Connection(server, user='user@domain.local', password='password', auto_bind=True)
print('SUCCESS' if conn.bound else 'FAILED')
conn.unbind()
"
```
