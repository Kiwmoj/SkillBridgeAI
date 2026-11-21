# Database

SQLAlchemy 2 models live in `apps/backend/models/`, one module per domain; `models/__init__.py`
imports all of them so `Base.metadata` is complete for Alembic. Migrations live in
`apps/backend/database/migrations/` and are configured by the root `alembic.ini`.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head     # apply
.\.venv\Scripts\python.exe -m alembic check            # models vs. schema (must print "No new upgrade operations detected.")
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
```

Current head: `20261121_repair`. The API refuses to start if the database is at a different
revision, so run `upgrade head` after pulling schema changes. The 2.0 refactor changed no tables.

## Engines

- **SQLite** (default, `sqlite:///./skillbridge.db`): foreign keys enabled per connection, 20 s busy timeout, `check_same_thread=False` for the threaded local launcher.
- **PostgreSQL** (`postgres://`/`postgresql://`, normalised to the `psycopg` driver): pool of 5 (+10 overflow), pre-ping, 30 min recycle. Required when `APP_ENV=production`.

## Tables by domain

| Domain (module) | Tables | Notes |
| --- | --- | --- |
| users | `users`, `profiles` | Argon2 password hash, `session_version` for token revocation, one-time `recovery_hash` |
| occupations | `occupations`, `alternate_titles`, `descriptors`, `related_occupations`, `saved_careers`, `custom_occupations` | Imported O*NET rows carry `dataset_version`; re-imports replace details and keep occupation IDs so saved careers survive |
| skills | `skill_assessments` | Self-ratings |
| roadmaps | `roadmaps`, `learning_activities` | Roadmap `sources` JSON records retrieved references |
| portfolio | `portfolios` | File names only; images live in `UPLOAD_DIR` as sanitized PNGs |
| projects | `projects` | `planned` / `in_progress` / `completed` |
| opportunities | `opportunities` | Saved directory entries with `application_status` |
| community | `community_contributions`, `training_consent`, `approved_knowledge`, `review_history`, `community_policy` | `community_policy` is a one-row counter used to serialise moderation/consent writes |
| training | `dataset_versions`, `dataset_records`, `training_history`, `model_versions` | Dataset drafts and audit trail; no model artefacts are stored |
| analytics | `ai_usage` | Provider, feature, success, latency; no prompt or response text |

## Privacy boundaries

- Private records (profiles, portfolios, activities, saved items) are never read by the retrieval or training code paths.
- Only `approved_knowledge` rows (moderator-reviewed public copies) are retrievable, and only contributions with both consent flags enter dataset drafts.
- Account deletion removes every user-owned row, derived approved copies and review history, revokes affected drafts, and deletes the user's files.

## Backups

Back up PostgreSQL and the upload volume together before `alembic upgrade`. For SQLite, copy
`skillbridge.db` and `uploads/` while the API is stopped.
