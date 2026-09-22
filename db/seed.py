import json
import os
import sys
from pathlib import Path

import psycopg
import yaml
from dotenv import load_dotenv

CHAINS_YAML = Path(__file__).parent.parent / "config" / "chains.yaml"

UPSERT = (
    "insert into chains "
    "(name, website, instagram_handle, has_loyalty_app, posts_promos, promo_url, footprint) "
    "values (%(name)s, %(website)s, %(instagram_handle)s, %(has_loyalty_app)s, "
    "%(posts_promos)s, %(promo_url)s, %(footprint)s) "
    "on conflict (name) do update set "
    "website = excluded.website, "
    "instagram_handle = excluded.instagram_handle, "
    "has_loyalty_app = excluded.has_loyalty_app, "
    "posts_promos = excluded.posts_promos, "
    "promo_url = excluded.promo_url, "
    "footprint = excluded.footprint"
)


def log(event, **fields):
    print(json.dumps({"event": event, **fields}), flush=True)


def main():
    load_dotenv()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("DATABASE_URL not set (copy .env.example to .env)")

    data = yaml.safe_load(CHAINS_YAML.read_text()) or {}
    chains = data.get("chains", [])
    if not chains:
        sys.exit(f"no chains found in {CHAINS_YAML}")

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for c in chains:
                cur.execute(
                    UPSERT,
                    {
                        "name": c["name"],
                        "website": c.get("website"),
                        "instagram_handle": c.get("instagram_handle"),
                        "has_loyalty_app": bool(c.get("has_loyalty_app", False)),
                        "posts_promos": c.get("posts_promos"),
                        "promo_url": c.get("promo_url"),
                        # Defaults to the safe side, never to melbourne_only: an
                        # unclassified chain must not make a silent caption
                        # look like a Melbourne deal.
                        "footprint": c.get("footprint") or "unknown",
                    },
                )
        conn.commit()

    log("seed.done", chains=len(chains))


if __name__ == "__main__":
    main()
