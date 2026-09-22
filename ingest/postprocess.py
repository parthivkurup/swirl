import hashlib
import re
from difflib import SequenceMatcher

MATCH_THRESHOLD = 0.72


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def resolve_store(store_hint, stores):
    """Fuzzy match a store_hint against stores on name plus suburb. Returns
    (store_id, chain_id) or (None, None) with no confident match. `stores` is a
    list of dict rows with id, name, suburb, chain_id."""
    if not store_hint:
        return None, None
    target = _norm(store_hint)
    best, best_score = None, 0.0
    for s in stores:
        hay = _norm(f"{s['name']} {s.get('suburb') or ''}")
        score = SequenceMatcher(None, target, hay).ratio()
        if target and (target in hay or hay in target):
            score = max(score, 0.9)
        if score > best_score:
            best, best_score = s, score
    if best and best_score >= MATCH_THRESHOLD:
        return best["id"], best.get("chain_id")
    return None, None


def _chains_by_handle(chains):
    by_handle = {}
    for ch in chains or []:
        h = (ch.get("instagram_handle") or "").strip().lstrip("@").lower()
        if h:
            by_handle[h] = ch["id"]
    return by_handle


def resolve_chain_from_handle(handle, chains):
    """Resolve the scraped-from profile handle to a chain_id by EXACT,
    case-insensitive match against chains.instagram_handle. The handle is known at
    scrape time (we visited that profile), so this is authoritative. Returns a
    chain_id or None (unknown handle; never fuzzy, never creates a chain)."""
    if not handle:
        return None
    return _chains_by_handle(chains).get(handle.strip().lstrip("@").lower())


_HANDLE = re.compile(r"@([A-Za-z0-9_.]+)")


def resolve_chain_from_text(text, chains):
    """Resolve an @mention to a chain_id by EXACT, case-insensitive match against
    chains.instagram_handle. Never fuzzy, never creates a chain. A handle is a
    structured key, unlike a free-text hashtag, so this is safe where hashtag ->
    store_hint is not. Returns the first matching chain_id, or None."""
    if not text or not chains:
        return None
    by_handle = _chains_by_handle(chains)
    for m in _HANDLE.finditer(text):
        handle = m.group(1).rstrip(".").lower()
        if handle in by_handle:
            return by_handle[handle]
    return None


def derive_scope(stated_location, footprint, store_matched=False):
    """Which city a deal is for, from caption-local evidence plus the chain.

    The rule in one line: USABLE EVIDENCE WINS, OTHERWISE THE CHAIN DECIDES.

    The extractor never returns a scope, only what the caption said. That split
    exists because the hard case is not answerable from the caption: most posts
    name no city, and what that silence means depends entirely on the business.
    For blu spoon (one shop, Port Melbourne) it means Melbourne. For Yo-Chi (70
    stores nationally) it means genuinely unknown. Same silence, different
    answer, so asking the model to interpret it would be asking it to guess.
    The chain's footprint is a curated fact in config/chains.yaml instead, which
    can be corrected and re-derived without re-running extraction.

    'unclear' falls through to the chain exactly like 'none'. A place that cannot
    be located carries no more information than no place at all, and treating it
    as unknown would wrongly demote a one-city chain's deals - Yokli is in
    Richmond, which also exists in Sydney, so its own suburb extracts as
    'unclear'.

    A footprint that is missing or 'unknown' behaves as 'national': the safe
    side. Being unsure about a chain must never publish a Melbourne claim.

    store_matched is for Phase 9: a store_hint that resolves to a real row in the
    stores table is direct evidence and outranks everything. It is always False
    today (the stores table is empty), so it costs nothing now and is correct the
    moment stores exist.
    """
    if store_matched:
        return "melbourne"
    if stated_location == "melbourne":
        return "melbourne"
    if stated_location == "other":
        return "other"
    # 'none', 'unclear', or a missing value: the caption gave us nothing usable.
    return "melbourne" if footprint == "melbourne_only" else "unknown"


# Deal types whose discount_value is legitimately null (there is no single
# number to state), so completeness does not require discount_value for them.
NON_NUMERIC_TYPES = {"bogo", "freebie", "loyalty"}


def _extraction_complete(deal):
    """No null in deal_type, headline, and either discount_value or an explicit
    non-numeric deal_type."""
    if not deal.get("deal_type") or not deal.get("headline"):
        return False
    if deal["deal_type"] in NON_NUMERIC_TYPES:
        return True
    return deal.get("discount_value") is not None


