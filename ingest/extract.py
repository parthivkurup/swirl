import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from ingest.db import connect
from ingest.extractor import CaptionInput, extract_captions
from ingest.fixtures_io import load_fixture_inputs
from ingest.gemini_client import GeminiClient
from ingest.log import log
from ingest.postprocess import INSERT_DEAL, build_deal_row

PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_deal.txt"
ROOT = Path(__file__).resolve().parent.parent
PROGRESS_MD = ROOT / "PROGRESS.md"

# Consecutive failed extractions before a capture stops being retried and is
# flagged instead. A thing that keeps failing quietly must eventually become loud.
#
# WHY 5, and not the 3 a scrape-side strike counter would use. The extract runs
# twice a day, so 5 strikes is
# ~2.5 days of sustained failure. Every failure seen so far has been transient
# API weather (429 bursts, the 503 UNAVAILABLE window on 2026-08-15) measured in
# hours, and 5 comfortably outlives that while 3 (~36 hours) sits uncomfortably
# close to a long outage or a weekend. The asymmetry with a scrape-side counter is
# deliberate and runs the other way for a reason: there, a fast trip is protective,
# because continuing to hammer a source that is refusing you makes things worse, so
# stopping early is the safe error. Here the opposite is true - abandoning a
# capture is the destructive act, retrying it costs one API call, and giving up
# early on a promo that is still live is the expensive mistake. Past ~5 the retry
# has stopped being automatic recovery: something that has failed 5 times over
# 2.5 days is a defect (an unreadable image, a caption that breaks the schema),
# not weather, and a human should look at it.
MAX_EXTRACT_ATTEMPTS = 5


def load_prompt():
    return PROMPT_PATH.read_text(encoding="utf-8")


def _load_stores(conn):
    with conn.cursor() as cur:
        cur.execute("select id, name, suburb, chain_id from stores")
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _load_chains(conn):
    with conn.cursor() as cur:
        cur.execute("select id, name, instagram_handle, footprint from chains")
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _fetch_captures(conn, reprocess_since):
    # source_type='fixture' captures are test data (tests/fixtures, seeded only by
    # the dev-only seed_fixtures.py). They must never become live deals, so the DB
    # extract path excludes them; the extractor test suite exercises fixtures
    # in memory via load_fixture_inputs, not through this path.
    with conn.cursor() as cur:
        if reprocess_since:
            cur.execute(
                "select id, source_type, source_url, content_text, image_path, "
                "source_handle, via_handle, submitted_store, content_hash, "
                "captured_at::date::text as capture_date "
                "from raw_captures where captured_at::date >= %s "
                "and source_type <> 'fixture' order by id",
                (reprocess_since,),
            )
        else:
            # Abandoned captures (extract_attempts at the limit) drop out of the
            # retry queue. They are not deleted and not marked processed: they sit
            # here flagged, and resetting extract_attempts to 0 requeues them.
            cur.execute(
                "select id, source_type, source_url, content_text, image_path, "
                "source_handle, via_handle, submitted_store, content_hash, "
                "captured_at::date::text as capture_date "
                "from raw_captures where processed = false "
                "and extract_attempts < %s "
                "and source_type <> 'fixture' order by id",
                (MAX_EXTRACT_ATTEMPTS,),
            )
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def record_abandoned(abandoned_ids, captures):
    """A capture hit MAX_EXTRACT_ATTEMPTS: stop retrying it and make that
    impossible to miss: a structured log line plus a dated note in PROGRESS.md,
    because a log line alone is exactly the kind of thing that scrolls past unread,
    and the whole point of the limit is that silent failure stops being an option.

    Nothing is deleted and nothing is marked processed. The capture stays in the
    table, flagged, and is requeued by resetting extract_attempts to 0."""
    by_id = {c["id"]: c for c in captures}
    lines = []
    for cid in abandoned_ids:
        c = by_id.get(cid, {})
        lines.append(f"  - capture {cid} ({c.get('source_type', '?')}, {c.get('source_url') or 'no url'})")
    log("extract.captures_abandoned", ids=abandoned_ids, limit=MAX_EXTRACT_ATTEMPTS)
    note = (
        f"\n## Extraction incident ({datetime.now(timezone.utc).date().isoformat()})\n\n"
        f"- **{len(abandoned_ids)} capture(s) abandoned after {MAX_EXTRACT_ATTEMPTS} consecutive "
        f"failed extractions.** They are no longer retried and have produced no deals. A "
        f"capture that fails every run must not keep failing quietly.\n"
        + "\n".join(lines)
        + f"\n\n  Investigate (unreadable image, caption that breaks the schema, a persistent API "
        f"error), then requeue with:\n"
        f"  `update raw_captures set extract_attempts = 0 where id in (...);`\n"
    )
    try:
        with PROGRESS_MD.open("a", encoding="utf-8") as f:
            f.write(note)
    except Exception as e:
        log("extract.progress_note_failed", error=f"{type(e).__name__}: {e}")


