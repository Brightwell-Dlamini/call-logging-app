# CallLog Pro

Production-style **call logging system** for organisational support desks: triage inbox, kanban board, agent queue, workload, reports, audit trail, REST API, saved views, in-app notifications, and API tokens.

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
    tables: users, call_log, call_activity, system_audit, departments,
            tags, call_tags, canned_responses, contacts, saved_views,
            notifications, api_tokens
```

| Layer | Responsibility |
|-------|----------------|
| **Blueprints** | `auth`, `dashboard`, `calls`, `board`, `reports`, `admin`, `api`, `api_extras` |
| **Models** | User, CallLog, CallActivity, SystemAudit, Department, Tag, CannedResponse, Contact, SavedView, Notification, ApiToken |
| **Security** | Flask-Login sessions, CSRF, hashed passwords, role decorators, personal API tokens |
| **Persistence** | `DATABASE_URL` → `postgresql+psycopg` + `sslmode=require`; SQLite fallback |
| **Ops UI** | Inbox + filters, kanban, my queue, workload, SLA chips, tags, follow-ups, saved views |

Serverless note: connections use **NullPool** so each invocation does not hold idle Postgres connections.

Every HTTP response includes `X-Request-ID` (honoured from a safe incoming header, otherwise generated) so logs and `/health` can be correlated.

---

## Features

### Core
- Role-based UI (Agent desk vs Manager ops vs Admin)
- Call CRUD, notes, assign, bulk status/assign, CSV export
- **Tags** – flexible coloured labels with multi-select and filtering
- **Follow-up dates** – schedule next action; overdue items highlighted
- **Canned responses** – reusable note/resolution templates
- Kanban board (drag status + assign dropdown)
- My queue + claim from unassigned pool
- Agent workload view
- **Configurable SLA** thresholds by priority (`ok` / `warn` / `breach`)
- Dashboard charts (status, 7-day volume, department, tag distribution, overdue)
- Reports: daily, monthly, agent, department · Excel & PDF
- **Audit trail** – call changes + system events
- **Dark mode** – system preference + manual toggle

### New / Enhanced
- **Saved Views** – pin and reuse filter combinations (status, tags, department, overdue, etc.)
- **In-app Notifications** – assignment, SLA, follow-up, and system events with unread tracking
- **Contact Timeline** – CRM-lite profile + full call history by phone number; VIP flag
- **Personal API Tokens** – long-lived tokens (`clp_…`) for external integrations (read/write scopes)
- Improved SLA engine with per-priority warn/breach hours
- Contact auto-creation on call logging

### REST API (session or future token)
| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/dashboard/stats` | Includes overdue, tag_counts, SLA, unread notifications |
| GET/POST | `/api/calls` | List / create |
| GET/PATCH | `/api/calls/<id>` | Detail / update |
| POST | `/api/calls/<id>/quick` | claim · resolve · escalate · pending · reopen |
| GET | `/api/views` | List saved views |
| POST/PUT/DELETE | `/api/views` / `/api/views/<id>` | Manage saved views |
| GET | `/api/inbox` | Notifications (supports `?unread=1`) |
| POST | `/api/inbox/read` | Mark notifications read |
| GET | `/api/contacts/timeline?phone=` | Contact + call history |
| POST | `/api/contacts` | Upsert contact profile |
| GET/POST/DELETE | `/api/tokens` | Personal access tokens |
| GET | `/api/tags`, `/api/canned`, `/api/search` | Supporting resources |

Error shape: `{ "ok": false, "error": "..." }`.

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

**Security:** `/seed` is blocked in production unless `ENABLE_SEED=1`. Rotate Neon credentials if they were ever shared. Change demo passwords before any real users.

---

## Local development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set SECRET_KEY
python run.py
```

Open http://127.0.0.1:5000

New tables (`saved_views`, `notifications`, `api_tokens`, etc.) are created automatically via `db.create_all()` on startup.

---

## Docker

Compose runs the Flask app with **Postgres 16** (not MySQL). Default credentials match `.env.example` comments and are for local use only.

```bash
docker compose up --build
```

App: http://127.0.0.1:8000  
Health: `GET /health` (returns `request_id` and database status).

Set `SECRET_KEY` in the environment before exposing the stack beyond localhost.

---

## Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Project layout

```
app/
  blueprints/   # auth, calls, board, dashboard, admin, reports, api, api_extras
  models/       # user, call, department, tag, canned, audit, contact,
                # saved_view, notification, api_token
  templates/    # shell UI + board + reports + admin
  static/       # CSS/JS design system + dark mode
  utils/        # decorators, helpers (SLA, notifications, timeline), audit
config.py
run.py
tests/
```

---

## License

MIT — final-year project / portfolio use encouraged.
