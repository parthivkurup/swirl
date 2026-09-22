"""User submission ingestion. Sanitizes the uploaded image (strips EXIF/GPS,
HEIC->JPEG) and then writes it through the SAME path as manual ingestion
(ManualScraper + insert_captures), only with source_type 'user_submission'. This
source_type is not 'website', so the auto-approve rule never fires: submissions
always land pending and go through /review."""
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from ingest.captures import insert_captures
from ingest.db import connect
from ingest.images import sanitize_image
from ingest.log import log
from ingest.scrapers.manual import ManualScraper

# Relative to the media root (see ingest/media.py), never an absolute path.
SUBMISSION_IMAGE_DIR = "submissions"


def main():
    ap = argparse.ArgumentParser("ingest.submit")
    ap.add_argument("--image", required=True)
    ap.add_argument("--stdin", action="store_true", help="read optional caption text from stdin")
    ap.add_argument("--store", help="shop name the submitter typed, kept structured")
    args = ap.parse_args()

    load_dotenv()
    clean_path, _mime = sanitize_image(Path(args.image).read_bytes(), SUBMISSION_IMAGE_DIR)
    text = sys.stdin.read().strip() or None if args.stdin else None
    store = (args.store or "").strip() or None

    # combine_hash: the photo is the evidence here, so it always participates in
    # the hash. Text alone would let two different signs with the same typed words
    # collide, and the second would be silently discarded as a duplicate.
    captures = ManualScraper(
        text=text, image_path=clean_path, source_type="user_submission",
        submitted_store=store, combine_hash=True,
    ).fetch()
    with connect() as conn:
        results = insert_captures(conn, captures)

    for r in results:
        log("submit.capture", content_hash=r["capture"].content_hash, id=r["id"],
            inserted=r["inserted"], image_path=clean_path, submitted_store=store)


if __name__ == "__main__":
    main()
