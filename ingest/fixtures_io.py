from pathlib import Path

from ingest.extractor import CaptionInput
from ingest.hashing import content_hash

FIXTURES_DIR = Path("tests/fixtures/captions")


def parse_caption(path):
    """Fixture .txt files start with a `CAPTURE_DATE: YYYY-MM-DD` line, a blank
    line, then the caption body. Returns (capture_date, body)."""
    raw = Path(path).read_text(encoding="utf-8")
    lines = raw.splitlines()
    capture_date = None
    start = 0
    if lines and lines[0].lower().startswith("capture_date:"):
        capture_date = lines[0].split(":", 1)[1].strip()
        start = 1
    body = "\n".join(lines[start:]).strip()
    return capture_date, body


def load_fixture_inputs(fixtures_dir=FIXTURES_DIR):
    inputs = []
    for txt in sorted(Path(fixtures_dir).glob("*.txt")):
        capture_date, body = parse_caption(txt)
        inputs.append(
            CaptionInput(
                content_hash=content_hash(text=body),
                text=body,
                capture_date=capture_date,
                label=txt.stem,
            )
        )
    return inputs


def expected_path(label, fixtures_dir=FIXTURES_DIR):
    return Path(fixtures_dir) / f"{label}.expected.json"
