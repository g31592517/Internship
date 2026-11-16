import re
from urllib.parse import quote_plus

from opportunity.search import CourseQuery
from scrapers.base import BaseScraper, now_str, soup_of


class MyJobMagScraper(BaseScraper):
    """MyJobMag Kenya. Its search matches literal words, so long phrases ('software engineering
    internship') return nothing; short queries ('software engineering intern') work.
    The list-page parsing is the original scraper's idea (job headers -> links), fixed to read the
    real card markup (company from the logo alt text, date, snippet)."""
    name = "MyJobMag"
    base_url = "https://www.myjobmag.co.ke"
    pages = 2

    def build_queries(self, course: str) -> list[str]:
        q = CourseQuery.parse(course)
        out = [f"{q.phrase} intern", f"{q.phrase} attachment"]
        for t in q.strong[:3]:
            out += [f"{t} intern", f"{t} attachment"]
        return list(dict.fromkeys(x.strip() for x in out if x.strip()))[:5]

    def scrape(self, query="internship", location=None):
        jobs, seen = [], set()
        for page in range(1, self.pages + 1):
            url = f"{self.base_url}/search/jobs?q={quote_plus(query)}" + (f"&currentpage={page}" if page > 1 else "")
            print(f"Scraping MyJobMag: {url}")
            soup = soup_of(self.get(url))
            cards = soup.select("li.job-list-li")
            if not cards:
                break
            for card in cards:
                a = card.select_one("h2 a")
                if not a or not a.get("href"):
                    continue
                link = a["href"] if a["href"].startswith("http") else self.base_url + a["href"]
                if link in seen:
                    continue
                seen.add(link)
                full_title = a.get_text(" ", strip=True)
                logo = card.select_one(".job-logo img")
                company = (logo.get("alt") or "").strip() if logo else ""
                title = full_title
                if company and full_title.lower().endswith(" at " + company.lower()):
                    title = full_title[: -len(company) - 4]
                elif " at " in full_title:  # logo missing: 'Role at Company'
                    title, company = (s.strip() for s in full_title.rsplit(" at ", 1))
                desc = card.select_one(".job-desc")
                date_tag = card.select_one("#job-date")
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": "",
                    "link": link,
                    "source": self.name,
                    "scraped_at": now_str(),
                    "snippet": desc.get_text(" ", strip=True) if desc else "",
                    "posted": date_tag.get_text(strip=True) if date_tag else "",
                })
        return jobs

    def enrich(self, raw: dict) -> dict:
        soup = soup_of(self.get(raw["link"], detail=True))
        info = {}
        for li in soup.select("ul.job-key-info li"):
            k, v = li.select_one(".jkey-title"), li.select_one(".jkey-info")
            if k and v:
                info[k.get_text(strip=True).lower()] = v.get_text(", ", strip=True)
        if info.get("location"):
            raw["location"] = info["location"]
        if info.get("job field"):
            raw["field_label"] = info["job field"]
        body = soup.select_one("#printable") or soup.select_one(".job-details")
        if body:
            text = body.get_text("\n", strip=True)
            raw["description"] = re.split(r"\n\s*Build your CV for free", text)[0]
        page_text = soup.get_text(" ", strip=True)
        m = re.search(r"Deadline:\s*([A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4})", page_text)
        if m:
            raw["deadline"] = m.group(1)
        apply_a = soup.select_one('a[href^="/apply-now/"]')
        if apply_a:
            raw["apply_url"] = self.base_url + apply_a["href"]
        for a in soup.select('a[href^="mailto:"]'):
            addr = a["href"][7:].split("?")[0].strip()
            if addr and "myjobmag" not in addr.lower():
                raw["apply_email"] = addr
                break
        raw["link_status"] = "ok"
        return raw
