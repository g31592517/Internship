"""SQLite persistence: student profiles, scraped opportunities (so detail pages survive restarts)
and the applications a student has made. Plain sqlite3 - nothing to install or administer."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("INTERNSHIP_DATA_DIR", ROOT / "data"))

PROFILE_FIELDS = ["full_name", "email", "course", "phone", "university", "year_of_study", "skills",
                  "linkedin", "github", "cover_letter"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, course TEXT NOT NULL,
  phone TEXT DEFAULT '', university TEXT DEFAULT '', year_of_study TEXT DEFAULT '', skills TEXT DEFAULT '',
  linkedin TEXT DEFAULT '', github TEXT DEFAULT '', cover_letter TEXT DEFAULT '',
  cv_filename TEXT DEFAULT '', cv_path TEXT DEFAULT '',
  token_hash TEXT DEFAULT '',                      -- sha256 of the browser's secret profile token
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS opportunities (
  id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS applications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL REFERENCES profiles(id),
  opportunity_id TEXT NOT NULL,
  title TEXT NOT NULL, organization TEXT DEFAULT '', url TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'Applied',
  method TEXT NOT NULL DEFAULT 'manual',          -- email | manual
  applied_at TEXT NOT NULL, updated_at TEXT NOT NULL, notes TEXT DEFAULT '',
  UNIQUE(profile_id, opportunity_id)
);
"""

STATUSES = ["Pending", "Applied", "Accepted", "Rejected"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.environ.get("INTERNSHIP_DB", DATA_DIR / "app.db"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.conn() as c:
            c.executescript(SCHEMA)
            cols = {r["name"] for r in c.execute("PRAGMA table_info(profiles)")}
            if "token_hash" not in cols:   # databases created before profile tokens existed
                c.execute("ALTER TABLE profiles ADD COLUMN token_hash TEXT DEFAULT ''")

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.path, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
            c.commit()
        finally:
            c.close()

    # ---- opportunities
    def save_opportunities(self, opps) -> None:
        now = _now()
        with self.conn() as c:
            c.executemany(
                "INSERT INTO opportunities(id, data, updated_at) VALUES(?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
                [(o.id, o.model_dump_json(exclude={"can_auto_apply"}), now) for o in opps])

    def get_opportunity(self, opp_id: str) -> dict | None:
        with self.conn() as c:
            row = c.execute("SELECT data FROM opportunities WHERE id=?", (opp_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    # ---- profiles
    def find_profile_by_email(self, email: str) -> dict | None:
        with self.conn() as c:
            row = c.execute("SELECT * FROM profiles WHERE lower(email)=lower(?)", (email.strip(),)).fetchone()
        return dict(row) if row else None

    def find_profile_by_token_hash(self, token_hash: str) -> dict | None:
        with self.conn() as c:
            row = c.execute("SELECT * FROM profiles WHERE token_hash=? AND token_hash != ''", (token_hash,)).fetchone()
        return dict(row) if row else None

    def create_profile(self, data: dict, token_hash: str) -> dict:
        now = _now()
        vals = {k: (data.get(k) or "").strip() for k in PROFILE_FIELDS}
        cols = ", ".join(PROFILE_FIELDS)
        qs = ", ".join("?" for _ in PROFILE_FIELDS)
        with self.conn() as c:
            pid = c.execute(f"INSERT INTO profiles({cols}, token_hash, created_at, updated_at) VALUES({qs},?,?,?)",
                            [*vals.values(), token_hash, now, now]).lastrowid
        return self.get_profile(pid)

    def update_profile(self, pid: int, data: dict) -> dict:
        vals = {k: (data.get(k) or "").strip() for k in PROFILE_FIELDS}
        sets = ", ".join(f"{k}=?" for k in PROFILE_FIELDS)
        with self.conn() as c:
            c.execute(f"UPDATE profiles SET {sets}, updated_at=? WHERE id=?", [*vals.values(), _now(), pid])
        return self.get_profile(pid)

    def get_profile(self, pid: int) -> dict | None:
        with self.conn() as c:
            row = c.execute("SELECT * FROM profiles WHERE id=?", (pid,)).fetchone()
        return dict(row) if row else None

    def set_cv(self, pid: int, filename: str, path: str) -> None:
        with self.conn() as c:
            c.execute("UPDATE profiles SET cv_filename=?, cv_path=?, updated_at=? WHERE id=?",
                      (filename, path, _now(), pid))

    # ---- applications
    def get_application_for(self, pid: int, opp_id: str) -> dict | None:
        with self.conn() as c:
            row = c.execute("SELECT * FROM applications WHERE profile_id=? AND opportunity_id=?",
                            (pid, opp_id)).fetchone()
        return dict(row) if row else None

    def create_application(self, pid: int, opp: dict, status: str, method: str, notes: str = "") -> dict:
        now = _now()
        with self.conn() as c:
            aid = c.execute(
                "INSERT INTO applications(profile_id, opportunity_id, title, organization, url, status, method,"
                " applied_at, updated_at, notes) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (pid, opp["id"], opp["title"], opp.get("organization", ""), opp.get("url", ""), status, method,
                 now, now, notes)).lastrowid
        return self.get_application(aid)

    def get_application(self, aid: int) -> dict | None:
        with self.conn() as c:
            row = c.execute("SELECT * FROM applications WHERE id=?", (aid,)).fetchone()
        return dict(row) if row else None

    def list_applications(self, pid: int) -> list[dict]:
        with self.conn() as c:
            rows = c.execute("SELECT * FROM applications WHERE profile_id=? ORDER BY applied_at DESC, id DESC",
                             (pid,)).fetchall()
        return [dict(r) for r in rows]

    def update_application(self, aid: int, status: str | None, notes: str | None) -> dict | None:
        with self.conn() as c:
            if status is not None:
                c.execute("UPDATE applications SET status=?, updated_at=? WHERE id=?", (status, _now(), aid))
            if notes is not None:
                c.execute("UPDATE applications SET notes=?, updated_at=? WHERE id=?", (notes, _now(), aid))
        return self.get_application(aid)
