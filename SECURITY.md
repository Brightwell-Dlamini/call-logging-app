# Security notes

This application handles support-desk call records and user credentials. Treat production deployments as containing personal data.

## Reporting

Report vulnerabilities privately to the repository owner. Do not open a public issue that includes exploit details or production secrets.

## Production checklist

- Set a strong unique `SECRET_KEY`. Do not use the development default.
- Set `FLASK_ENV=production` (and `VERCEL_ENV=production` on Vercel).
- Use Neon (or another hosted Postgres) via `DATABASE_URL`. Do not rely on ephemeral SQLite in production.
- Leave `ENABLE_SEED` unset unless you are deliberately bootstrapping an empty database. After seeding, disable it again.
- Set `SEED_TOKEN` and call `/seed` only with `X-Seed-Token` (or `?token=`) when seed is enabled.
- Change all demo passwords (`admin123`, `agent123`, `manager123`) before real users arrive.
- Session cookies are `HttpOnly` and `SameSite=Lax`. Production config also sets `Secure`.
- CSRF is enabled for browser forms. API clients using a session cookie must send `X-CSRFToken`.
- Login is rate-limited and locks after `MAX_LOGIN_ATTEMPTS` failures for `LOGIN_LOCKOUT_MINUTES`.
- Do not commit `.env` files or raw API tokens.

## Seed endpoint

`GET`/`POST` `/seed` is disabled when the process is considered production unless `ENABLE_SEED=1`. Production responses never include the demo password map.

## Authentication

Roles: Admin, Manager, Agent. Reports require Manager or Admin. Admin catalogue and user management require Admin. Failed logins and lockouts are written to `system_audit` without storing passwords.
