# Internship Finder

A web app where a student enters their **course** (and optionally a **location**), sees matching internship /
attachment opportunities scraped from several Kenyan job sites, applies, and tracks the application.
It grew out of the original scraper scripts (still in `src/`, still runnable — see "Original CLI" below).

```
Source site -> Scraper adapter -> raw dict -> normalize -> Opportunity -> rank / dedupe / filter -> API -> React
(src/scrapers)                                (src/opportunity)                           (src/api)   (frontend/)
Apply:  Opportunity + student profile -> application adapter (src/applications) -> review -> confirm -> record
```

## Run it

Backend (Python 3.11+), from the project root:
```bash
python -m venv .venv
.venv/Scripts/activate            # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt                 # server deps + tests (server only: requirements-api.txt)
uvicorn api.main:app --app-dir src --port 8000      # API docs: http://127.0.0.1:8000/docs
```
Frontend (Node 18+), in a second terminal:
```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173  (proxies /api -> http://127.0.0.1:8000)
```
Single-server alternative: `npm run build` in `frontend/`, then the backend alone serves the app at http://127.0.0.1:8000.

**Put it on the web:** see [DEPLOY_RENDER.md](DEPLOY_RENDER.md) (Dockerfile + `render.yaml` Blueprint included).

Tests (offline, no network): `python -m pytest tests -q`

The first search for a course takes ~20-60 s (it queries every source and opens each promising listing);
results are cached for 15 minutes per course, and changing the location or filters does not re-scrape.

## Sending applications by email (optional)
"Apply Automatically" is offered only when the ad names an application email address. To let the server send,
set environment variables before starting it (the password is never stored in the database or sent to the browser):
```
BREVO_API_KEY=<key>  MAIL_FROM=<verified sender>   # HTTPS email API - required on Render's free plan (SMTP blocked)
SMTP_USER=you@gmail.com   SMTP_PASSWORD=<gmail app password>   # or plain SMTP where the host allows it
# optional: SMTP_HOST (smtp.gmail.com)  SMTP_PORT (465)  SMTP_SECURITY (ssl|starttls|none)
# or, as before, GMAIL_USER / GMAIL_PASS in src/config.py
APPLY_DRY_RUN=1                   # try the whole flow without sending anything
```
Without SMTP configured the button explains this and offers a pre-filled `mailto:` link instead.
The student always reviews the exact email and ticks a confirmation box before anything is sent.

## Adding a new source site
1. Create `src/scrapers/<site>.py` with a class extending `BaseScraper` (or `WordPressSource` for WordPress job
   blogs: just set `name` and `base_url`). Implement `scrape(query)` (returns dicts with `title`, `link`, `source`
   and whatever else the list page shows), optionally `build_queries(course)` and `enrich(raw)` (detail page).
2. Add the class to `SOURCE_CLASSES` in `src/scrapers/registry.py`.
Nothing else changes: normalisation, course matching, location handling, de-duplication and the UI are source-agnostic.
To support a site's own application form, add an adapter in `src/applications/adapters.py` (`SOURCE_ADAPTERS`).

## API
`GET|POST /opportunities/search` · `GET /opportunities/{id}` · `POST /profile` · `GET /profile/{id}` ·
`POST /profile/{id}/cv` · `POST /applications/preview` · `POST /applications` · `GET /applications?profile_id=` ·
`PATCH /applications/{id}` · `GET /sources` · `GET /health` (all also under `/api/...`).
There are no accounts: `POST /profile` returns a secret `token` once; the browser keeps it and sends it as
`X-Profile-Token` on every profile/application request. Without it a profile id is useless (404).

## Original CLI
The original scraper pipeline still works: copy `src/config.sample.py` to `src/config.py`, then `python src/main.py`
(CSV files in `output/`) and `python src/apply_to_roles.py` (Selenium/Gmail auto-applier).

---

# Original README

This is a Python-based automation tool to find internship opportunities in Kenya, replacing the functionality of CodeWords automation.

## Features
- Scrapes job listings from various Kenyan job boards.
- Filters for "Internship" roles.
- Saves results to a structured format (CSV/Excel).

## Setup

### Prerequisites (Linux/Debian/Ubuntu)
If you encounter errors creating a virtual environment, you may need to install the `python3-venv` package:
```bash
sudo apt install python3-venv
```

1.  Create a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Run the scraper:
    ```bash
    python src/main.py
    ```

## Target Sites
The scraper operates in three phases:

1.  **Broad Job Boards**:
    - MyJobMag (Primary Source)
    - Corporate Staffing Services
    - CareerJet

2.  **Direct Company Sites**:
    - Microsoft Careers
    - KCB Group

3.  **Targeted Company Search (via Aggregators)**:
    - Scans specifically for "Safaricom", "Google", "Equity Bank", "Absa", "Oracle", "Cisco", and 40+ other major companies.

## Automation
The project is configured to run automatically every 30 minutes via checking `cron`.
- Logs are located in `scraper.log`
- Outputs are saved to `output/` with timestamps.

## Configuration
1. Copy the sample config file:
    ```bash
    cp src/config.sample.py src/config.py
    ```
2. Edit `src/config.py` with your personal details (Name, Email, Phone, Resume Path) and Google App Password.

## Important
Do not commit `src/config.py` or `output/` files to the repository. They are ignored by default.
