from scrapers.wordpress import WordPressSource


class CareerPointKenyaScraper(WordPressSource):
    """Career Point Kenya: same WordPress theme as Corporate Staffing, so only config is needed."""
    name = "Career Point Kenya"
    base_url = "https://www.careerpointkenya.co.ke"
