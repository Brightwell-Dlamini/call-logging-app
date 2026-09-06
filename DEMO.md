# Demo walkthrough (5–7 minutes)

Use this script for markers / viva demos.

**URL:** https://call-logging-app-six.vercel.app  

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Agent | `agent1` | `agent123` |
| Manager | `manager1` | `manager123` |

## Path A — Agent desk (2–3 min)

1. Login as **agent1**
2. Dashboard shows **My open**, unassigned pool, and overdue follow-ups (if any)
3. Open **My queue** → **Claim** an unassigned call
4. Open **Board** → drag a card to **In Progress** (note tag chips / Due badge if present)
5. Open a call detail → set a **Follow-up date**, add **Tags**, insert a **Canned response** into notes
6. Use the card **assign** dropdown to hand off to another agent

## Path B — Manager ops (2 min)

1. Login as **manager1**
2. Dashboard shows **Team workload** bars and tag distribution
3. **Calls** inbox → filter by **Overdue follow-ups** or a **Tag** chip
4. **Workload** page → capacity by agent
5. **Reports** → Monthly or Agent performance → export Excel/PDF

## Path C — Admin (1–2 min)

1. Login as **admin**
2. **Admin** overview shows Users, Departments, **Tags**, **Canned**, Audit
3. **Tags** → create or edit a coloured label
4. **Canned** → add a quick-reply template
5. **Calls** → bulk select → Mark Resolved

## Health check

`GET /health` should return `"backend": "postgres"` when Neon is connected.

## Theme

Toggle dark mode from the top bar (moon icon) or press **T**.
