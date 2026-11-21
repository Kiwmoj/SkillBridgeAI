# SkillBridge AI

A Windows desktop app (PyQt6) and FastAPI backend for career research, learning plans, portfolio feedback, progress tracking, and moderated community knowledge.

## Run on Windows

Use Python 3.12, the version used for local development and testing. From this folder in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m desktop.launch_local
```

In VS Code, open this project **as a folder**, not just a file from the older scratch copy. If imports are unresolved, run **Python: Select Interpreter** and choose this folder's `.venv\Scripts\python.exe`. The launcher command above is all you need on subsequent runs.

The launcher migrates the local SQLite database, starts the API on a free loopback port, and opens the desktop. Closing the app stops its API. Use **Create account** for a student account. The database and private uploads stay in this folder; the original chat-folder copy was not moved. This clean workspace uses a new schema. Do not point it at the older copy's database; keep that database and uploads as a backup.

To run the components separately:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# In another terminal:
.\.venv\Scripts\python.exe -m desktop.main
```

## Add the occupational data

After the first launch (or `alembic upgrade head`), create an administrator from the backend terminal:

```powershell
.\.venv\Scripts\python.exe -m backend.admin --email you@example.com
```

The command prompts for the password; desktop registration cannot create admins. Download the **CSV ZIP** from the [official O*NET database page](https://www.onetcenter.org/database.html). Then either load it from the project terminal (no login needed):

```powershell
.\.venv\Scripts\python.exe -m backend.load_onet "C:\path\to\db_31_0_csv.zip"
```

or sign in as the administrator, open **Administrator**, and select **Import official O*NET ZIP**. Leave the version blank to use the archive's own version when available. A full import can take several minutes; wait for the completion summary before opening Career Explorer. Close the desktop app before loading from the terminal so the two do not compete for the SQLite database. Reference data is not bundled.

The importer supports the 31.0 CSV layout and earlier compatible tab-delimited ZIPs. It loads occupations, aliases, skill scales, education, tasks, work context, related careers, and other supported occupational tables. Reimporting replaces imported details without duplicating records or changing IDs for existing occupations. Some reference-only lookup and crosswalk tables are not imported; output shows the files and row counts processed. After import, use **Career Explorer** for details, comparisons, saved careers, and clearly labeled custom careers.

Source: O*NET® Database, U.S. Department of Labor, Employment and Training Administration. Used under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). SkillBridge AI reformats this data; USDOL/ETA has not endorsed these changes.

## Enable Gemini (optional)

Copy `.env.example` to `.env` if you do not already have one. Set `GEMINI_API_KEY` and `GEMINI_MODEL` to the API key and a currently available multimodal Gemini model offered by your account, then restart. Do not share the key with students or put it in source control.

Official career search, saved records, and progress work without Gemini. Guided text and image review need a configured provider; failures are shown rather than replaced with sample responses. An image is sent for review only after explicit confirmation. Uploaded images are resized and stripped of metadata, but the visible pixels can still contain private information. AI output is labeled separately from retrieved sources.

## Community and privacy

- Only approved, reviewed public copies can be retrieved. Approved community text is distinguished from official sources. Retrieval uses local hashed term vectors, not a trained SkillBridge model.
- Training requires both the current account setting and explicit permission for each contribution. Enabling the setting does not opt in prior submissions. Withdrawal revokes affected drafts and removes the derived draft contents. It does not unpublish otherwise approved community content.
- Drafts use reviewed, de-identified copies only. Automatic checks help flag common identifiers but are not comprehensive; moderators must review the full text and rights. No private profiles, images, or activity records enter the training pipeline.
- The approved knowledge catalog uses separate tables in the application database, not a separate database service. Draft creation does not train, export, deploy, or switch models.
- Students can set up a one-time recovery code in **Settings**. Save it somewhere safe when shown; there is no email-based recovery service. Account deletion asks for confirmation and the current password.

## Backend configuration

All backend settings are read once in [backend/config.py](backend/config.py) from environment variables or a `.env` file, validated, and shared by the database, security, AI, and API modules. Invalid values stop startup with a clear message instead of running misconfigured. Rules:

- `APP_ENV` is `development` (default) or `production`.
- `DATABASE_URL` must be `sqlite://` or `postgresql://` (`postgres://` from hosting providers is normalised). Production refuses SQLite so hosted data always lives in PostgreSQL.
- `JWT_SECRET` must be a random value of at least 32 bytes in production. Locally it may be blank; sessions then end when the server stops.
- `ALLOWED_ORIGINS` entries must be origins (`https://host[:port]`), HTTPS in production. CORS runs without credentials and accepts the `Authorization` header. The desktop app does not need CORS.
- `BACKEND_URL` (desktop target) must be HTTPS unless it is a loopback address. `PORT` is honoured by the container start command. `LOG_LEVEL` controls server logging.

Logs record startup checks, database failures, rejected authentication, invalid requests, and unexpected errors. They never include passwords, tokens, API keys, database credentials, or request bodies.

### Troubleshooting sign-in

- **"Invalid email or password"** — the account does not exist on this backend or the password is wrong. New installs have no accounts: use **Create account** first. Each database (local `skillbridge.db`, a Docker PostgreSQL, a Railway PostgreSQL) has its own accounts.
- **"Cannot reach the backend"** — nothing is listening at the address in the **Backend address** field. With `desktop.launch_local` the field is filled in automatically; do not change it. With `desktop.main`, start the API first and set `BACKEND_URL` to it.
- **"Use HTTPS for a remote backend"** — remote addresses must start with `https://`.
- **"Invalid or expired session"** — the token expired (`ACCESS_TOKEN_MINUTES`), the server restarted without a fixed `JWT_SECRET`, or you signed out elsewhere. Sign in again.

## Deploy

`docker compose up --build` provides a local PostgreSQL and API at `http://127.0.0.1:8000`; run the desktop separately. For Railway, configure a managed `DATABASE_URL`, `APP_ENV=production`, a random `JWT_SECRET` of at least 32 bytes, and an `UPLOAD_DIR` on a durable volume writable by the container account. Use an HTTPS public URL for the desktop and an edge request-size limit appropriate for uploads. Keep one API replica for the in-process rate limiter and import guard. Back up PostgreSQL and the private upload volume before schema upgrades.

Railway builds the [Dockerfile](Dockerfile); its start command runs `alembic upgrade head` and then binds uvicorn to `0.0.0.0:$PORT`. [railway.json](railway.json) points the platform health check at `/health` and restarts on failure. After deploying, verify `https://<your-domain>/health` returns `"database": "healthy"` and `"environment": "production"`, then put that HTTPS URL in the desktop's **Backend address**. No deployment has been performed from this repository; the deployed service must be tested before relying on it.

`GET /health` reports status, database connectivity and backend type, application version, environment, the imported occupational version, and whether Gemini and a fixed JWT secret are configured. It returns HTTP 503 with `"database": "unhealthy"` when the database cannot be queried, does not probe Gemini, and never includes credentials. `GET /auth/me` returns the signed-in account's id, email, name, role, and creation time.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use isolated SQLite databases and test doubles for AI calls. Opportunities currently link to verified source directories and track saved applications; they do not receive live listings or deadlines. A proprietary model is not trained or deployed.
