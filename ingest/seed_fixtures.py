"""DEV-ONLY. Load the test fixture captions into raw_captures with
source_type='fixture'. This was used early on to give the phase-5 review queue
something to work through, but fixtures are test data and must not reach the live
set: the DB extract path now EXCLUDES source_type='fixture', so seeded fixtures no
longer become deals. Retained only as a local dev helper and guarded behind an
explicit --dev flag so it cannot run by accident. Never run it against a shared or
production database. The extractor test suite does not use this; it reads the
fixture files in memory via load_fixture_inputs."""
import sys
from ingest.captures import insert_captures
from ingest.db import connect
from ingest.fixtures_io import FIXTURES_DIR, parse_caption
from ingest.hashing import content_hash
from ingest.log import log
from ingest.scrapers.base import RawCapture
from pathlib import Path


def build_captures(fixtures_dir=FIXTURES_DIR):
    caps = []
    for txt in sorted(Path(fixtures_dir).glob("*.txt")):
        capture_date, body = parse_caption(txt)
        caps.append(
            RawCapture(
                source_type="fixture",
                content_hash=content_hash(text=body),
                source_url=None,
                content_text=body,
                image_path=None,
                captured_at=capture_date,
            )
        )
    return caps


def main():
    if "--dev" not in sys.argv:
        raise SystemExit(
            "seed_fixtures is dev-only and inserts source_type='fixture' test rows "
            "that the live pipeline ignores. Pass --dev to run it against a local dev DB."
        )
    caps = build_captures()
    with connect() as conn:
        results = insert_captures(conn, caps)
    inserted = sum(1 for r in results if r["inserted"])
    log("seed_fixtures.done", total=len(caps), inserted=inserted, duplicates=len(caps) - inserted)


if __name__ == "__main__":
    main()
