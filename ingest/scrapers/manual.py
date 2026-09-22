from ingest.hashing import content_hash
from ingest.media import resolve, to_stored
from ingest.scrapers.base import RawCapture, Scraper


class ManualScraper(Scraper):
    def __init__(
        self,
        text=None,
        image_path=None,
        source_type="manual",
        source_url=None,
        captured_at=None,
        submitted_store=None,
        combine_hash=False,
    ):
        if not text and not image_path:
            raise ValueError("manual capture needs --text or --image")
        self.text = text
        self.image_path = image_path
        self.source_type = source_type
        self.source_url = source_url
        self.captured_at = captured_at
        self.submitted_store = submitted_store
        # User submissions hash text and image together; see content_hash.
        self.combine_hash = combine_hash

    def fetch(self) -> list[RawCapture]:
        image_bytes = None
        stored_image = None
        if self.image_path:
            p = resolve(self.image_path)
            if not p.is_file():
                raise FileNotFoundError(self.image_path)
            image_bytes = p.read_bytes()
            # Record it relative to the media root when it lives there, so the row
            # does not depend on where this checkout happens to sit.
            stored_image = to_stored(p)

        h = content_hash(text=self.text, image_bytes=image_bytes, combine=self.combine_hash)
        return [
            RawCapture(
                source_type=self.source_type,
                content_hash=h,
                source_url=self.source_url,
                content_text=self.text,
                image_path=stored_image,
                submitted_store=self.submitted_store,
                captured_at=self.captured_at,
            )
        ]
