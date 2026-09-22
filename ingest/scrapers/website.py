from pathlib import Path
from urllib.parse import urljoin

import yaml
from bs4 import BeautifulSoup

from ingest.hashing import content_hash
from ingest.log import log
from ingest.media import media_root, to_stored
from ingest.scrapers.base import RawCapture, Scraper
from ingest.scrapers.http import PoliteFetcher

SCRAPERS_YAML = Path(__file__).resolve().parent.parent.parent / "config" / "scrapers.yaml"
# Resolved per run rather than at import, so MEDIA_ROOT applies after load_dotenv.
IMAGE_SUBDIR = "promo_images"

_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


def _ext_from(content_type, url):
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in _EXT:
        return _EXT[ct]
    suffix = Path(url.split("?")[0]).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"} else ".jpg"


class WebsiteScraper(Scraper):
    """Config-driven scraper. Nothing chain-specific is hardcoded: every URL,
    selector and status comes from config/scrapers.yaml. Writes to raw_captures
    only (returns RawCaptures); it never touches deals."""

    def __init__(self, config_path=SCRAPERS_YAML, fetcher=None, image_dir=None):
        self.config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        self.fetcher = fetcher or PoliteFetcher()
        self.image_dir = Path(image_dir) if image_dir else media_root() / IMAGE_SUBDIR

    def fetch(self):
        caps = []
        for entry in self.config.get("scrapers", []):
            chain, status = entry.get("chain"), entry.get("status")
            if status not in ("scrapeable", "image_only"):
                log("scrape.source", chain=chain, status=status, captures=0, note="not scraped")
                continue
            url = entry["url"]
            res = self.fetcher.get(url)
            if not res.get("allowed", False):
                log("scrape.source", chain=chain, status=status, url=url, captures=0, note="robots disallow")
                continue
            if res.get("status") != 200 or not res.get("content"):
                log("scrape.source", chain=chain, status=status, url=url,
                    http_status=res.get("status"), captures=0, note=res.get("error") or "no content")
                continue
            new = self._text_caps(entry, res, url) if status == "scrapeable" else self._image_caps(entry, res, url)
            caps += new
            log("scrape.source", chain=chain, status=status, url=url, http_status=200, captures=len(new))
        return caps

    def _text_caps(self, entry, res, url):
        soup = BeautifulSoup(res["content"], "html.parser")
        caps = []
        for el in soup.select(entry["selectors"]["text"]):
            text = el.get_text(" ", strip=True)
            if text:
                caps.append(RawCapture(source_type="website", content_hash=content_hash(text=text),
                                       source_url=url, content_text=text))
        return caps

    def _image_caps(self, entry, res, url):
        soup = BeautifulSoup(res["content"], "html.parser")
        self.image_dir.mkdir(parents=True, exist_ok=True)
        caps = []
        for img in soup.select(entry["selectors"]["image"]):
            src = img.get("src") or img.get("data-src")
            if not src:
                continue
            img_url = urljoin(url, src)
            r = self.fetcher.get(img_url)
            if not r.get("allowed") or r.get("status") != 200 or not r.get("content"):
                log("scrape.image_skip", url=img_url, http_status=r.get("status"))
                continue
            data = r["content"]
            h = content_hash(image_bytes=data)
            path = (self.image_dir / f"{h}{_ext_from(r.get('content_type'), img_url)}").resolve()
            path.write_bytes(data)
            caps.append(RawCapture(source_type="website", content_hash=h, source_url=url,
                                   image_path=to_stored(path)))
        return caps
