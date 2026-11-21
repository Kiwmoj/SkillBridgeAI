# Refactoring Plan and Report

This document records the audit that preceded the structural refactor, the plan that was
executed, and the before/after layout. Behaviour was preserved; the database schema and
Alembic revision (`20261121_repair`) are unchanged, so existing data is untouched.

## 1. Audit findings (before)

| Area | Finding |
| --- | --- |
| Oversized files | `backend/main.py` had 1,687 lines: 62 route handlers, the rate limiter, auth dependencies, prompt text, image processing and SQL in one module. `desktop/main.py` had 1,433 lines: both windows, 13 page builders and a 90-line stylesheet inside `main()`. |
| Duplicated code | The "retrieve sources, build prompt, call AI, record usage, map provider failure to 503" sequence appeared four times (guidance, roadmaps, projects, portfolio). Owner-scoped lookups (`filter_by(id=…, user_id=…)` then 404) appeared ten times. Occupation dictionaries were serialised by hand in three handlers. The consent version `2026-11-21` was written in four places. |
| Unused code | `backend/api/__init__.py` was an empty package nothing imported. `schemas.ProfileResponse` and `schemas.OccupationResponse` were never referenced. |
| Circular / inverted imports | No cycles. `services/retrieval.py` imported the O*NET importer only for attribution constants; `services/training_pipeline.py` imported an API schema (`CONSENT_VERSION`) — a service depending on the HTTP layer. |
| Tight coupling | Routes mixed HTTP handling, business rules, SQL, file I/O and AI prompts. `record_ai_usage` depended on a module-global provider object. Desktop pages were methods on `MainWindow` sharing one attribute namespace. `desktop/launch_local.py` imported uvicorn, Alembic and the backend into the desktop package. |
| Duplicated configuration | Backend settings had just been centralised, but the desktop read `BACKEND_URL` through its own `load_dotenv` call inside the transport class. Deployment files (Dockerfile, compose, Railway) lived unorganised at the repository root. |
| Naming | `backend/security/__init__.py` and `backend/database/__init__.py` were packages containing only an `__init__`. `admin.py` (a CLI) sat next to admin routes. The worker class lived in `workers/__init__.py`. `HTTPException` was called positionally in some places and with keywords in others. |
| Missing documentation and tests | No architecture, API, database or deployment documents. No unit tests for the O*NET parser, consent sanitiser or token handling; the desktop smoke test existed only as an ad-hoc script. |

## 2. Principles applied

- UI displays and collects; controllers coordinate background work and session state; services hold business rules; repositories hold SQL; the API layer validates input and maps results to HTTP.
- One AI entry point (`services/ai`) — no provider-specific code outside it.
- One configuration object per application (`apps/backend/core/config.py`, `apps/desktop/config/settings.py`), read from environment variables.
- Pure, reusable code with no framework dependency lives in `packages/`.
- Versioned API under `/api/v1`, with the unprefixed legacy paths still served (hidden from the schema) so older clients keep working.

## 3. Structure adjustments from the target layout

The target layout in the brief was followed with these deliberate changes:

- `packages/onet` contains only parsing and validation (no database code). An importer that writes rows must know the backend's SQLAlchemy models, so that part lives in `apps/backend/services/careers/onet_import.py`; a `packages/onet/repositories` package would have depended on the application, inverting the dependency direction.
- All automated tests live under `tests/` (unit, integration, end_to_end, fixtures) rather than a second `apps/backend/tests` tree, so one `pytest` invocation and one `conftest.py` cover everything.
- Alembic lives at `apps/backend/database/migrations`; `alembic.ini` at the root points to it so `python -m alembic upgrade head` is unchanged.
- `Dockerfile` moved to `infrastructure/docker/`; `docker-compose.yml`, `railway.json` and `.dockerignore` stay at the root because Compose, Railway and the Docker build context look for them there. No `infrastructure/railway` directory was created — Railway is configured by `railway.json` plus service variables, documented in `docs/deployment/railway.md`.
- No `assets/`, `packages/shared` or `data/onet/processed` directories were created because nothing would live in them yet; `data/onet/raw` is the documented drop location for downloaded archives (ignored by Git).

## 4. Old structure

