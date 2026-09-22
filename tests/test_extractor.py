import json

import pytest

from compare import compare_fixture
from ingest.fixtures_io import expected_path, load_fixture_inputs
from ingest.postprocess import (
    build_deal_row,
    resolve_chain_from_handle,
    resolve_chain_from_text,
    resolve_store,
)

LABELS = [inp.label for inp in load_fixture_inputs()]
# A negative is any fixture whose expected output is the empty array, derived
# from the fixture itself rather than an id range.
NEGATIVES = [
    label for label in LABELS if json.loads(expected_path(label).read_text()) == []
]


@pytest.mark.parametrize("label", LABELS)
def test_fixture_matches_expected(label, extraction):
    expected, actual = extraction[label]
    problems = compare_fixture(label, expected, actual)
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("label", NEGATIVES)
def test_negative_returns_empty(label, extraction):
    _, actual = extraction[label]
    assert actual == [], f"{label} expected [] but got {actual}"


def _status_for(confidence, source_type, **overrides):
    # stated_location defaults to melbourne so these cases isolate the
    # confidence and completeness gates; the scope gate has its own test below.
    deal = {
        "deal_type": "percent_off",
        "headline": "x",
        "discount_value": 10,
        "discount_unit": "percent",
        "confidence": confidence,
        "store_hint": None,
        "stated_location": "melbourne",
        **overrides,
    }
    capture = {"id": 1, "source_type": source_type, "source_url": None, "content_hash": "h"}
    return build_deal_row(deal, capture, [])["status"]


def test_auto_approve_threshold():
    # Auto-approve requires website AND confidence >= 0.8 AND a complete extraction.
    assert _status_for(0.80, "website") == "approved"
    assert _status_for(0.95, "website") == "approved"
    assert _status_for(0.79, "website") == "pending"  # just below the 0.8 line
    assert _status_for(0.80, "fixture") == "pending"  # right confidence, wrong source
    assert _status_for(0.80, "manual") == "pending"


def test_auto_approve_requires_complete_extraction():
    # Partial extraction never auto-approves, even website + high confidence.
    assert _status_for(0.95, "website", discount_value=None) == "pending"  # numeric type, no value
    assert _status_for(0.95, "website", headline=None) == "pending"
    assert _status_for(0.95, "website", deal_type=None) == "pending"
    # A non-numeric deal_type is complete without discount_value.
    assert _status_for(0.95, "website", deal_type="freebie", discount_value=None) == "approved"
    assert _status_for(0.95, "website", deal_type="loyalty", discount_value=None) == "approved"


def test_auto_approve_requires_melbourne_scope():
    # The one path that publishes without a human must not publish another
    # city's deal. A national chain's own promo page has exactly the same problem
    # as its Instagram.
    assert _status_for(0.95, "website", stated_location="other") == "pending"
    # Silence plus no chain derives to unknown, which is not good enough either.
    assert _status_for(0.95, "website", stated_location="none") == "pending"
    assert _status_for(0.95, "website", stated_location="unclear") == "pending"


def test_auto_approve_scope_can_come_from_the_chain():
    # A silent caption from a melbourne_only chain derives to melbourne, so it
    # still auto-approves. This is the derive_scope split working end to end:
    # the caption said nothing and the chain supplied the answer.
    deal = {"deal_type": "percent_off", "headline": "x", "discount_value": 10,
            "discount_unit": "percent", "confidence": 0.95, "store_hint": None,
            "stated_location": "none"}
    capture = {"id": 1, "source_type": "website", "source_url": None,
               "content_hash": "h", "source_handle": "bluspoon"}
    chains = [{"id": 15, "name": "blu spoon", "instagram_handle": "bluspoon",
               "footprint": "melbourne_only"}]
    row = build_deal_row(dict(deal), capture, [], chains)
    assert row["scope"] == "melbourne"
    assert row["status"] == "approved"

    national = [{"id": 1, "name": "Yo-Chi", "instagram_handle": "bluspoon",
                 "footprint": "national"}]
    row2 = build_deal_row(dict(deal), capture, [], national)
    assert row2["scope"] == "unknown"
    assert row2["status"] == "pending"


