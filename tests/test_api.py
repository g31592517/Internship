import pytest
from fastapi.testclient import TestClient

import api.main as m
from applications import adapters
from opportunity.service import SearchService
from scrapers.base import LinkBroken, SourceBlocked


class StubSource:
    """Stands in for a website: ads in two places, one with an application inbox, one with a dead link."""
    name = "Stub"
    calls = 0

    def build_queries(self, course):
        return [f"{course} intern"]

    def scrape(self, query, location=None):
        StubSource.calls += 1
        return [
            {"title": "Software Developer Intern", "company": "Acme", "link": "https://stub.test/a", "source": "Stub",
             "snippet": "Build web apps", "location": "Nairobi"},
            {"title": "Software Engineering Attachment", "company": "Beta", "link": "https://stub.test/b", "source": "Stub",
             "snippet": "Backend work", "location": "Mombasa"},
            {"title": "Software Intern (gone)", "company": "Ghost", "link": "https://stub.test/gone", "source": "Stub"},
            {"title": "Chef Intern", "company": "Kitchen", "link": "https://stub.test/chef", "source": "Stub"},
        ]

    def enrich(self, raw):
        if raw["link"].endswith("/gone"):
            raise LinkBroken(raw["link"])
        if raw["link"].endswith("/a"):
            raw["description"] = "Requirements:\n- Studying computer science\n\nSend CV to hr@acme.co.ke. Deadline: 30 December 2099"
            raw["field_label"] = "ICT / Computer"
        return raw


class BlockedSource(StubSource):
    name = "Walled"

    def scrape(self, query, location=None):
        raise SourceBlocked("Walled: bot-protection challenge")


class FakeSMTP:
    def __init__(self, sink):
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, *a):
        pass

    def send_message(self, msg):
        self.sink.append(msg)


@pytest.fixture(scope="module")
def client():
    m.service = SearchService([StubSource(), BlockedSource()], store=m.store)
    c = TestClient(m.app)
    created = c.post("/profile", json=PROFILE).json()
    c.pid = created["id"]
    c.headers["X-Profile-Token"] = created["token"]   # this "browser" owns the profile from now on
    return c


PROFILE = {"full_name": "Wanjiku Test", "email": "wanjiku@example.com", "course": "Software Engineering"}


def _ids(client):
    hits = client.get("/opportunities/search", params={"course": "Software Engineering"}).json()["results"]
    by_org = {h["organization"]: h["id"] for h in hits}
    return client.pid, by_org["Acme"], by_org["Beta"]


def test_search_dynamic_course_and_optional_location(client):
    r = client.get("/opportunities/search", params={"course": "Software Engineering"}).json()
    titles = {x["title"] for x in r["results"]}
    assert titles == {"Software Developer Intern", "Software Engineering Attachment"}   # chef filtered, dead link dropped
    by_name = {s["name"]: s for s in r["sources"]}
    assert by_name["Stub"]["status"] == "ok" and by_name["Walled"]["status"] == "blocked"
    assert "Nairobi" in r["facets"]["locations"]

    r = client.post("/opportunities/search", json={"course": "Software Engineering", "location": "Mombasa"}).json()
    assert [x["title"] for x in r["results"]] == ["Software Engineering Attachment"]


def test_location_filter_reuses_cached_scrape(client):
    client.get("/opportunities/search", params={"course": "Software Engineering"})
    before = StubSource.calls
    client.get("/opportunities/search", params={"course": "Software Engineering", "location": "Nairobi"})
    assert StubSource.calls == before


def test_search_validation(client):
    assert client.get("/opportunities/search").status_code == 422
    assert client.get("/opportunities/search", params={"course": "x"}).status_code == 422


def test_opportunity_detail_has_enriched_fields(client):
    _, acme, _ = _ids(client)
    d = client.get(f"/opportunities/{acme}").json()
    assert d["apply_email"] == "hr@acme.co.ke" and d["can_auto_apply"] is True
    assert d["deadline"] == "2099-12-30" and d["requirements"] == ["Studying computer science"]
    assert client.get("/opportunities/doesnotexist").status_code == 404


