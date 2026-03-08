#!/usr/bin/env python3
"""
build_resume_pdf.py  –  Generate resume.pdf from Geofrey Onyango's details
using ReportLab (no LaTeX needed).

Run from the INTERNSHIPS folder:
    python src/build_resume_pdf.py
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
)
from reportlab.lib.styles import ParagraphStyle

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PDF = os.path.join(BASE_DIR, "resume", "resume.pdf")

# ── Colour palette ─────────────────────────────────────────────────────────
BLACK = colors.HexColor("#000000")
DARK  = colors.HexColor("#1a1a1a")
RULE  = colors.HexColor("#333333")

# ── Styles ─────────────────────────────────────────────────────────────────
def make_styles():
    s = {}
    s['name'] = ParagraphStyle('name',
        fontName='Helvetica-Bold', fontSize=18,
        textColor=BLACK, alignment=TA_CENTER, spaceAfter=2)

    s['contact'] = ParagraphStyle('contact',
        fontName='Helvetica', fontSize=9.5,
        textColor=DARK, alignment=TA_CENTER, spaceAfter=2)

    s['tagline'] = ParagraphStyle('tagline',
        fontName='Helvetica-Bold', fontSize=9,
        textColor=DARK, alignment=TA_CENTER, spaceAfter=10)

    s['section'] = ParagraphStyle('section',
        fontName='Helvetica-Bold', fontSize=11,
        textColor=BLACK, alignment=TA_LEFT, spaceBefore=8, spaceAfter=2)

    s['subheading'] = ParagraphStyle('subheading',
        fontName='Helvetica-Bold', fontSize=10,
        textColor=DARK, alignment=TA_LEFT, spaceBefore=4, spaceAfter=1)

    s['subheading_right'] = ParagraphStyle('subheading_right',
        fontName='Helvetica', fontSize=9.5,
        textColor=DARK, alignment=TA_LEFT, spaceAfter=1)

    s['body'] = ParagraphStyle('body',
        fontName='Helvetica', fontSize=9.5,
        textColor=DARK, alignment=TA_JUSTIFY, spaceAfter=1, leading=13)

    s['bullet'] = ParagraphStyle('bullet',
        fontName='Helvetica', fontSize=9.5,
        textColor=DARK, alignment=TA_LEFT, spaceAfter=1, leading=13,
        leftIndent=12, bulletIndent=0)

    s['skill_label'] = ParagraphStyle('skill_label',
        fontName='Helvetica-Bold', fontSize=9.5,
        textColor=DARK, spaceAfter=1)

    return s

def hr():
    return HRFlowable(width="100%", thickness=0.8, color=RULE, spaceAfter=4, spaceBefore=2)

def section(title, S):
    return [Paragraph(title.upper(), S['section']), hr()]

def bullet_item(text, S):
    return Paragraph(f"• {text}", S['bullet'])

# ── Document content ────────────────────────────────────────────────────────
def build():
    S = make_styles()
    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.5*cm,  bottomMargin=1.5*cm,
    )

    story = []

    # ── Header ──
    story.append(Paragraph("GEOFREY ONYANGO", S['name']))
    story.append(Paragraph(
        "0112492399  |  "
        "<a href='mailto:g31592517@gmail.com' color='blue'>g31592517@gmail.com</a>  |  "
        "<a href='https://github.com/Weejay13' color='blue'>github.com/Weejay13</a>",
        S['contact']))
    story.append(Paragraph("Seeking Software Engineering Internship (Available Immediately)", S['tagline']))

    # ── Education ──
    story += section("Education", S)
    story.append(Paragraph("<b>Kisii University</b>  –  Kisii, Kenya", S['subheading']))
    story.append(Paragraph("<i>Bachelor of Science in Software Engineering</i>  |  Current Student", S['body']))
    story.append(bullet_item(
        "<b>Relevant Coursework:</b> Data Structures &amp; Algorithms, Database Systems, "
        "Web Development, Mobile Application Development, Operating Systems, "
        "Software Testing &amp; Quality Assurance.", S))

    # ── Experience ──
    story += section("Experience", S)
    story.append(Paragraph("<b>Software Developer</b>  –  Remote / Freelance", S['subheading']))
    story.append(Paragraph("<i>Self-Employed</i>  |  Jan 2023 – Present", S['body']))
    story.append(bullet_item("Designed and developed full-stack web applications for various startups.", S))
    story.append(bullet_item("Implemented responsive designs and ensured cross-browser compatibility.", S))

    # ── Projects ──
    story += section("Key Projects", S)

    projects = [
        ("Kaifway.com",
         "React Native, React, TypeScript, Python, PostgreSQL",
         "https://kaifway.com",
         [
             "Developed a comprehensive web platform and native mobile applications (iOS/Android) accessible at kaifway.com.",
             "Implemented user authentication, database management, and dynamic content rendering across platforms.",
             "Optimised site performance and SEO rankings for better visibility.",
         ]),
        ("Ineat.co.ke",
         "React Native, Full Stack Development",
         "https://ineat.co.ke",
         [
             "Architected and built a cross-platform mobile application and web portal at ineat.co.ke.",
             "Designed intuitive user interfaces and seamless navigation flows for both mobile and web.",
             "Integrated payment gateways and order processing systems.",
         ]),
        ("Auto Trade Nation",
         "React, Vercel, Web Development",
         "https://auto-trade-nation.vercel.app",
         [
             "Developed an automotive marketplace with vehicle listing comparison, ride booking, and service scheduling.",
             "Implemented parts shopping and user profile management systems.",
         ]),
        ("Topada Market",
         "React, Vercel, Web Development",
         "https://todapa-market.vercel.app",
         [
             "Developed a digital ecosystem for a diversified African conglomerate.",
             "Implemented modern corporate branding, contact integration, and accessible UI/UX.",
         ]),
        ("Internship Scraper",
         "Python, Pandas, BeautifulSoup",
         "https://github.com/Weejay13/INTERNSHIPS",
         [
             "Built an automated tool to scrape job listings across Kenyan job boards.",
             "Implemented targeted search for 100+ NGOs and Big Tech companies.",
             "Automated data collection pipelines using Linux Cron jobs.",
         ]),
    ]

    for proj_name, stack, link, bullets in projects:
        story.append(Paragraph(
            f"<b>{proj_name}</b>  |  <i>{stack}</i>  –  "
            f"<a href='{link}' color='blue'>{link.replace('https://', '')}</a>",
            S['subheading']))
        for b in bullets:
            story.append(bullet_item(b, S))
        story.append(Spacer(1, 3))

    # ── Technical Skills ──
    story += section("Technical Skills", S)
    skills = [
        ("Languages",       "Python, TypeScript, JavaScript, SQL (PostgreSQL), HTML/CSS"),
        ("Frameworks",      "React, React Native, Node.js"),
        ("Developer Tools", "Git, Docker, VS Code, Linux/Bash"),
        ("Libraries",       "Pandas, NumPy, BeautifulSoup, Requests"),
    ]
    for label, val in skills:
        story.append(Paragraph(f"<b>{label}:</b>  {val}", S['body']))

    # ── Referees ──
    story += section("Referees", S)
    refs = [
        ("Dalmas Ongwari", "Founder &amp; CEO, Kaifway", "0746 571 585"),
        ("Pascal Oloo",    "CEO, Topada Enterprises",    "0788 996 378"),
        ("Chrispinus Oduor","Businessman",               "0724 551 343"),
    ]
    for name, role, phone in refs:
        story.append(Paragraph(f"<b>{name}</b>  –  {role}  |  {phone}", S['body']))

    doc.build(story)
    print(f"✓ Resume PDF written to: {OUTPUT_PDF}")

if __name__ == "__main__":
    build()
