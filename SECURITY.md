# Security notes

This document describes how CallLog Pro is intended to be operated. It is not a penetration-test report.

## Secrets and configuration

- Never commit `.env` or live database credentials. Use `.env.example` as the template.
- Set a long random `SECRET_KEY` in every deployed environment. Changing it invalidates sessions.
- Production should set `FLASK_ENV=production` (or run under `VERCEL_ENV=production`).
- Prefer a pooled Neon URL with `sslmode=require`. On Vercel the app uses `NullPool` so invocations do not hold idle connections.

## Authentication and sessions

- Passwords are stored hashed via the `User` model helpers.
- Flask-Login uses `session_protection = 'strong'`.
- Login is rate-limited (10 attempts per minute per remote address).
- Five consecutive failed passwords for the same username lock that username for 15 minutes (in-process; resets on cold start).
- Failed login, lockout, inactive-account, successful login, and logout are written to `system_audit`.
- CSRF protection is enabled application-wide. JSON clients may send `X-CSRFToken` or `X-CSRF-Token`.

## Roles

Access is enforced with blueprint decorators (`login_required_active`, `agent_required`, `manager_required`, `admin_required`). Agents, managers, and administrators see different navigation and APIs. Do not grant Admin for routine desk work.

## HTTP `/seed`

The seed route can create demo users and sample calls.

- In production it is disabled unless `ENABLE_SEED=1`.
- When `SEED_TOKEN` is set, callers must send it as `X-Seed-Token` or `?token=`.
- Production responses never include demo passwords, even when seeding is temporarily enabled.
- Seed success and rejection are recorded in `system_audit` (`ops.seed`, `ops.seed_denied`).
- Leave `ENABLE_SEED` unset (or `0`) after a one-off bootstrap. Change demo passwords immediately if those accounts will remain.

## API tokens and imports

- Personal tokens (`clp_…`) are hashed at rest. Treat the plaintext token as a password.
- Scope tokens to the minimum needed (read vs write) and revoke unused tokens from the admin/token UI.
- CSV import is size-capped (`MAX_CONTENT_LENGTH` / `MAX_IMPORT_BYTES`, default 2 MiB). Only administrators should import.

## Health endpoint

`GET /health` is CSRF-exempt and reports database reachability. It does not require a session. Do not put secrets in the payload.

## Reporting issues

Open a private GitHub issue or contact the repository owner. Do not file public issues that include credentials, customer call notes, or live connection strings.
