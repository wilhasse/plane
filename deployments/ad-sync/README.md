# AD to Plane User Sync

Scripts for synchronizing Active Directory users to Plane.

## Scripts

| Script | Purpose |
|--------|---------|
| `docker-sync.sh` | Sync AD users to Plane (create/update accounts) |
| `set-ad-password.sh` | Manual: User sets their Plane password using AD credentials |
| `sync_full.py` | Fetches users from AD (runs inside container) |
| `plane_sync.py` | Creates/updates users in Plane (runs inside container) |
| `ad_login.py` | Verifies AD credentials and sets Plane password |

## Quick Start

### 1. Configure AD Connection

Set environment variables in your `.env`:

```env
AD_SERVER=192.168.20.5
AD_PORT=389
AD_BASE_DN=DC=yourdomain,DC=local
AD_USERS_OU=OU=Users
AD_BIND_USER=CN=service-account,OU=Services,DC=yourdomain,DC=local
AD_BIND_PASSWORD=your-service-account-password
```

### 2. Sync All AD Users to Plane

```bash
cd /path/to/plane
bash deployments/ad-sync/docker-sync.sh
```

Options:
- `--list` - List AD users without syncing
- `--dry-run` - Show what would be synced
- `--group "GroupName"` - Only sync users from specific AD group

### 3. Add Users to Workspace

After syncing users, add them to your workspace:

```bash
docker exec plane-api-1 python manage.py shell -c "
from plane.db.models import Workspace, User, WorkspaceMember

workspace = Workspace.objects.get(slug='your-workspace')
admin = User.objects.get(email='admin@example.com')

# Add all users from your domain
for user in User.objects.filter(email__endswith='@yourdomain.com'):
    if not WorkspaceMember.objects.filter(workspace=workspace, member=user).exists():
        WorkspaceMember.objects.create(
            workspace=workspace,
            member=user,
            role=15,  # 15=Member, 20=Admin
            created_by=admin,
            updated_by=admin,
        )
        print(f'Added: {user.email}')
"
```

## How It Works

```
                                    docker-sync.sh
                                          |
                                          v
+------------------+              +------------------+
|  Active Directory |  <------   |  sync_full.py    |
|  (Samba AD)       |   LDAP     |  (fetch users)   |
+------------------+              +--------+---------+
                                          |
                                          | JSON
                                          v
                                  +------------------+
                                  |  plane_sync.py   |
                                  |  (create users)  |
                                  +--------+---------+
                                          |
                                          v
                                  +------------------+
                                  |  Plane Database  |
                                  +------------------+
```

## User Authentication

This sync only creates user accounts. For authentication, use one of:

1. **LDAP Authentication** (recommended) - See `../ldap-auth/`
   - Users login with AD credentials directly
   - No password sync needed

2. **Password Sync** - Use `set-ad-password.sh`
   - User manually syncs their AD password to Plane
   - Must be run each time AD password changes

## Files

```
ad-sync/
├── README.md           # This documentation
├── docker-sync.sh      # Main sync script
├── sync_full.py        # Fetches users from AD
├── plane_sync.py       # Syncs users to Plane
├── ad_login.py         # AD credential verification
└── set-ad-password.sh  # Manual password sync
```
