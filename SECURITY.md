# Security

This document describes the security posture of CallLog Pro and how to report issues.

## Reporting a vulnerability

Email the repository owner or open a **private** security advisory on GitHub. Do not file a public issue for credential leaks or remote-code findings.

Please include:

- Affected environment (local, Vercel, Docker)
- Steps to reproduce
- Impact (data exposure, privilege escalation, denial of service)

## Application controls

| Control | Notes |
|---------|--------|
| Authentication | Flask-Login sessions with `session_protection = strong` |
| CSRF | Flask-WTF CSRF on HTML forms; `/health` and `/seed` are exempt |
| Passwords | Werkzeug hashes; change demo passwords before any real users |
| Roles | Agent / Manager / Admin decorators on blueprints |
| Rate limits | Flask-Limiter on selected write routes |
| API | Session required. Unauthenticated `/api/*` returns JSON `401` |
| Seed | Disabled in production unless `ENABLE_SEED=1`; optional `SEED_TOKEN` |
| Secrets | Never commit `.env`. Rotate `SECRET_KEY` and `DATABASE_URL` if leaked |

## Production checklist

1. Set a long random `SECRET_KEY`.
2. Use Neon (or other) Postgres with `sslmode=require`.
3. Leave `ENABLE_SEED` unset unless you intentionally bootstrap demo data.
4. If `SEED_TOKEN` is set, require `X-Seed-Token` on `/seed`.
5. Change `admin` / `agent1` / `manager1` demo passwords immediately after first login.
6. Prefer HTTPS only (Vercel terminates TLS by default).

## Data handling

Call records include names, phone numbers, and free-text notes. Treat the database as personal data. Restrict Admin access, keep backups private, and delete demo data before handing the instance to a live desk.
