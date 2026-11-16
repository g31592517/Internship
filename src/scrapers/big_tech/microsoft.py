import requests
from datetime import datetime

class MicrosoftScraper:
    # Legacy adapter kept from the original project; not used by the web app until fixed.
    name = "Microsoft Careers"
    enabled = False
    disabled_reason = "The old careers API host fails TLS verification / returns 404; needs the current careers API."

    def __init__(self):
        self.api_url = "https://gcsservices.careers.microsoft.com/search/api/v1/search"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Origin': 'https://jobs.careers.microsoft.com',
            'Referer': 'https://jobs.careers.microsoft.com/',
            'Accept': 'application/json, text/plain, */*',
            'x-service-name': 'gcs-search'
        }

    def scrape(self, query="internship", location="Kenya"):
        print(f"Scraping Microsoft Careers for {query} in {location}...")
        
        # Microsoft's API parameters
        params = {
            "q": query,
            "l": "en_us", 
            "lc": "Kenya", # Simplified location
            "p": 1, 
            "pg": 20
        }
        
        try:
            response = requests.get(self.api_url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            jobs = []
            
            if 'operationResult' in data and 'result' in data['operationResult']:
                results = data['operationResult']['result']['jobs']
                
                for job in results:
                    title = job.get('title')
                    job_id = job.get('jobId')
                    # Construct link
                    link = f"https://jobs.careers.microsoft.com/global/en/job/{job_id}"
                    
                    jobs.append({
                        'title': title,
                        'company': "Microsoft",
                        'location': "Nairobi, Kenya",
                        'link': link,
                        'source': "Microsoft Careers",
                        'scraped_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            return jobs

        except Exception as e:
            print(f"Error scraping Microsoft: {e}")
            return []
