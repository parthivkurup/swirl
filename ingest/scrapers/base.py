from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RawCapture:
    source_type: str
    content_hash: str
    source_url: str | None = None
    content_text: str | None = None
    image_path: str | None = None
    # The handle that actually authored the post (Instagram). None for sources
    # with no owning handle (website, manual, user submissions).
    source_handle: str | None = None
    # The monitored profile a capture was surfaced under, when that differs from
    # the author (a tagged / collab / feature post). None for the account's own
    # posts and for non-Instagram sources.
    via_handle: str | None = None
    # The shop name a submitter typed into /submit. Structured rather than
    # concatenated into content_text, because a labelled form field is not caption
    # prose and the extractor prompt correctly declines to read it as one. Null for
    # every source except a user submission.
    submitted_store: str | None = None
    # None lets the database apply its captured_at default (now()). Set
    # explicitly when replaying historical or fixture captures.
    captured_at: str | None = None


class Scraper(ABC):
    """Every scraper returns a list of RawCapture and never touches deals.

    This two-stage split (scrapers write raw_captures, the extractor reads them)
    is what lets extraction be re-run over history when the prompt changes.
    """

    @abstractmethod
    def fetch(self) -> list[RawCapture]:
        ...
