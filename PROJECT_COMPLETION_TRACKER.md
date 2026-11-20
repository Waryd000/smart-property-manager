# Smart Property Manager — Loop Engineering Completion Tracker

Last updated: 20 November 2026  
Repository: https://github.com/Waryd000/smart-property-manager  
Engineering branch: `loop/phase-01-dashboard-access`

This is the canonical project tracker. Each module follows **Plan → Design → Develop → Test → Debug → Improve → Deploy**. A module is complete only when its acceptance tests pass and deployment is verified.

## Verified baseline and engineering evidence

- [x] Inspected repository tree, Django settings, routes, models, views, forms, templates, tests, README and payment/import workflows.
- [x] Confirmed this is a development foundation under active hardening, not yet production-ready.
- [x] Confirmed redesigned templates are merged to `main`; local browser sync/acceptance remains open.
- [x] Added initial migrations for accounts, properties, tenants, rent, payments and operations.
- [x] Added migration consistency check, clean PostgreSQL migration and automated CI workflow.
- [x] A fresh PostgreSQL CI run passed all 9 then-current tests; a second run passed after production-like settings and migrations were applied.
- [x] Scoped dashboard counts, balances, arrears, review flags and recent payments to the user's visible properties.
- [x] Added safe optional StaffProfile lookup; inactive staff profiles cannot retain manager access.
- [x] Hardened payment verification to require exact bank reference and amount, prevent transaction reuse, and report excess as unallocated.
- [x] Hardened production settings: require production secret key, hosts and CSRF origins; default HTTPS redirect and secure cookies outside DEBUG; set upload bounds and media root.
- [x] Added tenancy model/form safeguards and database constraints for one active tenancy per unit and a required start date on active tenancies.
- [x] Filtered prefetched tenant tenancy rows to the current staff user's assigned properties.
- [ ] Run CI after tenancy migration reconciliation and the latest tenant visibility changes.

## Module completion tracker

| Module | Plan / Design | Develop | Test / Debug | Improve | Deploy |
|---|---|---|---|---|---|
| Repository baseline and CI | Complete | Complete | PostgreSQL runs passed; latest tenancy branch rerun pending | In progress | Not deployed |
| Frontend shell and registers | Complete in GitHub main | Complete in GitHub main | Local browser sync/acceptance pending | Pending | Not deployed |
| Authentication and staff profiles | Audited | Login/profile foundations exist | Provisioning, reset, 2FA, offboarding tests missing | Pending | Not deployed |
| Dashboard and access isolation | Complete | Implemented on engineering branch | 3 PostgreSQL regression tests passed | Pending review/merge | Not deployed |
| Landlords, properties and units | Audited | List/create foundations | CRUD, validation and permission coverage missing | Pending | Not deployed |
| Tenants and tenancies | Complete | Lifecycle validation, database constraints and assignment-filtered tenant list implemented | 6 tenancy tests added; current CI rerun pending | In progress | Not deployed |
| Rent generation and ledger | Audited | Monthly generator and allocation-derived paid/balance exist | Month-boundary, arrears, allocation, concurrency and reversals need wider tests | Pending | Not deployed |
| Payments and bank reconciliation | Audited | Exact bank reference/amount verification, transaction uniqueness and oldest-charge allocation | 5 payment tests passed; tenancy/property scope, real statement import, reversals and credit/refund remain | In progress | Not deployed |
| NAHA register import | JSON command exists | CLI dry-run/import foundation only | Idempotency, duplicate tenant resolution and source-data tests required | Pending | Not deployed |
| Maintenance and expenses | Models/admin only | No full staff-facing workflows | Pending | Pending | Not deployed |
| Utilities | Models/admin only | Deferred from first import by user instruction | Pending | Deferred | Not deployed |
| Management fees and landlord statements | Minimal model | No complete invoicing/remittance workflow | Pending | Pending | Not deployed |
| Audit, reporting and exports | AuditLog model exists | Consistent event writes/report screens missing | Pending | Pending | Not deployed |
| Notifications | No complete provider workflow | Not implemented | Pending | Pending | Not deployed |
| Production security | Settings hardening implemented on branch | File validation, 2FA, throttling and full audit hardening remain | Production deployment check and security test suite pending | In progress | Not deployed |
| Cloud VPS deployment | Requirements documented | Not started | No VPS smoke test | Blocked on authorized VPS access | Not deployed |

## Production blockers

1. Enforce property-level permissions on every staff-facing read, create, update, delete, export, file-download and financial endpoint.
2. Scope each payment to a tenancy/property; prevent a tenant's payment from being allocated against another property's charges.
3. Complete import validation, deterministic tenant identity matching and duplicate handling; do not infer identity from name alone.
4. Supply source workbook privately, run import dry-run, review ambiguous rows, then import tenant names without historical payments or utilities.
5. Complete official bank statement upload/parser and date/reference/amount/currency matching. Do not accept a screenshot or free-form assertion as bank evidence.
6. Implement controlled tenant credit/refund and payment reversal workflows with immutable audit history.
7. Finish maintenance, expense, landlord accounting, management-fee and reporting screens or keep them outside first release.
8. Complete file-type validation, 2FA, throttling, audit events, log retention, HTTPS, Nginx/Gunicorn and process supervision.
9. Configure PostgreSQL private networking, Redis/Celery where required, encrypted off-site backups and verified restore.
10. Complete user acceptance, reconciliation and security testing before real money or personal data is processed.

## Deployment prerequisites

Cloud VPS deployment remains **blocked** until an authorized target exists: VPS provider, hostname/IP, Ubuntu version, deployment user and safe SSH access method, domain/subdomain, TLS plan and backup/restore policy. Never share passwords or private SSH keys in chat or commit them to Git.

## Operating requirements

- Currency: UGX.
- Time zone: Africa/Kampala.
- Landlord display name: Waryd.
- Initial properties: Bukesa, Sir Apollo and Kisenyi.
- Import tenant names first; user will update rent values after review.
- Leave water and utility data out of the initial import.
- Keep Sir Apollo units 23 (MUHAMMAD) and 24 (joush) as Pending Verification until occupancy is explicitly confirmed.
- Source workbook data and local `.env` must never be committed to Git.
