"""HTTP API.  Run from the project root:  uvicorn api.main:app --app-dir src --reload

  GET|POST /opportunities/search     course (required) + location (optional) + filters
  GET      /opportunities/{id}
  POST     /profile                  create the student profile (returns a secret token once), or update it
  GET      /profile/{id}   POST /profile/{id}/cv
  POST     /applications/preview     exactly what would be submitted
  POST     /applications             record (and, for mode=auto with confirm=true, send) an application
  GET      /applications?profile_id=
  PATCH    /applications/{id}        update status / notes
  GET      /sources   GET /health
Every route is also reachable under /api/... (what the React app calls).

There are no user accounts. Creating a profile returns a random token that the browser keeps; every
profile/application endpoint requires it in the X-Profile-Token header, so knowing a profile id is not
enough to read or act on someone's profile."""
import hashlib
import hmac
import logging
import os
import re
import secrets
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:      # lets `python -m` / tests import scrapers & opportunity the same way main.py does
    sys.path.insert(0, str(SRC))

from api.db import DATA_DIR, Store                      # noqa: E402
from applications.adapters import ApplyError, adapter_for, dry_run, smtp_settings   # noqa: E402
from opportunity.service import SearchService                      # noqa: E402
from scrapers.registry import active_sources, source_info          # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

store = Store()
service = SearchService(active_sources(), store=store)

app = FastAPI(title="Internship & Attachment Finder", version="1.1")
# Only needed when the frontend is served from a different origin than the API (e.g. Vite dev server).
_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
                   allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def strip_api_prefix(request, call_next):
    """The React app calls /api/...; serve those from the same routes as the bare paths."""
    path = request.scope["path"]
    if path == "/api" or path.startswith("/api/"):
        request.scope["path"] = path[4:] or "/"
    return await call_next(request)


_EMAIL_RX = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
MAX_CV_BYTES = 5 * 1024 * 1024
MAX_AUTO_APPLICATIONS_PER_DAY = 20


# ------------------------------------------------------------------ schemas
class ProfileIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str
    course: str = Field(min_length=2, max_length=120)
    phone: str = Field(default="", max_length=40)
    university: str = Field(default="", max_length=120)
    year_of_study: str = Field(default="", max_length=40)
    skills: str = Field(default="", max_length=500)
    linkedin: str = Field(default="", max_length=200)
    github: str = Field(default="", max_length=200)
    cover_letter: str = Field(default="", max_length=3000)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip()
        if not _EMAIL_RX.match(v):
            raise ValueError("Enter a valid email address")
        return v


class SearchIn(BaseModel):
    course: str = Field(min_length=2, max_length=120)
    location: str = Field(default="", max_length=80)
    strict_location: bool = False
    organization: str = ""
    field: str = ""
    deadline_before: date | None = None
    include_expired: bool = False
    refresh: bool = False


class PreviewIn(BaseModel):
    profile_id: int
    opportunity_id: str


class ApplicationIn(BaseModel):
    profile_id: int
    opportunity_id: str
    mode: Literal["auto", "manual"] = "manual"
    confirm: bool = False                      # must be true for mode=auto
    subject: str | None = None
    body: str | None = None
    status: Literal["Pending", "Applied"] = "Applied"   # for manual tracking
    notes: str = ""


class ApplicationPatch(BaseModel):
    status: Literal["Pending", "Applied", "Accepted", "Rejected"] | None = None
    notes: str | None = Field(default=None, max_length=1000)


# ------------------------------------------------------------------ helpers
def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _public_profile(p: dict) -> dict:
    out = {k: v for k, v in p.items() if k not in ("cv_path", "token_hash")}
    out["has_cv"] = bool(p.get("cv_path"))
    return out


def _opp_or_404(opp_id: str) -> dict:
    opp = store.get_opportunity(opp_id)
    if not opp:
        raise HTTPException(404, "Opportunity not found. Run a search first.")
    return opp


def _owned_profile(pid: int, token: str | None) -> dict:
    """The profile, but only for the browser holding its token. Same 404 either way, so ids can't be probed."""
    p = store.get_profile(pid)
    if not p or not token or not p.get("token_hash") or not hmac.compare_digest(p["token_hash"], _hash(token)):
        raise HTTPException(404, "Profile not found. Save your profile first.")
    return p


def _with_apply_flags(opp: dict) -> dict:
    opp = dict(opp)
    if opp.get("deadline"):
        opp["expired"] = opp["deadline"] < date.today().isoformat()   # may have passed since it was scraped
    opp["can_auto_apply"] = bool(opp.get("apply_email")) and not opp.get("expired") and adapter_for(opp).supports_auto(opp)
    return opp


Token = Header(default=None, alias="X-Profile-Token")


# ------------------------------------------------------------------ routes
@app.get("/health")
def health():
    return {"ok": True, "email_sending": "dry-run" if dry_run() else ("configured" if smtp_settings() else "not configured")}


@app.get("/sources")
def sources():
    return source_info()


def _run_search(p: SearchIn) -> dict:
    res = service.search(p.course.strip(), p.location.strip(), strict_location=p.strict_location,
                         organization=p.organization, field_=p.field, deadline_before=p.deadline_before,
                         include_expired=p.include_expired, refresh=p.refresh)
    out = []
    for r in res["results"]:
        d = r.model_dump(mode="json")
        d["can_auto_apply"] = d["can_auto_apply"] and adapter_for(d).supports_auto(d)   # e.g. login-only sites
        out.append(d)
    res["results"] = out
    return res


