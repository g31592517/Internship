# Internship Job Scraper

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
