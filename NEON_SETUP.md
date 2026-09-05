# Neon (Postgres) setup for CallLog Pro

## 1. Create a Neon project
1. Go to https://console.neon.tech and sign up / log in
2. **New Project** → name it `call-logging` (or any name)
3. Region: pick the closest to your Vercel region (e.g. `eu-central-1` or US East)
4. After create, open **Connection details**
5. Copy the connection string that looks like:

```
postgresql://USER:PASSWORD@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require
```

## 2. Add env vars on Vercel
Project → **Settings** → **Environment Variables**

| Name | Value | Environments |
|------|--------|----------------|
| `DATABASE_URL` | paste Neon connection string | Production, Preview |
| `FLASK_ENV` | `production` | Production, Preview |
| `SECRET_KEY` | long random string | Production, Preview |

Then **Redeploy** the latest deployment (Deployments → ⋯ → Redeploy).

## 3. Seed data
After deploy, open once:

```
https://YOUR-APP.vercel.app/seed
```

Default logins:

- `admin` / `admin123`
- `agent1` / `agent123`
- `manager1` / `manager123`

## 4. Verify
```
https://YOUR-APP.vercel.app/health
```

Expect `"backend": "postgres"` and `"database": "ok"`.

## Notes
- The app auto-normalizes `postgres://` → `postgresql+psycopg://` and adds `sslmode=require`.
- On Vercel serverless we use `NullPool` so connections are not held across invocations.
- Free Neon projects may suspend after inactivity; first request can be slower (cold start).
