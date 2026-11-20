# Smart Property Manager (SPM)

Django/PostgreSQL property-management system for a single landlord portfolio. Currency: UGX. Time zone: Africa/Kampala. The repository is being hardened through the Loop Engineering cycle and is **not yet approved for production financial operations**.

## Current modules

- Manager/staff accounts with property assignments.
- Landlords, properties and rental units.
- Tenant profiles and tenancy records, including pending verification and database protections against duplicate active tenancies.
- Dashboard, property, tenant, rent and payment registers.
- Monthly rent charge generation and partial allocations.
- Payment-to-bank-statement reconciliation with property-scoped rent allocation.
- Maintenance, expenses, utilities, management-fee and audit data models; several still need full staff-facing workflows.
- PostgreSQL migrations and GitHub Actions CI.

## 1. Requirements

- Python 3.11 or newer
- PostgreSQL 14 or newer
- Redis is needed when scheduled Celery tasks are enabled.

## 2. Local setup (Windows PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with a new strong secret key and your PostgreSQL credentials. Create the PostgreSQL database and user, then run:

```powershell
python manage.py migrate
python manage.py check
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/. Create the landlord in `/admin/`, then add properties, units, tenants and confirmed tenancies. Use the committed migrations; do not create schema manually on the VPS.

## 3. Generate monthly rent charges

```powershell
python manage.py generate_rent
```

The command generates charges for active tenancies within the requested billing month. It is intended to be safe to rerun because each tenancy/month pair is unique. Review the ledger and run the CI tests before relying on it for financial posting.

## 4. Payment reconciliation

A payment can only be verified after an imported bank transaction matches the payment's bank reference and amount, and the tenant has a tenancy in the selected property. The service locks the payment and bank transaction, prevents a bank row from being matched twice, and allocates funds to that tenant's oldest outstanding rent charges within the selected property.

Any verified excess is stored in `Payment.unallocated_amount`; it is **not** silently assigned to another property or rent charge. The live credit/refund and reversal workflow is not yet complete, so excess amounts must remain under manager review and must not be treated as available landlord funds.

The verification screen is not a substitute for the bank's official statement. Do not verify against a tenant screenshot or an unconfirmed transaction.

## 5. Equity Bank statement ingestion

`payments.services.import_equity_statement_row` accepts a normalized incoming-credit row with:

- `reference`: bank transaction reference
- `transaction_date`: ISO-8601 timestamp
- `amount`: positive decimal credit amount
- `narrative`: optional description

The function is idempotent for an identical reference, date and amount, and raises a conflict error if the same reference is later supplied with a different date or amount. The actual Equity Bank export format still needs to be obtained and mapped, and the user-facing statement upload/review UI is not complete. Never assume an arbitrary CSV is an official bank confirmation. API/webhook access needs written bank approval and a separate security review.

## 6. Importing the initial NAHA tenant register

The existing management command accepts a validated JSON file and supports `--dry-run`. The source workbook's latest tenant registers must be converted and reviewed before import. Current import hardening and source-row identity tests are still in progress.

First release import scope:
- Properties: Bukesa, Sir Apollo and Kisenyi.
- Import tenant names/records first; monthly rent values are to be reviewed and updated by the manager.
- Do not import historical payment columns as verified payments.
- Do not import water or utility sheets in the first pass.
- Sir Apollo units 23 (MUHAMMAD) and 24 (joush) remain Pending Verification until occupancy is confirmed.

Keep the private source workbook and tenant data out of Git.

## 7. Production security and deployment

Production settings require a unique `SECRET_KEY`, strict `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`. HTTPS redirects and secure session/CSRF cookies default on when `DEBUG=False`. Enable HSTS only after TLS and reverse-proxy behavior are verified.

Before go-live:
- Use supported Ubuntu LTS, Nginx + Gunicorn, PostgreSQL on a private network, and Redis/Celery only where needed.
- Store secrets outside Git; rotate any development secret exposed during setup.
- Add file type/size validation, 2FA policy, throttling, complete authorization coverage and immutable audit events.
- Configure encrypted off-site backups and prove restoration.
- Complete import reconciliation, finance acceptance, privacy and security testing.
- Complete user acceptance before processing real money or personal data.

Cloud VPS deployment is pending an authorized target and access path (provider/host/IP, Ubuntu version, deployment user/SSH method, domain/TLS and backup/restore approach). Never put passwords or SSH private keys in chat or Git.

## 8. Engineering tracker

Follow `PROJECT_COMPLETION_TRACKER.md` for the current module status, verified test evidence, remaining production blockers and deployment prerequisites.

This is an actively developed system and must not be represented as production-ready until the tracker’s release criteria have been satisfied.
