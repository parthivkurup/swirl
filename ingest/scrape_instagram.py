"""Instagram scrape runner.

Wires the Instagram capture source to the database: fetch captures, insert them
(deduped on content_hash), then advance the per-account high-water marks in
`instagram_seen`. It writes to `raw_captures` only; extraction runs separately on
its own schedule, so the two-stage split holds for this source as it does for the
website scraper.

The capture source itself is private and not included in this repository (see
ingest/scrapers/instagram.py), so a run here raises NotImplementedError and
writes nothing. Everything below — the monitored-account set, the dedupe, the
high-water table — is the public half and is unchanged.

Run:   python -m ingest.scrape_instagram
"""
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from ingest.captures import insert_captures
from ingest.db import connect
from ingest.log import log
from ingest.scrapers.instagram import InstagramScraper

ROOT = Path(__file__).resolve().parent.parent
CHAINS_YAML = ROOT / "config" / "chains.yaml"


def load_monitored_handles(chains_yaml=CHAINS_YAML):
    """Return {handle_lower: chain_name} for every chain with a non-null
    instagram_handle. Only these accounts are ever visited or captured."""
    data = yaml.safe_load(Path(chains_yaml).read_text(encoding="utf-8"))
    out = {}
    for chain in data.get("chains", []):
        handle = chain.get("instagram_handle")
        if handle:
            out[handle.strip().lstrip("@").lower()] = chain.get("name")
    return out


def load_seen(conn):
    """Return {account: last_shortcode} high-water marks."""
    shortcodes = {}
    with conn.cursor() as cur:
        cur.execute("select account, last_shortcode from instagram_seen")
        for account, shortcode in cur.fetchall():
            shortcodes[account] = shortcode
    return shortcodes


UPSERT_SEEN = (
    "insert into instagram_seen (account, last_shortcode, last_seen_at) "
    "values (%(account)s, %(shortcode)s, now()) "
    "on conflict (account) do update set "
    "last_shortcode = coalesce(excluded.last_shortcode, instagram_seen.last_shortcode), "
    "last_seen_at = now()"
)


def update_seen(conn, matched, newest):
    """Bump last_seen_at for every account seen this run (even with no new posts),
    and advance last_shortcode to the newest one we saw."""
    with conn.cursor() as cur:
        for account in matched:
            cur.execute(UPSERT_SEEN, {"account": account, "shortcode": newest.get(account)})
    conn.commit()


def run():
    load_dotenv()
    monitored = load_monitored_handles()
    try:
        with connect() as conn:
            scraper = InstagramScraper(monitored, seen_shortcodes=load_seen(conn))
            captures = scraper.fetch()
            results = insert_captures(conn, captures)
            update_seen(conn, scraper.matched, scraper.newest)
    except NotImplementedError as e:
        # Write nothing. A missing capture source must not read as a healthy run
        # that found no posts.
        log("instagram.source_unavailable", detail=str(e))
        return 1
    inserted = sum(1 for r in results if r["inserted"])
    log("instagram.run_ok", captures=len(captures), inserted=inserted,
        duplicates=len(captures) - inserted, accounts_matched=len(scraper.matched))
    return 0


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