def test_profile_create_update_and_validation(client):
    assert client.post("/profile", json={**PROFILE, "email": "nope"}).status_code == 422
    p2 = client.post("/profile", json={**PROFILE, "phone": "0700000000"}).json()
    assert p2["id"] == client.pid and p2["phone"] == "0700000000"
    assert "cv_path" not in p2 and "token_hash" not in p2 and "token" not in p2   # token is only returned at creation
    assert client.get("/api/health").json()["ok"] is True                         # /api prefix used by the web app


def test_another_browser_cannot_see_or_use_the_profile(client):
    pid, acme, _ = _ids(client)
    stranger = TestClient(m.app)                                   # no token
    forged = TestClient(m.app, headers={"X-Profile-Token": "guess"})
    for c in (stranger, forged):
        assert c.get(f"/profile/{pid}").status_code == 404
        assert c.get("/applications", params={"profile_id": pid}).status_code == 404
        assert c.post("/applications/preview", json={"profile_id": pid, "opportunity_id": acme}).status_code == 404
        assert c.post("/applications", json={"profile_id": pid, "opportunity_id": acme}).status_code == 404
        assert c.post(f"/profile/{pid}/cv", files={"file": ("cv.pdf", b"%PDF", "application/pdf")}).status_code == 404
    # nor take it over by re-registering the same email
    assert stranger.post("/profile", json={**PROFILE, "full_name": "Impostor"}).status_code == 409
    assert client.get(f"/profile/{pid}").json()["full_name"] == "Wanjiku Test"
    # a different person can still create their own profile, and can't move it onto the first email
    other = stranger.post("/profile", json={**PROFILE, "email": "other@example.com"}).json()
    stranger.headers["X-Profile-Token"] = other["token"]
    assert other["id"] != pid
    assert stranger.post("/profile", json={**PROFILE, "email": "wanjiku@example.com"}).status_code == 409


def test_preview_shows_what_would_be_submitted(client):
    pid, acme, beta = _ids(client)
    d = client.post("/applications/preview", json={"profile_id": pid, "opportunity_id": acme}).json()
    assert d["method"] == "email" and d["to"] == "hr@acme.co.ke"
    assert "Wanjiku Test" in d["body"] and "Software Engineering" in d["body"]
    assert {f["label"] for f in d["fields"]} >= {"Full name", "Course"}
    d2 = client.post("/applications/preview", json={"profile_id": pid, "opportunity_id": beta}).json()
    assert d2["method"] == "link" and d2["can_auto_apply"] is False


def test_auto_apply_requires_confirmation_and_sending_config(client):
    pid, acme, _ = _ids(client)
    body = {"profile_id": pid, "opportunity_id": acme, "mode": "auto"}
    assert client.post("/applications", json=body).status_code == 400                    # no confirm
    r = client.post("/applications", json={**body, "confirm": True})
    assert r.status_code == 502 and "configured" in r.json()["detail"]                   # no SMTP -> nothing recorded
    assert client.get("/applications", params={"profile_id": pid}).json() == []


def test_auto_apply_sends_once_and_is_tracked(client, monkeypatch):
    pid, acme, _ = _ids(client)
    sent = []
    monkeypatch.setenv("SMTP_USER", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "x")
    monkeypatch.setattr(adapters.smtplib, "SMTP_SSL", lambda *a, **k: FakeSMTP(sent))
    body = {"profile_id": pid, "opportunity_id": acme, "mode": "auto", "confirm": True}
    r = client.post("/applications", json=body)
    assert r.status_code == 201 and r.json()["status"] == "Applied" and r.json()["method"] == "email"
    assert len(sent) == 1 and sent[0]["To"] == "hr@acme.co.ke" and sent[0]["Reply-To"].endswith("<wanjiku@example.com>")
    assert client.post("/applications", json=body).status_code == 409 and len(sent) == 1   # never sent twice


