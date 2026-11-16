"""Application adapters: how a student's profile gets turned into an application for ONE opportunity.

  EmailApplicationAdapter  the ad names an application inbox -> we draft the email, the student
                           reviews it, and only after explicit confirmation is it sent.
  LinkApplicationAdapter   everything else (web forms, logins, CAPTCHAs, other sites): we do not
                           automate; the student is sent to the original application page.

Per-site behaviour goes in SOURCE_ADAPTERS (e.g. a site whose form we learn to fill later gets its
own adapter class). We never bypass CAPTCHA/MFA/bot protection and never store third-party passwords.
The recipient address always comes from the scraped opportunity, never from the request, so the API
cannot be used to send mail to arbitrary people."""
import os
import re
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

_EMAIL_RX = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class ApplyError(Exception):
    pass


@dataclass
class Draft:
    method: str                      # "email" | "link"
    can_auto_apply: bool
    open_url: str
    to: str = ""
    subject: str = ""
    body: str = ""
    attachments: list[str] = field(default_factory=list)
    fields: list[dict] = field(default_factory=list)   # what will be submitted, label/value
    note: str = ""


# ------------------------------------------------------------------ SMTP configuration
def smtp_settings() -> dict | None:
    """Sender mailbox for email applications. Env vars first; falls back to the original project's
    src/config.py (GMAIL_USER / GMAIL_PASS). The password lives only in the server environment."""
    user, pw = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    if not (user and pw):
        try:
            from config import GMAIL_USER, GMAIL_PASS  # original project config (gitignored)
            if GMAIL_USER and GMAIL_PASS and "your" not in GMAIL_USER.lower():
                user, pw = GMAIL_USER, GMAIL_PASS
        except Exception:
            pass
    if not (user and pw):
        return None
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.environ.get("SMTP_PORT", "465")),
        "security": os.environ.get("SMTP_SECURITY", "ssl"),     # ssl | starttls | none
        "user": user,
        "password": pw,
    }


def dry_run() -> bool:
    return os.environ.get("APPLY_DRY_RUN", "").lower() in ("1", "true", "yes")


# ------------------------------------------------------------------ drafting
def _intro(profile: dict) -> str:
    bits = []
    year = (profile.get("year_of_study") or "").strip()
    bits.append(f"I am {'a ' + year + ' student' if year else 'a student'} pursuing {profile['course']}")
    if profile.get("university"):
        bits[0] += f" at {profile['university']}"
    return bits[0] + "."


def build_email(opp: dict, profile: dict) -> tuple[str, str]:
    org = opp.get("organization") or "your organisation"
    subject = f"Application for {opp['title']} - {profile['full_name']}"
    lines = [
        "Dear Hiring Team,",
        "",
        f"I am writing to apply for the {opp['title']} opportunity at {org}.",
        "",
        _intro(profile),
    ]
    if profile.get("skills"):
        lines.append(f"My key skills include {profile['skills']}.")
    if profile.get("cover_letter"):
        lines += ["", profile["cover_letter"].strip()]
    if profile.get("cv_filename"):
        lines += ["", "Please find my CV attached."]
    lines += ["", "Thank you for your time and consideration.", "", "Yours sincerely,", profile["full_name"],
              f"Email: {profile['email']}"]
    if profile.get("phone"):
        lines.append(f"Phone: {profile['phone']}")
    for label, key in (("LinkedIn", "linkedin"), ("GitHub", "github")):
        if profile.get(key):
            lines.append(f"{label}: {profile[key]}")
    return subject, "\n".join(lines)


class LinkApplicationAdapter:
    method = "link"

    def supports_auto(self, opp: dict) -> bool:
        return False

    def preview(self, opp: dict, profile: dict) -> Draft:
        return Draft(
            method="link", can_auto_apply=False, open_url=opp.get("apply_url") or opp.get("url", ""),
            note="This employer takes applications on its own website (or behind a login), so we can't fill it "
                 "in for you. Open the application, then come back and mark it as applied to track it.",
            fields=[{"label": "Full name", "value": profile["full_name"]},
                    {"label": "Email", "value": profile["email"]},
                    {"label": "Course", "value": profile["course"]}],
        )

    def submit(self, opp: dict, profile: dict, subject=None, body=None) -> None:
        raise ApplyError("Automatic submission is not available for this opportunity. Use Open Application.")


