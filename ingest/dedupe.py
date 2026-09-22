"""Duplicate scoring for the nightly merge job.

This is a Python port of the review-queue matcher in web/lib/dedupe.ts. KEEP THE
TWO IN SYNC: the review queue flags possible duplicates with the TS version, and
this one decides which flagged pairs the merge job actually collapses. A drift
between them would merge pairs the UI never surfaced, or vice versa. The
similarity function and thresholds are intentionally identical to the TS file.
"""
import re

# Headline-similarity gates, identical to web/lib/dedupe.ts. Valued pairs (equal
# non-null discount_value) need only weak headline agreement because the value is
# already strong identity; null-value pairs would need the higher bar, but the
# merge job never auto-merges them anyway (see merge_candidate).
SIM_VALUED = 0.35
SIM_NULL_VALUE = 0.6

_NON = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")


def norm_headline(s):
    s = _NON.sub(" ", (s or "").lower())
    return _WS.sub(" ", s).strip()


def _bigrams(s):
    m = {}
    for i in range(len(s) - 1):
        g = s[i : i + 2]
        m[g] = m.get(g, 0) + 1
    return m


def similarity(a, b):
    """Dice coefficient over character bigrams: 1.0 identical, 0 disjoint."""
    if a == b:
        return 1.0 if a else 0.0
    if len(a) < 2 or len(b) < 2:
        return 0.0
    A, B = _bigrams(a), _bigrams(b)
    inter = total = 0
    for g, n in A.items():
        total += n
        bn = B.get(g)
        if bn:
            inter += min(n, bn)
    for n in B.values():
        total += n
    return (2 * inter) / total


def scope_compatible(a, b):
    """Two deals for different cities are not the same deal, however identical
    their wording. Mirrors scopeCompatible in web/lib/dedupe.ts. 'unknown' stays
    compatible with everything: it means we do not know, and blocking on it would
    strand exactly the reposts this matcher exists to catch."""
    if not a or not b:
        return True
    if a == "unknown" or b == "unknown":
        return True
    return a == b


def windows_overlap(a_from, a_to, b_from, b_to):
    """null valid_from = open start (-inf), null valid_to = open end (+inf)."""
    start_ok = a_from is None or b_to is None or a_from <= b_to
    end_ok = b_from is None or a_to is None or b_from <= a_to
    return start_ok and end_ok


def merge_candidate(a, b):
    """Strict AUTO-MERGE gate (stricter than the review flag). Merge only when all
    hold: same non-null chain_id, same deal_type, equal non-null discount_value,
    overlapping validity window, headline similarity above SIM_VALUED. Two offers
    from the SAME post are never merged. NULL discount_value on either side is
    never auto-merged (the freebie over-flag case is left for the review queue).
    a and b are dicts with those keys. Does not gate on model confidence."""
    if a.get("raw_capture_id") is not None and a.get("raw_capture_id") == b.get("raw_capture_id"):
        return False
    if a.get("chain_id") is None or a.get("chain_id") != b.get("chain_id"):
        return False
    if not scope_compatible(a.get("scope"), b.get("scope")):
        return False
    if not a.get("deal_type") or a.get("deal_type") != b.get("deal_type"):
        return False
    if a.get("discount_value") is None or b.get("discount_value") is None:
        return False
    if float(a["discount_value"]) != float(b["discount_value"]):
        return False
    if not windows_overlap(a.get("valid_from"), a.get("valid_to"), b.get("valid_from"), b.get("valid_to")):
        return False
    return similarity(norm_headline(a.get("headline")), norm_headline(b.get("headline"))) >= SIM_VALUED
