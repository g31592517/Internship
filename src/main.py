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
        self.it_queries = [
            "Information Technology Internship",
            "Computer Science Internship",
            "Software Engineering Internship",
        ]
        
        self.it_direct_scrapers = [
            MicrosoftScraper(),
            KCBScraper(),
        ]

        self.it_targeted_companies = [
            "Safaricom", "Google", "Equity Bank", "Absa Bank", 
            "Co-operative Bank", "NCBA", "Stanbic", "I&M Bank", 
            "Oracle", "IBM", "Cisco", "Andela", "Visa",
            "Cellulant", "Interswitch", "DPO Group", "Little App",
            "Jubilee Insurance", "Britam", "APA Insurance",
            "ICT Authority", "Kenya Revenue Authority", "KenGen", "Kenya Power"
        ]

        # TRACK 2: Public Administration Config
        self.admin_queries = [
            "Public Administration Internship",
            "Public Policy Internship",
            "Government Internship",
            "Policy Analyst Internship",
            "Administrative Officer Internship",
            "Governance Internship",
            "Civic Engagement Internship",
            "County Government Internship",
            "Parliamentary Internship",
            "Program Assistant Internship",
            "Project Management Internship",
            "Monitoring and Evaluation Internship",
            "Social Work Internship",
            "Political Science Internship",
            "International Relations Internship",
            "Non-Governmental Organization Internship",
            "Humanitarian Internship"
        ]
        
        self.admin_targeted_companies = [
            # UN & Multilaterals
            "United Nations", "UNEP", "UNDP", "UNICEF", "UNHCR", "WFP", "WHO", "FAO", 
            "UN Women", "IOM", "World Bank", "IMF",
            
            # Major International NGOs
            "World Vision", "Save the Children", "Oxfam", "Care International", 
            "Plan International", "International Rescue Committee", "Catholic Relief Services", 
            "Mercy Corps", "ActionAid", "Goal Kenya", "Concern Worldwide", 
            "Danish Refugee Council", "Norwegian Refugee Council", "Doctors Without Borders", 
            "Fred Hollows Foundation", "FHI 360", "PATH", "TechnoServe", "RTI International", 
            "Pact", "Palladium", "Chemonics", "Compassion International", "ChildFund", 
            "SOS Children's Villages", "Habitat for Humanity", "Heifer International", 
            "SNV Netherlands", "VSO", "Lutheran World Federation", "Islamic Relief", "ADRA", 
            "Johanniter International", "Welthungerhilfe", "Trocaire", "Christian Aid", 
            "Tearfund", "War Child", "Search for Common Ground", "Saferworld", "Interpeace",
            "Finn Church Aid", "Hand in Hand Eastern Africa", "Self Help Africa", "Solidaridad",
            "Action Against Hunger", "Hivos", "Sightsavers", "Light for the World", "CBM",
            "HelpAge International", "ForumCiv", "Vi Agroforestry", "WeWorld", "Avsi Foundation",

            # Health, Research & Foundations
            "Amref Health Africa", "Living Goods", "Marie Stopes", "LVCT Health", 
            "Elizabeth Glaser Pediatric AIDS Foundation", "APHRC", "ILRI", "ICRAF", "URC",
            "Jacaranda Health", "Evidence Action", "GiveDirectly", "IDinsight", "Busara Center",
            "Innovations for Poverty Action", "Aga Khan Foundation", "M-PESA Foundation",
            "Mastercard Foundation", "Rockefeller Foundation", "Ford Foundation",

            # Rights, Governance & Civil Society
            "Amnesty International", "Human Rights Watch", "Transparency International", 
            "Kenya Human Rights Commission", "International Justice Mission", "Haki Africa",
            "Act Change Transform", "Uraia Trust", "Inuka Kenya", "Twaweza",

            # Conservation
            "WWF Kenya", "African Wildlife Foundation", "The Nature Conservancy", 
            "Green Belt Movement", "BirdLife International", "Rainforest Alliance",

            # Local/Regional & Social Enterprises
            "Kenya Red Cross", "Shining Hope for Communities", "Carolina for Kibera", 
            "ZanaAfrica", "Dignitas", "One Acre Fund", "Farm Africa", "Sanergy", "RefuSHE", 
            "HIAS", "Xavier Project", "Windle International",

            # Government Commissions (Administrative)
            "IEBC", "Ethics and Anti-Corruption Commission", "Public Service Commission", 
            "National Environment Management Authority", "Kenya National Commission on Human Rights"
        ]

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

    def save_results(self):
        if not self.all_jobs:
            print("No jobs found to save.")
            return

        df = pd.DataFrame(self.all_jobs)
        
        # Ensure output directory exists
        os.makedirs('output', exist_ok=True)
        
        filename = f"output/internships_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        print(f"Results saved to {filename}")

if __name__ == "__main__":
    scraper = JobScraper()
    scraper.run()
