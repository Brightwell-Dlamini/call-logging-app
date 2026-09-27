# Security policy

This document describes how CallLog Pro handles secrets, authentication, and production hardening.

## Reporting

If you discover a vulnerability in a deployment you control, treat it as an operational incident: rotate `SECRET_KEY` and database credentials, disable `ENABLE_SEED`, and review `system_audit` plus application logs. Do not open a public issue that includes live credentials.

## Secrets

- Never commit `.env`, Neon passwords, session keys, or personal API tokens.
- Copy `.env.example` for local work. Production must set a strong `SECRET_KEY` and `DATABASE_URL`.
- Session cookies are HttpOnly and SameSite=Lax. Production config also sets the Secure flag.
- Personal tokens (`clp_…`) are stored hashed. Revoke unused tokens from the admin or token UI.

## Seed endpoint

`GET`/`POST` `/seed` is a demo bootstrap. It is **disabled in production** unless `ENABLE_SEED=1`.

When `SEED_TOKEN` is set, the request must supply that value via the `X-Seed-Token` header or a `token` query parameter. Leave `ENABLE_SEED` unset on Vercel after the first bootstrap. Change demo passwords (`admin123`, `agent123`, `manager123`) before any real users exist.

## Authentication and CSRF

- Flask-Login sessions with `session_protection = 'strong'`.
- WTForms CSRF on browser POSTs (`X-CSRFToken` / `X-CSRF-Token` headers accepted).
- Login lockout: five failed attempts, then a 15-minute lock (`MAX_LOGIN_ATTEMPTS`, `LOGIN_LOCKOUT_MINUTES`).
- Role decorators gate Agent / Manager / Admin routes. Agents must not reach admin user management or unrestricted reports.

## Uploads and request size

`MAX_CONTENT_LENGTH` defaults to 2 MiB. CSV import should stay within that cap. Do not raise the limit without reviewing memory on Vercel.

## HTTP headers

The application factory adds conservative defaults when missing:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`

Vercel or a reverse proxy may overlay HSTS. Prefer HTTPS only in production.

## Database

- Prefer Neon or another managed Postgres with `sslmode=require`.
- On Vercel the engine uses `NullPool` so serverless invocations do not hold idle connections.
- `ensure_schema` and `ensure_indexes` are idempotent and run at startup. They add missing columns/indexes; they do not drop data.

## Health checks

`GET /health` is CSRF-exempt and returns database reachability. Do not expose extra internals on that route.

## Checklist before a public demo

1. `ENABLE_SEED` is not `1`.
2. Demo passwords rotated or the instance is clearly labelled as disposable.
3. `SECRET_KEY` is not the development default.
4. Neon credentials were never pasted into a public gist or chat.
