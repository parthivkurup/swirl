"""Nightly job: an approved deal whose valid_to is in the past is no longer
active, so mark it expired. Deals with a null valid_to (open-ended, e.g. a
loyalty program) never expire on date."""
from dotenv import load_dotenv

from ingest.db import connect
from ingest.log import log

EXPIRE_SQL = (
    "update deals set status = 'expired' "
    "where status = 'approved' and valid_to is not null and valid_to < current_date "
    "returning id"
)


def main():
    load_dotenv()
    with connect() as conn, conn.cursor() as cur:
        cur.execute(EXPIRE_SQL)
        ids = [r[0] for r in cur.fetchall()]
        conn.commit()
    log("expire_deals.done", expired=len(ids), ids=ids)


if __name__ == "__main__":
    main()
