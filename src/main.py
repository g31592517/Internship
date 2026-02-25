import pandas as pd
from datetime import datetime
from scrapers.careerjet import CareerJetScraper
from scrapers.corporate_staffing import CorporateStaffingScraper
from scrapers.fuzu import FuzuScraper
from scrapers.myjobmag import MyJobMagScraper
from scrapers.big_tech.microsoft import MicrosoftScraper
from scrapers.banking.kcb import KCBScraper
from scrapers.generic_company import GenericCompanyScraper
import re
import os
import urllib3

# Import configuration
try:
    from src.config import IT_QUERIES, IT_TARGETED_COMPANIES, ADMIN_QUERIES, ADMIN_TARGETED_COMPANIES
except ImportError:
    print("Error: src/config.py not found using 'src.config'. Trying local import...")
    try: 
        from config import IT_QUERIES, IT_TARGETED_COMPANIES, ADMIN_QUERIES, ADMIN_TARGETED_COMPANIES
    except ImportError:
        print("CRITICAL ERROR: config.py not found. create one from src/config.sample.py")
        exit(1)

# Suppress SSL warnings for KCB/others
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class JobScraper:
    def __init__(self):
        # 1. Broad Job Boards
        self.general_scrapers = [
            MyJobMagScraper(), 
            CareerJetScraper(),
            CorporateStaffingScraper(),
        ]
        
        # TRACK 1: IT & CS Config
        self.it_queries = IT_QUERIES
        
        self.it_direct_scrapers = [
            MicrosoftScraper(),
            KCBScraper(),
        ]

        self.it_targeted_companies = IT_TARGETED_COMPANIES

        # TRACK 2: Public Administration Config
        self.admin_queries = ADMIN_QUERIES
        
        self.admin_targeted_companies = ADMIN_TARGETED_COMPANIES

    def run(self):
        print(f"Starting comprehensive job scraper...")
        
        # --- TRACK 1: IT & CS ---
        print("\n=== STARTING TRACK: IT & CS ===")
        it_jobs = self.run_track(
            queries=self.it_queries, 
            direct_scrapers=self.it_direct_scrapers,
            targeted_companies=self.it_targeted_companies,
            track_name="IT/CS"
        )
        self.save_results(it_jobs, "it_internships")

        # --- TRACK 2: Public Administration ---
        print("\n=== STARTING TRACK: Public Administration ===")
        admin_jobs = self.run_track(
            queries=self.admin_queries,
            direct_scrapers=[], # No direct scrapers for admin yet
            targeted_companies=self.admin_targeted_companies,
            track_name="Public Admin"
        )
        self.save_results(admin_jobs, "public_admin_internships")

    def run_track(self, queries, direct_scrapers, targeted_companies, track_name):
        jobs = []
        seen_links = set()
        
        # Phase 1: General Boards
        print(f"\n[{track_name}] Phase 1: Broad Job Boards")
        for query in queries:
            for scraper in self.general_scrapers:
                self._run_scraper_logic(scraper, query, jobs, seen_links)

        # Phase 2: Direct Scrapers
        if direct_scrapers:
            print(f"\n[{track_name}] Phase 2: Direct Company Sites")
            for scraper in direct_scrapers:
                # Direct scrapers often have fixed logic, but we can pass a hint
                self._run_scraper_logic(scraper, "internship", jobs, seen_links)

        # Phase 3: Targeted Companies
        if targeted_companies:
            print(f"\n[{track_name}] Phase 3: Targeted Search")
            for company in targeted_companies:
                scraper = GenericCompanyScraper(company)
                self._run_scraper_logic(scraper, "Internship", jobs, seen_links)
                
        print(f"[{track_name}] Completed. Found {len(jobs)} jobs.")
        return jobs

    def _run_scraper_logic(self, scraper, query, jobs_list, seen_set):
        try:
            found = scraper.scrape(query=query, location="Kenya")
            for job in found:
                # Filter: Title must contain "intern", "internship", etc.
                # Must check for word boundaries to avoid matching "International" or "Internet"
                # Regex: \b matches word boundary. Matches "Intern", "Interns", "Internship", "Internships"
                # This excludes "International Relations" unless it also says "Intern" elsewhere.
                if re.search(r'\bintern(ship|s)?\b', job['title'], re.IGNORECASE) and job['link'] not in seen_set:
                    jobs_list.append(job)
                    seen_set.add(job['link'])
        except Exception as e:
            print(f"Error executing scraper: {e}")

    def save_results(self, jobs, filename_prefix):
        if not jobs:
            print(f"No jobs found for {filename_prefix}.")
            return

        df = pd.DataFrame(jobs)
        
        os.makedirs('output', exist_ok=True)
        
        filename = f"output/{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        print(f"Results saved to {filename}")

if __name__ == "__main__":
    scraper = JobScraper()
    scraper.run()
