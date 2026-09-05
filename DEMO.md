# Demo walkthrough (5 minutes)

Use this script for markers / viva demos.

**URL:** https://call-logging-app-six.vercel.app  

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Agent | `agent1` | `agent123` |
| Manager | `manager1` | `manager123` |

## Path A — Agent desk (2 min)

1. Login as **agent1**
2. Dashboard shows **My open** and unassigned pool
3. Open **My queue** → **Claim** an unassigned call
4. Open **Board** → drag a card to **In Progress**
5. Use the card **assign** dropdown to hand off to another agent

## Path B — Manager ops (2 min)

1. Login as **manager1**
2. Dashboard shows **Team workload** bars
3. **Workload** page → capacity by agent
4. **Reports** → Monthly or Agent performance → export Excel/PDF

## Path C — Admin (1 min)

1. Login as **admin**
2. **Users** / **Departments** / **Audit log**
3. **Calls** → bulk select → Mark Resolved

## Health check

`GET /health` should return `"backend": "postgres"` when Neon is connected.
