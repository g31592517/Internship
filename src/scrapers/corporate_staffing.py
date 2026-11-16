from scrapers.wordpress import WordPressSource


class CorporateStaffingScraper(WordPressSource):
    """Corporate Staffing Services (WordPress). Parsing moved into the shared WordPressSource;
    the original behaviour (search `/?s=` -> article > h2 > a) is unchanged."""
    name = "Corporate Staffing"
    base_url = "https://www.corporatestaffing.co.ke"
