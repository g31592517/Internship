"""All sources the platform knows about. To add a website: write an adapter, add it to SOURCES."""
from scrapers.brightermonday import BrighterMondayScraper
from scrapers.careerjet import CareerJetScraper
from scrapers.careerpointkenya import CareerPointKenyaScraper
from scrapers.corporate_staffing import CorporateStaffingScraper
from scrapers.fuzu import FuzuScraper
from scrapers.banking.kcb import KCBScraper
from scrapers.big_tech.microsoft import MicrosoftScraper
from scrapers.myjobmag import MyJobMagScraper

# Order matters only for display. Disabled adapters (enabled = False) are listed but never run.
SOURCE_CLASSES = [
    MyJobMagScraper,
    CorporateStaffingScraper,
    CareerPointKenyaScraper,
    BrighterMondayScraper,
    CareerJetScraper,
    FuzuScraper,
    MicrosoftScraper,
    KCBScraper,
]


def source_info() -> list[dict]:
    return [{"name": c.name, "enabled": c.enabled, "reason": c.disabled_reason} for c in SOURCE_CLASSES]


def active_sources() -> list:
    return [c() for c in SOURCE_CLASSES if c.enabled]
