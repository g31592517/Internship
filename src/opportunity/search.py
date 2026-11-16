"""Search layer: decides what is an internship-type ad, how well it fits the student's course,
removes duplicates and applies the optional filters. Works only on normalised Opportunity objects,
so it knows nothing about any particular website."""
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher

from .fields import STOPWORDS, WEAK_TOKENS, course_fields, related_keywords, significant_tokens, tokens
from .locations import match_location
from .model import AlsoOn, Opportunity, SearchHit

MIN_RELEVANCE = 2.0

_INTERNSHIP_RX = re.compile(
    r"\b(intern|interns|internship|internships|attach[eé]e?s?|attachment|attachments|trainee|trainees|"
    r"apprentice|apprentices|apprenticeship|industrial\s+(?:training|attachment)|graduate\s+(?:programme|program|scheme)|"
    r"work[\s-]?study|placement)\b", re.I)
_DEGREE_PREFIX = [
    re.compile(r"^(?:bachelor|master|diploma|certificate|degree)s?\s+(?:of|in)\s+(?:science|arts|commerce|technology)?\s*(?:in|of)?\s*"),
    re.compile(r"^(?:bsc|ba|bcom|msc|ma|hnd|phd|btech)\.?\s+(?:in\s+)?"),
]


def is_internship_like(o: Opportunity) -> bool:
    return bool(_INTERNSHIP_RX.search(o.title) or _INTERNSHIP_RX.search(" ".join(o.tags)))


# ---------------------------------------------------------------- course matching
@dataclass
class CourseQuery:
    raw: str
    phrase: str
    strong: list[str] = field(default_factory=list)
    weak: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)

    @classmethod
    def parse(cls, course: str) -> "CourseQuery":
        low = " ".join(tokens(course))
        for rx in _DEGREE_PREFIX:
            low = rx.sub("", low).strip()
        toks = significant_tokens(low) or significant_tokens(course)
        strong = [t for t in toks if t not in WEAK_TOKENS]
        weak = [t for t in toks if t in WEAK_TOKENS]
        rel = [k for k in related_keywords(low) if k not in toks]
        return cls(raw=course.strip(), phrase=low, strong=strong, weak=weak, related=rel, fields=course_fields(low))


def _has(text: str, word: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(word)}(?:s|es)?(?![a-z0-9])", text) is not None


def relevance(o: Opportunity, q: CourseQuery) -> float:
    title = o.title.lower()
    tags = " ".join(o.tags).lower()
    desc = f"{o.summary} {o.description[:1500]}".lower()
    s = 0.0
    if q.phrase and len(q.phrase.split()) > 1:
        if q.phrase in title:
            s += 6
        elif q.phrase in tags or q.phrase in desc:
            s += 3
    s += min(4, 2 * sum(_has(title, t) for t in q.strong))
    s += min(2, 1 * sum(_has(title, t) for t in q.weak))
    s += min(2, sum(_has(tags, t) for t in q.strong + q.weak))
    s += min(2, sum(_has(desc, t) for t in q.strong))
    s += min(4, 2 * sum(_has(title, k) for k in q.related))
    s += min(1, sum(_has(desc, k) for k in q.related))
    if o.field and o.field in q.fields:
        s += 2
    if q.phrase and len(q.phrase.split()) == 1 and _has(title, q.phrase) and q.phrase in q.weak:
        s += 1
    return round(s, 1)


# ---------------------------------------------------------------- de-duplication
_NOISE = re.compile(r"\b(job|jobs|vacancy|vacancies|opportunity|opportunities|kenya|nairobi|ltd|limited|the|at|a|an|for|and|of|in)\b")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", _NOISE.sub(" ", re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()))).strip()


def _richness(o: Opportunity) -> int:
    return (len(o.description) // 20 + (40 if o.apply_email else 0) + (30 if o.deadline else 0)
            + (20 if o.requirements else 0) + (10 if o.organization else 0) + (10 if o.location else 0))


def _same_ad(a: Opportunity, b: Opportunity) -> bool:
    if a.id == b.id:
        return True
    ta, tb = _norm(a.title), _norm(b.title)
    if not ta or not tb:
        return False
    oa, ob = _norm(a.organization), _norm(b.organization)
    sim = SequenceMatcher(None, ta, tb).ratio()
    if oa and ob:
        return (oa == ob or oa in ob or ob in oa) and sim >= 0.85
    return sim >= 0.95 or (sim >= 0.85 and (oa and oa in tb or ob and ob in ta))


def dedupe(opps: list[Opportunity]) -> list[Opportunity]:
    """Merge the same ad seen on several sources (or several queries) into one richer record."""
    buckets: dict[str, list[list[Opportunity]]] = defaultdict(list)
    groups: list[list[Opportunity]] = []
    for o in opps:
        key = (_norm(o.title).split() or [""])[0]
        for g in buckets[key]:
            if _same_ad(g[0], o):
                g.append(o)
                break
        else:
            g = [o]
            buckets[key].append(g)
            groups.append(g)

    merged: list[Opportunity] = []
    for g in groups:
        g.sort(key=_richness, reverse=True)
        best = g[0].model_copy(deep=True)
        for other in g[1:]:
            if other.url != best.url and not any(x.url == other.url for x in best.also_on):
                best.also_on.append(AlsoOn(source=other.source, url=other.url))
            for attr in ("organization", "location", "field", "deadline", "posted_date", "apply_email", "apply_url"):
                if not getattr(best, attr) and getattr(other, attr):
                    setattr(best, attr, getattr(other, attr))
            if not best.counties and other.counties:
                best.counties = list(other.counties)
            if not best.requirements and other.requirements:
                best.requirements = list(other.requirements)
        best.apply_method = "email" if best.apply_email else "link"
        merged.append(best)
    return merged


# ---------------------------------------------------------------- ranking + filters
def rank(opps: list[Opportunity], course: str, *, today: date | None = None) -> list[tuple[Opportunity, float]]:
    """Internship-type ads relevant to the course, best first. Location is NOT considered here
    so the (expensive) scraped pool can be reused for any location."""
    q = CourseQuery.parse(course)
    scored = []
    for o in opps:
        if not is_internship_like(o):
            continue
        r = relevance(o, q)
        if r >= MIN_RELEVANCE:
            scored.append((o, r))
    scored.sort(key=lambda t: (-t[1], t[0].deadline or date.max))
    return scored


def apply_filters(
    ranked: list[tuple[Opportunity, float]],
    *,
    location: str = "",
    strict_location: bool = False,
    organization: str = "",
    field_: str = "",
    deadline_before: date | None = None,
    include_expired: bool = False,
    drop_broken: bool = True,
) -> list[SearchHit]:
    hits: list[SearchHit] = []
    org_l = organization.strip().lower()
    for o, r in ranked:
        if o.expired and not include_expired:
            continue
        if drop_broken and o.link_status == "broken":
            continue
        loc = match_location(location, o.location, o.counties, o.remote)
        if loc is None or (strict_location and loc != "exact"):
            continue
        if org_l and org_l not in o.organization.lower():
            continue
        if field_ and o.field.lower() != field_.strip().lower():
            continue
        if deadline_before and o.deadline and o.deadline > deadline_before:
            continue
        hits.append(SearchHit(**o.model_dump(exclude={"can_auto_apply"}), relevance=r, location_match=loc))
    # exact location matches first when a location was asked for
    if location.strip():
        hits.sort(key=lambda h: (h.location_match != "exact", -h.relevance))
    return hits
