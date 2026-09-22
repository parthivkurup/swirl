"""Unit tests for derive_scope: how a deal's city is decided from the caption's
evidence plus the chain's footprint. The hard case is a caption that names no
city at all, which means Melbourne for a one-shop operator and genuinely unknown
for a national chain."""
from ingest.postprocess import derive_scope


def test_named_melbourne_place_wins_regardless_of_chain():
    for fp in ("melbourne_only", "national", "unknown", None):
        assert derive_scope("melbourne", fp) == "melbourne"


def test_named_other_city_wins_regardless_of_chain():
    # The case that shipped: Yo-Bar's Canberra grand opening extracted as a
    # normal deal and was published as a Melbourne one.
    for fp in ("melbourne_only", "national", "unknown", None):
        assert derive_scope("other", fp) == "other"


def test_silent_caption_is_melbourne_for_a_melbourne_only_chain():
    assert derive_scope("none", "melbourne_only") == "melbourne"


def test_silent_caption_is_unknown_for_a_national_chain():
    # THE HARD CASE. Same caption, same silence, different answer, decided by a
    # curated fact about the chain rather than by the model guessing.
    assert derive_scope("none", "national") == "unknown"


def test_unresolved_or_missing_footprint_behaves_as_national():
    # Being unsure about a chain must never publish a Melbourne claim.
    assert derive_scope("none", "unknown") == "unknown"
    assert derive_scope("none", None) == "unknown"


def test_unclear_place_falls_through_to_the_chain_exactly_like_none():
    # Yokli is in Richmond, which also exists in Sydney, so its own suburb
    # extracts as 'unclear'. Treating that as unknown would demote every deal
    # from a chain that only has Melbourne shops.
    assert derive_scope("unclear", "melbourne_only") == "melbourne"
    assert derive_scope("unclear", "national") == "unknown"


def test_a_matched_store_outranks_everything():
    # Phase 9: a store_hint that resolves to a real Melbourne store row is direct
    # evidence. Always False today because the stores table is empty.
    assert derive_scope("none", "national", store_matched=True) == "melbourne"
    assert derive_scope("unclear", "unknown", store_matched=True) == "melbourne"
