"""Generic adapter for WordPress job blogs that use the same article markup (Kadence theme):
Corporate Staffing and Career Point Kenya today. A new WordPress site is ~5 lines of config."""
import re

from opportunity.search import CourseQuery
from scrapers.base import BaseScraper, now_str, soup_of


_BOILERPLATE = re.compile(r"choose your goal below|browse latest jobs|post a free job advert|professional cv writing|"
                          r"job interview answers|top short courses|not getting interviews|fix your cv", re.I)


def split_title_org(title: str) -> tuple[str, str]:
    """'Software Engineering Internship Job Hanmak Technologies' -> ('Software Engineering Internship', 'Hanmak Technologies').
    These blogs append ' Job <Organisation>' to every post title."""
    m = re.match(r"^(.*\S)\s+Jobs?\s+(?:Job\s+)?(\S.*)$", title.strip())
    if m and len(m.group(2).split()) <= 7:
        t = re.sub(r"\s+Jobs?$", "", m.group(1)).strip()
        return t, m.group(2).strip()
    return re.sub(r"\s+Jobs?$", "", title.strip()), ""


def org_from_tags(title: str, tags: list[str]) -> tuple[str, str]:
    """Some posts have no ' Job <Org>' marker, but are tagged '<org>-jobs-in-kenya'. If the title ends
    with that organisation name, split it off: ('Electrical Intern Ramco Group', ['ramco group jobs in kenya'])
    -> ('Electrical Intern', 'Ramco Group')."""
    low = title.lower()
    for tag in tags:
        m = re.match(r"^(.{3,60}?)\s+jobs?\s+in\s+\w+$", tag)
        if m and low.endswith(" " + m.group(1)):
            n = len(m.group(1))
            return title[: -n].strip(" -–:"), title[-n:].strip()
    return title, ""


class WordPressSource(BaseScraper):
    name = ""
    base_url = ""
    pages = 1

    def build_queries(self, course: str) -> list[str]:
        q = CourseQuery.parse(course)
        out = [f"{q.phrase} intern"]
        for t in q.strong[:2]:
            out.append(f"{t} intern")
        out.append(f"{q.phrase} attachment")
        return list(dict.fromkeys(x.strip() for x in out if x.strip()))[:4]

    def scrape(self, query="internship", location=None):
        jobs, seen = [], set()
        for page in range(1, self.pages + 1):
            url = f"{self.base_url}/" + (f"page/{page}/" if page > 1 else "")
            print(f"Scraping {self.name}: {url}?s={query}")
            soup = soup_of(self.get(url, params={"s": query}))
            for art in soup.find_all("article"):
                a = art.select_one("h2 a, h3 a")
                if not a or not a.get("href") or a["href"] in seen:
                    continue
                seen.add(a["href"])
                title, org = split_title_org(a.get_text(" ", strip=True))
                time_tag = art.select_one("time.published, time.entry-date, time")
                excerpt = art.select_one(".entry-summary, .entry-content")
                classes = art.get("class") or []
                # category-/tag- classes carry the site's own labels, including places ('jobs-in-nakuru')
                tags = [c.split("-", 1)[1].replace("-", " ") for c in classes if c.startswith(("category-", "tag-"))]
                if not org:
                    title, org = org_from_tags(title, tags)
                jobs.append({
                    "title": title,
                    "company": org,
                    "location": "",
                    "link": a["href"],
                    "source": self.name,
                    "scraped_at": now_str(),
                    "snippet": excerpt.get_text(" ", strip=True) if excerpt else "",
                    "posted": time_tag.get("datetime", "")[:10] if time_tag else "",
                    "tags": tags,
                })
        return jobs

    def enrich(self, raw: dict) -> dict:
        soup = soup_of(self.get(raw["link"], detail=True))
        body = soup.select_one(".entry-content") or soup.select_one("article")
        if body:
            for junk in body.select("script, style, .sharedaddy, .addtoany_share_save_container, form"):
                junk.decompose()
            for block in body.find_all(recursive=False):   # site banner / promo blocks, not the ad itself
                if re.search(r"choose your goal below", block.get_text(" ", strip=True)[:400], re.I):
                    block.decompose()
            text = body.get_text("\n", strip=True)
            raw["description"] = "\n".join(ln for ln in text.splitlines() if not _BOILERPLATE.search(ln))
            for a in body.select('a[href^="mailto:"]'):
                addr = a["href"][7:].split("?")[0].strip()
                if addr:
                    raw["apply_email"] = addr
                    break
            for a in body.find_all("a", href=True):
                if re.search(r"\bapply\b", a.get_text(" "), re.I) and a["href"].startswith("http"):
                    raw["apply_url"] = a["href"]
                    break
        raw["link_status"] = "ok"
        return raw
