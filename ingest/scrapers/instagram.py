"""Instagram capture source.

Instagram captures come from a private ingestion source that is not part of this
repository; this module is the interface stub it satisfies.

The pipeline around it is unaffected either way. Like every other scraper, this
one returns `RawCapture`s and never touches `deals`, so captures from a private
source flow through the same two stages (scrape, then extract) as the website and
manual sources, and are reviewed by hand like any other non-website capture. The
provenance fields a capture can carry are documented on `RawCapture` in base.py:
`source_handle` (the post's actual author) and `via_handle` (the monitored
profile that surfaced it, when those differ).
"""
from ingest.scrapers.base import RawCapture, Scraper


class InstagramScraper(Scraper):
    """Stub. Construction is accepted so the runner can wire it up, but fetch()
    is not implemented here; the working implementation is private."""

    def __init__(self, monitored=None, seen_shortcodes=None, **kwargs):
        self.monitored = monitored or {}
        self.seen_shortcodes = seen_shortcodes or {}
        # Side outputs the runner reads after a real fetch(): the accounts seen
        # this run, their newest post per account, and run counters.
        self.matched = set()
        self.newest = {}
        self.stats = {"posts_seen": 0, "posts_captured": 0, "accounts_matched": 0, "duration_s": 0.0}

    def fetch(self) -> list[RawCapture]:
        raise NotImplementedError(
            "the Instagram capture source is private and not included in this repository"
        )