def test_manual_tracking_and_status_update(client):
    pid, _, beta = _ids(client)
    r = client.post("/applications", json={"profile_id": pid, "opportunity_id": beta, "mode": "manual", "status": "Pending"})
    assert r.status_code == 201 and r.json()["method"] == "manual"
    aid = r.json()["id"]
    assert client.patch(f"/applications/{aid}", json={"status": "Accepted"}).json()["status"] == "Accepted"
    assert client.patch(f"/applications/{aid}", json={"status": "Bogus"}).status_code == 422
    assert TestClient(m.app).patch(f"/applications/{aid}", json={"status": "Rejected"}).status_code == 404
    rows = client.get("/applications", params={"profile_id": pid}).json()
    assert "Accepted" in {x["status"] for x in rows} and rows[0]["title"]


def test_cv_upload_rules(client):
    pid, *_ = _ids(client)
    ok = client.post(f"/profile/{pid}/cv", files={"file": ("cv.pdf", b"%PDF-1.4 test", "application/pdf")})
    assert ok.status_code == 200 and ok.json()["has_cv"] is True and ok.json()["cv_filename"] == "cv.pdf"
    bad = client.post(f"/profile/{pid}/cv", files={"file": ("evil.exe", b"MZ", "application/octet-stream")})
    assert bad.status_code == 400


def test_search_results_respect_site_specific_apply_rules(client, monkeypatch):
    hits = client.get("/opportunities/search", params={"course": "Software Engineering"}).json()["results"]
    assert next(h for h in hits if h["organization"] == "Acme")["can_auto_apply"] is True
    monkeypatch.setitem(adapters.SOURCE_ADAPTERS, "Stub", adapters.LinkApplicationAdapter())   # e.g. a login-only site
    hits = client.get("/opportunities/search", params={"course": "Software Engineering"}).json()["results"]
    assert next(h for h in hits if h["organization"] == "Acme")["can_auto_apply"] is False


class _Resp:
    def __init__(self, status, data):
        self.status_code, self._data = status, data

    def json(self):
        return self._data


def test_brevo_https_transport_used_when_configured(monkeypatch, tmp_path):
    """Render's free plan blocks SMTP ports, so email can go out through Brevo's HTTPS API instead."""
    calls = []
    monkeypatch.setenv("BREVO_API_KEY", "test-key")
    monkeypatch.setenv("MAIL_FROM", "apply@platform.test")
    monkeypatch.setenv("SMTP_USER", "ignored@example.com")      # Brevo wins over SMTP when both are set
    monkeypatch.setenv("SMTP_PASSWORD", "x")
    monkeypatch.setattr(adapters.requests, "post", lambda url, **kw: calls.append((url, kw)) or _Resp(201, {"messageId": "1"}))
    assert adapters.sending_mode() == "brevo"
    cv = tmp_path / "cv.pdf"
    cv.write_bytes(b"%PDF-1.4")
    opp = {"title": "Dev Intern", "organization": "Acme", "apply_email": "hr@acme.co.ke", "expired": False}
    profile = {**PROFILE, "cv_filename": "My CV.pdf", "cv_path": str(cv)}
    adapters.EmailApplicationAdapter().submit(opp, profile)
    url, kw = calls[0]
    p = kw["json"]
    assert url == "https://api.brevo.com/v3/smtp/email" and kw["headers"]["api-key"] == "test-key"
    assert p["sender"] == {"email": "apply@platform.test", "name": "Wanjiku Test"}
    assert p["to"] == [{"email": "hr@acme.co.ke"}] and p["replyTo"]["email"] == "wanjiku@example.com"
    assert p["attachment"][0]["name"] == "My CV.pdf" and "Software Engineering" in p["textContent"]

    monkeypatch.setattr(adapters.requests, "post", lambda url, **kw: _Resp(401, {"message": "Key not found"}))
    with pytest.raises(adapters.ApplyError, match="401: Key not found"):
        adapters.EmailApplicationAdapter().submit(opp, profile)