@app.get("/opportunities/search")
def search_get(course: str = Query(min_length=2, max_length=120), location: str = "", strict_location: bool = False,
               organization: str = "", field: str = "", deadline_before: date | None = None,
               include_expired: bool = False, refresh: bool = False):
    return _run_search(SearchIn(course=course, location=location, strict_location=strict_location,
                                organization=organization, field=field, deadline_before=deadline_before,
                                include_expired=include_expired, refresh=refresh))


@app.post("/opportunities/search")
def search_post(body: SearchIn):
    return _run_search(body)


@app.get("/opportunities/{opp_id}")
def get_opportunity(opp_id: str):
    return _with_apply_flags(_opp_or_404(opp_id))


@app.post("/profile")
def save_profile(body: ProfileIn, x_profile_token: str | None = Token):
    data = body.model_dump()
    existing = store.find_profile_by_email(body.email)
    mine = store.find_profile_by_token_hash(_hash(x_profile_token)) if x_profile_token else None
    if mine:   # update: the token decides which profile; the email may change, but not to someone else's
        if existing and existing["id"] != mine["id"]:
            raise HTTPException(409, "Another profile already uses this email address.")
        return _public_profile(store.update_profile(mine["id"], data))
    if existing:
        raise HTTPException(409, "A profile with this email already exists. Open the site in the browser where you "
                                 "created it, or use a different email address.")
    token = secrets.token_urlsafe(32)
    created = _public_profile(store.create_profile(data, _hash(token)))
    return {**created, "token": token}   # the only time the token is returned; the browser stores it


@app.get("/profile/{pid}")
def get_profile(pid: int, x_profile_token: str | None = Token):
    return _public_profile(_owned_profile(pid, x_profile_token))


@app.post("/profile/{pid}/cv")
async def upload_cv(pid: int, file: UploadFile = File(...), x_profile_token: str | None = Token):
    _owned_profile(pid, x_profile_token)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".pdf", ".doc", ".docx"):
        raise HTTPException(400, "CV must be a PDF, DOC or DOCX file.")
    data = await file.read(MAX_CV_BYTES + 1)
    if len(data) > MAX_CV_BYTES:
        raise HTTPException(400, "CV is larger than 5 MB.")
    folder = DATA_DIR / "cv"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"profile_{pid}{ext}"
    for old in folder.glob(f"profile_{pid}.*"):
        old.unlink(missing_ok=True)
    dest.write_bytes(data)
    safe_name = re.sub(r"[^\w.\- ]+", "_", Path(file.filename).name)[:80]
    store.set_cv(pid, safe_name, str(dest))
    return _public_profile(store.get_profile(pid))


@app.post("/applications/preview")
def preview_application(body: PreviewIn, x_profile_token: str | None = Token):
    profile, opp = _owned_profile(body.profile_id, x_profile_token), _opp_or_404(body.opportunity_id)
    draft = adapter_for(opp).preview(opp, profile)
    existing = store.get_application_for(body.profile_id, body.opportunity_id)
    return {**draft.__dict__, "dry_run": dry_run(), "already_applied": existing}


@app.post("/applications", status_code=201)
def create_application(body: ApplicationIn, x_profile_token: str | None = Token):
    profile, opp = _owned_profile(body.profile_id, x_profile_token), _opp_or_404(body.opportunity_id)
    if store.get_application_for(body.profile_id, body.opportunity_id):
        raise HTTPException(409, "You have already applied to this opportunity.")

    status, method, notes = body.status, "manual", body.notes
    if body.mode == "auto":
        if not body.confirm:
            raise HTTPException(400, "Please review the application and confirm before it is sent.")
        adapter = adapter_for(opp)
        if not adapter.supports_auto(opp):
            raise HTTPException(400, "This opportunity can't be applied to automatically. Use Open Application.")
        sent_today = sum(1 for a in store.list_applications(body.profile_id)
                         if a["method"] == "email" and a["applied_at"][:10] == datetime.now().date().isoformat())
        if sent_today >= MAX_AUTO_APPLICATIONS_PER_DAY:
            raise HTTPException(429, "Daily limit for automatic applications reached. Try again tomorrow.")
        try:
            adapter.submit(opp, profile, body.subject, body.body)
        except ApplyError as e:
            raise HTTPException(502, str(e))
        method = "email"
        status = "Pending" if dry_run() else "Applied"
        notes = ("Dry run - nothing was actually sent. " if dry_run() else f"Emailed {opp['apply_email']}. ") + notes
    return store.create_application(body.profile_id, opp, status, method, notes.strip())


@app.get("/applications")
def list_applications(profile_id: int, x_profile_token: str | None = Token):
    _owned_profile(profile_id, x_profile_token)
    return store.list_applications(profile_id)


@app.patch("/applications/{aid}")
def update_application(aid: int, body: ApplicationPatch, x_profile_token: str | None = Token):
    a = store.get_application(aid)
    if not a:
        raise HTTPException(404, "Application not found.")
    try:
        _owned_profile(a["profile_id"], x_profile_token)
    except HTTPException:
        raise HTTPException(404, "Application not found.")
    return store.update_application(aid, body.status, body.notes)


# Serve the built React app (npm run build) from the same server, if present.
_dist = SRC.parent / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="web")
