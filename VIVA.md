# Viva / marker talking points

## One-sentence pitch

CallLog Pro is a role-based call desk for an organisation: agents triage and claim work, managers watch workload and SLA, admins govern users and audit — deployed serverless on Vercel with persistent Neon Postgres.

## Architecture (30 seconds)

- **Flask application factory** with blueprints for auth, calls, board, reports, admin, API.
- **Vercel** runs the app as serverless Python; **Neon** holds data so cold starts don’t wipe the queue.
- Connection strategy: **NullPool** + SSL-normalised `DATABASE_URL` (no sticky connection pool on serverless).
- **CSRF** on forms and AJAX; **RBAC** via role properties and decorators; **audit trail** on meaningful call changes.

## Demo path (point at the screen)

1. Login **agent1** → dashboard “My open” → **My queue** → Claim.
2. **Board** → drag status → change assignee on a card.
3. Login **manager1** → workload bars → **Reports** → export.
4. Login **admin** → Users / Audit log.
5. Open `/health` → show `backend: postgres`.

Full script: [DEMO.md](DEMO.md).

## Design decisions worth defending

| Choice | Why |
|--------|-----|
| Neon over SQLite on Vercel | `/tmp` SQLite is ephemeral; markers need persistent data |
| Board + list + my queue | Matches real contact-centre workflows |
| SLA chips by priority age | Simple, visible ops metric without a separate SLA product |
| Seed locked in production | Avoids public re-seed / credential exposure |
| Server-rendered UI + progressive JS | Reliable for demo; no separate SPA build pipeline |

## Limitations (honest answers)

- No email/SMS notifications yet.
- API uses session auth (fine for same-origin UI; tokens would be next for mobile).
- SLA rules are fixed thresholds, not per-customer contracts.
- Demo passwords are weak by design for assessment access.

## Tests

```bash
pip install pytest
pytest tests/ -v
```

Covers health, login, create call, bulk status, API stats.
