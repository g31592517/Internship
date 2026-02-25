import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

ua = UserAgent()
headers = {'User-Agent': ua.random}

urls = [
    "https://mnu.ac.ke/contact-us/",
    "https://mnu.ac.ke/vision-mission/",
    "https://mnu.ac.ke/undergraduate-courses-2/",
    "https://sbeh.mnu.ac.ke/our-programs/",
    "https://mnu.ac.ke/academic-programmes/"
]

for url in urls:
    print(f"--- Fetching {url} ---")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            print(text[:2000]) # Print first 2000 chars to see what we got
            
            # Simple search for keywords
            if "Public Policy" in text:
                print("\n*** FOUND 'Public Policy' in text! ***\n")
            if "Motto" in text:
                print("\n*** FOUND 'Motto' in text! ***\n")
        else:
            print(f"Failed with status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    print("\n\n")
