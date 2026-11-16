"""Search orchestration:  sources -> raw dicts -> normalise -> rank/dedupe -> enrich -> filter.

The expensive part (scraping) depends only on the COURSE, so its result is cached per course and
the optional location / other filters are applied on top without re-scraping."""
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date

from scrapers.base import LinkBroken, SourceBlocked, SourceError
from . import search as S
from .model import Opportunity, SearchHit
from .normalize import normalize

log = logging.getLogger("opportunity.service")


@dataclass
class SourceStatus:
    name: str
    status: str = "ok"          # ok | blocked | unavailable | error
    message: str = ""
    found: int = 0              # raw listings returned by the site
    relevant: int = 0           # listings that made it into the final results
    ms: int = 0


@dataclass
class Pool:
    opportunities: list[Opportunity]
    statuses: list[SourceStatus]
    built_at: float = field(default_factory=time.time)


class SearchService:
    def __init__(self, sources, store=None, ttl: int = 900, max_enrich: int = 30):
        self.sources = list(sources)
        self.store = store
        self.ttl = ttl
        self.max_enrich = max_enrich
        self._cache: dict[str, Pool] = {}
        self._lock = threading.Lock()
        self._key_locks: dict[str, threading.Lock] = {}
        # Fresh scrapes are expensive for us and for the job sites; on a public server only a few run at once.
        self._scrape_slots = threading.BoundedSemaphore(int(os.environ.get("MAX_CONCURRENT_SCRAPES", "2")))

    # ------------------------------------------------------------------ scraping
    def _scrape_source(self, source, course: str) -> tuple[list[dict], SourceStatus]:
        st = SourceStatus(name=source.name)
        t0 = time.time()
        raws: list[dict] = []
        seen: set[str] = set()
        queries = source.build_queries(course)
        with ThreadPoolExecutor(max_workers=min(4, max(1, len(queries)))) as ex:
            futures = {ex.submit(source.scrape, q): q for q in queries}
            for fut in as_completed(futures):
                try:
                    for r in fut.result():
                        if r.get("link") and r["link"] not in seen:
                            seen.add(r["link"])
                            r.setdefault("source", source.name)
                            raws.append(r)
                except SourceBlocked as e:
                    st.status, st.message = "blocked", str(e)
                except SourceError as e:
                    if st.status == "ok":
                        st.status, st.message = "unavailable", str(e)
                except Exception as e:  # one broken adapter must never break the search
                    log.exception("%s failed on %r", source.name, futures[fut])
                    if st.status == "ok":
                        st.status, st.message = "error", f"{type(e).__name__}: {e}"
        # if some queries worked, the source is usable even if another query errored
        if raws and st.status in ("unavailable", "error"):
            st.status, st.message = "ok", ""
        st.found = len(raws)
        st.ms = int((time.time() - t0) * 1000)
        return raws, st

    def _enrich_one(self, source, raw: dict) -> dict:
        try:
            return source.enrich(dict(raw))
        except LinkBroken:
            return {**raw, "link_status": "broken"}
        except Exception as e:
            log.info("enrich failed for %s: %s", raw.get("link"), e)
            return raw

    # ------------------------------------------------------------------ pool
    def collect(self, course: str, refresh: bool = False) -> Pool:
        key = S.CourseQuery.parse(course).phrase or course.strip().lower()
        with self._lock:
            key_lock = self._key_locks.setdefault(key, threading.Lock())
        with key_lock:      # identical searches wait for the first one instead of scraping twice
            with self._lock:
                pool = self._cache.get(key)
            if pool and not refresh and time.time() - pool.built_at < self.ttl:
                return pool
            with self._scrape_slots:
                return self._build(course, key)

    def _build(self, course: str, key: str) -> Pool:

        by_source = {s.name: s for s in self.sources}
        raw_by_url: dict[str, dict] = {}
        statuses: list[SourceStatus] = []
        with ThreadPoolExecutor(max_workers=max(1, len(self.sources))) as ex:
            for fut in [ex.submit(self._scrape_source, s, course) for s in self.sources]:
                raws, st = fut.result()
                statuses.append(st)
                for r in raws:
                    raw_by_url[r["link"]] = r

        opps = []
        for r in raw_by_url.values():
            try:
                opps.append(normalize(r))
            except Exception:
                log.exception("could not normalise %s", r.get("link"))
        ranked = S.rank(S.dedupe(opps), course)

        # Second request for the best candidates: full description, deadline, location, apply info.
        top = [o for o, _ in ranked[: self.max_enrich]]
        enriched: dict[str, Opportunity] = {}
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {}
            for o in top:
                raw = raw_by_url.get(o.url)
                if raw and raw.get("source") in by_source:
                    futs[ex.submit(self._enrich_one, by_source[raw["source"]], raw)] = o
            for fut in as_completed(futs):
                o = futs[fut]
                try:
                    new = normalize(fut.result())
                    new.also_on = o.also_on
                    enriched[o.id] = new
                except Exception:
                    log.exception("re-normalise failed for %s", o.url)

        final_opps = [enriched.get(o.id, o) for o, _ in ranked]
        final_opps = S.dedupe(final_opps)
        # Re-rank now that descriptions are known (may drop ads that were only borderline).
        final_ranked = S.rank(final_opps, course)

        counts: dict[str, int] = {}
        for o, _ in final_ranked:
            for name in {o.source, *(a.source for a in o.also_on)}:
                counts[name] = counts.get(name, 0) + 1
        for st in statuses:
            st.relevant = counts.get(st.name, 0)

        pool = Pool(opportunities=[o for o, _ in final_ranked], statuses=statuses)
        if self.store:
            self.store.save_opportunities(pool.opportunities)
        with self._lock:
            self._cache[key] = pool
        return pool

    # ------------------------------------------------------------------ public search
    def search(self, course: str, location: str = "", *, strict_location: bool = False, organization: str = "",
               field_: str = "", deadline_before: date | None = None, include_expired: bool = False,
               refresh: bool = False) -> dict:
        pool = self.collect(course, refresh=refresh)
        ranked = S.rank(pool.opportunities, course)
        in_scope = S.apply_filters(ranked, location=location, strict_location=strict_location,
                                   include_expired=include_expired)
        hits: list[SearchHit] = S.apply_filters(
            ranked, location=location, strict_location=strict_location, organization=organization,
            field_=field_, deadline_before=deadline_before, include_expired=include_expired)
        return {
            "course": course,
            "location": location,
            "count": len(hits),
            "results": hits,
            "facets": {
                "fields": sorted({h.field for h in in_scope if h.field}),
                "organizations": sorted({h.organization for h in in_scope if h.organization}, key=str.lower),
                "locations": sorted({c for h in in_scope for c in h.counties}),
            },
            "sources": [st.__dict__ for st in pool.statuses],
            "searched_at": pool.built_at,
        }
