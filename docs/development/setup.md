# Development Guide

## Prerequisites

- Windows 10/11 (the desktop is tested on Windows; the backend is cross-platform)
- Python **3.12** (`py -3.12`); the machine default may be newer, so always use the project `.venv`
- Git; Docker Desktop only for the Compose deployment

## Setup

```powershell
git clone https://github.com/Kiwmoj/SkillBridgeAI.git
cd SkillBridgeAI
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env   # optional; defaults work locally
```

VS Code: open the repository **folder** and select `.venv\Scripts\python.exe` as the interpreter
(`.vscode/settings.json` already points at it). Pyright and pytest settings live in `pyproject.toml`.

## Run

| Goal | Command |
| --- | --- |
| Desktop + local API together | `.\.venv\Scripts\python.exe scripts\launch_local.py` |
| API only | `.\.venv\Scripts\python.exe -m alembic upgrade head` then `.\.venv\Scripts\python.exe -m uvicorn apps.backend.main:app --host 127.0.0.1 --port 8000` |
| Desktop only (against a running API) | `.\.venv\Scripts\python.exe -m apps.desktop.main` (uses `BACKEND_URL`) |
| Create an administrator | `.\.venv\Scripts\python.exe -m apps.backend.cli.create_admin --email you@example.com` |
| Load O*NET data | `.\.venv\Scripts\python.exe -m apps.backend.cli.load_onet data\onet\raw\db_31_0_csv.zip` |

## Test and check

```powershell
.\.venv\Scripts\python.exe -m pytest                 # unit + integration + end-to-end
.\.venv\Scripts\python.exe -m pytest tests\unit      # fast, no database
npx pyright --pythonpath .\.venv\Scripts\python.exe   # type check (configured in pyproject.toml)
.\.venv\Scripts\python.exe -m alembic check          # models match the migration head
```

Tests use a fresh migrated SQLite database per test (`tests/conftest.py`), an isolated upload
directory, and test doubles for AI calls; they never touch `skillbridge.db`.

## Where things go

| I want to… | Put it in |
| --- | --- |
| Add an endpoint | A router in `apps/backend/api/routes/<domain>.py` (validate, call a service, return). Register new routers in `api/router.py`. |
| Add business logic | `apps/backend/services/<domain>/`. Raise `core.exceptions` types; commit here. |
| Add a query | `apps/backend/repositories/<domain>.py`. No commits, no policy. |
| Add a table or column | `apps/backend/models/<domain>.py`, export it from `models/__init__.py`, then `alembic revision --autogenerate`. |
| Add a request schema | `apps/backend/schemas/<domain>.py` (subclass `Form` for strict bodies). |
| Add an AI provider | Implement `AIProvider` in `services/ai/providers.py` and register it in `AIService`. |
| Add a desktop page | A `Page` subclass in `apps/desktop/ui/pages/`, a typed method in `services/backend.py`, and an entry in the nav list in `ui/windows/main_window.py`. |
| Parse a new O*NET file | Add its normalised stem to `packages/onet/constants.py`. |

## Conventions

- Services own transactions; routes and repositories never call `commit`.
- Never log passwords, tokens, API keys, database URLs, or request bodies.
- AI output is always labelled as generated and shown separately from retrieved sources.
- Keep the unprefixed legacy routes working until a major version removes them.
- Add a focused test next to the behaviour you change (`tests/unit` for pure code, `tests/integration` for API behaviour, `tests/end_to_end` for launcher + desktop flows).
