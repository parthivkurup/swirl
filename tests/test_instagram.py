"""The Instagram source's public half: the monitored-account set read from
config/chains.yaml, and the scraper interface itself. The capture source is
private and not included in this repository, so fetch() is a stub here and the
profile walk is not exercised."""
import pytest

from ingest.scrape_instagram import load_monitored_handles
from ingest.scrapers.base import Scraper
from ingest.scrapers.instagram import InstagramScraper


def test_monitored_handles_excludes_null_and_normalises():
    handles = load_monitored_handles()
    # Every monitored handle is lowercased and @-stripped.
    assert all(h == h.lower() and not h.startswith("@") for h in handles)
    # A known chain with a handle is present; the null-handle chain is absent.
    assert "iloveyochi" in handles
    assert None not in handles
    # Vanilla Dessert Bar has a null handle, so its name never appears as a value
    # under a truthy key mapping.
    assert "Yo-Chi" in handles.values()


def test_stub_implements_the_scraper_interface():
    scraper = InstagramScraper(load_monitored_handles())
    assert isinstance(scraper, Scraper)
    # The side outputs the runner reads after fetch() exist and start empty, so
    # wiring the runner up does not depend on the private implementation.
    assert scraper.matched == set()
    assert scraper.newest == {}
    assert scraper.stats["posts_captured"] == 0


def test_stub_fetch_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        InstagramScraper({}).fetch()
