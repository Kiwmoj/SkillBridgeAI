# API Reference

Base path: `/api/v1`. Interactive documentation is served at `/docs` and `/openapi.json`.
Authenticated endpoints require `Authorization: Bearer <access_token>`. Tokens expire after
`ACCESS_TOKEN_MINUTES` (default 60) and are revoked by logout, password reset, or account deletion.

The same routes are also served without the prefix (for example `/health`, `/auth/login`) for
clients built before version 2.0; those aliases are hidden from the schema and may be removed in a
future major version.

## Errors

```json
{"detail": "Invalid email or password", "error": "authentication"}
{"detail": [{"loc": ["body", "email"], "msg": "value is not a valid email address"}], "error": "validation"}
```

| Status | `error` | Meaning |
| --- | --- | --- |
| 400 / 413 / 422 | `validation` | Bad input, oversize upload, or schema violation |
| 401 | `authentication` | Missing, invalid, expired, or revoked token / wrong credentials |
| 403 | `authorization` | Wrong role or wrong current password |
| 404 | `not_found` | Record missing or not owned by the caller |
| 409 | `conflict` | Duplicate email / dataset / model name, import already running |
| 429 | `rate_limited` | Per-client limit on auth, generation, and submission POSTs (30/min each); `Retry-After` header |
| 503 | `ai_provider` / `database` | Provider failure (message from the provider wrapper) or database unavailable |
| 500 | `server` | Unexpected failure; details are logged server-side only |

## Endpoints

### Health
| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/health` | – | `status`, `database`, `database_backend`, `ai`, `version`, `environment`, `onet_version`, `jwt_secret_configured`. 503 when the database cannot be queried. |

### Authentication
| Method | Path | Auth | Body / notes |
| --- | --- | --- | --- |
| POST | `/auth/register` | – | `{name, email, password(8–128)}` → `{access_token, token_type, role}`; 409 on duplicate email |
| POST | `/auth/login` | – | `{email, password}` → token response; 401 on bad credentials |
| GET | `/auth/me` | user | `{id, email, name, role, created_at}` |
| POST | `/auth/logout` | user | Revokes every session of the user |
| POST | `/auth/recovery-code` | user | `{password}` → `{recovery_code}` shown once |
| POST | `/auth/reset-password` | – | `{email, recovery_code, password}` |
| POST | `/auth/delete-account` | student | `{password}`; removes all owned records and private files |

### Profiles
| GET / PUT | `/profile` | user | `{education, interests, goals, location}` |

### Careers (O*NET)
| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/occupations/search?q=&limit=` | – | Title, description, code, or alternate title match; empty query → `[]` |
| GET | `/occupations/{id}?category=&offset=&limit=` | – | Detail with attribution, categories, descriptors, related occupations |
| POST | `/occupations/compare` | – | `{occupation_ids: [2–5]}` → top importance descriptors per occupation |
| GET | `/occupations/saved` | user | Saved careers |
| PUT / DELETE | `/occupations/saved/{id}` | user | Save / unsave |
| POST / GET | `/custom-occupations` | user | Careers outside O*NET, always labelled unverified |
| DELETE | `/custom-occupations/{id}` | user | |

### Guidance and skills
| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| POST | `/ai/generate` | user | `{purpose, question}` → `{answer, sources, generated, retrieved, provider}` |
| POST | `/skill-gap` | user | `{occupation_id | occupation_title, current_skills[]}` → strengths / gaps with source label |
| POST / GET | `/assessments` | user | Self-rated skills |

### Roadmaps and activities
| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| POST / GET | `/roadmaps` | user | Generate (AI) and list saved roadmaps with sources |
| DELETE | `/roadmaps/{id}` | user | Detaches activities, then deletes |
| POST / GET | `/activities` | user | `{title, status, notes, roadmap_id?}` |
| PATCH | `/activities/{id}` | user | |

### Portfolio
| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| POST | `/portfolio/upload` | user | multipart `file` ≤ 10 MB, ≤ 20 MP; stored as a sanitized PNG |
| GET | `/portfolio` | user | |
| POST | `/portfolio/{id}/evaluate` | user | `{send_to_provider: true}` — explicit confirmation before the image leaves the server |

### Projects
| POST / GET | `/projects` | user | Generate (AI) and list |
| PATCH / DELETE | `/projects/{id}` | user | `{status: planned | in_progress | completed}` |

### Opportunities and colleges
| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/opportunities?q=` | – | Official directory starting points (not live listings) |
| POST | `/opportunities/save` | user | |
| GET | `/opportunities/saved` | user | |
| PATCH / DELETE | `/opportunities/saved/{id}` | user | `{application_status: saved | preparing | applied | closed}` |

### Analytics
| GET | `/progress` | user | Counts used by the dashboard and charts |

### Community and consent
| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET / PUT | `/training-consent` | user | Account-level training permission; disabling withdraws all per-contribution consent |
| POST / GET | `/contributions` | user | Submit for review / list own submissions |
| PUT | `/contributions/{id}/consent` | user | Per-contribution training permission |

### Administration (role `admin`)
| Method | Path | Notes |
| --- | --- | --- |
| GET | `/admin/dashboard` | Totals for contributions, consent, eligible records, datasets, models, AI usage |
| POST | `/admin/onet/import?version=` | multipart ZIP ≤ 500 MB; one import at a time |
| GET | `/admin/contributions` | Full moderation queue |
| POST | `/admin/contributions/{id}/review` | `{status, deidentified, quality_rating, notes, public_title, public_body, public_source}` |
| GET | `/admin/contributions/{id}/history` | Review history |
| POST / GET | `/admin/datasets` (`/build`) | Create a reviewed draft / list versions |
| GET | `/admin/datasets/{id}/records` | Draft records (drafts only) |
| GET | `/admin/training/history` | Audit trail |
| GET / POST | `/admin/models` | Recorded model versions and evaluations |

## Changes in 2.0

- Added the `/api/v1` prefix; unprefixed paths remain as hidden aliases.
- Added the `error` category field to every error body. `detail` is unchanged.
- No request or response schema changed.
