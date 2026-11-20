# Smart Property Manager — Loop Engineering Completion Tracker

Last updated: 20 November 2026  
Repository: https://github.com/Waryd000/smart-property-manager  
Branch for current hardening cycle: `loop/phase-01-dashboard-access`

This tracker records verified repository work separately from local-user actions and items that still require a live VPS or bank-provider environment. A code change is not marked complete until its tests have run successfully.

## Loop Engineering cycle

| Cycle stage | Current status | Evidence / next action |
|---|---|---|
| Plan | In progress | Repository and module audit started; risks and deployment gaps documented below. |
| Design | In progress | Responsive frontend is merged to `main`; financial and access-control designs need completion. |
| Develop | In progress | Dashboard property scoping and bank-transaction verification safeguards are implemented on the current branch. |
| Test | Pending execution | Regression tests and PostgreSQL GitHub Actions workflow added; must obtain a green workflow run. Local runner currently has no Django packages and no package-index network access. |
| Debug | In progress | Previously exposed dashboard data and unverified payment approval paths are addressed in code; further failures depend on test results. |
| Improve | In progress | Import workflow, maintenance/expense modules, reporting and audit coverage remain. |
| Deploy | Blocked | No VPS host, SSH/deployment credentials, domain, TLS details, or production database/backup configuration have been supplied. Do not deploy without these. |

## Module completion

| Module | Repository state | Completion |
|---|---|---:|
| Authentication and staff profiles | Django login and StaffProfile exist; account provisioning, password reset, 2FA and offboarding controls need work. | Partial |
| Landlords, properties and units | Models, admin, list/create screens exist. Update/delete flows, full authorization tests and validation need work. | Partial |
| Tenants and tenancies | Models, forms, list/create screens exist. Tenant identity/deduplication, tenancy lifecycle and overlap protection need work. | Partial |
| Dashboard | Counts, review flags, balances, payment activity exist. Per-user property scoping is being hardened with tests. | In progress |
| Rent | Monthly charge generation and allocation-derived paid/balance values exist. Comprehensive arrears, month-boundary, status and reversal tests remain. | Partial |
| Payments and bank reconciliation | Payment models and allocation exist. Verification now requires exact imported bank reference + amount match on this branch. Statement upload/parser, matching UI, reversal, refund and tenant-credit workflows remain. | In progress |
| Excel register import | JSON management command with dry-run exists in `main`; source workbook JSON is not in repository. Import UI, review resolution, safer identity matching, real data dry-run and verified import remain. | Partial |
| Maintenance and expenses | Data models and admin registration exist; staff-facing workflows, approvals, supplier records and tests are missing. | Not complete |
| Utilities | Models exist, but user requested these be deferred for current initial import. Utility screens and billing remain out of current first release scope. | Deferred |
| Management fees and landlord statements | Minimal ManagementFee model exists; invoicing, receipts, balances, remittance and statements are not implemented. | Not complete |
| Audit and reporting | AuditLog model exists, but important changes are not yet consistently written to it; reports/export screens remain. | Not complete |
| Notifications | No complete SMS/email provider, consent, delivery log, retries or templates. | Not complete |
| Migrations and schema lifecycle | No migration files were present in the audited Git tree. CI currently uses `migrate --run-syncdb` for the unmigrated development apps. Generate, commit and test initial migrations before production. | Blocker |
| Automated testing | Existing tests were very limited; dashboard isolation and payment reconciliation tests added on current branch. A PostgreSQL CI workflow was added but has not yet reported a green run. | In progress |
| Production security | Current settings need production-only security headers/cookies, strict CSRF origins, HTTPS proxy configuration, secrets policy, file upload validation, backup/restore and security testing. | Not complete |
| Cloud VPS deployment | No deployment scripts, web server/systemd configuration, domain or VPS access details available. | Blocked |

## Confirmed issues and safeguards

- Dashboard data must be scoped to the current user's visible properties, including counts, balances, overdue charges, recent payments and source-review flags.
- An inactive staff profile must not inherit manager rights through Django's `is_staff` flag.
- A pending payment must not be verified without an imported bank transaction with the same reference and amount.
- A bank transaction must not be matched to more than one payment.
- Any verified amount left after rent allocation must be visible as unallocated; a controlled tenant-credit/refund workflow is still required.
- Historical figures in the source Excel workbook must not be presented as verified bank payments.
- Sir Apollo units 23 (MUHAMMAD) and 24 (joush) remain pending occupancy verification until the user confirms their current status.
- The source Excel register data is private and must not be committed to this repository.

## Required before production deployment

1. Commit and test initial Django migrations.
2. Obtain a green PostgreSQL CI run and build comprehensive tests for authorization, rent calculations, imports and payment reconciliation.
3. Finish import UI and execute a dry run on the user's supplied current registers; obtain explicit review of ambiguous records.
4. Complete payment statement ingestion and reconciliation using an actual bank-provided statement specification/sample.
5. Complete staff workflows, audit trails, landlord accounting, reports and backups.
6. Configure production environment variables and hardening; rotate the Django secret key that was previously exposed during development.
7. Obtain VPS connection details, deployment user, DNS/domain and TLS plan; deploy and verify health checks, backups and rollback.

## User-specific operating rules

- Currency: UGX.
- Time zone: Africa/Kampala.
- Initial properties: Bukesa, Sir Apollo and Kisenyi.
- Landlord display name: Waryd.
- Import tenant names and records first; update rent values after review where needed.
- Do not import water or utility records in the first import.
- Keep uncertain occupancy records pending verification, especially Sir Apollo units 23 and 24.
