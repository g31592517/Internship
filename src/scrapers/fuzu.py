import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

class FuzuScraper:
    def __init__(self):
        self.base_url = "https://www.fuzu.com"
        # Fuzu has strict bot protection (Cloudflare). 
        # Using a more realistic user agent might help, but often fails without a headless browser.
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/'
        }

    def scrape(self, query="internship", location="Kenya"):
        url = f"{self.base_url}/kenya/search?q={query}"
        print(f"Scraping Fuzu: {url}")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 403:
                print("Fuzu returned 403 Forbidden (likely Cloudflare protection). Skipping Fuzu.")
                return []
                
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            jobs = []
            
            # Fuzu structure is complex and React-based often, but let's try to find job cards.
            # Classes like 'JobCard', 'job-card-container' are common.
            # If standard classes fail, we look for links containing '/jobs/'
            
            job_links = soup.find_all('a', href=lambda href: href and '/jobs/' in href)
            
            seen_urls = set()
            
            for link in job_links:
                href = link['href']
                if not href.startswith('http'):
                    job_url = self.base_url + href
                else:
                    job_url = href
                    
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)
                
                # Try to get title from text inside the link or a child div
                title = link.get_text(strip=True)
                if not title or len(title) < 5: # Skip likely icons or "Apply" buttons
                    # Try finding a title container
                    # This is speculative as we can't see the live DOM
                    continue
                
                jobs.append({
                    'title': title,
                    'company': "Unknown", 
                    'location': "Kenya",
                    'link': job_url,
                    'source': 'Fuzu',
                    'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
            return jobs

        except Exception as e:
            print(f"Error scraping Fuzu: {e}")
            return []
