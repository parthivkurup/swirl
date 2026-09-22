"""Weekly job: confirm each approved deal's source still carries the offer, and
bump last_verified if so. This does NOT re-extract (no model call): it re-fetches
the configured sources with the polite scraper and checks whether the deal's
original raw_capture content_hash still appears. A deal whose source no longer
carries it is not bumped, so it ages toward stale under the dashboard's 14-day
rule."""
from dotenv import load_dotenv

from ingest.db import connect
from ingest.log import log
from ingest.scrapers.website import WebsiteScraper

BUMP_SQL = "update deals set last_verified = now() where id = %s"


def partition(rows, current_hashes):
    """Split (deal_id, content_hash) rows into (bumped, stale) deal ids: bumped if
    the source still carries the content_hash, stale otherwise."""
    bumped, stale = [], []
    for deal_id, chash in rows:
        (bumped if chash in current_hashes else stale).append(deal_id)
    return bumped, stale


def main():
    load_dotenv()
    # Re-scrape the configured sources to see what they carry right now. fetch()
    # only reads; it does not write raw_captures or deals.
    current_hashes = {c.content_hash for c in WebsiteScraper().fetch()}

    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "select d.id, r.content_hash from deals d "
            "join raw_captures r on r.id = d.raw_capture_id "
            "where d.status = 'approved' and d.source_url is not null"
        )
        rows = cur.fetchall()
        bumped, stale = partition(rows, current_hashes)
        for deal_id in bumped:
            cur.execute(BUMP_SQL, (deal_id,))
        conn.commit()  # stale deals are not bumped; they age to stale on the dashboard

    log("reverify.done", checked=len(rows), bumped=len(bumped), stale=len(stale), stale_ids=stale)


if __name__ == "__main__":
    main()