def source_hash(content_hash, deal):
    """Stable per-offer hash so a repost of the same offer does not create a
    duplicate deal."""
    key = "|".join(
        str(x)
        for x in (
            content_hash,
            deal.get("deal_type"),
            deal.get("discount_value"),
            deal.get("discount_unit"),
            _norm(deal.get("headline")),
            deal.get("valid_from"),
            deal.get("valid_to"),
            _norm(deal.get("store_hint")),
        )
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def build_deal_row(deal, capture, stores, chains=None):
    """Map an extracted deal dict plus its raw_capture to a deals table row."""
    # A typed shop name beats the model's store_hint. The submitter physically
    # stood there, and on a submission the model's hint can only come from that
    # same person's free text anyway, so the direct answer is the better source.
    store_hint = capture.get("submitted_store") or deal.get("store_hint")
    store_id, chain_id = resolve_store(store_hint, stores)
    # If no store matched, attach the chain in priority order:
    #   1. source_handle - the actual post author, if it maps to a known chain
    #      (the account's own announcement);
    #   2. via_handle - the monitored profile that surfaced the post, if the
    #      author was a third party (a tagged / feature post resolves to the shop
    #      it was surfaced under, e.g. a blogger's post read off YO-TO's profile);
    #   3. the @mention rule, for captures with no chain-mapping handle at all.
    if chain_id is None and chains:
        chain_id = (
            resolve_chain_from_handle(capture.get("source_handle"), chains)
            or resolve_chain_from_handle(capture.get("via_handle"), chains)
            or resolve_chain_from_text(capture.get("content_text"), chains)
        )
    min_spend = deal.get("min_spend_aud")
    min_spend_cents = round(min_spend * 100) if min_spend is not None else None

    footprint = None
    if chain_id is not None:
        for ch in chains or []:
            if ch["id"] == chain_id:
                footprint = ch.get("footprint")
                break
    scope = derive_scope(
        deal.get("stated_location"), footprint, store_matched=store_id is not None
    )

    # Auto-approve only a website deal that is confident AND structurally
    # complete. A partial extraction never auto-approves regardless of stated
    # confidence: a human must fill the gap.
    #
    # Scope must be 'melbourne' too. A national chain's own promo page has
    # exactly the same problem as its Instagram, so without this gate the one
    # path that publishes without a human could publish another city's deal.
    auto_approve = (
        capture["source_type"] == "website"
        and (deal.get("confidence") or 0) >= 0.8
        and _extraction_complete(deal)
        and scope == "melbourne"
    )
    status = "approved" if auto_approve else "pending"

    return {
        "auto_approved": auto_approve,
        "raw_capture_id": capture.get("id"),
        "chain_id": chain_id,
        "store_id": store_id,
        "store_hint_raw": store_hint,
        "deal_type": deal["deal_type"],
        "category": deal.get("category"),
        "scope": scope,
        "headline": deal["headline"],
        "discount_value": deal.get("discount_value"),
        "discount_unit": deal.get("discount_unit"),
        "unit_basis": deal.get("unit_basis"),
        "conditions": deal.get("conditions"),
        "min_spend_cents": min_spend_cents,
        "max_grams": deal.get("max_grams"),
        "channels": deal.get("channels") or [],
        "days_of_week": deal.get("days_of_week") or [],
        "valid_from": deal.get("valid_from"),
        "valid_to": deal.get("valid_to"),
        "recurring": bool(deal.get("recurring")),
        "source_type": capture["source_type"],
        "source_url": capture.get("source_url"),
        "source_hash": source_hash(capture["content_hash"], deal),
        "confidence": deal.get("confidence"),
        "status": status,
    }


INSERT_DEAL = (
    "insert into deals (raw_capture_id, chain_id, store_id, store_hint_raw, deal_type, "
    "category, scope, headline, discount_value, discount_unit, unit_basis, conditions, "
    "min_spend_cents, max_grams, channels, days_of_week, valid_from, valid_to, "
    "recurring, source_type, source_url, source_hash, confidence, status, last_verified) "
    "values (%(raw_capture_id)s, %(chain_id)s, %(store_id)s, %(store_hint_raw)s, "
    "%(deal_type)s, %(category)s, %(scope)s, %(headline)s, %(discount_value)s, %(discount_unit)s, "
    "%(unit_basis)s, %(conditions)s, %(min_spend_cents)s, %(max_grams)s, "
    "%(channels)s, %(days_of_week)s, %(valid_from)s, %(valid_to)s, %(recurring)s, "
    "%(source_type)s, %(source_url)s, %(source_hash)s, %(confidence)s, %(status)s, "
    "case when %(auto_approved)s then now() else null end) "
    "on conflict (source_hash) do nothing returning id"
)
