# Smart Property Manager — Loop Engineering Completion Tracker

Last updated: 20 November 2026  
Repository: https://github.com/Waryd000/smart-property-manager  
Engineering branch: `loop/phase-01-dashboard-access`

This is the canonical project tracker. Each module follows **Plan → Design → Develop → Test → Debug → Improve → Deploy**. A module is complete only when its acceptance tests pass and deployment is verified.

## Verified baseline and engineering evidence

- [x] Inspected the repository tree, Django settings, routes, models, views, forms, templates, tests, README and payment/import workflows.
- [x] Confirmed this is an actively developed Django/PostgreSQL foundation, not yet production-ready.
- [x] Confirmed redesigned templates are merged on `main`; local browser copy still needs to be synced and verified by the user.
- [x] Added initial migrations for `accounts`, `properties`, `tenants`, `rent`, `payments` and `operations`.
- [x] Added CI migration consistency check, fresh PostgreSQL migration and automated test run.
- [x] First PostgreSQL CI test run passed: 9 tests passed (dashboard staff/manager/inactive-profile isolation, due-date clamp, and payment bank-reference/amount match, allocation, idempotency and overpayment tests).
- [x] Scoped dashboard counts, balances, arrears, review flags and recent payments to a user's visible properties.
- [x] Added safe optional StaffProfile lookup and blocked inactive StaffProfiles from retaining manager access.
- [x] Hardened payment verification to require an exact bank reference and amount match, prevent transaction reuse and show verified unallocated excess explicitly.
- [x] Added PostgreSQL-backed GitHub Actions CI.

## Module completion tracker

| Module | Plan / Design | Develop | Test / Debug | Improve | Deploy |
|---|---|---|---|---|---|
| Repository baseline and CI | Complete | Complete | 9 tests passed in initial CI run; fresh-migration CI rerun pending | In progress | Not deployed |
| Frontend shell and registers | Complete in GitHub main | Complete in GitHub main | Local browser sync/acceptance still pending | Pending | Not deployed |
| Authentication and staff profiles | Audited | Login/profile foundations exist | Account provisioning, password reset, 2FA and offboarding coverage missing | Pending | Not deployed |
| Dashboard and access isolation | Complete | Implemented on engineering branch | 3 PostgreSQL regression tests passed | Pending code review/merge | Not deployed |
| Landlords, properties and units | Audited | List/create foundations only | CRUD, validation, staff permission tests missing | Pending | Not deployed |
| Tenants and tenancies | Audited | List/create foundations only | Identity deduplication, lifecycle, overlap guard and permission tests missing | Pending | Not deployed |
| Rent generation and ledger | Audited | Monthly generator and allocation-derived paid/balance fields exist | Partial, arrears, concurrency, month-boundary and reversal tests needed | Pending | Not deployed |
| Payments and bank reconciliation | Audited | Exact bank reference/amount verification and oldest-charge allocation added | 5 tests passed; real bank statement parser/upload, date validation, reversal and credit/refund flows remain | In progress | Not deployed |
| NAHA register import | JSON command exists | CLI dry-run/import foundation only | Idempotency, duplicate tenant resolution and source-data tests needed | Pending | Not deployed |
| Maintenance and expenses | Models/admin only | No full staff-facing workflows | Pending | Pending | Not deployed |
| Utilities | Models/admin only | Deferred from first import by user instruction | Pending | Deferred | Not deployed |
| Management fees and landlord statements | Minimal model | No complete invoicing/remittance workflow | Pending | Pending | Not deployed |
| Audit, reporting and exports | AuditLog model exists | Consistent event writes and report pages missing | Pending | Pending | Not deployed |
| Notifications | No complete provider workflow | Not implemented | Pending | Pending | Not deployed |
| Production security | Settings hardening under development | No full file validation, 2FA, throttling or security audit | Full security review and restore test pending | In progress | Not deployed |
| Cloud VPS deployment | Requirements documented | Not started | No VPS smoke test | Blocked on authorized VPS access | Not deployed |

## Production blockers

1. Enforce property-level permissions on every staff-facing read, create, update, delete, export, file-download and financial endpoint.
2. Add a database-level rule or transactional service guard against overlapping active tenancies on the same unit.
3. Complete import file validation, deterministic tenant identity matching and duplicate handling; do not infer identity from name alone.
4. Supply the source workbook privately, run an import dry run, review ambiguous rows, then import tenant names without historical payments or utilities.
5. Complete official bank statement upload/parser and date/reference/amount/currency matching. Do not accept a screenshot or free-form manual assertion as bank evidence.
6. Implement controlled tenant credit/refund and payment reversal workflows with immutable audit history.
7. Finish maintenance, expense, landlord accounting, management-fee and reporting screens or keep them explicitly outside the first release.
8. Complete file-type/size validation, production security settings, 2FA/OTP policy, throttling, audit events and log retention.
9. Configure HTTPS, Nginx, Gunicorn, process supervision, PostgreSQL private networking, Redis/Celery where required, encrypted off-site backups and verified restoration.
10. Complete user acceptance, reconciliation and security testing before real money or personal data is processed.

## Deployment prerequisites

Cloud VPS deployment remains **blocked** until an authorized connection and deployment target exist: VPS provider, hostname/IP, Ubuntu version, deployment user and safe SSH access method, domain/subdomain, TLS plan and backup/restore policy. Never share passwords or private SSH keys in chat or commit them to Git.

## Operating requirements

- Currency: UGX.
- Time zone: Africa/Kampala.
- Landlord display name: Waryd.
- Initial properties: Bukesa, Sir Apollo and Kisenyi.
- Import tenant names first; the user will update rent values after review.
- Leave water and utility data out of the initial import.
- Keep Sir Apollo units 23 (MUHAMMAD) and 24 (joush) as Pending Verification until occupancy is explicitly confirmed.
- Source workbook data and the local `.env` must never be committed to Git.
