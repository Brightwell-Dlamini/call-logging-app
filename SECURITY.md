# Security checklist (CallLog Pro)

Use this before marking the project “production ready” or sharing credentials outside the team.

## Credentials

- [ ] **Rotate Neon database password** if it was ever pasted in chat, Discord, email, or a screenshot.
- [ ] Update `DATABASE_URL` on Vercel after rotating (Project → Settings → Environment Variables).
- [ ] Set a strong unique `SECRET_KEY` on Vercel (e.g. `openssl rand -hex 32`). Do not use the default `dev-secret-key-…`.
- [ ] Demo logins (`admin` / `admin123`, etc.) are for **assessment demos only**. Change or disable them if the app is exposed beyond markers.

## Seed endpoint

- [ ] `/seed` is **disabled** when `FLASK_ENV=production` or `VERCEL_ENV=production`, unless `ENABLE_SEED=1`.
- [ ] If `SEED_TOKEN` is set, requests must send `X-Seed-Token` (or `?token=`).
- [ ] Demo passwords are returned only when users are first created, not on subsequent `/seed` calls.
- [ ] Auto-bootstrap on empty DB runs in development only. Production must use an explicit `/seed` with `ENABLE_SEED=1`.
- [ ] Leave `ENABLE_SEED` unset in production after initial bootstrap.

## Application controls already in place

| Control | Implementation |
|---------|----------------|
| Password hashing | `pbkdf2:sha256` via Werkzeug |
| Sessions | Flask-Login + secure cookie flags in production |
| CSRF | Flask-WTF; AJAX uses `X-CSRFToken` |
| RBAC | Admin / Manager / Agent decorators |
| Call audit | `CallActivity` on create, assign, status, bulk |
| System audit | `SystemAudit` on login/logout/lockout and admin CRUD |
| Injection | SQLAlchemy ORM (no raw string SQL for user input) |
| Rate limit | Flask-Limiter on app |
| API enums | Status, priority, and call type validated on write |
| HTTP headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`; HSTS in production |
| DB SSL | `sslmode=require` for Neon/hosted URLs; `DATABASE_SSLMODE=disable` for local Docker Postgres |

Passwords are never written to audit details. Login failures record username only.

## Operational

- [ ] Confirm `/health` returns `"backend": "postgres"` and `"database": "ok"`.
- [ ] Confirm HTTPS only (Vercel provides this).
- [ ] Repo: avoid committing `.env`, real connection strings, or production dumps.
- [ ] Review Admin → Audit log after go-live (filter source = system).
- [ ] Local Compose uses Postgres 16 (not MySQL). Change default Compose passwords before exposing ports.

## If credentials leaked

1. Rotate Neon password immediately in the Neon console.
2. Update Vercel `DATABASE_URL` and redeploy.
3. Optionally force-logout by changing `SECRET_KEY` (invalidates all sessions).
