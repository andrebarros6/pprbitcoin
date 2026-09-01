FROM python:3.12-slim

WORKDIR /app

# psycopg2 needs libpq at runtime; build-essential is only needed to compile
# wheels that have no prebuilt binary, so it is removed in the same layer.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway injects PORT. Default to 8000 for local `docker run`.
ENV PORT=8000
EXPOSE 8000

# A backtest is CPU-bound pandas work taking seconds, and one worker serves
# them one at a time: measured latency rose linearly with load (1 user 7s,
# 10 users 45s, 30 users timing out). Workers are separate processes, so they
# use separate cores. Override WEB_CONCURRENCY to match the plan's CPU count.
ENV WEB_CONCURRENCY=4

# Migrations run at start so a fresh Postgres is usable on first boot.
# Seeding is a separate, explicit step (see scripts/migrate_to_postgres.py).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-4}"]
