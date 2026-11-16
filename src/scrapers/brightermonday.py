import re

from opportunity.search import CourseQuery
from scrapers.base import BaseScraper, now_str, soup_of

_NOT_A_PLACE = re.compile(r"contract|full[\s-]?time|part[\s-]?time|internship|ksh|usd|volunteer|temporary|casual|per\s", re.I)


class BrighterMondayScraper(BaseScraper):
    """BrighterMonday Kenya. Search results are server-rendered and the site's search does filter.
    Applying needs a BrighterMonday login, so these are 'open application' only."""
    name = "BrighterMonday"
    base_url = "https://www.brightermonday.co.ke"

    def build_queries(self, course: str) -> list[str]:
        q = CourseQuery.parse(course)
        out = [f"{q.phrase} intern", f"{q.phrase} attachment"]
        out += [f"{t} intern" for t in q.strong[:2]]
        return list(dict.fromkeys(x.strip() for x in out if x.strip()))[:4]

    def scrape(self, query="internship", location=None):
        print(f"Scraping BrighterMonday: {query}")
        soup = soup_of(self.get(f"{self.base_url}/jobs", params={"q": query}))
        jobs, seen = [], set()
        for a in soup.select('a[data-cy="listing-title-link"]'):
            link = a.get("href", "")
            if not link or link in seen:
                continue
            seen.add(link)
            card = a.find_parent("div", class_="w-full") or a.parent
            paras = [p.get_text(" ", strip=True) for p in card.find_all("p")]
            paras = [p for p in paras if p and p != a.get("title")]
            chips = [s.get_text(" ", strip=True) for s in card.find_all("span") if s.get_text(strip=True)]
            place = next((c for c in chips if not _NOT_A_PLACE.search(c)), "")
            jobs.append({
                "title": a.get("title") or a.get_text(" ", strip=True),
                "company": paras[0] if paras else "",
                "location": place,
                "link": link,
                "source": self.name,
                "scraped_at": now_str(),
                "field_label": paras[-1] if len(paras) > 1 else "",
                "tags": chips,
            })
        return jobs

    def enrich(self, raw: dict) -> dict:
        soup = soup_of(self.get(raw["link"], detail=True))
        text = soup.get_text("\n", strip=True)
        m = re.search(r"\nJob summary\n(.*?)(?:\nSimilar jobs|\nShare this job|\nReport this job|\nApply|\Z)", text, re.S)
        if m:
            raw["description"] = m.group(1).strip()
        raw["apply_url"] = raw["link"]  # sign-in is on BrighterMonday itself
        raw["link_status"] = "ok"
        return raw
