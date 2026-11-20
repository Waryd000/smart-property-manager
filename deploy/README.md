# Cloud VPS deployment guide

This deployment package is prepared for an Ubuntu LTS VPS using Docker Compose, PostgreSQL, Redis/Celery and Caddy automatic HTTPS. **It has not been deployed to a real VPS yet.** A server, domain and authorised access path are still required.

## Before deployment

1. Provision a supported Ubuntu LTS server and create a non-root deployment user with Docker access.
2. Point the domain's DNS A/AAAA record at the VPS. Allow inbound TCP 80/443 and restrict SSH to trusted administrator IPs. Do not open PostgreSQL or Redis to the public internet.
3. Install Docker Engine and the Docker Compose plugin from Docker's official repository.
4. Ensure the VPS has a persistent disk with adequate capacity and a separate off-site backup destination.
5. Install `age` for encrypted backups. Generate an age key pair on an administrator-controlled device. Store the private identity offline and copy only the public recipient to `deploy/backup.age-recipient` on the VPS.

## Configure secrets

From the repository root on the VPS:

```bash
cp .env.production.example .env.production
chmod 600 .env.production
nano .env.production
```

Replace every example value:
- `DOMAIN`, `ACME_EMAIL`, `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- A newly generated `SECRET_KEY` (never reuse a key that has been shared in a chat or committed).
- A long random `DB_PASSWORD` with URL-safe characters.
- SMTP account details if outbound email is configured.

Keep `.env.production` outside Git. The sample is not an operational secret file. Confirm DNS resolves to the VPS before starting Caddy; Caddy obtains and renews TLS certificates automatically when public DNS and ports 80/443 are correct.

## Validate and start

```bash
docker compose --env-file .env.production -f compose.production.yml config --quiet
docker compose --env-file .env.production -f compose.production.yml build
docker compose --env-file .env.production -f compose.production.yml up -d
docker compose --env-file .env.production -f compose.production.yml ps
docker compose --env-file .env.production -f compose.production.yml logs -f web caddy
```

The web container applies committed database migrations and collects static assets at startup. PostgreSQL and Redis are only reachable on the private Docker network. Caddy handles HTTPS and proxies requests to Gunicorn. Celery Beat schedules the monthly rent-charge task for 00:10 on day one in `Africa/Kampala`.

Create the initial administrator only after the services are healthy:

```bash
docker compose --env-file .env.production -f compose.production.yml exec web python manage.py createsuperuser
```

Check `https://YOUR_DOMAIN/healthz/` (expected JSON `{"status":"ok","database":"ok"}`) and log in. Perform manager/staff permission checks and review the deployment logs. Never run data imports until the source register has been reviewed and a pre-import backup exists.

## Backups and restore

Create `deploy/backup.age-recipient` containing only the age public recipient. Keep the corresponding private age key offline and separately backed up.

```bash
chmod 700 deploy/backup.sh deploy/restore.sh
./deploy/backup.sh
```

The script encrypts both a PostgreSQL custom-format dump and the private media archive. Copy the encrypted `.age` files to a different off-site storage account/device; a backup stored only on the VPS is not disaster recovery.

A restore replaces live database contents and media. It requires explicit confirmation and an offline private identity key:

```bash
CONFIRM_RESTORE=YES \
AGE_IDENTITY_FILE=/secure/path/age-identity.txt \
DB_BACKUP=/secure/backups/spm-database-TIMESTAMP.dump.age \
MEDIA_BACKUP=/secure/backups/spm-media-TIMESTAMP.tar.gz.age \
./deploy/restore.sh
```

Perform a restore drill into a separate staging environment before production go-live. Reconcile tenant balances and recent bank transactions afterward.

## Operations and rollback

- Follow logs: `docker compose --env-file .env.production -f compose.production.yml logs -f`.
- Inspect health: `docker compose --env-file .env.production -f compose.production.yml ps`.
- Deploy a reviewed Git commit, not an arbitrary working tree.
- Before updates, take an encrypted backup. Rebuild and restart with the new reviewed commit.
- Do not blindly roll back database migrations. Use a tested forward-fix or a coordinated database restore if a migration has altered live data.
- Configure host-level monitoring, disk alerts, SSH security updates and remote backup copy/retention.

## Important security notes

- Uploaded tenancy agreements are stored in the private media volume. Caddy intentionally does not serve `/media/`; add a staff-authenticated, property-authorised document download view before enabling downloads.
- The deployment has not received a real VPS restore test, certificate test, external vulnerability scan or manager/user acceptance test.
- Run Django's production deployment checklist on the configured VPS before launch. Do not enable any live rent collection or bank reconciliation process until financial acceptance is signed off.
