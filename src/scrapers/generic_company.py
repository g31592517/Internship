from scrapers.myjobmag import MyJobMagScraper

class GenericCompanyScraper:
    # Legacy adapter kept from the original project; not used by the web app until fixed.
    name = "Company search via MyJobMag"
    enabled = False
    disabled_reason = "Superseded by the Organization filter on search results."

    """
    A scraper that uses existing aggregators (MyJobMag, Corporate Staffing)
    to find jobs for specific companies that are hard to scrape directly.
    """
    def __init__(self, company_name):
        self.company_name = company_name
        self.aggregator = MyJobMagScraper() # Primary backup

    def scrape(self, query="internship", location="Kenya"):
        print(f"Scraping aggregators for company: {self.company_name}...")
        
        # We search the aggregator for the COMPANY NAME + QUERY
        # e.g. "Safaricom Internship"
        search_term = f"{self.company_name} {query}"
        
        try:
            results = self.aggregator.scrape(query=search_term, location=location)
            
            # Post-process to ensure company is roughly correct
            filtered = []
            for job in results:
                # We trust the aggregator search relevance, but we can double check
                filtered.append(job)
                # Overwrite source to indicate it Was a targeted company search
                job['source'] = f"{self.company_name} (via MyJobMag)"
                
            return filtered
        except Exception as e:
            print(f"Error recursive scraping for {self.company_name}: {e}")
            return []