def run_fixtures(client, prompt):
    inputs = load_fixture_inputs()
    results, stats = extract_captions(inputs, prompt, client)
    for inp, deals in zip(inputs, results):
        print(f"\n### {inp.label}")
        print(json.dumps(deals, ensure_ascii=False, indent=2))
    log("extract.fixtures", **stats)


def run_db(client, prompt, reprocess_since):
    with connect() as conn:
        captures = _fetch_captures(conn, reprocess_since)
        if not captures:
            log("extract.noop", reprocess_since=reprocess_since)
            return
        stores = _load_stores(conn)
        chains = _load_chains(conn)
        inputs = [
            CaptionInput(
                content_hash=c["content_hash"],
                text=c["content_text"] or "",
                capture_date=c["capture_date"],
                image_path=c["image_path"],
                label=str(c["id"]),
            )
            for c in captures
        ]
        results, stats = extract_captions(inputs, prompt, client)

        inserted = 0
        processed_ids = []
        failed_ids = []
        with conn.cursor() as cur:
            for cap, deals in zip(captures, results):
                if deals is None:
                    failed_ids.append(cap["id"])
                    continue  # stayed unprocessed, try again next run
                for deal in deals:
                    row = build_deal_row(deal, cap, stores, chains)
                    cur.execute(INSERT_DEAL, row)
                    if cur.fetchone():
                        inserted += 1
                processed_ids.append(cap["id"])
            if not reprocess_since and processed_ids:
                cur.execute(
                    "update raw_captures set processed = true where id = any(%s)",
                    (processed_ids,),
                )

            # A run where EVERY capture failed is the API being down, not these
            # captures being bad. Counting strikes then would burn the whole
            # backlog's budget in lockstep during one outage and abandon all of
            # it together, which is the opposite of what the limit is for. With a
            # single capture the two cases are indistinguishable, so it counts.
            outage = len(captures) > 1 and len(failed_ids) == len(captures)
            abandoned = []
            if failed_ids and not reprocess_since and not outage:
                cur.execute(
                    "update raw_captures set extract_attempts = extract_attempts + 1 "
                    "where id = any(%s) returning id, extract_attempts",
                    (failed_ids,),
                )
                abandoned = [r[0] for r in cur.fetchall() if r[1] >= MAX_EXTRACT_ATTEMPTS]
        conn.commit()

        # Successes and failures in the same line. Reporting only successes made a
        # partial run indistinguishable from a clean one: the real log line
        # `"captures": 1, "total": 2` was a capture failing silently.
        log("extract.db", deals_inserted=inserted, captures=len(processed_ids),
            failed=len(failed_ids), failed_ids=failed_ids,
            outage_suspected=outage, abandoned=len(abandoned), **stats)
        if outage:
            log("extract.outage_suspected", captures=len(captures),
                detail="every capture failed; strikes not counted, all will retry next run")
        if abandoned:
            record_abandoned(abandoned, captures)


def main():
    ap = argparse.ArgumentParser("ingest.extract")
    ap.add_argument("--reprocess-since", metavar="YYYY-MM-DD")
    ap.add_argument("--fixtures", action="store_true", help="run over test fixtures, print output, no DB write")
    args = ap.parse_args()

    load_dotenv()
    client = GeminiClient()
    prompt = load_prompt()
    if args.fixtures:
        run_fixtures(client, prompt)
    else:
        run_db(client, prompt, args.reprocess_since)


if __name__ == "__main__":
    main()
