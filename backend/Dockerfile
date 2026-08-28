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

# Migrations run at start so a fresh Postgres is usable on first boot.
# Seeding is a separate, explicit step (see scripts/migrate_to_postgres.py).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
