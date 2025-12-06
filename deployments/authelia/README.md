# Authelia OIDC Provider for Plane

Authelia can be used as an OIDC provider to enable Single Sign-On (SSO) with your Active Directory.

## Architecture

```
User Browser
     |
     v
+--------------------+
| Plane Login Page   |
| "Login with OIDC"  |
+--------+-----------+
         |
         | Redirect
         v
+--------------------+
| Authelia           |
| (OIDC Provider)    |
+--------+-----------+
         |
         | LDAP Auth
         v
+--------------------+
| Active Directory   |
| (Samba AD)         |
+--------------------+
```

## Setup

### 1. Generate Secrets

```bash
# Generate all required secrets
openssl rand -hex 32  # JWT secret
openssl rand -hex 32  # Session secret
openssl rand -hex 32  # Encryption key
openssl rand -hex 32  # HMAC secret

# Generate RSA key for OIDC
openssl genrsa -out oidc.pem 4096

# Generate client secret hash
# First, choose a client secret (e.g., "my-plane-secret")
# Then hash it:
docker run --rm authelia/authelia:latest crypto hash generate pbkdf2 --variant sha512 --password 'my-plane-secret'
```

### 2. Configure Authelia

```bash
cd deployments/authelia/config
cp configuration.yml.example configuration.yml

# Edit configuration.yml with your values:
# - AD server address
# - AD credentials
# - Domain names
# - Generated secrets
```

### 3. Configure Plane for OIDC

In Plane's God Mode (Admin panel), configure OIDC:

- **Provider Name**: Authelia
- **Client ID**: plane
- **Client Secret**: your-plain-text-secret (not the hash)
- **Authorization URL**: https://authelia.yourdomain.com/api/oidc/authorization
- **Token URL**: https://authelia.yourdomain.com/api/oidc/token
- **User Info URL**: https://authelia.yourdomain.com/api/oidc/userinfo
- **Scopes**: openid profile email

### 4. Start Authelia

Add to your docker-compose.yml:

```yaml
services:
  authelia:
    image: authelia/authelia:latest
    deploy:
      replicas: 1
      restart_policy:
        condition: any
    volumes:
      - ./authelia/config:/config
    ports:
      - "9091:9091"
```

Then:

```bash
docker compose up -d authelia
```

## Files

```
authelia/
├── README.md                           # This documentation
└── config/
    ├── configuration.yml.example       # Template configuration
    ├── configuration.yml               # Your actual configuration (git-ignored)
    ├── db.sqlite3                       # SQLite database (auto-created)
    └── notification.txt                 # Notification log (auto-created)
```

## Security Notes

1. **Secrets**: Never commit `configuration.yml` with real secrets to git
2. **HTTPS**: Always use HTTPS in production
3. **LDAPS**: Consider using LDAPS (port 636) for encrypted AD communication

## Troubleshooting

### View Authelia logs

```bash
docker logs authelia --tail 100
```

### Test OIDC discovery

```bash
curl https://authelia.yourdomain.com/.well-known/openid-configuration
```

### Common Issues

| Issue | Solution |
|-------|----------|
| "Invalid client" | Check client_id matches in Authelia and Plane |
| "Invalid redirect URI" | Ensure redirect_uris includes your Plane callback URL |
| LDAP connection failed | Check AD server address and credentials |
