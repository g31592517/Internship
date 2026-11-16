"""Location normalisation. Sites describe places as 'Nairobi', 'Westlands, Nairobi', 'Kenya',
'Remote', or hide them in tags like 'jobs-in-nakuru'. We map those to Kenyan counties so the
user's optional location can be matched consistently. Non-Kenyan places fall back to text match."""
import re

COUNTIES = [
    "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita Taveta", "Garissa", "Wajir", "Mandera",
    "Marsabit", "Isiolo", "Meru", "Tharaka Nithi", "Embu", "Kitui", "Machakos", "Makueni", "Nyandarua",
    "Nyeri", "Kirinyaga", "Murang'a", "Kiambu", "Turkana", "West Pokot", "Samburu", "Trans Nzoia",
    "Uasin Gishu", "Elgeyo Marakwet", "Nandi", "Baringo", "Laikipia", "Nakuru", "Narok", "Kajiado",
    "Kericho", "Bomet", "Kakamega", "Vihiga", "Bungoma", "Busia", "Siaya", "Kisumu", "Homa Bay",
    "Migori", "Kisii", "Nyamira", "Nairobi",
]

# Towns / neighbourhoods / spelling variants -> county
ALIASES = {
    "westlands": "Nairobi", "kilimani": "Nairobi", "karen": "Nairobi", "upper hill": "Nairobi",
    "cbd": "Nairobi", "industrial area": "Nairobi", "parklands": "Nairobi", "kasarani": "Nairobi",
    "embakasi": "Nairobi", "lavington": "Nairobi", "langata": "Nairobi", "ruaraka": "Nairobi",
    "thika": "Kiambu", "ruiru": "Kiambu", "juja": "Kiambu", "limuru": "Kiambu", "kikuyu": "Kiambu",
    "ngong": "Kajiado", "kitengela": "Kajiado", "rongai": "Kajiado", "athi river": "Machakos",
    "mlolongo": "Machakos", "naivasha": "Nakuru", "eldoret": "Uasin Gishu", "kitale": "Trans Nzoia",
    "malindi": "Kilifi", "watamu": "Kilifi", "diani": "Kwale", "ukunda": "Kwale", "voi": "Taita Taveta",
    "kapsabet": "Nandi", "kabarnet": "Baringo", "nanyuki": "Laikipia", "kisumu city": "Kisumu",
    "murang a": "Murang'a", "muranga": "Murang'a", "tharaka-nithi": "Tharaka Nithi",
    "taita-taveta": "Taita Taveta", "trans-nzoia": "Trans Nzoia", "uasin-gishu": "Uasin Gishu",
    "elgeyo-marakwet": "Elgeyo Marakwet", "west-pokot": "West Pokot", "homabay": "Homa Bay",
    "tana-river": "Tana River", "bondo": "Siaya", "mumias": "Kakamega", "webuye": "Bungoma",
    "nyahururu": "Laikipia", "kericho town": "Kericho", "lodwar": "Turkana", "kakuma": "Turkana",
    "dadaab": "Garissa", "isebania": "Migori", "oyugis": "Homa Bay", "ol kalou": "Nyandarua",
}

_NATIONWIDE = re.compile(r"^(kenya|nationwide|countrywide|all counties|multiple( locations)?|various|n/?a)?$", re.I)
_REMOTE = re.compile(r"\b(remote|work from home|wfh|hybrid|virtual)\b", re.I)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9']+", " ", s.lower().replace("-", " ")).strip()


_COUNTY_KEYS = {_slug(c): c for c in COUNTIES}
_COUNTY_KEYS.update({_slug(k): v for k, v in ALIASES.items()})
# Longest keys first so 'trans nzoia' wins over 'nzoia', 'homa bay' over 'bay'.
_KEYS_SORTED = sorted(_COUNTY_KEYS, key=len, reverse=True)
_KEY_RX = re.compile(r"(?<![a-z])(" + "|".join(re.escape(k) for k in _KEYS_SORTED) + r")(?![a-z])")


def find_counties(text: str) -> list[str]:
    """All Kenyan counties mentioned in free text (order of appearance, unique)."""
    if not text:
        return []
    found: list[str] = []
    for m in _KEY_RX.finditer(_slug(text)):
        county = _COUNTY_KEYS[m.group(1)]
        if county not in found:
            found.append(county)
    return found


def is_remote(text: str) -> bool:
    return bool(text and _REMOTE.search(text))


def resolve_user_location(text: str) -> str | None:
    """User typed 'Westlands' / 'nakuru' / 'Nairobi County' -> canonical county, else None."""
    cleaned = re.sub(r"\bcounty\b", "", text or "", flags=re.I)
    found = find_counties(cleaned)
    return found[0] if found else None


def display_location(raw: str, counties: list[str]) -> str:
    raw = re.sub(r"\s+", " ", (raw or "")).strip(" ,-|")
    if raw and not _NATIONWIDE.match(raw):
        return raw
    if counties:
        return ", ".join(counties)
    return raw or ""


def match_location(user_text: str, location_text: str, counties: list[str], remote: bool) -> str | None:
    """Return 'exact', 'unspecified' (could apply anywhere / site didn't say) or None (different place)."""
    user_text = (user_text or "").strip()
    if not user_text:
        return "exact"
    wanted = resolve_user_location(user_text)
    if wanted:
        if wanted in counties:
            return "exact"
    elif _slug(user_text) and _slug(user_text) in _slug(location_text or ""):
        return "exact"
    if not counties and (not location_text or _NATIONWIDE.match(location_text.strip()) or remote):
        return "unspecified"
    return None
