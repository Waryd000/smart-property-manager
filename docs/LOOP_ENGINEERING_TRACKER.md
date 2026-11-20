# Smart Property Manager — Loop Engineering Completion Tracker

Last updated: 2026-11-20

## Engineering cycle

The team applies this cycle per module: **Plan → Design → Develop → Test → Debug → Improve → Deploy**. A module is not marked complete until its automated checks pass, acceptance criteria are met, and its deployment is verified.

## Baseline audit

- [x] Confirm repository and default branch: `main`.
- [x] Inspect application structure, Django settings, URLs, models, views, templates, requirements and README.
- [x] Confirm the application is a Django/PostgreSQL development foundation, not yet production-ready.
- [x] Identify that the GitHub `main` branch contains the redesigned frontend templates.
- [x] Identify the user's local `templates/base.html` was stale or was not overwritten correctly.
- [x] Identify missing committed Django app migrations in the repository tree.
- [x] Identify insufficient automated coverage for dashboard scope, permissions, rent, allocations and imports.
- [x] Identify payment verification currently does not require a matched bank transaction.

## Module tracker

| Module | Plan / Design | Develop | Test / Debug | Improve | Deploy |
|---|---|---|---|---|---|
| Repository baseline and CI | Complete | Complete | CI pending | In progress | Not deployed |
| Dashboard and access isolation | Complete | In progress on feature branch | Regression tests added; execution pending | In progress | Not deployed |
| Frontend shell and registers | Complete in GitHub main | Complete in GitHub main | Local browser verification pending | Pending | Not deployed |
| Landlord / property / units | Existing foundation audited | Partial CRUD | Permission and validation tests missing | Pending | Not deployed |
| Tenant / tenancy | Existing foundation audited | Partial CRUD | Tenant scoping and overlapping-tenancy tests missing | Pending | Not deployed |
| Rent generation / ledger | Existing foundation audited | Basic generator and ledger | Allocation, month boundary, concurrency tests missing | Pending | Not deployed |
| Payments / reconciliation | Existing foundation audited | Prototype verification only | Bank matching, duplicate, partial and excess-payment tests missing | Pending | Not deployed |
| Maintenance / expenses / utilities | Models exist; no complete user-facing workflows audited | Not implemented | Pending | Pending | Not deployed |
| Notifications / statements / reports | Requirements identified only | Not implemented | Pending | Pending | Not deployed |
| Security / audit / backups | Partial foundations; hardening gaps identified | Partial | Full security test and restore drill pending | Pending | Not deployed |
| Import NAHA registers | Command exists; source JSON is not in repository | Partial | Idempotency / duplicate matching / source validation tests pending | Pending | Not deployed |
| Cloud VPS deployment | Deployment checklist in README | Not started | No VPS verification | Not started | Blocked on VPS access and deployment details |

## Current cycle — Phase 01: dashboard access isolation

- [x] Scope dashboard data using the authenticated user's permitted properties.
- [x] Scope property, unit, occupied unit, tenant, outstanding rent, overdue charges, recent payment and review-alert data.
- [x] Add regression tests for assigned staff, managers, inactive staff profiles.
- [x] Fix optional reverse OneToOne staff-profile lookup so manager accounts without a StaffProfile do not crash.
- [x] Add PostgreSQL-backed GitHub Actions workflow.
- [ ] Run GitHub Actions and correct any failures.
- [ ] Complete code review and merge to `main`.
- [ ] Apply changes to the user's local working copy and verify in browser.

## Production blockers — must be closed before go-live

1. Commit real initial migrations for every Django app; do not generate schema migrations ad hoc on the VPS.
2. Enforce tenant/property data isolation on every list, detail, update, download and financial endpoint.
3. Prevent overlapping active tenancies for the same unit at database level.
4. Require a matched, amount/reference/date-validated bank statement transaction before payment verification.
5. Implement safe treatment of excess payments and tenant credit; never silently mark unallocated amounts as rent allocated.
6. Add import validation and idempotent identity matching; do not infer tenant identity from name alone.
7. Finish maintenance, expense, utility and landlord reporting workflows or explicitly remove unused menu/model promises.
8. Harden production settings, HTTPS, allowed hosts, CSRF origins, secure cookies, secrets, uploaded file handling, logging and admin access.
9. Configure Gunicorn, Nginx, process supervision, PostgreSQL backups, off-site backup encryption and tested restore.
10. Complete user acceptance tests and financial reconciliation before live collections.

## Deployment prerequisites

Cloud VPS deployment is **blocked** until the user supplies or connects: VPS provider/IP or hostname, Ubuntu version, SSH access method, domain/subdomain (if any), and the agreed backup/restore approach. Never put passwords or private SSH keys in chat or Git.
