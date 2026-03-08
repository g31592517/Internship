#!/usr/bin/env python3
"""
test_send.py  –  Send a test application email to your own address
so you can verify how it looks before blasting to companies.

Usage:
    cd /home/gohon/Desktop/Internship/INTERNSHIPS
    python src/test_send.py
"""

import os
import ssl
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# ── Config ──────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SENDER_EMAIL    = "g31592517@gmail.com"
RECIPIENT_EMAIL = "goefrey83@gmail.com"        # preview recipient

RESUME_PDF    = os.path.join(BASE_DIR, "resume", "resume.pdf")
ATTACH_LETTER = os.path.join(BASE_DIR, "Attachment Letter from school.pdf")
INSURANCE_PDF = os.path.join(BASE_DIR, "Insurance cover.pdf")

SUBJECT = "Software Engineering Internship Application"

BODY = """\
Dear Hiring Team,

I am writing to express my interest in a Software Engineering Internship position at your organization.

I am currently a student at Kisii University pursuing a Bachelor of Science in Software Engineering. I have hands-on experience building full-stack web and mobile applications, and I am eager to apply my skills while contributing to a dynamic and innovative team.

Please find the following documents attached for your consideration:

1. My CV/Resume
2. Attachment Letter from my University
3. Insurance Cover

I am available to begin immediately and can be reached at 0112492399 or via email at g31592517@gmail.com.

Thank you for your time and consideration. I look forward to the opportunity to contribute and learn from your team.

Yours sincerely,
Geofrey Onyango
"""

# ── Attachments ──────────────────────────────────────────────────────────────
ATTACHMENTS = [
    ("Resume",                   RESUME_PDF),
    ("Attachment Letter",        ATTACH_LETTER),
    ("Insurance Cover",          INSURANCE_PDF),
]

def send_test():
    missing = [(label, path) for label, path in ATTACHMENTS if not os.path.exists(path)]
    if missing:
        for label, path in missing:
            print(f"[MISSING] {label}: {path}")
        if any(label == "Resume" for label, _ in missing):
            print("\nResume PDF not found – compile resume.tex first (see instructions below).")
            print("  cd INTERNSHIPS/resume && pdflatex resume.tex")
            return

    msg = MIMEMultipart()
    msg['From']    = SENDER_EMAIL
    msg['To']      = RECIPIENT_EMAIL
    msg['Subject'] = SUBJECT
    msg.attach(MIMEText(BODY, 'plain'))

    attached_count = 0
    for label, path in ATTACHMENTS:
        if os.path.exists(path):
            with open(path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(path)}"'
            msg.attach(part)
            print(f"  ✓ Attached: {os.path.basename(path)}")
            attached_count += 1
        else:
            print(f"  ⚠  Skipping (not found): {path}")

    import getpass
    print()
    print("Enter your Gmail App Password for g31592517@gmail.com")
    print("(Get one at: myaccount.google.com → Security → App Passwords)")
    sender_pass = getpass.getpass("App Password: ")

    print(f"\nSending test email to {RECIPIENT_EMAIL} ...")
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(SENDER_EMAIL, sender_pass)
            server.send_message(msg)
        print(f"  ✓ SUCCESS! Email sent with {attached_count} attachment(s). Check your inbox.")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

if __name__ == "__main__":
    send_test()
