"""Normalisation: raw dicts from any scraper -> Opportunity.

Raw dict contract (the original scrapers' keys, plus optional extras):
  required : title, link, source
  original : company, location, scraped_at
  optional : description, snippet, deadline (text/date), posted (text), field_label, tags (list),
             requirements (list), apply_url, apply_email, opportunity_type
Everything optional may be missing; normalisation never raises on a sparse record."""
import hashlib
import html
import re
import unicodedata
from datetime import date, datetime
from urllib.parse import urlsplit, urlunsplit

from .dates import find_deadline, parse_date
from .fields import infer_field, map_site_field
from .locations import display_location, find_counties, is_remote
from .model import Opportunity

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
# Site/support addresses that are not the employer's application inbox.
_EMAIL_BLOCK = re.compile(r"(myjobmag|corporatestaffing|careerpointkenya|brightermonday|careerjet|fuzu|"
                          r"example\.|noreply|no-reply|donotreply|sentry|wixpress|gmail\.com\.|@\d)", re.I)
STALE_DAYS = 180
_UNKNOWN = {"", "unknown", "n/a", "na", "none", "-", "confidential"}
_REQ_HEAD = re.compile(r"^\s*(?:key\s+)?(requirements?|qualifications?|minimum\s+qualifications?|"
                       r"who\s+(?:can\s+apply|we(?:'re| are)\s+looking\s+for)|eligibility|"
                       r"skills(?:\s+and\s+experience)?|required\s+skills(?:\s+and\s+experience)?|"
                       r"person\s+specification|what\s+you(?:'ll)?\s+need)\b[^\n]{0,30}:?\s*$", re.I)
_OTHER_HEAD = re.compile(r"^\s*(responsibilit|duties|how\s+to\s+apply|method\s+of\s+application|about|job\s+summary|"
                         r"benefits|key\s+responsib|description|overview|deadline|location|what\s+we\s+offer)", re.I)
_TYPE_RX = [
    (re.compile(r"\battach(?:é|e|ment)s?\b", re.I), "Attachment"),
    (re.compile(r"\bgraduate\s+(trainee|programme|program)|\bmanagement\s+trainee|\btrainee", re.I), "Graduate Trainee"),
    (re.compile(r"\bapprentice", re.I), "Apprenticeship"),
    (re.compile(r"\bintern(s|ship|ships)?\b", re.I), "Internship"),
]


def clean_text(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", html.unescape(str(s))).replace("�", "-").replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n\s*\n+", "\n\n", s)
    return s.strip()


def canonical_url(url: str) -> str:
    p = urlsplit((url or "").strip())
    path = p.path.rstrip("/") or "/"
    return urlunsplit((p.scheme.lower() or "https", p.netloc.lower().removeprefix("www."), path, p.query, ""))


def make_id(url: str) -> str:
    return hashlib.sha1(canonical_url(url).encode()).hexdigest()[:12]


_TLDS = {"com", "org", "net", "ke", "co", "ac", "go", "or", "ne", "info", "edu", "gov", "int", "io", "africa",
         "uk", "us", "ug", "tz", "rw", "et", "za", "ng", "gh", "biz", "me", "dev", "app", "tech", "ngo"}


def clean_email(addr: str) -> str:
    """Repair addresses glued to the next word in page text: 'jobs@rvibs.ac.keSubject' -> 'jobs@rvibs.ac.ke',
    'hr@acme.comdeadline' -> 'hr@acme.com'. Returns '' if it still doesn't look like an address."""
    addr = (addr or "").strip().rstrip(".")
    local, _, domain = addr.partition("@")
    labels = domain.split(".")
    if not local or len(labels) < 2:
        return ""
    last = re.split(r"(?<=[a-z])(?=[A-Z])", labels[-1])[0].lower()   # cut at a camelCase join
    if last not in _TLDS:
        last = next((t for t in sorted(_TLDS, key=len, reverse=True) if last.startswith(t)), last)
    labels[-1] = last
    out = f"{local}@{'.'.join(labels).lower()}"
    return out if _EMAIL.fullmatch(out) else ""


