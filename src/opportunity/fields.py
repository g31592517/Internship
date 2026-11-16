"""Course / field knowledge. A student's course ('BSc Software Engineering') is mapped to the broad
field(s) it belongs to, which gives us related keywords to match opportunities against. Courses we
do not know still work: their own words are matched directly (see search.py)."""
import re

STOPWORDS = {
    "a", "an", "and", "the", "of", "in", "for", "to", "with", "at", "on", "bachelor", "bachelors",
    "degree", "diploma", "certificate", "master", "masters", "bsc", "ba", "bcom", "msc", "ma", "phd",
    "hnd", "b", "sc", "science", "arts", "studies", "applied", "general", "course", "program",
    "programme", "student", "year", "internship", "intern", "attachment", "industrial", "trainee",
}
# Words that appear in many unrelated ads; they count for less on their own.
WEAK_TOKENS = {"engineering", "management", "technology", "business", "services", "development",
               "systems", "administration", "design", "applied", "social", "public", "health"}

# field -> (course aliases, ad keywords). Aliases decide which field a course belongs to;
# keywords are what we look for in titles/descriptions. Keep keywords specific.
FIELDS: dict[str, dict[str, list[str]]] = {
    "ICT & Computing": {
        "aliases": ["software engineering", "computer science", "information technology", "information systems",
                    "informatics", "computing", "cyber security", "cybersecurity", "data science",
                    "computer engineering", "computer technology", "ict", "bit", "networking", "web development",
                    "artificial intelligence", "machine learning"],
        "keywords": ["software", "developer", "programmer", "programming", "web", "mobile app", "frontend",
                     "backend", "full stack", "fullstack", "devops", "cloud", "network", "cyber", "security analyst",
                     "data analyst", "data science", "data engineer", "machine learning", "database", "ict",
                     "information technology", "it support", "technical support", "systems", "qa", "tester",
                     "computer", "ui/ux", "digital"],
    },
    "Engineering": {
        "aliases": ["electrical engineering", "electronic engineering", "mechanical engineering", "civil engineering",
                    "mechatronics", "chemical engineering", "industrial engineering", "telecommunication",
                    "electrical and electronic", "engineering", "construction", "quantity surveying", "architecture",
                    "geospatial", "geomatics", "surveying", "building technology"],
        "keywords": ["engineer", "engineering", "electrical", "electronics", "mechanical", "civil", "mechatronics",
                     "technician", "maintenance", "construction", "site", "power", "telecom", "surveyor", "cad",
                     "architect", "plant"],
    },
    "Business & Management": {
        "aliases": ["business administration", "business management", "commerce", "entrepreneurship",
                    "human resource", "procurement", "supply chain", "logistics", "marketing", "project management",
                    "public administration", "public policy", "international relations", "business information"],
        "keywords": ["business", "administration", "administrative", "operations", "human resource", "hr",
                     "procurement", "supply chain", "logistics", "marketing", "sales", "project", "policy",
                     "office", "customer", "management trainee", "corporate", "public affairs", "governance"],
    },
    "Finance & Accounting": {
        "aliases": ["accounting", "accountancy", "finance", "banking", "actuarial", "economics", "statistics",
                    "financial engineering", "insurance", "audit"],
        "keywords": ["finance", "financial", "accounts", "accounting", "accountant", "audit", "tax", "banking",
                     "treasury", "credit", "risk", "insurance", "economist", "economics", "statistician",
                     "bookkeeping", "payroll"],
    },
    "Health & Medicine": {
        "aliases": ["nursing", "medicine", "clinical medicine", "pharmacy", "public health", "medical laboratory",
                    "nutrition", "dental", "physiotherapy", "health records", "biomedical"],
        "keywords": ["nurse", "nursing", "clinical", "medical", "pharmacy", "pharmacist", "laboratory", "public health",
                     "health", "nutrition", "dental", "physiotherapy", "hospital", "patient", "community health"],
    },
    "Education": {
        "aliases": ["education", "teaching", "early childhood", "curriculum"],
        "keywords": ["teacher", "teaching", "tutor", "education", "curriculum", "lecturer", "school", "training"],
    },
    "Agriculture & Environment": {
        "aliases": ["agriculture", "agribusiness", "horticulture", "environmental science", "environment",
                    "forestry", "food science", "animal science", "veterinary", "natural resource", "water engineering"],
        "keywords": ["agri", "agriculture", "farm", "horticulture", "environment", "environmental", "forestry",
                     "food", "veterinary", "livestock", "crop", "climate", "water", "conservation", "natural resource"],
    },
    "Law & Governance": {
        "aliases": ["law", "legal", "criminology", "security studies"],
        "keywords": ["legal", "law", "advocate", "paralegal", "compliance", "contracts", "litigation", "court"],
    },
    "Media & Creative": {
        "aliases": ["journalism", "mass communication", "communication", "public relations", "media", "film",
                    "graphic design", "creative", "fashion", "interior design"],
        "keywords": ["journalist", "journalism", "content", "communications", "media", "public relations", "pr",
                     "graphic", "designer", "video", "social media", "editor", "writer", "photography", "brand"],
    },
    "Hospitality & Tourism": {
        "aliases": ["hospitality", "tourism", "travel", "catering", "hotel management", "events management"],
        "keywords": ["hotel", "hospitality", "tourism", "travel", "restaurant", "front office", "housekeeping",
                     "chef", "kitchen", "events", "guest"],
    },
    "Science & Research": {
        "aliases": ["biology", "chemistry", "physics", "mathematics", "biochemistry", "biotechnology", "microbiology",
                    "geology", "actuarial science", "applied science", "laboratory"],
        "keywords": ["research", "laboratory", "scientist", "chemist", "biologist", "microbiology", "biotechnology",
                     "geologist", "analyst", "field officer", "statistics", "monitoring and evaluation", "m&e"],
    },
    "Social Sciences & Development": {
        "aliases": ["sociology", "social work", "community development", "psychology", "development studies",
                    "gender", "counselling", "peace"],
        "keywords": ["community", "social", "programme", "program", "ngo", "development", "psychosocial",
                     "counsellor", "gender", "protection", "humanitarian", "livelihood", "monitoring and evaluation"],
    },
}

