# Deployment (Railway)

Two services plus a database, all in one Railway project:

| Service | Root directory | Notes |
|---|---|---|
| `backend` | `backend/` | FastAPI + uvicorn, Dockerfile |
| `frontend` | `frontend/` | Vite build served by nginx, Dockerfile |
| `Postgres` | — | Railway plugin |

## 1. Create the project and database

1. New Project → Deploy from GitHub repo.
2. Add the **Postgres** plugin. Railway injects `DATABASE_URL` into services
   in the same project.

Railway's `DATABASE_URL` uses the `postgres://` scheme, which SQLAlchemy 2.x
does not accept. `config.sqlalchemy_url` rewrites it to `postgresql://`, so the
variable can be referenced verbatim.

## 2. Backend service

Set **Root Directory** to `backend`. Variables:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
DEBUG=False
CORS_ORIGINS=https://<your-frontend-domain>
RATE_LIMIT_PER_MINUTE=100
ENABLE_SCHEDULER=True
TZ=Europe/Lisbon
```

- `DEBUG` **must** be `False` in production. It enables SQLAlchemy statement
  logging (one log line per query) and exposes stack traces.
- `CORS_ORIGINS` must contain the frontend's real origin or the browser will
  block every API call. Comma-separated for multiple origins.
- `ENABLE_SCHEDULER` should be `True` on exactly one instance. If the backend
  is ever scaled beyond one replica, set it to `False` and run the refresh as
  a separate cron service instead, or every replica repeats the work.

Migrations run automatically on boot (`alembic upgrade head` in the
Dockerfile `CMD`), so the schema is created on first deploy.

## 3. Load the verified data

The database is empty after the first deploy. Load the cross-checked dataset
(see `backend/DATA_SOURCES.md`) from your machine:

```bash
cd backend
TARGET_DATABASE_URL="<Railway Postgres public URL>" \
  venv/Scripts/python.exe scripts/migrate_to_postgres.py --dry-run   # preview
TARGET_DATABASE_URL="<Railway Postgres public URL>" \
  venv/Scripts/python.exe scripts/migrate_to_postgres.py
```

Use the **public** connection string from the Postgres plugin's Connect tab
(the internal `.railway.internal` host only resolves inside Railway).

The script refuses to run against SQLite, clears the target first so it is
repeatable, and verifies row counts match the source before reporting success.

Alternative (no local dataset needed): run the seeds against the target to
fetch fresh from source — `seed_bitcoin.py --refresh` and
`seed_pprs.py --refresh`. Slower and depends on the upstream sources being
reachable, which is why migrating the verified snapshot is the default.

After loading, confirm the data is intact:

```bash
TARGET_DATABASE_URL="..." venv/Scripts/python.exe scripts/verify_ppr_data.py
```

## 4. Frontend service

Set **Root Directory** to `frontend`. Add a **build argument** (not just a
variable):

```
VITE_API_URL=https://<your-backend-domain>
```

Vite inlines env vars at **build** time. Setting `VITE_API_URL` only as a
runtime variable silently leaves `http://localhost:8000` compiled into the
bundle, and the deployed app will fail to reach the API.

`nginx.conf.template` falls back to `index.html` for unknown paths so client
routes (`/privacidade`, `/termos`) survive a hard refresh.

## 5. Post-deploy checks

```bash
curl https://<backend>/health          # {"status":"healthy"}
curl https://<backend>/api/v1/pprs     # 4 funds
```

Then in the browser:
- the calculator returns a chart and metrics
- `/privacidade` and `/termos` load, including on hard refresh
- no CORS errors in the console

## Verified locally against Postgres 15

The whole path below was exercised against the `docker-compose.yml` Postgres
before writing this, not just reasoned about:

- `alembic upgrade head` applies both migrations cleanly.
- Railway's `postgres://` scheme is rewritten and connects.
- `migrate_to_postgres.py` copied all 18,722 rows with matching counts.
- `verify_ppr_data.py` passes against the migrated data (all 12 APFIPP
  return checks within 0.1pp).
- The API returns identical metrics on Postgres and SQLite.
- The full test suite passes against both backends.

To repeat it:

```bash
docker compose up -d
cd backend
DATABASE_URL="postgresql://pprbitcoin:pprbitcoin_dev_password@localhost:5432/pprbitcoin" \
  venv/Scripts/python.exe -m alembic upgrade head
TARGET_DATABASE_URL="postgresql://pprbitcoin:pprbitcoin_dev_password@localhost:5432/pprbitcoin" \
  venv/Scripts/python.exe scripts/migrate_to_postgres.py
```

## Notes and known gaps

- **Scheduler**: refreshes a 30-day trailing window daily via
  `services/data_refresh.py`, reusing the same validated fetchers as the
  seeds. A failed refresh leaves existing rows untouched.
- **Rate limiting**: `RATE_LIMIT_PER_MINUTE` per IP on the two portfolio
  calculation endpoints, which each run a full historical backtest. It is
  in-memory, so limits are per instance rather than global.
- **Sentry**: `sentry-sdk` is in `requirements.txt` and `SENTRY_DSN` is a
  recognised setting, but it is **not initialised** in `app.py`. Error
  monitoring is not active.
- **`/docs`**: FastAPI's interactive docs are public. Disable by passing
  `docs_url=None` to `FastAPI()` if that is not wanted.
