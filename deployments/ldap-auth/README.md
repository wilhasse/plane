# Plane LDAP/Active Directory Authentication

This modification allows Plane to authenticate users directly against LDAP/Active Directory (Samba AD), eliminating the need for password synchronization.

## How It Works

```
User Login (email + password)
         |
         v
+-----------------------------+
|  Plane Login Form           |
|  plane.yourdomain.com       |
+-------------+---------------+
              |
              v
+-----------------------------+
|  Modified email.py          |
|  (LDAP Authentication)      |
+-------------+---------------+
              |
              v
+-----------------------------+
|  1. Try LDAP/AD auth first  |---> AD Server
|  2. Fallback to local DB    |
+-------------+---------------+
              |
              v
         Login Success/Fail
```

## Files Modified

Only **ONE file** is modified in Plane:

```
/code/plane/authentication/provider/credentials/email.py
```

The original file is backed up to:
```
/code/plane/authentication/provider/credentials/email.py.bak
```

## Installation

### Quick Install

```bash
cd /path/to/plane
bash deployments/ldap-auth/install.sh
```

### Manual Installation

1. Install ldap3 library:
```bash
docker exec plane-api-1 pip install ldap3
```

2. Backup original file:
```bash
docker exec plane-api-1 cp \
    /code/plane/authentication/provider/credentials/email.py \
    /code/plane/authentication/provider/credentials/email.py.bak
```

3. Copy modified file:
```bash
docker cp deployments/ldap-auth/email_ldap.py \
    plane-api-1:/code/plane/authentication/provider/credentials/email.py
```

4. Restart API:
```bash
docker restart plane-api-1
```

## Uninstall / Restore Original

```bash
cd /path/to/plane
bash deployments/ldap-auth/uninstall.sh
```

## Configuration

LDAP settings are configured via environment variables in `.env`:

```env
LDAP_ENABLED=1
LDAP_SERVER=192.168.20.5
LDAP_PORT=389
LDAP_DOMAIN=cslog.local
```

| Variable | Default | Description |
|----------|---------|-------------|
| `LDAP_ENABLED` | `1` | Enable/disable LDAP auth (1=enabled, 0=disabled) |
| `LDAP_SERVER` | `192.168.20.5` | LDAP/AD server IP or hostname |
| `LDAP_PORT` | `389` | LDAP port (389=standard, 636=SSL) |
| `LDAP_DOMAIN` | `cslog.local` | AD domain for authentication |

After changing `.env`, restart the containers and re-apply the modification:

```bash
docker compose down && docker compose up -d
bash deployments/ldap-auth/install.sh
```

## Upgrading Plane

When you upgrade Plane to a new version:

1. The containers will be recreated with fresh images
2. The modification will be lost
3. Re-apply it after upgrade:

```bash
# Pull new version and restart
docker compose pull
docker compose down && docker compose up -d

# Wait for API to be ready
sleep 30

# Re-apply LDAP modification
bash deployments/ldap-auth/install.sh
```

## Security Notes

1. **LDAP vs LDAPS**: Current config uses LDAP (port 389, unencrypted). For production, consider using LDAPS (port 636) with SSL.

2. **Fallback**: If LDAP fails, the system falls back to local password. This is intentional for:
   - Admin recovery if AD is down
   - Service accounts that don't exist in AD

3. **No passwords stored**: AD passwords are never stored in Plane - they're verified in real-time against AD.

## Troubleshooting

### Check if LDAP modification is applied

```bash
docker exec plane-api-1 head -20 /code/plane/authentication/provider/credentials/email.py
```

Should show `LDAP_ENABLED`, `LDAP_SERVER`, etc.

### Check if ldap3 is installed

```bash
docker exec plane-api-1 pip list | grep ldap3
```

### Test LDAP connection

```bash
docker exec plane-api-1 python -c "
from ldap3 import Server, Connection, ALL
server = Server('YOUR_AD_SERVER', port=389, get_info=ALL)
conn = Connection(server, user='user@domain.local', password='PASSWORD', auto_bind=True)
print('SUCCESS' if conn.bound else 'FAILED')
conn.unbind()
"
```

### View authentication logs

```bash
docker logs plane-api-1 --tail 100 | grep -i "ldap\|auth"
```
