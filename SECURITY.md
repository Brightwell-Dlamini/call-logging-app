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
| Audit | `CallActivity` on create, assign, status, bulk |
| Injection | SQLAlchemy ORM (no raw string SQL for user input) |
| Rate limit | Flask-Limiter on app |
| API enums | Status, priority, and call type validated on write |

## Operational

- [ ] Confirm `/health` returns `"backend": "postgres"` and `"database": "ok"`.
- [ ] Confirm HTTPS only (Vercel provides this).
- [ ] Repo: avoid committing `.env`, real connection strings, or production dumps.

## If credentials leaked

1. Rotate Neon password immediately in the Neon console.
2. Update Vercel `DATABASE_URL` and redeploy.
3. Optionally force-logout by changing `SECRET_KEY` (invalidates all sessions).
