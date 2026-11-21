# Deployment

## Docker Compose (local PostgreSQL)

```powershell
docker compose up --build
```

Builds `infrastructure/docker/Dockerfile` (Python 3.12 slim, non-root user, `apps/backend` +
`packages` only), starts PostgreSQL 16 with a persistent volume, runs `alembic upgrade head`, and
serves the API on `http://127.0.0.1:8000`. Pass `GEMINI_API_KEY`, `GEMINI_MODEL`, and `JWT_SECRET`
through the environment or a root `.env`. Run the desktop separately with
`BACKEND_URL=http://127.0.0.1:8000`.

## Railway

`railway.json` selects the Dockerfile builder, the `/health` health check (120 s timeout), and
restart-on-failure. The container start command runs migrations and binds uvicorn to
`0.0.0.0:$PORT`, so Railway's assigned port is honoured automatically.

Service variables to set:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Reference the Railway PostgreSQL plugin variable (`postgres://…` is accepted). SQLite is refused in production. |
| `APP_ENV` | `production` |
| `JWT_SECRET` | Random, ≥ 32 bytes (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) |
| `UPLOAD_DIR` | A path on a mounted volume, writable by the container user |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Optional; AI features report "not configured" without them |
| `ALLOWED_ORIGINS` | Only if a browser client will call the API; HTTPS origins, comma-separated |
| `LOG_LEVEL` | `INFO` (default) or `DEBUG` |

Keep **one replica**: the rate limiter and the O*NET import guard are in-process. Set an edge
request-size limit that allows the 500 MB O*NET upload if administrators will import through the
API; otherwise load data with `python -m apps.backend.cli.load_onet` from a one-off job.

After the first deploy:

1. `curl https://<domain>/health` → `"database": "healthy"`, `"environment": "production"`, `"jwt_secret_configured": true`.
2. Create an administrator from a Railway shell: `python -m apps.backend.cli.create_admin --email you@example.com`.
3. Put `https://<domain>` into the desktop **Backend address** field (HTTPS is required for non-loopback hosts).

No deployment has been performed from this repository; verify the deployed health check before
pointing students at it.

## Production checklist

- `APP_ENV=production` with PostgreSQL and a fixed `JWT_SECRET` (startup refuses otherwise).
- Migrations applied (`alembic upgrade head`) — the API checks the revision at startup.
- Backups of PostgreSQL and the upload volume scheduled.
- `GET /health` monitored; it returns 503 when the database is unreachable.
