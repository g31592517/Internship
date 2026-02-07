import requests
from bs4 import BeautifulSoup
from datetime import datetime

class MyJobMagScraper:
    def __init__(self):
        self.base_url = "https://www.myjobmag.co.ke"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def scrape(self, query="internship", location="Kenya"):
        # MyJobMag search URL structure
        url = f"{self.base_url}/search/jobs?q={query}"
        print(f"Scraping MyJobMag: {url}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            jobs = []
            
            # Jobs seem to be listed in a container, often <ul> with class 'job-list' or similar
            # Based on the text dump, there are headers <h2> with links inside.
            
            # Find all job headers
            job_headers = soup.find_all('h2')
            
            for header in job_headers:
                link = header.find('a')
                if not link:
                    continue
                
                title = link.get_text(strip=True)
                job_url = self.base_url + link['href'] if not link['href'].startswith('http') else link['href']
                
                # Context extraction (Company, Date)
                # Usually follows the h2
                container = header.find_parent('li')
                
                company = "Unknown"
                date_posted = "Unknown"
                
                if container:
                    # Company is often in a specific tag or just text
                    # Looking for a link to /jobs-at/...
                    company_link = container.find('a', href=lambda href: href and '/jobs-at/' in href)
                    if company_link:
                        company = company_link.get_text(strip=True)
                    
                    # Date is often in a small tag or at the end
                    date_tag = container.find('li', class_='job-date') # Hypothetical class
                    if not date_tag:
                        # Try finding text that looks like a date
                        pass

                jobs.append({
                    'title': title,
                    'company': company,
                    'location': "Kenya", # Default
                    'link': job_url,
                    'source': 'MyJobMag',
                    'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            
            return jobs

        except Exception as e:
            print(f"Error scraping MyJobMag: {e}")
            return []
