# Security

This document describes the controls currently implemented in CallLog Pro and how to report issues.

## Reporting a vulnerability

Please open a private GitHub security advisory on this repository, or contact the maintainer directly. Do not file a public issue that includes exploit details or production credentials.

## Current controls

- Passwords are stored with Werkzeug password hashes; sessions use Flask-Login with `session_protection = strong`.
- CSRF protection is enabled application-wide via Flask-WTF. The health and seed endpoints are exempt because they are not browser form targets.
- Login is rate-limited (`10 per minute`) and locks a username after five consecutive failures for 15 minutes. Failures and lockouts are written to `system_audit`.
- Role decorators (`admin_required`, `manager_required`, `agent_required`) gate administrative and reporting routes.
- `/seed` is disabled in production unless `ENABLE_SEED=1`. When `SEED_TOKEN` is set, the request must present that token. Successful seed responses do **not** include demo passwords.
- Responses include `X-Request-ID` (honouring an incoming header when present) plus `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and a restrictive `Permissions-Policy`.
- Report Excel/PDF downloads are audited as `report.export`.
- Personal API tokens are hashed at rest. Treat unused tokens as secrets and revoke them from Admin settings.

## Production checklist

1. Set a long random `SECRET_KEY`.
2. Use Neon (or equivalent) Postgres over TLS (`sslmode=require`).
3. Leave `ENABLE_SEED` unset except for a controlled bootstrap window.
4. Change demo account passwords before any real users are added.
5. Rotate `DATABASE_URL` if it was ever committed or shared.
6. Keep `MAX_CONTENT_LENGTH` bounded so CSV import cannot exhaust memory.

## Out of scope / known limits

- Login lockout is in-process memory and resets on cold start (acceptable on Vercel; not a durable ban list).
- Content-Security-Policy is not yet enforced because the UI loads third-party CDN assets (Bootstrap, Chart.js).
