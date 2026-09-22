import hashlib
import re

_URL = re.compile(r"https?://\S+|www\.\S+")
# Common emoji and pictograph blocks, plus variation selectors and ZWJ.
_EMOJI = re.compile(
    "[\U0001f000-\U0001faff\U00002600-\U000027bf\U00002190-\U000021ff"
    "\U00002b00-\U00002bff\U0001f1e6-\U0001f1ff️‍]"
)


def normalise(text):
    t = text.lower()
    t = _URL.sub(" ", t)
    t = _EMOJI.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def content_hash(text=None, image_bytes=None, combine=False):
    """Default (combine=False): text wins when present, else the image bytes. That
    is what deduping Instagram reposts by caption depends on, so it does not change.

    combine=True is for user submissions, where text alone is wrong: two people can
    photograph two different signs and type the same few words, and hashing the text
    alone makes the second collide with the first and be silently dropped by
    `on conflict (content_hash) do nothing`. The photo is the evidence, so on this
    path it always participates in the hash.
    """
    if combine:
        if image_bytes is None:
            raise ValueError("combined content_hash needs image_bytes")
        digest = hashlib.sha256(image_bytes).hexdigest()
        payload = f"{normalise(text or '')}|{digest}".encode("utf-8")
    elif text and text.strip():
        payload = normalise(text).encode("utf-8")
    elif image_bytes is not None:
        # Image-only capture has no text to normalise, so hash the raw bytes.
        payload = image_bytes
    else:
        raise ValueError("content_hash needs text or image_bytes")
    return hashlib.sha256(payload).hexdigest()
