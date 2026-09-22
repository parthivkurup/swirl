import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ingest.log import log

CACHE_DIR = Path(".cache/extract")
BATCH_SIZE = 10


@dataclass
class CaptionInput:
    content_hash: str
    text: str
    capture_date: str
    image_path: str | None = None
    label: str | None = None


def prompt_hash(prompt_text):
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:16]


def _cache_path(cache_dir, content_hash, phash):
    return Path(cache_dir) / f"{content_hash}__{phash}.json"


def _cache_get(cache_dir, content_hash, phash):
    p = _cache_path(cache_dir, content_hash, phash)
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _cache_put(cache_dir, content_hash, phash, deals):
    p = _cache_path(cache_dir, content_hash, phash)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(deals, ensure_ascii=False), encoding="utf-8")


def _batches(miss_indices, inputs):
    """Text-only captions batch up to BATCH_SIZE. Any caption with an image is
    sent on its own.

    Images are deliberately NOT batched: a multi-image request semantically
    contaminates its members (a price/date visible in one image bleeds onto
    another caption's deal), which index-alignment cannot catch. This was tested,
    not assumed, against the 90 stored Instagram captures; see DEFERRED.md."""
    text_only, images = [], []
    for i in miss_indices:
        (images if inputs[i].image_path else text_only).append(i)
    for k in range(0, len(text_only), BATCH_SIZE):
        yield text_only[k : k + BATCH_SIZE]
    for i in images:
        yield [i]


def _aligned_batch(batch, client, prompt_text):
    """One multi-item batch request, accepted only if the response is index-aligned
    to the inputs. Returns a list of per-caption deal lists, or None to signal the
    caller to fall back to singletons. Alignment is verified by identity, not just
    count: the model must return exactly one object per caption with caption_index
    equal to its position (0..n-1) in order. A reorder or drop-and-duplicate is
    rejected, because trusting array position would silently misattribute a deal's
    chain / dates / store to the wrong caption."""
    labels = [inp.label for inp in batch]
    try:
        raw = client.extract_batch(prompt_text, batch)
    except Exception as e:
        log("extract.batch_error", labels=labels, error=f"{type(e).__name__}: {e}")
        return None
    indices = [c.get("index") for c in raw]
    if len(raw) != len(batch) or indices != list(range(len(batch))):
        log("extract.batch_misaligned", labels=labels, expected=len(batch),
            got_count=len(raw), got_indices=indices)
        return None
    return [c["deals"] for c in raw]


def _singletons(batch, client, prompt_text):
    """Extract each caption in its own request. A single input has exactly one
    possible owner, so nothing can be misattributed; we flatten every array the
    model returns for it into that caption's deal list. Flattening (not [0]) is
    what preserves the second offer in a multi-offer caption if the model splits
    it across arrays (the fixture-015 shape). A per-item failure yields None so
    the capture is left unprocessed for a later run.

    An EMPTY response yields None too, and must. BatchResult(captions=[]) is
    schema-valid, so the model returning nothing at all flattens to [] - which is
    the same value as "I read this and there is no promotion here". _aligned_batch
    already rejects that shape on the count check, but it then falls back HERE,
    so without this the safety check was undone by the very retry it triggered:
    the identical empty response was rejected as malformed and then accepted as
    fact seconds later. Downstream, [] marks the capture processed and it is
    never looked at again, so a real promo could be consumed with no deal, no
    error and a clean-looking run.

    Only the empty case is rejected. len(res) > 1 is the deliberate multi-array
    shape above, not a fault."""
    out = []
    for inp in batch:
        try:
            res = client.extract_batch(prompt_text, [inp])
        except Exception as e:
            log("extract.item_error", label=inp.label, error=f"{type(e).__name__}: {e}")
            out.append(None)
            continue
        if not res:
            log("extract.item_empty", label=inp.label,
                detail="model returned no caption objects; treated as a failure, not as 'no deals'")
            out.append(None)
            continue
        out.append([deal for cap in res for deal in cap["deals"]])
    return out


def extract_captions(inputs, prompt_text, client, cache_dir=CACHE_DIR, use_cache=True):
    """Returns (results, stats). results[i] is a list of deal dicts for inputs[i].
    Cache is per caption, keyed by content_hash + prompt_hash, so re-runs with an
    unchanged prompt make no API calls."""
    phash = prompt_hash(prompt_text)
    results = [None] * len(inputs)
    misses = []
    for i, inp in enumerate(inputs):
        cached = _cache_get(cache_dir, inp.content_hash, phash) if use_cache else None
        if cached is not None:
            results[i] = cached
        else:
            misses.append(i)

    stats = {"total": len(inputs), "cache_hits": len(inputs) - len(misses),
             "batches": 0, "text_batches": 0, "image_calls": 0}

    for batch_idx in _batches(misses, inputs):
        batch = [inputs[i] for i in batch_idx]
        stats["batches"] += 1
        # Count text batches and image (singleton) calls separately, so the cost
        # split is visible in the logs rather than hidden in one aggregate: each
        # image caption is its own request, so image_calls is the real driver.
        if any(inp.image_path for inp in batch):
            stats["image_calls"] += 1
        else:
            stats["text_batches"] += 1
        # A single-item batch goes straight to the lenient singleton path (no
        # alignment to check). A multi-item batch is verified and, on any
        # misalignment, retried as singletons.
        if len(batch) == 1:
            out = _singletons(batch, client, prompt_text)
        else:
            out = _aligned_batch(batch, client, prompt_text)
            if out is None:
                out = _singletons(batch, client, prompt_text)

        for j, i in enumerate(batch_idx):
            if out[j] is None:
                continue
            results[i] = out[j]
            if use_cache:
                _cache_put(cache_dir, inputs[i].content_hash, phash, out[j])

    stats["api_calls"] = client.call_count
    return results, stats