```
SkillBridgeAI/
├── alembic/                      env.py, versions/20261121_repair_…py
├── backend/
│   ├── main.py                   1,687 lines: app, middleware, dependencies, 62 routes
│   ├── admin.py                  create-admin CLI
│   ├── load_onet.py              O*NET loader CLI
│   ├── config.py
│   ├── api/__init__.py           empty
│   ├── database/__init__.py      engine, session, Base
│   ├── models/__init__.py        24 models in one file
│   ├── schemas/__init__.py       all Pydantic models
│   ├── security/__init__.py      hashing + JWT
│   └── services/                 ai_providers.py, onet_import.py, retrieval.py, training_pipeline.py
├── desktop/
│   ├── main.py                   1,433 lines: LoginWindow, MainWindow, 13 pages, stylesheet
│   ├── launch_local.py           migrations + uvicorn + desktop
│   ├── services/api_client.py
│   └── workers/__init__.py
├── tests/test_api.py, tests/test_backend_config_and_auth.py
├── Dockerfile, docker-compose.yml, railway.json, alembic.ini, README.md
```

## 5. New structure

```
SkillBridgeAI/
├── apps/
│   ├── backend/
│   │   ├── main.py                       create_app(); legacy + /api/v1 mounting
│   │   ├── api/
│   │   │   ├── router.py                 composes the versioned router
│   │   │   ├── dependencies/             auth.py (current_user, admin_user), database.py
│   │   │   ├── middleware/rate_limit.py
│   │   │   └── routes/                   health, auth, profiles, careers, guidance, skills,
│   │   │                                 roadmaps, portfolio, projects, opportunities,
│   │   │                                 analytics, community, admin
│   │   ├── core/                         config.py, security.py, logging.py, exceptions.py
│   │   ├── database/                     base.py, connection.py, session.py, migrations/
│   │   ├── models/                       users, occupations, skills, roadmaps, portfolio,
│   │   │                                 projects, opportunities, community, training, analytics
│   │   ├── schemas/                      same domain split as models (+ base.py)
│   │   ├── repositories/                 SQL only, one module per domain
│   │   ├── services/
│   │   │   ├── ai/                       providers.py, service.py, retrieval.py, grounded.py
│   │   │   ├── authentication/accounts.py
│   │   │   ├── careers/                  explorer.py, onet_import.py
│   │   │   ├── skills/gap_analysis.py
│   │   │   ├── roadmaps/generation.py
│   │   │   ├── portfolio/images.py
│   │   │   ├── projects/generation.py
│   │   │   ├── opportunities/directories.py
│   │   │   ├── community/                contributions.py, privacy.py
│   │   │   ├── training/pipeline.py
│   │   │   └── analytics/                progress.py, dashboard.py
│   │   └── cli/                          create_admin.py, load_onet.py
│   └── desktop/
│       ├── main.py, application.py
│       ├── config/settings.py
│       ├── controllers/                  session.py, tasks.py
│       ├── services/                     api_client.py (transport), backend.py (typed endpoints)
│       ├── workers/api_worker.py
│       └── ui/
│           ├── styles/theme.py
│           ├── components/               widgets.py, formatting.py
│           ├── dialogs/records.py
│           ├── windows/                  login_window.py, main_window.py
│           └── pages/                    one module per sidebar page (+ base.py)
├── packages/onet/                        constants.py, validators.py, parser.py
├── data/onet/raw/                        local drop folder for archives (ignored)
├── docs/                                 architecture/, api/, database/, deployment/, development/
├── infrastructure/docker/Dockerfile
├── scripts/launch_local.py               migrate + API + desktop on one loopback port
├── tests/                                conftest.py, fixtures/, unit/, integration/, end_to_end/
├── alembic.ini, docker-compose.yml, railway.json, pyproject.toml, requirements*.txt, README.md
```

## 6. Execution order

1. Create the branch `refactor/modular-architecture`; move `backend/` → `apps/backend/`, `desktop/` → `apps/desktop/`, `alembic/` → `apps/backend/database/migrations/`.
2. Split core, database, models and schemas by domain; keep `models/__init__.py` importing every model so Alembic autogenerate still sees the full metadata.
3. Extract repositories and services from the route handlers; create domain routers; mount them under `/api/v1` and (hidden) at the legacy paths.
4. Move O*NET parsing into `packages/onet`; keep the database writer in the backend.
5. Split the desktop into application, config, controllers, services, workers and UI packages; the API client targets `/api/v1`.
6. Reorganise tests, add unit and end-to-end coverage, update deployment files and documentation.
7. Validate: Pyright, the full test suite, a live desktop run against the launcher, then open and merge the pull request.
