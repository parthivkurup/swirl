"""Compare extractor output against fixture ground truth.

An LLM extractor cannot reproduce free-text phrasing (headline, conditions) or a
subjective confidence value verbatim, so those are checked by rule rather than
by equality. The structured fields that encode extraction correctness are
compared exactly. This is the contract the fixtures test; see NOTES.md for the
arguable calls behind specific values.
"""
import re

STRICT = [
    "deal_type",
    "discount_value",
    "discount_unit",
    "min_spend_aud",
    "max_grams",
    "valid_from",
    "valid_to",
    "recurring",
]
SET_FIELDS = ["channels", "days_of_week"]


def _tokens(s):
    return set(t for t in re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split() if t)


def _store_hint_ok(exp, act):
    if exp is None:
        return act is None
    if act is None:
        return False
    et, at = _tokens(exp), _tokens(act)
    return bool(et) and (et <= at or at <= et)


def _confidence_ok(exp, act):
    if act is None or not (0 <= act <= 1):
        return False
    # Bracket the 0.6 boundary in both directions: an ambiguous or illegible
    # caption (fixture < 0.6, e.g. 017 at 0.35) must come out < 0.6, and a clear
    # promotion (fixture >= 0.6, e.g. 013 at 0.62) must come out >= 0.6.
    #
    # The 0.8 auto-approve threshold is NOT tested here. It is a deterministic
    # decision in postprocess.build_deal_row, covered by
    # test_auto_approve_threshold. It cannot be tested through fixture output
    # because the model's confidence is effectively bimodal (~0.95 for clear
    # promos, ~0.3 for illegible) and does not reproduce the fixtures' mid-band
    # values, so an upper bound at 0.8 would assert calibration the model lacks.
    if exp < 0.6:
        return act < 0.6
    return act >= 0.6


def compare_deal(exp, act):
    problems = []
    for f in STRICT:
        if exp.get(f) != act.get(f):
            problems.append(f"{f}: expected {exp.get(f)!r} got {act.get(f)!r}")
    # unit_basis is compared only for fixtures that declare it. The original 30
    # predate the field and omit it, so they are unaffected; the exclusion and
    # holdout fixtures include it and are checked.
    if "unit_basis" in exp and exp.get("unit_basis") != act.get("unit_basis"):
        problems.append(f"unit_basis: expected {exp.get('unit_basis')!r} got {act.get('unit_basis')!r}")
    if "category" in exp and exp.get("category") != act.get("category"):
        problems.append(f"category: expected {exp.get('category')!r} got {act.get('category')!r}")
    for f in SET_FIELDS:
        if set(exp.get(f) or []) != set(act.get(f) or []):
            problems.append(f"{f}: expected {exp.get(f)!r} got {act.get(f)!r}")
    if not _store_hint_ok(exp.get("store_hint"), act.get("store_hint")):
        problems.append(f"store_hint: expected {exp.get('store_hint')!r} got {act.get('store_hint')!r}")
    if not _confidence_ok(exp.get("confidence"), act.get("confidence")):
        problems.append(f"confidence: expected side of 0.6 for {exp.get('confidence')!r}, got {act.get('confidence')!r}")
    if not (act.get("headline") or "").strip():
        problems.append("headline: empty")
    return problems


def compare_fixture(label, expected, actual):
    """Returns a list of human-readable problem strings, empty when the fixture
    passes."""
    if actual is None:
        return [f"{label}: no extractor output (unprocessed)"]
    if len(expected) != len(actual):
        return [f"{label}: deal count expected {len(expected)} got {len(actual)}"]
    if not expected:
        return []
    problems = []
    remaining = list(actual)
    for exp in expected:
        match = next((a for a in remaining if a.get("deal_type") == exp.get("deal_type")), None)
        if match is None:
            problems.append(f"{label}: no extracted deal with deal_type {exp.get('deal_type')!r}")
            continue
        remaining.remove(match)
        for p in compare_deal(exp, match):
            problems.append(f"{label}: {p}")
    return problems