class EmailApplicationAdapter(LinkApplicationAdapter):
    method = "email"

    def supports_auto(self, opp: dict) -> bool:
        return bool(_EMAIL_RX.match(opp.get("apply_email") or "")) and not opp.get("expired")

    def preview(self, opp: dict, profile: dict) -> Draft:
        subject, body = build_email(opp, profile)
        cv = profile.get("cv_filename") or ""
        d = Draft(
            method="email", can_auto_apply=True, open_url=opp.get("apply_url") or opp.get("url", ""),
            to=opp["apply_email"], subject=subject, body=body, attachments=[cv] if cv else [],
            fields=[{"label": "To", "value": opp["apply_email"]},
                    {"label": "Full name", "value": profile["full_name"]},
                    {"label": "Email (reply-to)", "value": profile["email"]},
                    {"label": "Course", "value": profile["course"]}],
        )
        if not cv:
            d.note = "No CV is attached. Upload one on your profile to include it."
        if smtp_settings() is None and not dry_run():
            d.can_auto_apply = False
            d.note = ("Automatic sending isn't set up on this server (no SMTP account configured). "
                      "You can still open your email app with this message pre-filled.")
        return d

    def submit(self, opp: dict, profile: dict, subject=None, body=None) -> None:
        if not self.supports_auto(opp):
            raise ApplyError("This opportunity can't be applied to automatically.")
        default_subject, default_body = build_email(opp, profile)
        subject = (subject or default_subject).strip()[:200]
        body = (body or default_body).strip()
        if dry_run():
            return
        cfg = smtp_settings()
        if cfg is None:
            raise ApplyError("Automatic sending isn't configured on this server.")

        msg = EmailMessage()
        msg["From"] = formataddr((profile["full_name"], cfg["user"]))
        msg["Reply-To"] = formataddr((profile["full_name"], profile["email"]))
        msg["To"] = opp["apply_email"]
        msg["Subject"] = subject
        msg.set_content(body)
        cv_path = profile.get("cv_path")
        if cv_path and Path(cv_path).is_file():
            data = Path(cv_path).read_bytes()
            ext = Path(cv_path).suffix.lower()
            maintype, subtype = ("application", "pdf") if ext == ".pdf" else ("application", "octet-stream")
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=profile.get("cv_filename") or "cv" + ext)
        try:
            if cfg["security"] == "ssl":
                with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ssl.create_default_context(), timeout=30) as s:
                    s.login(cfg["user"], cfg["password"])
                    s.send_message(msg)
            else:
                with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as s:
                    if cfg["security"] == "starttls":
                        s.starttls(context=ssl.create_default_context())
                    if cfg["security"] != "none":
                        s.login(cfg["user"], cfg["password"])
                    s.send_message(msg)
        except (smtplib.SMTPException, OSError) as e:
            raise ApplyError(f"The email could not be sent ({type(e).__name__}). Nothing was recorded.") from e


# Site-specific adapters go here, e.g. {"SomeSite": SomeSiteFormAdapter()}.
# BrighterMonday needs the student to sign in on brighter-monday itself, so it stays link-only even if
# the ad text happens to contain an address.
SOURCE_ADAPTERS: dict[str, LinkApplicationAdapter] = {
    "BrighterMonday": LinkApplicationAdapter(),
}

_EMAIL = EmailApplicationAdapter()
_LINK = LinkApplicationAdapter()


def adapter_for(opp: dict) -> LinkApplicationAdapter:
    if opp.get("source") in SOURCE_ADAPTERS:
        return SOURCE_ADAPTERS[opp["source"]]
    return _EMAIL if _EMAIL.supports_auto(opp) else _LINK
