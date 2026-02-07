import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

class CareerJetScraper:
    def __init__(self):
        self.base_url = "https://www.careerjet.co.ke"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def scrape(self, query="internship", location="Kenya"):
        url = f"{self.base_url}/jobs?s={query}&l={location}"
        print(f"Scraping CareerJet: {url}")
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            jobs = []
            # CareerJet often uses article tags for job cards. 
            # If not, we can look for specific classes.
            # Based on inspection, we look for job containers.
            
            # Strategy: Find all 'a' tags with href containing '/jobad/' which are title links
            job_links = soup.find_all('a', href=lambda href: href and '/jobad/' in href)
            
            seen_urls = set()

            for link in job_links:
                job_url = self.base_url + link['href']
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                title = link.get_text(strip=True)
                
                # Find the container to extract company and location
                # Usually the link is inside a container. We go up parents to find relevant info.
                # Simplistic approach: just get title and url for now, maybe location if close by.
                
                # Try to find parent article or div.job
                container = link.find_parent('article')
                if not container:
                    container = link.find_parent('div', class_='job') # fallback
                
                company = "Unknown"
                location_text = "Unknown"
                posted_date = "Unknown"

                if container:
                    # Attempt to find company
                    company_tag = container.find('p', class_='company')
                    if company_tag:
                        company = company_tag.get_text(strip=True)
                    
                    # Attempt to find location
                    location_tag = container.find('ul', class_='location') # sometimes ul
                    if not location_tag:
                         location_tag = container.find('div', class_='locations')
                    
                    if location_tag:
                        location_text = location_tag.get_text(strip=True)
                        
                    # Attempt to find date
                    date_tag = container.find('div', class_='locations_compact') # often date is here or distinct
                    if not date_tag:
                         date_tag = container.find('span', class_='badge-time') # sometimes

                jobs.append({
                    'title': title,
                    'company': company,
                    'location': location_text,
                    'link': job_url,
                    'source': 'CareerJet',
                    'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
            return jobs

        except Exception as e:
            print(f"Error scraping CareerJet: {e}")
            return []
