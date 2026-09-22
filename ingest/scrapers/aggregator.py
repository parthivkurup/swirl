from ingest.scrapers.base import RawCapture, Scraper


class AggregatorScraper(Scraper):
    def fetch(self) -> list[RawCapture]:
        raise NotImplementedError("aggregator scraper is not implemented yet")