# Site category strings (MyJobMag 'Job Field', WP categories) -> our field label
SITE_FIELD_MAP = [
    (r"ict|computer|software|it\b|information tech|data", "ICT & Computing"),
    (r"engineering|technician|construction|architect|survey", "Engineering"),
    (r"bank|financ|account|audit|insurance|econom", "Finance & Accounting"),
    (r"health|medic|nurs|pharma|clinic|hospital", "Health & Medicine"),
    (r"educat|teach|train", "Education"),
    (r"agri|environment|forest|food|veterin", "Agriculture & Environment"),
    (r"law|legal|compliance", "Law & Governance"),
    (r"media|journal|communicat|creative|design|marketing|advert|public relations", "Media & Creative"),
    (r"hotel|hospitality|tourism|travel|catering", "Hospitality & Tourism"),
    (r"scien|research|laborator", "Science & Research"),
    (r"ngo|social|community|development|humanitarian|non.?profit", "Social Sciences & Development"),
    (r"admin|business|management|human resource|procurement|supply|logistic|sales|customer|secretar|office|operations",
     "Business & Management"),
]


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9+#&']+", (text or "").lower())]


def significant_tokens(course: str) -> list[str]:
    return [t for t in tokens(course) if t not in STOPWORDS and len(t) > 1]


def _alias_hit(course_l: str, alias: str) -> bool:
    return re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", course_l) is not None


def course_fields(course: str) -> list[str]:
    """Which broad fields does this course belong to? Longest alias phrase wins."""
    course_l = " ".join(tokens(course))
    scored: list[tuple[int, str]] = []
    for name, spec in FIELDS.items():
        best = max((len(a.split()) * 10 + len(a) / 100 for a in spec["aliases"] if _alias_hit(course_l, a)), default=0)
        if best:
            scored.append((best, name))
    if not scored:
        return []
    top = max(s for s, _ in scored)
    # keep the best, plus anything that matched an alias of equal strength
    return [name for s, name in sorted(scored, reverse=True) if s >= top - 0.5]


def related_keywords(course: str) -> list[str]:
    seen: list[str] = []
    for name in course_fields(course):
        for k in FIELDS[name]["keywords"]:
            if k not in seen:
                seen.append(k)
    return seen


def map_site_field(label: str) -> str:
    """Normalise a site's own category label ('ICT / Computer', 'Banking') to one of our fields."""
    label_l = (label or "").lower()
    if not label_l.strip():
        return ""
    for rx, name in SITE_FIELD_MAP:
        if re.search(rx, label_l):
            return name
    return label.strip().title()


def infer_field(title: str, text: str = "") -> str:
    """Guess the field from the ad itself when the site gives no category."""
    blob = f"{title} {title} {text[:600]}".lower()
    best, best_n = "", 0
    for name, spec in FIELDS.items():
        n = sum(1 for k in spec["keywords"] if re.search(rf"(?<![a-z]){re.escape(k)}(?![a-z])", blob))
        if n > best_n:
            best, best_n = name, n
    return best if best_n >= 1 else ""