def test_user_submission_never_auto_approves():
    # User submissions are not 'website', so they never auto-approve, even when
    # confident and complete. They always go through /review.
    assert _status_for(0.95, "user_submission") == "pending"
    assert _status_for(1.0, "user_submission", deal_type="freebie", discount_value=None) == "pending"


CHAINS = [
    {"id": 4, "name": "YOMG", "instagram_handle": "yomgburgers"},
    {"id": 1, "name": "Yo-Chi", "instagram_handle": "iloveyochi"},
]


def test_resolve_chain_from_mention_exact_only():
    # Known chain handle in a customer-repost-style caption -> attaches to chain.
    assert resolve_chain_from_text("obsessed with this bowl 😍 @yomgburgers", CHAINS) == 4
    # Case-insensitive.
    assert resolve_chain_from_text("midweek deal @YOMGBURGERS", CHAINS) == 4
    # Unknown handle -> null.
    assert resolve_chain_from_text("tag us @sweettooth.example", CHAINS) is None
    # Exact match only, never fuzzy / partial.
    assert resolve_chain_from_text("check @yomg today", CHAINS) is None
    assert resolve_chain_from_text("no mentions at all", CHAINS) is None


def test_resolve_chain_from_handle_exact_only():
    assert resolve_chain_from_handle("yomgburgers", CHAINS) == 4
    assert resolve_chain_from_handle("YOMGBURGERS", CHAINS) == 4  # case-insensitive
    assert resolve_chain_from_handle("@iloveyochi", CHAINS) == 1  # @ tolerated
    assert resolve_chain_from_handle("yomg", CHAINS) is None       # never fuzzy
    assert resolve_chain_from_handle(None, CHAINS) is None


def test_chain_resolution_source_then_via_then_mention():
    deal = {"deal_type": "percent_off", "headline": "x", "discount_value": 10,
            "discount_unit": "percent", "store_hint": None, "confidence": 0.9}

    def cap(**kw):
        base = {"id": 1, "source_type": "instagram", "source_url": None, "content_hash": "h",
                "source_handle": None, "via_handle": None, "content_text": None}
        return {**base, **kw}

    # 1. source_handle (the author) maps to a chain -> that chain wins, even over a
    #    caption that @mentions a different one.
    assert build_deal_row(deal, cap(source_handle="iloveyochi",
                          content_text="collab with @yomgburgers"), [], CHAINS)["chain_id"] == 1
    # 2. author is a third party that does not map; via_handle (the monitored
    #    profile that surfaced the post) maps -> resolves to the surfaced shop.
    assert build_deal_row(deal, cap(source_handle="melbfoodieee", via_handle="yomgburgers"),
                          [], CHAINS)["chain_id"] == 4
    # 3. neither handle maps -> the @mention rule is the final fallback.
    assert build_deal_row(deal, cap(source_handle="someblogger", via_handle="unknownprof",
                          content_text="grab a deal @iloveyochi"), [], CHAINS)["chain_id"] == 1
    # nothing resolves -> None.
    assert build_deal_row(deal, cap(content_text="no handles here"), [], CHAINS)["chain_id"] is None


def test_build_deal_row_chain_from_mention():
    deal = {
        "deal_type": "percent_off",
        "headline": "x",
        "discount_value": 10,
        "discount_unit": "percent",
        "store_hint": None,
        "confidence": 0.9,
    }
    # Repost mentioning a chain handle still attaches the chain.
    cap = {"id": 1, "source_type": "fixture", "source_url": None, "content_hash": "h",
           "content_text": "loved this @yomgburgers"}
    assert build_deal_row(deal, cap, [], CHAINS)["chain_id"] == 4
    # Unknown handle -> null.
    cap2 = {**cap, "content_text": "loved this @sweettooth.example"}
    assert build_deal_row(deal, cap2, [], CHAINS)["chain_id"] is None


def test_reverify_partition():
    from ingest.reverify import partition

    rows = [(1, "still-here"), (2, "also-here"), (3, "gone-from-source")]
    bumped, stale = partition(rows, {"still-here", "also-here"})
    assert bumped == [1, 2]
    assert stale == [3]


from ingest.extractor import CaptionInput, extract_captions


