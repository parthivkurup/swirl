"""Integration tests that execute each Python write-path's real SQL against the
live schema in a rolled-back transaction. These catch parameter-type and column
bugs (like the INSERT_DEAL status ambiguity) that unit tests on Python objects
cannot see. Each uses the db_conn fixture, which rolls back and skips without a
database. The TS review-route writes (approve, reject, edit-and-approve, save)
are covered separately in web/tests/mutations.test.ts."""
from ingest.captures import _INSERT as INSERT_CAPTURE
from ingest.expire_deals import EXPIRE_SQL
from ingest.merge_dupes import UPDATE as MERGE_UPDATE
from ingest.postprocess import INSERT_DEAL, build_deal_row
from ingest.reverify import BUMP_SQL
from ingest.scrape_instagram import UPSERT_SEEN


def test_expire_sql_executes(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(EXPIRE_SQL)  # must not raise; rolled back by the fixture


def test_reverify_bump_sql_executes(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(BUMP_SQL, (-1,))  # id -1 matches nothing, but the SQL still executes


def test_insert_deal_executes(db_conn):
    base = {
        "deal_type": "fixed_price",
        "headline": "insert test",
        "discount_value": 5,
        "discount_unit": "aud",
        "confidence": 0.95,
        "store_hint": None,
        "stated_location": "melbourne",
    }
    cases = [
        ({"id": None, "source_type": "user_submission", "source_url": None, "content_hash": "ti1", "content_text": None}, "pending"),
        ({"id": None, "source_type": "website", "source_url": None, "content_hash": "ti2", "content_text": None}, "approved"),
    ]
    with db_conn.cursor() as cur:
        for capture, expected in cases:
            row = build_deal_row(dict(base), capture, [], [])
            assert row["status"] == expected
            cur.execute(INSERT_DEAL, row)  # must not raise (catches param-type bugs)


def test_insert_capture_with_source_handle_executes(db_conn):
    # Exercises the raw_captures insert (now carrying source_handle) against the
    # real schema, rolled back. The SQL is executed directly rather than through
    # insert_captures, which commits internally.
    with db_conn.cursor() as cur:
        cur.execute(INSERT_CAPTURE, {
            "source_type": "instagram",
            "source_url": "https://www.instagram.com/p/WTESTZZ/",
            "content_text": "hi",
            "image_path": None,
            "source_handle": "melbfoodieee",   # third-party author
            "via_handle": "iloveyochi",         # surfaced under a monitored profile
            "submitted_store": None,            # only a user submission carries one
            "content_hash": "wtest-cap-src-handle",
            "captured_at": None,
        })
        assert cur.fetchone() is not None  # inserted
        cur.execute("select source_handle, via_handle from raw_captures where content_hash = %s",
                    ("wtest-cap-src-handle",))
        assert cur.fetchone() == ("melbfoodieee", "iloveyochi")  # rolled back by the fixture


def test_insert_capture_with_submitted_store_executes(db_conn):
    # A user submission carries the typed shop name structurally (migration 0010)
    # instead of concatenating "Store: X" into content_text. Rolled back.
    with db_conn.cursor() as cur:
        cur.execute(INSERT_CAPTURE, {
            "source_type": "user_submission",
            "source_url": None,
            "content_text": None,
            "image_path": "media/submissions/wtest.jpg",
            "source_handle": None,
            "via_handle": None,
            "submitted_store": "Froyo & More",
            "content_hash": "wtest-cap-submitted-store",
            "captured_at": None,
        })
        assert cur.fetchone() is not None
        cur.execute("select submitted_store from raw_captures where content_hash = %s",
                    ("wtest-cap-submitted-store",))
        assert cur.fetchone() == ("Froyo & More",)


def test_merge_supersede_and_undo_execute(db_conn):
    # Exercises the merge job's superseded_by UPDATE (a real FK to deals.id) and the
    # undo, against the schema, rolled back.
    with db_conn.cursor() as cur:
        cur.execute("select id from deals order by id limit 2")
        ids = [r[0] for r in cur.fetchall()]
        if len(ids) < 2:
            import pytest
            pytest.skip("need at least two deals")
        canonical, victim = ids[0], ids[1]
        cur.execute(MERGE_UPDATE, (canonical, victim))  # supersede victim -> canonical
        cur.execute("select superseded_by from deals where id = %s", (victim,))
        assert cur.fetchone()[0] == canonical
        cur.execute("update deals set superseded_by = null where id = %s", (victim,))  # undo
        cur.execute("select superseded_by from deals where id = %s", (victim,))
        assert cur.fetchone()[0] is None  # rolled back by the fixture


def test_upsert_instagram_seen_executes(db_conn):
    with db_conn.cursor() as cur:
        # Insert path.
        cur.execute(UPSERT_SEEN, {"account": "wtest", "shortcode": "SC1"})
        cur.execute("select last_shortcode from instagram_seen where account = 'wtest'")
        assert cur.fetchone()[0] == "SC1"
        # Conflict path: a newer shortcode advances the high-water mark.
        cur.execute(UPSERT_SEEN, {"account": "wtest", "shortcode": "SC2"})
        cur.execute("select last_shortcode from instagram_seen where account = 'wtest'")
        assert cur.fetchone()[0] == "SC2"
        # Conflict with a null shortcode keeps the existing one (coalesce), and
        # still bumps last_seen_at.
        cur.execute(UPSERT_SEEN, {"account": "wtest", "shortcode": None})
        cur.execute("select last_shortcode from instagram_seen where account = 'wtest'")
        assert cur.fetchone()[0] == "SC2"  # rolled back by the fixture


def _cap_input(label):
    from ingest.extractor import CaptionInput
    return CaptionInput(content_hash=f"h_{label}", text=f"caption {label}",
                        capture_date="2026-08-16", image_path=None, label=label)


class _EmptyResponseClient:
    """Schema-valid but empty: BatchResult(captions=[]) passes validation."""
    call_count = 0

    def extract_batch(self, prompt, batch):
        self.call_count += 1
        return []


class _SplitArraysClient:
    """One input, two caption objects - the deliberate multi-offer shape."""
    call_count = 0

    def extract_batch(self, prompt, batch):
        self.call_count += 1
        return [{"index": 0, "deals": [{"headline": "a"}]},
                {"index": 1, "deals": [{"headline": "b"}]}]


def test_empty_model_response_is_a_failure_not_no_deals(tmp_path):
    """The silent-drop path. An empty response flattens to [], which means "read
    it, found no promotion" - so the capture was marked processed and never
    looked at again. _aligned_batch already rejected this shape and then fell
    back to _singletons, which accepted it, undoing the check that fired."""
    from ingest.extractor import extract_captions

    results, _ = extract_captions([_cap_input("x")], "p", _EmptyResponseClient(),
                                  cache_dir=tmp_path, use_cache=False)
    assert results == [None], "an empty response must leave the capture unprocessed"


def test_empty_response_rejected_on_the_batch_fallback_path_too(tmp_path):
    from ingest.extractor import extract_captions

    batch = [_cap_input("a"), _cap_input("b"), _cap_input("c")]
    results, _ = extract_captions(batch, "p", _EmptyResponseClient(),
                                  cache_dir=tmp_path, use_cache=False)
    assert results == [None, None, None]


def test_multi_array_response_still_flattens(tmp_path):
    """Guard on the fix: only the EMPTY case is a failure. len(res) > 1 is the
    fixture-015 shape, where the model splits one caption's offers across arrays,
    and both offers must survive."""
    from ingest.extractor import extract_captions

    results, _ = extract_captions([_cap_input("y")], "p", _SplitArraysClient(),
                                  cache_dir=tmp_path, use_cache=False)
    assert results[0] is not None and len(results[0]) == 2
