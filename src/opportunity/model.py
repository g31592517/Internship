"""The one Opportunity shape every source is normalised into."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class AlsoOn(BaseModel):
    source: str
    url: str


class Opportunity(BaseModel):
    id: str
    title: str
    organization: str = ""
    opportunity_type: str = "Internship"        # Internship | Attachment | Graduate Trainee | ...
    field: str = ""                              # normalised course/field label
    location: str = ""                           # display text
    counties: list[str] = Field(default_factory=list)
    remote: bool = False
    deadline: date | None = None
    posted_date: date | None = None
    summary: str = ""                            # short description for cards
    description: str = ""                        # full text for the detail view
    requirements: list[str] = Field(default_factory=list)
    source: str                                  # source website name
    url: str                                     # original posting
    apply_url: str = ""                          # where to apply, when different from url
    apply_email: str = ""
    apply_method: Literal["email", "link"] = "link"
    tags: list[str] = Field(default_factory=list)
    link_status: Literal["ok", "unknown", "broken"] = "unknown"
    expired: bool = False
    also_on: list[AlsoOn] = Field(default_factory=list)   # same ad found on other sources
    scraped_at: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def can_auto_apply(self) -> bool:
        return bool(self.apply_email) and not self.expired


class SearchHit(Opportunity):
    """An Opportunity plus the per-search computed fields."""
    relevance: float = 0
    location_match: Literal["exact", "unspecified"] = "exact"
