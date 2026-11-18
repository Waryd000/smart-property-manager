# Smart Property Manager (SPM)

Django/PostgreSQL foundation for managing one landlord's portfolio of up to 10 properties and 10–30 units. Currency: UGX. Bank workflow: Equity Bank Uganda statement import/reconciliation initially; direct API integration is a later bank-approved phase.

## Included in this foundation
- Manager/staff profile model and Django authentication.
- One landlord linked to multiple properties; units and staff-property assignments.
- Tenant and tenancy records, with rent amount, deposit, due day and agreement upload.
- Monthly rent charge model with partial-payment allocations and status calculation.
- Payment records, bank transaction records and manager verification/oldest-charge allocation service.
- Management fee, utility bill, maintenance request, expense and audit-log models.
- Responsive starter pages for dashboard, properties, tenants, rent register and payment verification.
- Management command to generate monthly rent charges.

## 1. Requirements
- Python 3.11 or newer
- PostgreSQL 14 or newer
- Redis (for scheduled jobs in the next implementation stage)

## 2. Local setup (Windows PowerShell)
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
Edit `.env` with a strong secret key and your PostgreSQL credentials. Create the database and user in PostgreSQL, then:
```powershell
python manage.py makemigrations accounts properties tenants rent payments operations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Open http://127.0.0.1:8000/ and sign in. Create the landlord first in `/admin/`, then add properties, units, tenants and tenancies.

## 3. Generate monthly rent charges
```powershell
python manage.py generate_rent
```
The command creates charges for active tenancies for the current month and is safe to rerun because each tenancy/month pair is unique.

## 4. Payment verification
Create a pending Payment record only after a bank transaction is found or imported. A manager can verify it in the Payments screen. The service allocates the verified amount to the tenant's oldest outstanding rent charges. Any excess remains unallocated and must be handled as tenant credit/refund through a controlled workflow before production.

**Important:** the included verify button is a prototype manager action, not a substitute for a bank API or bank statement match. Restrict access to trusted managers and only verify after checking the original bank record.

## 5. Equity Bank integration
The bank CSV format must be obtained from Equity Bank and mapped to the normalized fields used by `payments.services.import_equity_statement_row`: `reference`, `transaction_date` (ISO format), `amount`, `narrative`. Do not assume a generic CSV is an official bank confirmation. Direct API/webhook integration requires written bank approval, credentials, callback verification, idempotency and security review.

## 6. Production deployment checklist
- Use a supported Ubuntu LTS VPS, PostgreSQL and Redis on private network interfaces.
- Set `DEBUG=False`, a unique long `SECRET_KEY`, strict `ALLOWED_HOSTS`, HTTPS and `CSRF_TRUSTED_ORIGINS`.
- Use Nginx + Gunicorn; run Celery workers and Celery Beat as supervised services.
- Store secrets outside source control; never commit `.env` or bank credentials.
- Configure encrypted off-site backups and test restoration.
- Enable 2FA, least-privilege property assignments, audit logging and staff offboarding.
- Add SMS provider integration only after sender ID, consent, delivery and cost testing.
- Complete financial, privacy, security and user acceptance testing before real collections.

## 7. Known next engineering tasks
1. Add database-level protection against overlapping active tenancies for a unit.
2. Extend property-level filtering to every new staff-facing endpoint and add automated permission tests.
3. Implement notification templates, SMS provider adapter, deduplication and delivery logs.
4. Implement bank CSV upload UI, statement parser, transaction matching and immutable reconciliation audit.
5. Add double-entry accounting journal and controlled landlord remittance workflow.
6. Add approval thresholds, management fee invoicing/payment tracking and landlord statements.
7. Add tests for allocation, duplicate bank references, partial payments, month boundaries, permissions and reversals.

This is a development starter, not a production-ready financial platform. Review and harden it before processing real money or personal data.
