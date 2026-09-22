"""Unit tests for the merge-job duplicate scorer (ingest/dedupe.py), the Python
port of web/lib/dedupe.ts. Covers the similarity parity values, the strict
merge_candidate gate, and find_merges' canonical selection."""
from ingest.dedupe import merge_candidate, norm_headline, similarity
from ingest.merge_dupes import find_merges


def _s(a, b):
    return round(similarity(norm_headline(a), norm_headline(b)), 3)


def test_similarity_matches_ts_values():
    # Same values the TS matcher produced, so the two stay in sync.
    assert _s("50% off Frozen Yogurt", "50% off Frozen Yogurt") == 1.0
    assert _s("15% off when you show this post",
              "15% off if you successfully flip the bottle straight") == 0.380
    assert similarity("free cupcake", "50 percent off") < 0.3


def _deal(**kw):
    base = {"id": 1, "status": "approved", "chain_id": 15, "deal_type": "percent_off",
            "discount_value": 50.0, "valid_from": "2026-07-20", "valid_to": "2026-08-10",
            "headline": "50% off Frozen Yogurt", "raw_capture_id": 72}
    return {**base, **kw}


def test_merge_candidate_positive():
    a = _deal(id=119, raw_capture_id=72)
    b = _deal(id=120, raw_capture_id=75)
    assert merge_candidate(a, b) is True


def test_merge_candidate_gates():
    a = _deal(id=119, raw_capture_id=72)
    # same post -> never merge
    assert merge_candidate(a, _deal(id=120, raw_capture_id=72)) is False
    # different chain -> no
    assert merge_candidate(a, _deal(id=120, raw_capture_id=75, chain_id=9)) is False
    # null chain on either side -> no
    assert merge_candidate(_deal(chain_id=None), _deal(id=120, raw_capture_id=75)) is False
    # value differs -> no
    assert merge_candidate(a, _deal(id=120, raw_capture_id=75, discount_value=40.0)) is False
    # null value (freebie) -> never auto-merge
    assert merge_candidate(_deal(discount_value=None, deal_type="freebie"),
                           _deal(id=120, raw_capture_id=75, discount_value=None, deal_type="freebie")) is False
    # non-overlapping windows -> no
    assert merge_candidate(a, _deal(id=120, raw_capture_id=75,
                           valid_from="2026-09-01", valid_to="2026-09-02")) is False
    # different deal_type -> no
    assert merge_candidate(a, _deal(id=120, raw_capture_id=75, deal_type="fixed_price")) is False


def test_find_merges_keeps_lowest_id_canonical():
    # three identical valued dups from different posts -> keep 10, supersede 11 & 12
    rows = [_deal(id=10, raw_capture_id=1), _deal(id=11, raw_capture_id=2), _deal(id=12, raw_capture_id=3)]
    merges = find_merges(rows)
    assert merges == [(10, 11, 1.0), (10, 12, 1.0)]
    # a non-duplicate is left alone
    rows2 = rows + [_deal(id=13, raw_capture_id=4, chain_id=1, headline="entirely different loyalty thing")]
    assert 13 not in {sup for _, sup, _ in find_merges(rows2)}


def test_find_merges_approved_wins_over_lower_id_pending():
    # A pending with a LOWER id must yield to an approved duplicate: never demote a
    # vetted, live deal behind an unreviewed one.
    rows = [_deal(id=30, raw_capture_id=1, status="pending"),
            _deal(id=50, raw_capture_id=2, status="approved")]
    assert find_merges(rows) == [(50, 30, 1.0)]  # canonical 50 (approved), superseded 30


def test_find_merges_two_pendings_keep_earliest():
    rows = [_deal(id=40, raw_capture_id=1, status="pending"),
            _deal(id=41, raw_capture_id=2, status="pending")]
    assert find_merges(rows) == [(40, 41, 1.0)]  # earliest pending canonical


def test_find_merges_expired_wins_over_higher_id_pending():
    # The repost case this job exists for: last cycle's run has expired by the time
    # the chain posts the promo again. The expired row is the vetted one and the
    # pending repost is unreviewed, so expired is canonical despite the lower id.
    rows = [_deal(id=119, raw_capture_id=72, status="expired"),
            _deal(id=174, raw_capture_id=210, status="pending")]
    assert find_merges(rows) == [(119, 174, 1.0)]


def test_find_merges_approved_wins_over_expired():
    # A live approved deal is never demoted behind a retired one.
    rows = [_deal(id=119, raw_capture_id=72, status="expired"),
            _deal(id=174, raw_capture_id=210, status="approved")]
    assert find_merges(rows) == [(174, 119, 1.0)]


def test_find_merges_expired_repost_with_new_window_is_not_merged():
    # The safety property behind including expired: a repost carrying a genuinely
    # new date range is a new deal, not a duplicate of the old run, so it stays in
    # the queue. Only reposts whose window still overlaps collapse.
    rows = [_deal(id=119, raw_capture_id=72, status="expired"),
            _deal(id=174, raw_capture_id=210, status="pending",
                  valid_from="2026-08-17", valid_to="2026-08-24")]
    assert find_merges(rows) == []


def test_scope_incompatible_deals_never_merge():
    # A national chain runs one promo in several cities and posts it once per
    # city, so the copies are word-identical. Merging them would hide a real
    # Melbourne deal behind a row the dashboard refuses to publish.
    mel = _deal(id=200, raw_capture_id=1, scope="melbourne")
    other = _deal(id=201, raw_capture_id=2, scope="other")
    assert merge_candidate(mel, other) is False
    assert find_merges([mel, other]) == []
    # Same scope still merges.
    assert merge_candidate(mel, _deal(id=202, raw_capture_id=3, scope="melbourne")) is True


def test_unknown_scope_stays_compatible_with_everything():
    # 'unknown' means we do not know, not "different". Blocking on it would
    # strand the reposts the matcher exists to catch, since a national chain's
    # silent captions are exactly the ones that derive to unknown.
    unk = _deal(id=210, raw_capture_id=1, scope="unknown")
    assert merge_candidate(unk, _deal(id=211, raw_capture_id=2, scope="melbourne")) is True
    assert merge_candidate(unk, _deal(id=212, raw_capture_id=3, scope="other")) is True
    # A missing scope key must not block either (older rows, partial dicts).
    assert merge_candidate(_deal(id=213, raw_capture_id=1), _deal(id=214, raw_capture_id=2)) is True
