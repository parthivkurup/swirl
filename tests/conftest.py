import json
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

load_dotenv(ROOT / ".env")

from ingest.extract import load_prompt
from ingest.extractor import extract_captions
from ingest.fixtures_io import expected_path, load_fixture_inputs
from ingest.gemini_client import GeminiClient


@pytest.fixture
def db_conn():
    """A database connection whose transaction is always rolled back, so write-path
    tests can execute real SQL against the schema without persisting anything.
    Skips if no database is reachable.

    Note the BaseException catch: ingest.db.connect raises SystemExit when
    DATABASE_URL is unset, which `except Exception` does not catch, so on a fresh
    clone with no .env these tests used to ERROR out of the fixture rather than
    skip. A missing database is an absent prerequisite, not a failure."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set (copy .env.example to .env and start Postgres)")
    try:
        from ingest.db import connect

        conn = connect()
    except (Exception, SystemExit) as e:
        pytest.skip(f"no database available: {e}")
    try:
        yield conn
        conn.rollback()
    finally:
        conn.close()


@pytest.fixture(scope="session")
def gemini_client():
    """The live extraction client, or a skip when it cannot be built. GeminiClient
    raises SystemExit on a missing key, which would error every dependent test out
    of its fixture instead of skipping it."""
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY is not set (copy .env.example to .env); "
                    "tests that call the live extractor cannot run")
    try:
        return GeminiClient()
    except (Exception, SystemExit) as e:
        pytest.skip(f"extraction client unavailable: {e}")


def pytest_addoption(parser):
    parser.addoption(
        "--no-cache",
        action="store_true",
        default=False,
        help=(
            "Re-extract every fixture from the live model, ignoring .cache/extract. "
            "A cached run only proves the cache still holds the answers recorded when "
            "the prompt hash last changed; it is not evidence the model still produces "
            "them. Costs real API calls and takes minutes."
        ),
    )


# Populated by the `extraction` fixture, read by pytest_terminal_summary. A dict
# rather than a return value because the warning has to fire once for the whole
# session, after every test that used the fixture has run.
_EXTRACTION_STATS = {}


@pytest.fixture(scope="session")
def extraction(request, gemini_client):
    """Run the extractor over every fixture once. Cache keyed by content_hash +
    prompt_hash means a warm cache costs zero API calls; a changed or corrupted
    prompt invalidates the cache and re-hits the model.

    That cache is why a green run can mean nothing. If every fixture is served
    from it, the suite has verified the cache, not the model: extraction quality
    can drift for weeks behind an unchanged prompt hash and the suite stays green
    throughout. pytest_terminal_summary says so out loud when that happens, and
    --no-cache is how you actually check."""
    use_cache = not request.config.getoption("--no-cache")
    inputs = load_fixture_inputs()
    results, stats = extract_captions(
        inputs, load_prompt(), gemini_client, use_cache=use_cache
    )
    _EXTRACTION_STATS.update(stats)
    _EXTRACTION_STATS["use_cache"] = use_cache
    data = {}
    for inp, actual in zip(inputs, results):
        expected = json.loads(expected_path(inp.label).read_text(encoding="utf-8"))
        data[inp.label] = (expected, actual)
    return data


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Report what the fixture extractions were actually measured against.

    A fully-cached green run is the dangerous case: it looks identical to a
    verified one and is not, so it gets a red banner rather than a footnote."""
    if not _EXTRACTION_STATS:
        return
    total = _EXTRACTION_STATS.get("total", 0)
    hits = _EXTRACTION_STATS.get("cache_hits", 0)
    live = total - hits
    w = terminalreporter.write_line

    if not _EXTRACTION_STATS.get("use_cache", True):
        w("")
        w(f"extraction: --no-cache sweep, all {total} fixtures re-extracted from the live model.", green=True)
        w("This result reflects current model behaviour.", green=True)
        return

    if total and hits == total:
        w("")
        w("=" * 78, red=True, bold=True)
        w(f"CACHED RUN: all {total} fixtures came from .cache/extract. 0 API calls.", red=True, bold=True)
        w("This verified the CACHE, not the model. The cache is keyed on the prompt", red=True)
        w("hash, so these answers are from whenever the prompt last changed and the", red=True)
        w("model's current behaviour is untested. Extraction quality can drift for", red=True)
        w("weeks behind an unchanged prompt and this suite will stay green.", red=True)
        w("Verify with:  pytest tests/test_extractor.py --no-cache", red=True, bold=True)
        w("=" * 78, red=True, bold=True)
    elif total:
        w("")
        w(f"extraction: {live} of {total} fixtures hit the live model, {hits} from cache.", yellow=True)
        w("Only the live ones say anything about current model behaviour.", yellow=True)
