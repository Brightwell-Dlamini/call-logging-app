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
    tables: users, call_log, call_activity, system_audit, departments, tags, call_tags, canned_responses
```

| Layer | Responsibility |
|-------|----------------|
| **Blueprints** | `auth`, `dashboard`, `calls`, `board`, `reports`, `admin`, `api` |
| **Models** | User (Admin/Manager/Agent), CallLog, CallActivity, SystemAudit, Department, Tag, CannedResponse |
| **Security** | Flask-Login sessions, CSRF (header + form), hashed passwords, role decorators |
| **Persistence** | `DATABASE_URL` → `postgresql+psycopg` + `sslmode=require`; SQLite fallback for local/dev |
| **Ops UI** | Inbox + filters, kanban board, my queue, workload bars, SLA chips, tags, follow-ups |

Serverless note: connections use **NullPool** so each invocation does not hold idle Postgres connections.

---

## Features

- Role-based UI (Agent desk vs Manager ops vs Admin)
- Call CRUD, notes, assign, bulk status/assign, CSV export
- **Tags** – flexible coloured labels with multi-select and filtering
- **Follow-up dates** – schedule next action; overdue items highlighted on dashboard and list
- **Canned responses** – reusable note/resolution templates managed by Admin
- Kanban board (drag status + assign dropdown)
- My queue + claim from unassigned pool
- Agent workload view
- SLA risk chips (`ok` / `warn` / `breach`) by priority age
- Dashboard charts (status, 7-day volume, department, tag distribution, overdue counts)
- Reports: daily, monthly, agent, department · Excel & PDF
- **Audit trail** – call changes (`CallActivity`) plus auth/admin events (`SystemAudit`)
- **Dark mode** – system preference + manual toggle (persisted)
- REST API under `/api/*` (session auth; mutating routes need Agent+)
- `/health` probes DB backend (`postgres` vs `sqlite`)

Reports and inbox filters use range predicates on `DateLogged` plus composite indexes (`Status+DateLogged`, `AssignedTo+Status`, audit `ActivityDate`, `FollowUpDate`) so Neon can avoid full table scans as volume grows.

---

## REST API notes

Session cookie required (same as the web UI). Send CSRF token on POST/PUT/PATCH via `X-CSRFToken`.

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/dashboard/stats` | Includes overdue, tag_counts, avg_handle_mins, SLA |
| GET | `/api/calls` | Optional `status`, `tag`, `overdue`, `page`, `per_page` |
| POST | `/api/calls` | Supports `tag_ids`, `follow_up_date` |
| GET | `/api/calls/<id>` | Full detail including tags and follow-up |
| PATCH | `/api/calls/<id>` | Status / priority / assign / tags / follow-up |
| POST | `/api/calls/<id>/quick` | `claim` \| `resolve` \| `escalate` |
| GET | `/api/tags` | Active tags |
| GET | `/api/canned` | Active canned responses |
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

### Docker

Image exposes port 8000 and includes a `/health` HEALTHCHECK.

```bash
docker compose up --build
# http://127.0.0.1:8000
```

Pass `SECRET_KEY` and `DATABASE_URL` via the environment or a local `.env` file. Leave `ENABLE_SEED` unset in production-like runs.

New tables (`tags`, `call_tags`, `canned_responses`, `system_audit`) and the `FollowUpDate` column are created automatically via `db.create_all()` on startup.

---

## Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Covers health, login (including lockout and open-redirect rejection), create call, bulk status, API stats, API validation, JSON 404s, monthly date bounds, system audit writes, and `/seed` token gating.

GitHub Actions (`.github/workflows/tests.yml`) runs the same suite on pushes and pull requests to `main`.

---

## Project layout

```
app/
  blueprints/   # auth, calls, board, dashboard, admin, reports, api
  models/       # user, call, department, tag, canned, audit
  templates/    # shell UI + board + reports + admin
  static/       # CSS/JS design system + dark mode
  utils/        # decorators, helpers, audit writer
config.py       # URL normalizer, NullPool
run.py          # Vercel / local entrypoint
tests/
.github/workflows/tests.yml
docker-compose.yml
DEMO.md
```

---

## License

MIT — final-year project / portfolio use encouraged.
