import re

from scrapers.base import BaseScraper, now_str, soup_of


class CareerJetScraper(BaseScraper):
    """CareerJet Kenya. From many networks it answers with a Cloudflare Turnstile challenge instead
    of results. We do NOT try to pass it: BaseScraper.get raises SourceBlocked and the search just
    reports CareerJet as blocked. If a network is let through, the parser below works as before."""
    name = "CareerJet"
    base_url = "https://www.careerjet.co.ke"

    def scrape(self, query="internship", location=None):
        print(f"Scraping CareerJet: {query}")
        soup = soup_of(self.get(f"{self.base_url}/jobs", params={"s": query, "l": "Kenya"}))
        jobs, seen = [], set()
        for link in soup.find_all("a", href=lambda h: h and "/jobad/" in h):
            job_url = link["href"] if link["href"].startswith("http") else self.base_url + link["href"]
            if job_url in seen:
                continue
            seen.add(job_url)
            container = link.find_parent("article") or link.find_parent("div", class_="job")
            company, loc = "", ""
            if container:
                c = container.find("p", class_="company")
                company = c.get_text(strip=True) if c else ""
                l = container.find("ul", class_="location") or container.find("div", class_="locations")
                loc = l.get_text(" ", strip=True) if l else ""
                desc = container.find("div", class_="desc")
            jobs.append({
                "title": link.get_text(strip=True),
                "company": company,
                "location": loc,
                "link": job_url,
                "source": self.name,
                "scraped_at": now_str(),
                "snippet": desc.get_text(" ", strip=True) if container and desc else "",
            })
        return jobs
