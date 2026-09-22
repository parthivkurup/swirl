from dotenv import load_dotenv

from ingest.captures import insert_captures
from ingest.db import connect
from ingest.log import log
from ingest.scrapers.website import WebsiteScraper


def main():
    load_dotenv()
    captures = WebsiteScraper().fetch()
    with connect() as conn:
        results = insert_captures(conn, captures)
    inserted = sum(1 for r in results if r["inserted"])
    log("scrape.done", captures=len(captures), inserted=inserted, duplicates=len(captures) - inserted)


if __name__ == "__main__":
    main()
