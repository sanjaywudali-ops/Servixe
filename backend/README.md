# Servixe Backend (FastAPI modular monolith)

Implements the API described in *Servixe – Website Application Technical Specifications* (12 Nov 2026):
FastAPI · PostgreSQL · SQLAlchemy + Alembic · server-side sessions + RBAC (+TOTP MFA for staff) · Redis + Celery ·
private S3 storage · Docker.

## Quick start (Docker)
```bash
cp .env.example .env          # edit secrets
docker compose up --build     # db, redis, migrate+seed, api (:8000), worker, beat
```
API docs (non-production only): http://localhost:8000/docs

## Quick start (local Python)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # use a local PostgreSQL, or DATABASE_URL=sqlite:///./dev.db for a quick look
alembic upgrade head
python -m scripts.seed        # roles, starter services/areas/pricing/checklists, admin from SEED_ADMIN_*
uvicorn app.main:app --reload
pytest -q                     # 23 tests
```
First admin sign-in forces **MFA enrolment** (TOTP); staff sessions cannot reach any admin endpoint until MFA is verified.

## Module layout (`app/modules/*`)
| Module | Responsibility |
|---|---|
| identity | register/login, sessions, MFA, password reset, session list/revoke |
| families | customers, parents, **consents** (dated, scoped), **family_authorisations** |
| providers | onboarding, verification documents, verification checklist, coverage |
| catalogue | services, areas, pricing rules, packages (+ public read endpoints) |
| requests | service requests, **workflow state machine** (`workflow.py`), timeline, quality review |
| approvals | versioned quotes, price calculation, customer approve/reject |
| assignments | primary/backup assignment, **provider portal API** (minimum-necessary data), check-in/out, checklist |
| evidence | private uploads, validation, signed URLs, checklist templates |
| incidents | incidents/complaints, severity, escalation, closure review |
| billing | invoices, payments (hosted-checkout adapter), refunds (4-eyes), provider payouts, signed idempotent webhooks |
| notifications | templates, delivery log, email/WhatsApp adapters, Celery retries |
| audit | append-only audit log (ORM guard + PostgreSQL trigger) |
| admin | staff management, audit viewer, operations overview, reports |

## Key rules enforced server-side
* **Separate people**: payer (`customers`), service recipient (`parents`), requestor authority (`family_authorisations`). Adding a parent creates a *pending* authorisation; ops record the parent's consent and then activate it. The payer never gets automatic authority.
* **Workflow gates** (`requests/workflow.py`): states and transitions are explicit; staff cannot skip consent, approval, checklist, quality or invoice gates by editing a status. A documented admin-only *approval exception* is the only bypass and is audited.
* **No paid work without approval**: assignment and check-in require the *latest* quote version to be approved. A changed quote supersedes the old one and pauses work until re-approved.
* **Provider least-privilege**: providers see only their jobs; address, phone and task details appear only after acceptance, parent first name only.
* **Consent-aware evidence**: completion photos need active `photographs` consent; evidence is `ops_only` until released to the customer.
* **Uploads**: type allow-list, magic-byte check, size limit, private storage, short-lived signed URLs, malware-scan hook (`core/storage.py::scan_for_malware` – plug in a real scanner).
* **Webhooks**: HMAC signature verification + idempotency table; amount/currency mismatch is flagged, not applied.
* **Security**: Argon2id, HttpOnly/SameSite cookies, CSRF custom-header check, lockout, rate limiting, generic auth errors, session revocation on password change/reset, no secrets in code.
* **Not an emergency service**: `emergency_notice` is returned by the API and shown in provider incident flows.

## Integrations (all behind adapters)
`billing/gateway.py` (payments – **stub**, implement after payment review) · `notifications/service.py` (SES email, WhatsApp Cloud API) ·
`core/storage.py` (S3/local) · Turnstile CAPTCHA in `enquiries/router.py`.

## Money
All amounts are integer minor units (paise/cents) + ISO currency. Tax is applied to Servixe's coordination fee; provider charges are passed through at cost – **confirm with your tax adviser**.

## Before real customer data
Seed catalogue values, Nellore micro-areas and prices are placeholders for the requirements workshop (spec §14). Complete: legal/privacy/tax review, a real payment adapter, malware scanning, retention/deletion policy jobs, backup + restore test, and production secrets management (spec §8, §11).

## Deployment notes
Run `alembic upgrade head` as a release step, then start `api`, `worker` and `beat` containers (ECS/Fargate suggested). Set `ENV=production`, `COOKIE_SECURE=true`, `CELERY_EAGER=false`, `STORAGE_BACKEND=s3`, managed PostgreSQL/Redis, and secrets from a secrets manager. Terminate TLS at the load balancer and keep the API and frontend on the same site (the Next.js app proxies `/api/*`).
