"""Nightly auto-merge of duplicate deals. Supersede, never delete.

Runs on approved, expired AND pending deals, so the review queue shows one
canonical row per promo instead of four copies to adjudicate by hand. Among
non-superseded deals in those three states, collapse strict duplicate pairs (see
ingest.dedupe.merge_candidate): the canonical is the best-ranked deal in the group
(see _STATUS_RANK), and superseded_by is set on the others. Merging never changes
status - a superseded pending stays pending, just hidden from the queue by default
and visible under the /review superseded filter. Gates on the duplicate scorer's
match strength, never on the model's confidence (every Instagram deal scores
0.9-1.0, so a confidence gate filters nothing). Null-value freebie look-alikes are
never merged here; they are left for the review queue. Every merge is logged as
structured output with both ids and the score.

Rejected deals are excluded and stay excluded: a rejected deal was judged not to
be a real deal, so nothing can be a duplicate of it, and it is therefore beyond
this job's reach forever. That is the correct scope only as long as the reject set
means "not a real deal" - if duplicates get filed there by hand, this job can
never clean up after them.

Dry-run by default (prints what it would do); pass --commit to apply.
"""
import argparse

from dotenv import load_dotenv

from ingest.db import connect
from ingest.dedupe import merge_candidate, norm_headline, similarity
from ingest.log import log

SELECT = (
    "select id, status, chain_id, deal_type, discount_value::float8 as discount_value, "
    "valid_from::text as valid_from, valid_to::text as valid_to, headline, raw_capture_id, scope "
    "from deals where status in ('approved', 'expired', 'pending') and superseded_by is null order by id"
)
UPDATE = "update deals set superseded_by = %s where id = %s"

# Canonical preference within a duplicate group: approved first (never demote a
# vetted, live deal behind anything), then expired, then pending, with
# earliest-created (lowest id) breaking same-status ties.
#
# EXPIRED OUTRANKS PENDING ON PURPOSE. Chains re-post the same promo each time it
# comes round, so a new capture's true canonical is usually the previous run,
# which has expired by the time the repost lands - it is the vetted row, and the
# pending repost is the unreviewed one. Excluding expired entirely (as this job
# and the review queue both used to) meant the nightly merge went quiet in exactly
# the case it exists for, and every recurring promo's second appearance became
# hand-work. Mirrors getDedupePool in web/lib/deals.ts; keep the two in step.
#
# This cannot resurrect a dead deal or hide a live one. Superseding only sets
# superseded_by, and merge_candidate still requires overlapping validity windows,
# so a repost carrying a genuinely new date range does not merge into the old run
# - it is a new deal and stays in the queue as one.
_STATUS_RANK = {"approved": 0, "expired": 1, "pending": 2}


def find_merges(rows):
    """rows: non-superseded approved/expired/pending deal dicts. Returns a list of
    (canonical_id, superseded_id, score). The canonical of each duplicate group is
    the best-ranked deal by _STATUS_RANK, earliest id breaking ties; every
    superseded id points at a canonical (non-superseded) deal, so pointers never
    chain. Merging never changes status - a superseded pending stays pending, just
    hidden from the queue."""
    # Unranked default sorts after every known status, so an unexpected status can
    # only ever be superseded, never chosen as a group's canonical.
    ordered = sorted(rows, key=lambda r: (_STATUS_RANK.get(r.get("status"), 99), r["id"]))
    superseded = set()
    merges = []
    for i, a in enumerate(ordered):
        if a["id"] in superseded:
            continue
        for b in ordered[i + 1:]:
            if b["id"] in superseded:
                continue
            if merge_candidate(a, b):
                score = round(similarity(norm_headline(a["headline"]), norm_headline(b["headline"])), 3)
                merges.append((a["id"], b["id"], score))
                superseded.add(b["id"])
    return merges


def main():
    ap = argparse.ArgumentParser("ingest.merge_dupes")
    ap.add_argument("--commit", action="store_true", help="apply the merges (default is a dry-run preview)")
    args = ap.parse_args()
    load_dotenv()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(SELECT)
            cols = [c.name for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        merges = find_merges(rows)
        for canonical, superseded, score in merges:
            log("merge.superseded", canonical=canonical, superseded=superseded, score=score,
                dry_run=not args.commit)
        if args.commit and merges:
            with conn.cursor() as cur:
                for canonical, superseded, _ in merges:
                    cur.execute(UPDATE, (canonical, superseded))
            conn.commit()
        log("merge.done", scanned=len(rows), pairs=len(merges), committed=args.commit)


if __name__ == "__main__":
    main()