def extract_email(text: str) -> str:
    for m in _EMAIL.finditer(text or ""):
        if not _EMAIL_BLOCK.search(m.group(0)):
            addr = clean_email(m.group(0))
            if addr:
                return addr
    return ""


def extract_requirements(text: str, limit: int = 12) -> list[str]:
    """Pull the bullet lines under a Requirements/Qualifications style heading."""
    lines = [ln.strip(" \t•·▪‣-*–") for ln in (text or "").splitlines()]
    out: list[str] = []
    capturing = False
    for ln in lines:
        if not ln:
            if capturing and out:
                break
            continue
        if _REQ_HEAD.match(ln):
            capturing = True
            continue
        if capturing:
            if _OTHER_HEAD.match(ln) and len(ln) < 60:
                break
            if 8 <= len(ln) <= 300:
                out.append(ln)
            if len(out) >= limit:
                break
    return out


def _as_date(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return parse_date(str(v), future=True) if v else None


def opportunity_type(title: str, tags: list[str]) -> str:
    blob = f"{title} {' '.join(tags)}"
    for rx, label in _TYPE_RX:
        if rx.search(title):
            return label
    for rx, label in _TYPE_RX:
        if rx.search(blob):
            return label
    return "Internship"


def normalize(raw: dict, today: date | None = None) -> Opportunity:
    today = today or date.today()
    title = clean_text(raw.get("title")) or "Untitled opportunity"
    tags = [clean_text(t) for t in (raw.get("tags") or []) if t]
    org = clean_text(raw.get("company") or raw.get("organization"))
    org = "" if org.lower() in _UNKNOWN else org

    description = clean_text(raw.get("description")) or clean_text(raw.get("snippet"))
    blob = f"{title}\n{description}"

    # --- location: explicit text first, then tags, then a 'Location:' line in the ad ---
    loc_text = clean_text(raw.get("location"))
    counties = find_counties(loc_text)
    if not counties:
        counties = find_counties(" ".join(tags))
    if not counties:
        m = re.search(r"(?im)^\s*(?:job\s+)?location\s*[:\-]\s*([^\n:]{2,80})$", description)
        if m:
            counties = find_counties(m.group(1))
            if counties and (not loc_text or loc_text.lower() == "kenya"):
                loc_text = m.group(1).strip()
    if not counties:
        counties = find_counties(title)
    remote = is_remote(f"{loc_text} {title}") or is_remote(" ".join(tags))

    # --- dates ---
    deadline = _as_date(raw.get("deadline")) or find_deadline(description, today)
    posted = parse_date(str(raw.get("posted") or ""), today, future=False)

    # --- apply info ---
    apply_email = clean_email(raw.get("apply_email") or "") or extract_email(description)
    apply_url = (raw.get("apply_url") or "").strip()
    url = (raw.get("link") or raw.get("url") or "").strip()

    requirements = [clean_text(r) for r in (raw.get("requirements") or []) if r] or extract_requirements(description)

    field = map_site_field(raw.get("field_label") or "") or infer_field(title, description)
    summary = re.sub(r"\s+", " ", description)[:280].strip()
    if len(description) > 280:
        summary = summary.rsplit(" ", 1)[0] + "…"

    return Opportunity(
        id=make_id(url or title),
        title=title,
        organization=org,
        opportunity_type=raw.get("opportunity_type") or opportunity_type(title, tags),
        field=field,
        location=display_location(loc_text, counties),
        counties=counties,
        remote=remote,
        deadline=deadline,
        posted_date=posted,
        summary=summary,
        description=description[:8000],
        requirements=requirements,
        source=raw.get("source") or "Unknown",
        url=url,
        apply_url=apply_url,
        apply_email=apply_email,
        apply_method="email" if apply_email else "link",
        tags=tags,
        link_status=raw.get("link_status") or "unknown",
        # No deadline + posted long ago: almost certainly filled/closed, so treat it as expired.
        expired=bool((deadline and deadline < today) or (not deadline and posted and (today - posted).days > STALE_DAYS)),
        scraped_at=_scraped_at(raw.get("scraped_at")),
    )


def _scraped_at(v) -> datetime:
    if isinstance(v, datetime):
        return v
    try:
        return datetime.strptime(str(v), "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return datetime.now()
