"""Shared plumbing for source adapters.

An adapter has three jobs and nothing else (no filtering, no course logic, no database):
  build_queries(course) -> search strings that suit THIS site's search box
  scrape(query)         -> raw dicts for the listings the site returns (original contract)
  enrich(raw)           -> optional second request for the detail page (description, deadline, ...)

To add a new site: subclass BaseScraper (or WordPressSource for WordPress sites), implement the
methods above, and add it to scrapers/registry.py. Nothing else in the app changes.

Access controls are respected, never bypassed: a CAPTCHA / bot-challenge raises SourceBlocked and
the source is simply reported as blocked for that search."""
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from opportunity.search import CourseQuery

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0.0.0 Safari/537.36")


class SourceError(Exception):
    """The source could not be searched this time."""


class SourceBlocked(SourceError):
    """Bot protection / login wall. We stop; we do not try to get around it."""


class SourceUnavailable(SourceError):
    """Endpoint missing, site down, or markup no longer matches."""


class LinkBroken(Exception):
    """A listing's own page is gone (404/410)."""


def soup_of(resp: requests.Response) -> BeautifulSoup:
    # Parse bytes so bs4 can honour the page's declared charset (avoids mojibake like 'Bachelor�s').
    return BeautifulSoup(resp.content, "lxml")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_CHALLENGE = re.compile(r"cf-turnstile|challenge-platform|Just a moment|g-recaptcha|h-captcha|px-captcha", re.I)


class BaseScraper:
    name = "Unnamed source"
    base_url = ""
    enabled = True
    disabled_reason = ""
    timeout = 12
    max_queries = 4

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
        self.headers = self.session.headers  # kept for the original scrapers' attribute name

    # -- http ---------------------------------------------------------------------------
    def get(self, url: str, *, params: dict | None = None, detail: bool = False) -> requests.Response:
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as e:
            raise SourceUnavailable(f"{self.name}: {type(e).__name__}") from e
        if resp.status_code in (404, 410):
            raise (LinkBroken(url) if detail else SourceUnavailable(f"{self.name}: HTTP {resp.status_code}"))
        if resp.status_code in (401, 403, 429) or (resp.status_code == 503 and _CHALLENGE.search(resp.text[:5000])):
            raise SourceBlocked(f"{self.name}: access restricted (HTTP {resp.status_code})")
        if len(resp.content) < 60000 and _CHALLENGE.search(resp.text[:20000]) and "<article" not in resp.text:
            raise SourceBlocked(f"{self.name}: bot-protection challenge")
        if resp.status_code >= 400:
            raise SourceUnavailable(f"{self.name}: HTTP {resp.status_code}")
        return resp

    # -- the contract -------------------------------------------------------------------
    def build_queries(self, course: str) -> list[str]:
        q = CourseQuery.parse(course)
        out = [f"{q.phrase} intern", f"{q.phrase} attachment"]
        for t in q.strong[:3]:
            out.append(f"{t} intern")
        return list(dict.fromkeys(x.strip() for x in out if x.strip()))[: self.max_queries]

    def scrape(self, query: str, location: str | None = None) -> list[dict]:
        raise NotImplementedError

    def enrich(self, raw: dict) -> dict:
        """Fetch the listing's own page and add description/deadline/etc. Raise LinkBroken on 404."""
        return raw