def _inp(label):
    return CaptionInput(content_hash=f"h-{label}", text=label, capture_date="2026-08-06", label=label)


class _ScriptedClient:
    """Fake GeminiClient. `batch_fn(batch)` and `single_fn(inp)` return the same
    shape extract_batch does: a list of {"index": int, "deals": [...]}."""

    def __init__(self, batch_fn=None, single_fn=None):
        self.batch_fn = batch_fn
        self.single_fn = single_fn
        self.call_count = 0
        self.batch_sizes = []

    def extract_batch(self, prompt_text, batch):
        self.call_count += 1
        self.batch_sizes.append(len(batch))
        if len(batch) == 1:
            return self.single_fn(batch[0])
        return self.batch_fn(batch)


def _deal(h):
    return {"headline": h}


def test_aligned_batch_maps_by_index():
    inputs = [_inp("A"), _inp("B"), _inp("C")]
    client = _ScriptedClient(
        batch_fn=lambda b: [
            {"index": 0, "deals": [_deal("a")]},
            {"index": 1, "deals": []},
            {"index": 2, "deals": [_deal("c")]},
        ]
    )
    results, _ = extract_captions(inputs, "p", client, use_cache=False)
    assert results == [[_deal("a")], [], [_deal("c")]]
    assert client.call_count == 1  # one batch call, no singleton retries
    assert client.batch_sizes == [3]


def test_misaligned_batch_falls_back_to_singletons():
    inputs = [_inp("A"), _inp("B"), _inp("C")]
    # Model drops caption 1 and duplicates 0: right count, wrong identity.
    single = {"A": [_deal("a")], "B": [_deal("b")], "C": [_deal("c")]}
    client = _ScriptedClient(
        batch_fn=lambda b: [
            {"index": 0, "deals": [_deal("a")]},
            {"index": 0, "deals": [_deal("a")]},
            {"index": 2, "deals": [_deal("c")]},
        ],
        single_fn=lambda inp: [{"index": 0, "deals": single[inp.label]}],
    )
    results, _ = extract_captions(inputs, "p", client, use_cache=False)
    # Each caption gets its OWN deal, none misattributed.
    assert results == [[_deal("a")], [_deal("b")], [_deal("c")]]
    assert client.call_count == 1 + 3  # rejected batch + three singleton retries


def test_singleton_keeps_all_arrays_when_model_splits_a_caption():
    # An image-bearing caption is sent alone; if the model splits one caption's
    # offers across two arrays, both must survive (fixture-015 shape).
    img = CaptionInput(content_hash="h-img", text="two offers", capture_date="2026-08-06",
                       image_path="/nope.jpg", label="IMG")
    client = _ScriptedClient(
        single_fn=lambda inp: [
            {"index": 0, "deals": [_deal("first")]},
            {"index": 1, "deals": [_deal("second")]},
        ]
    )
    results, _ = extract_captions([img], "p", client, use_cache=False)
    assert results == [[_deal("first"), _deal("second")]]
    assert client.batch_sizes == [1]  # went straight to the singleton path


def test_batch_counts_split_text_and_image():
    text = [_inp("A"), _inp("B")]
    img = CaptionInput(content_hash="h-i", text="x", capture_date="2026-08-06",
                       image_path="/nope.jpg", label="I")
    client = _ScriptedClient(
        batch_fn=lambda b: [{"index": i, "deals": []} for i in range(len(b))],
        single_fn=lambda inp: [{"index": 0, "deals": []}],
    )
    _, stats = extract_captions(text + [img], "p", client, use_cache=False)
    assert stats["text_batches"] == 1   # A and B share one text batch
    assert stats["image_calls"] == 1    # the image caption is its own call
    assert stats["batches"] == 2


def test_resolve_store_fuzzy_match():
    stores = [
        {"id": 1, "name": "Yo-Chi", "suburb": "Carlton", "chain_id": 10},
        {"id": 2, "name": "Moochi", "suburb": "Glen Waverley", "chain_id": 11},
    ]
    assert resolve_store("glen waverley", stores) == (2, 11)
    assert resolve_store("nonexistent place xyz", stores) == (None, None)
    assert resolve_store(None, stores) == (None, None)
