import time
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import urlparse

# Identifiable, honest User-Agent. This is a hobby project reading public promo
# pages; behave like a polite reader.
USER_AGENT = "FroyoDealTracker/0.1 (+hobby project; polite promo reader)"
MIN_INTERVAL = 5.0  # seconds between requests to the same host


class PoliteFetcher:
    """Sequential, rate-limited fetcher that respects robots.txt. One request to
    a host at a time (calls are synchronous) and at least MIN_INTERVAL seconds
    between requests to the same host."""

    def __init__(self, user_agent=USER_AGENT, min_interval=MIN_INTERVAL, timeout=20):
        self.ua = user_agent
        self.min_interval = min_interval
        self.timeout = timeout
        self._last = {}
        self._robots = {}

    def _host(self, url):
        return urlparse(url).netloc

    def _throttle(self, host):
        last = self._last.get(host)
        if last is not None:
            wait = self.min_interval - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self._last[host] = time.monotonic()

    def _robot(self, url):
        host = self._host(url)
        rp = self._robots.get(host)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{urlparse(url).scheme}://{host}/robots.txt"
            self._throttle(host)
            try:
                req = urllib.request.Request(robots_url, headers={"User-Agent": self.ua})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    rp.parse(r.read().decode("utf-8", "replace").splitlines())
            except Exception:
                rp.allow_all = True  # robots unreachable: default to allow, politely
            self._robots[host] = rp
        return rp

    def allowed(self, url):
        try:
            return self._robot(url).can_fetch(self.ua, url)
        except Exception:
            return True

    def get(self, url):
        """Fetch a URL. Returns a dict with allowed, status, content_type,
        content (bytes) and optional error. Does not fetch if robots disallows."""
        if not self.allowed(url):
            return {"url": url, "allowed": False, "status": None, "content_type": None, "content": None}
        self._throttle(self._host(url))
        req = urllib.request.Request(url, headers={"User-Agent": self.ua})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return {
                    "url": url,
                    "allowed": True,
                    "status": getattr(r, "status", 200),
                    "content_type": r.headers.get("content-type", ""),
                    "content": r.read(),
                }
        except urllib.error.HTTPError as e:
            return {"url": url, "allowed": True, "status": e.code, "content_type": "", "content": None, "error": f"HTTP {e.code}"}
        except Exception as e:
            return {"url": url, "allowed": True, "status": None, "content_type": None, "content": None, "error": str(e)}
