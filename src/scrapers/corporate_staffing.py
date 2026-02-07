import requests
from bs4 import BeautifulSoup
from datetime import datetime

class CorporateStaffingScraper:
    def __init__(self):
        self.base_url = "https://www.corporatestaffing.co.ke"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def scrape(self, query="internship", location="Kenya"):
        url = f"{self.base_url}/?s={query}"
        print(f"Scraping Corporate Staffing: {url}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            jobs = []
            
            # Based on inspection, jobs are usually in articles or divs with class 'post' or similar structure
            # The search results often have titles in h2 or h3
            
            # Find all articles/divs that look like search results
            # Common pattern in WordPress sites (which this seems to be)
            articles = soup.find_all('article')
            
            if not articles:
                # Fallback to generic search for h2 links if articles aren't found
                articles = soup.find_all('div', class_='post') # Another common WP class

            for article in articles:
                title_tag = article.find('h2') or article.find('h3')
                if not title_tag:
                    continue
                
                link_tag = title_tag.find('a')
                if not link_tag:
                    continue

                title = link_tag.get_text(strip=True)
                job_url = link_tag['href']
                
                # Filter for "intern" in title if needed, but since we searched for it, it should be relevant.
                # Only skipping if it's clearly not a job (ads, etc)
                
                # Check for date
                date_tag = article.find('time')
                posted_date = date_tag.get_text(strip=True) if date_tag else "Unknown"

                # Check for excerpt / description
                excerpt_tag = article.find('div', class_='entry-summary') or article.find('div', class_='entry-content')
                description = excerpt_tag.get_text(strip=True)[:200] + "..." if excerpt_tag else ""

                jobs.append({
                    'title': title,
                    'company': "Corporate Staffing (Recruiter)", # Usually they are the recruiter
                    'location': "Kenya", # Defaults to Kenya
                    'link': job_url,
                    'source': 'Corporate Staffing',
                    'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            
            return jobs

        except Exception as e:
            print(f"Error scraping Corporate Staffing: {e}")
            return []
