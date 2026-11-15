# Servixe Frontend (Next.js + TypeScript + Tailwind)

One Next.js app delivering all four interfaces from the technical specification (12 Nov 2026), sharing one design system and one API:

| Interface | Routes | Who |
|---|---|---|
| Public website | `/`, `/services`, `/pricing`, `/how-it-works`, `/about`, `/faq`, `/contact`, `/privacy`, `/terms` | everyone |
| Overseas customer portal | `/portal/*` – dashboard, parents (profile, consent status, authority), requests (create, quote approve/decline, timeline, evidence, concern, cancel), invoices & pay, account (profile, WhatsApp opt-in, password, sessions) | customers |
| Admin & operations dashboard | `/admin/*` – overview, requests workspace (workflow, quote, assignment, quality review, evidence, billing, audit timeline), enquiries, customers & consent/authority, providers & verification, incident desk, finance, reports, catalogue & pricing, audit trail, staff | support / admin (MFA) |
| Provider PWA (mobile-first) | `/provider/*` – assigned jobs, accept/decline, check-in/out, checklist, evidence upload, incident report, history & payout status, document upload. Installable (manifest + service worker; API responses are never cached). | providers |

## Run
```bash
npm install
cp .env.example .env.local       # BACKEND_URL=http://localhost:8000
npm run dev                      # http://localhost:3000
npm run typecheck && npm run build
```
Start the backend first (see the backend README). Sign in as the seeded admin; MFA enrolment is forced on first login.

## Design notes
* **Same-origin API proxy**: `next.config.mjs` rewrites `/api/*` to `BACKEND_URL`, so the HttpOnly, SameSite session cookie belongs to the site itself – no tokens in JS, no CORS in the browser. The API client (`src/lib/api.ts`) sends the `X-Requested-With: Servixe` header the backend requires as CSRF defence.
* **UI system**: Tailwind + shadcn/ui-style primitives (`src/components/ui`: Button, Card, Form fields, Badge, Alert, Table) built on Radix `Slot`, class-variance-authority and tailwind-merge. Colour tokens are CSS variables (navy/teal brand, light + dark).
* **Authorisation**: route guards (`RequireRole`) only improve UX. Every permission is enforced by the backend; the UI hides nothing that is security-relevant.
* **Provider least-privilege**: the provider UI shows only what the API returns – address/contact/task details appear after acceptance, parent first name only.
* **Safety copy**: the non-emergency notice appears on every layout, in the enquiry form and in the provider incident flow. The enquiry form has no free-text health field.
* **Placeholders to finalise**: privacy notice, terms/refund text, response hours, retention periods and the Nellore micro-areas/prices are drafts for legal review and the requirements workshop (spec §8, §14).

## Docker
```bash
docker build -t servixe-web --build-arg BACKEND_URL=http://api:8000 .
docker run -p 3000:3000 servixe-web
```
`BACKEND_URL` is baked into the rewrites at build time. Production should serve web + API under one domain behind HTTPS (set `COOKIE_SECURE=true` on the backend).

## Structure
```
src/app/(public)   marketing pages      src/app/(auth)  login/register/reset
src/app/portal     customer portal      src/app/admin   operations dashboard
src/app/provider   provider PWA         src/components  ui primitives + shell
src/lib            api client, auth context, hooks, types, formatting
public             manifest, service worker, offline page, icons
```
