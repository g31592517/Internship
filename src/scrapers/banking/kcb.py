import requests
from bs4 import BeautifulSoup
from datetime import datetime

class KCBScraper:
    # Legacy adapter kept from the original project; not used by the web app until fixed.
    name = "KCB Group"
    enabled = False
    disabled_reason = "Careers page lists no postings (jobs live on an external system); the old link-keyword scan only returned site navigation."

    def __init__(self):
        self.base_url = "https://ke.kcbgroup.com/about-us/careers"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def scrape(self, query="internship", location="Kenya"):
        # KCB often uses a simple list or an iframe.
        # Direct scraping is reliable if they list jobs on the main page.
        # If they use Taleo/Oracle, it's harder.
        
        print(f"Scraping KCB Group...")
        
        try:
            response = requests.get(self.base_url, headers=self.headers, verify=False) # Skip SSL if needed for some local corporate sites
            # KCB site might have redirects or SSL issues with some py libs
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            jobs = []
            
            # This logic mimics a generic search for "intern" on their careers page text
            # Because structure varies wildly.
            
            # Find any links that mention "Intern" or "Graduate" or "IT" if we passed that in query
            # We look for keywords in the link text or surrounding logic
            
            possible_jobs = soup.find_all('a')
            
            for link in possible_jobs:
                text = link.get_text(strip=True).lower()
                href = link.get('href', '')
                
                if not href:
                    continue
                    
                full_link = href if href.startswith('http') else f"https://ke.kcbgroup.com{href}"
                
                # Check for relevant keywords in the link text
                keywords = ['intern', 'graduate', 'technology', 'developer', 'software', 'ict', 'program']
                if any(k in text for k in keywords):
                    jobs.append({
                        'title': link.get_text(strip=True),
                        'company': "KCB Group",
                        'location': "Kenya",
                        'link': full_link,
                        'source': "KCB Careers",
                        'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            print(f"Found {len(jobs)} jobs at KCB.")
            return jobs
            
        except Exception as e:
            print(f"Error scraping KCB: {e}")
            return []
