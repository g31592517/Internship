"""Date helpers: pull deadlines / posted dates out of the many ways job sites write them."""
import re
from datetime import date, timedelta

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MON = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"

# "15th October 2026", "15 Oct, 2026", "15 October"
_DMY = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s*(?:of\s+)?{_MON}\b\.?,?\s*(\d{{4}})?", re.I)
# "Oct 16, 2026", "October 15th", "October 2026" is deliberately NOT matched (no day)
_MDY = re.compile(rf"\b{_MON}\b\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s*(\d{{4}}))?", re.I)
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_COMPACT = re.compile(r"(?<!\d)(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)")  # 20260724 (only trusted after 'deadline')
_SLASH = re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b")  # Kenya writes day/month/year

_DEADLINE_KEYS = re.compile(
    r"(deadline|closing\s+date|date\s+of\s+closing|closes?\s+(?:on|at)?|close\s+of\s+business|"
    r"apply\s+(?:on\s+or\s+)?(?:by|before)|application\s+deadline|on\s+or\s+before|not\s+later\s+than|"
    r"submitted\s+(?:by|before)|expires?(?:\s+on)?)",
    re.I,
)


def _mk(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _month(token: str) -> int:
    return _MONTHS[token[:3].lower()]


def parse_date(text: str, ref: date | None = None, *, future: bool = True) -> date | None:
    """First date found in `text`. A missing year is inferred relative to `ref`
    (future=True: deadlines roll forward; future=False: posted dates roll back)."""
    if not text:
        return None
    ref = ref or date.today()
    candidates: list[tuple[int, date]] = []

    for m in _ISO.finditer(text):
        d = _mk(int(m[1]), int(m[2]), int(m[3]))
        if d:
            candidates.append((m.start(), d))
    for m in _SLASH.finditer(text):
        d = _mk(int(m[3]), int(m[2]), int(m[1]))
        if d:
            candidates.append((m.start(), d))
    for rx, order in ((_DMY, "dm"), (_MDY, "md")):
        for m in rx.finditer(text):
            day, mon = (int(m[1]), _month(m[2])) if order == "dm" else (int(m[2]), _month(m[1]))
            year = int(m[3]) if m[3] else None
            d = _mk(year or ref.year, mon, day)
            if d and year is None:
                if future and d < ref - timedelta(days=60):
                    d = _mk(ref.year + 1, mon, day)
                elif not future and d > ref + timedelta(days=2):
                    d = _mk(ref.year - 1, mon, day)
            if d:
                candidates.append((m.start(), d))
    if not candidates:
        return None
    return min(candidates, key=lambda c: c[0])[1]


def find_deadline(text: str, ref: date | None = None) -> date | None:
    """Look for a deadline phrase and parse the date that follows it."""
    if not text:
        return None
    for m in _DEADLINE_KEYS.finditer(text):
        window = text[m.end(): m.end() + 70]
        d = parse_date(window, ref, future=True)
        if not d:
            c = _COMPACT.search(window)
            d = _mk(int(c[1]), int(c[2]), int(c[3])) if c else None
        if d:
            return d
    return None
