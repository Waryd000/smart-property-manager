# Smart Property Manager — Loop Engineering Completion Tracker

Last updated: 20 November 2026  
Repository: https://github.com/Waryd000/smart-property-manager  
Engineering branch: `loop/phase-01-dashboard-access`

Each module follows **Plan → Design → Develop → Test → Debug → Improve → Deploy**. A module is not complete until automated and acceptance tests pass and deployment is verified.

## Verified baseline and evidence

- [x] Inspected source tree, Django settings, URLs, models, forms, views, templates, migrations, import command, tests, payment workflows and README.
- [x] Confirmed frontend redesign merged on `main`; user local copy still needs synchronization/browser acceptance.
- [x] Added initial migrations for six app schemas and incremental migrations for tenancy, payment, and operations controls.
- [x] Added PostgreSQL-backed GitHub Actions CI with migration consistency check, fresh database migrate, Django system check and full test suite.
- [x] Latest clean PostgreSQL CI run at commit `3a31b15f9760b33581a1dc48fb44036fbea7906f`: **76 tests passed**.
- [x] In the same run, production Compose configuration validated and production Docker image built successfully.
- [x] Hardened dashboard and staff access to property-assigned data; made StaffProfile role authoritative; restricted global Django Admin.
- [x] Added manager-only property/unit setup; staff-facing maintenance and expense submission/approval workflows; audit events.
- [x] Added tenant lifecycle rules and database constraints: active tenancy needs a start date; one active tenancy per unit.
- [x] Added idempotent monthly rent generator, month-end due-date clamping and date-aware overdue display.
- [x] Added payment statement import, pending payment recording, exact bank reference/amount match, property/tenant scoping and allocation.
- [x] Added soft payment reversal with original allocation and bank evidence retained; active rent balances exclude reversed allocations.
- [x] Added safe NAHA import dry-run, source markers, idempotency, duplicate/conflict checks, no spreadsheet rent imports and pending unverified tenancies.
- [x] Added production settings, non-root Docker image, PostgreSQL/Redis/Celery/Caddy Compose stack, health endpoint, monthly scheduled rent task and encrypted backup/restore scripts.
- [ ] Perform a real VPS deployment, certificate validation, external security scan and separate-environment backup restore drill.

## Module completion tracker

| Module | Plan / Design | Develop | Test / Debug | Improve | Deploy |
|---|---|---|---|---|---|
| CI and schema | Complete | Complete | 76 PostgreSQL tests passed; clean migration check passed | Ongoing | CI only |
| Frontend shell/registers | Complete in `main` | Complete in GitHub | Local copy/browser acceptance pending | Improve based on user review | Not deployed |
| Authentication and staff administration | Audited | Basic profile model only; staff CRUD pending | Coverage missing for create/edit/deactivate/invite | Pending | Not deployed |
| Dashboard and property access | Complete | Implemented | Staff/manager/inactive role tests pass | Further endpoint review pending | Not deployed |
| Landlords/properties/units | Audited | List/create foundation | Manager-only create tests pass; edit/archive workflows pending | Pending | Not deployed |
| Tenants/tenancies | Complete | Create/list, property scope, validation and DB constraints | Date, uniqueness, access and lifecycle tests pass | Agreement upload/download hardening pending | Not deployed |
| Rent ledger | Complete | Monthly generation, allocations, live overdue view and scheduled task | Generator and visibility tests pass; monthly policy/proration acceptance pending | Pending | Not deployed |
| Bank reconciliation | Complete | Normalized CSV ingestion, pending payment form, verify/allocate, reverse | Reference, date/amount conflict, tenant/property, upload, audit and reversal tests included | Real bank export format still needs mapping | Not deployed |
| Maintenance | Complete | Staff report and manager status workflow | Property scope, role transition, cost and audit tests pass | Assigning technicians / attachments pending | Not deployed |
| Expenses | Complete | Staff submit, manager approve/reject/mark paid | Property scope, reference-required payment, role and audit tests pass | Receipt evidence and accounting reports pending | Not deployed |
| NAHA import | Complete | Safe JSON dry-run/idempotent command | Import tests included; actual source workbook not re-uploaded this session | Need reconcile source register | Not deployed |
| Utilities | Deferred for first import by user instruction | Model only | No utility workflow tests/UI | Deferred | Not deployed |
| Landlord fees/statements/remittance | Audited | Incomplete | Pending | Pending | Not deployed |
| Reports/exports | Audited | Incomplete | Pending | Pending | Not deployed |
| Private documents | Security requirement established | Private media volume; no public media route | Authenticated download route/upload validation pending | Pending | Not deployed |
| Security/audit | Core access, settings and event logging implemented | Partial | 76 tests; full penetration/security review pending | Add rate-limits, 2FA, log retention, private media controls | Not deployed |
| Cloud VPS deployment | Production stack prepared | Compose/Docker package committed on branch | Compose config and image build pass; no live server/restore drill | Host monitoring/offsite backups pending | Blocked on authorized VPS details |

## Operating requirements

- Currency: UGX.
- Time zone: Africa/Kampala.
- Landlord display name: Waryd.
- First properties: Bukesa, Sir Apollo and Kisenyi.
- Import tenant names first; rent values to be reviewed and entered by the manager.
- Do not import historical payments or utilities in the first pass.
- Sir Apollo units 23 (MUHAMMAD) and 24 (joush) remain Pending Verification until occupancy is confirmed.

## Open production blockers

1. Finish manager-controlled staff account CRUD, role/assignment changes and deactivation.
2. Complete authenticated private agreement upload/download, file validation and malware scanning strategy.
3. Review property-level authorization on every update/delete/export/report endpoint.
4. Implement management fees, landlord statements and remittance reconciliation.
5. Finalize rent proration/charge policy for mid-month start/end dates. Current generator creates the full monthly charge for a tenancy overlapping that month; get landlord approval before live use.
6. Map and reconcile the actual official Equity Bank export format. The current parser expects a normalized reference/date/amount CSV.
7. Finish maintenance attachments/technician assignment, expense receipt evidence and management reports.
8. Complete 2FA/MFA policy, login throttling, secure headers review, audit log retention and external security test.
9. Configure VPS monitoring, disk alerts, encrypted off-site backup copy and prove restore in staging.
10. Complete user acceptance and financial reconciliation before handling real rent collections or personal data.

## Cloud VPS deployment prerequisites

The deployable Docker/Compose package is prepared, but deployment is not performed. It requires:
- VPS provider and hostname/IP;
- Ubuntu LTS version and non-root deployment account;
- approved SSH/deploy-key access method (never send passwords or private SSH keys in chat);
- production domain/subdomain with DNS pointing at the VPS;
- SMTP details if email delivery is required;
- designated encrypted off-site backup destination and restoration operator.

The deployment uses Caddy automatic HTTPS, a private PostgreSQL/Redis network, Gunicorn, Celery worker/beat, and encrypted backup/restore scripts. A live deployment will not be reported complete until the real host responds over HTTPS and a backup restore has been demonstrated.

## Security notes

- The local development SECRET_KEY was disclosed earlier in the conversation; generate and use a new secret before deployment.
- Keep `.env`, `.env.production`, source Excel registers, tenant data, SSH keys and backups out of Git.
- Private tenancy agreements are not publicly served by the reverse proxy. Add authenticated downloads before staff access is enabled.
