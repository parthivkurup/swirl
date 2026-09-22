import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def log(event, **fields):
    print(json.dumps({"event": event, **fields}), flush=True)


def applied_set(cur):
    cur.execute("select filename from schema_migrations")
    return {row[0] for row in cur.fetchall()}


def main():
    load_dotenv()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("DATABASE_URL not set (copy .env.example to .env)")

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "create table if not exists schema_migrations ("
                "filename text primary key, "
                "applied_at timestamptz not null default now())"
            )
        conn.commit()

        with conn.cursor() as cur:
            already = applied_set(cur)

        pending = [p for p in sorted(MIGRATIONS_DIR.glob("*.sql")) if p.name not in already]
        if not pending:
            log("migrate.noop", already_applied=len(already), applied_this_run=0)
            return

        for path in pending:
            # No parameters in the query, so a multi-statement file runs as one batch.
            with conn.cursor() as cur:
                cur.execute(path.read_text())
                cur.execute("insert into schema_migrations (filename) values (%s)", (path.name,))
            conn.commit()
            log("migrate.applied", filename=path.name)

        log("migrate.done", applied_this_run=len(pending), total_applied=len(already) + len(pending))


if __name__ == "__main__":
    main()
