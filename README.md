# CallLog Pro

Production-style **call logging system** for organisational support desks: triage inbox, kanban board, agent queue, workload, reports, audit trail, and REST API.

**Live:** [call-logging-app-six.vercel.app](https://call-logging-app-six.vercel.app)  
**Stack:** Flask · SQLAlchemy · Neon Postgres · Vercel serverless · Bootstrap 5

---

## Architecture

```
Browser (SPA-like UI)
    |
    v
Vercel Serverless (Python / run.py entrypoint)
    |  Flask application factory (app/__init__.py)
    |  CSRF · Login · Rate limit · RBAC decorators
    v
Neon Postgres (pooler URL, NullPool on Vercel)
    tables: users, call_log, call_activity, departments
```

| Layer | Responsibility |
|-------|----------------|
| **Blueprints** | `auth`, `dashboard`, `calls`, `board`, `reports`, `admin`, `api` |
| **Models** | User (Admin/Manager/Agent), CallLog, CallActivity (audit), Department |
| **Security** | Flask-Login sessions, CSRF (header + form), hashed passwords, role decorators |
| **Persistence** | `DATABASE_URL` → `postgresql+psycopg` + `sslmode=require`; SQLite fallback for local/dev |
| **Ops UI** | Inbox + filters, kanban board, my queue, workload bars, SLA chips |

Serverless note: connections use **NullPool** so each invocation does not hold idle Postgres connections.

---

## Features

- Role-based UI (Agent desk vs Manager ops vs Admin)
- Call CRUD, notes, assign, bulk status/assign, CSV export
- Kanban board (drag status + assign dropdown)
- My queue + claim from unassigned pool
- Agent workload view
- SLA risk chips (`ok` / `warn` / `breach`) by priority age
- Dashboard charts (status, 7-day volume, department)
- Reports: daily, monthly, agent, department · Excel & PDF
- Audit log on status/assign changes
- REST API under `/api/*` (session auth; mutating routes need Agent+)
- `/health` probes DB backend (`postgres` vs `sqlite`)

---

## REST API notes

Session cookie required (same as the web UI). Send CSRF token on POST/PUT/PATCH via `X-CSRFToken`.

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/dashboard/stats` | Includes `avg_handle_mins`, SLA counts |
| GET | `/api/calls` | Optional `status`, `page`, `per_page` (max 100). Array body; `X-Total-Count` header |
| POST | `/api/calls` | Validates `call_type` and `priority` enums |
| GET | `/api/calls/<id>` | JSON 404 `{ok:false,error}` if missing |
| PATCH | `/api/calls/<id>` | Status / priority / assign / resolution |
| POST | `/api/calls/<id>/quick` | `claim` \| `resolve` \| `escalate` |
| GET | `/api/search?q=` | Calls + users |
| GET | `/api/phone-lookup?phone=` | Recent matches |

Error shape: `{ "ok": false, "error": "..." }` plus optional `missing` / `allowed`.

---

## Demo credentials

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |
| agent1 | agent123 | Agent |
| manager1 | manager123 | Manager |

See **[DEMO.md](DEMO.md)** for a 5-minute viva script.

---

## Environment variables (Vercel)

| Key | Required | Notes |
|-----|----------|--------|
| `DATABASE_URL` | Yes (prod) | Neon connection string |
| `SECRET_KEY` | Yes | Strong random string |
| `FLASK_ENV` | Recommended | `production` |
| `ENABLE_SEED` | Optional | Set to `1` to allow `/seed` in production |

**Security:** `/seed` is blocked in production unless `ENABLE_SEED=1`. Rotate Neon credentials if they were ever shared in chat. Change demo passwords before any real users.

---

## Local development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set SECRET_KEY
python run.py
```

Open http://127.0.0.1:5000

With Neon: set `DATABASE_URL` in `.env` the same way as on Vercel.

---

## Tests

```bash
pip install pytest
pytest tests/ -v
```

Covers health, login, create call, bulk status, API stats, API validation and JSON 404s.

---

## Project layout

```
app/
  blueprints/   # auth, calls, board, dashboard, admin, reports, api
  models/       # user, call, department
  templates/    # shell UI + board + reports
  static/       # CSS/JS design system
  utils/        # decorators, helpers (stats, SLA)
config.py       # URL normalizer, NullPool
run.py          # Vercel / local entrypoint
tests/
DEMO.md
```

---

## License

MIT — final-year project / portfolio use encouraged.
