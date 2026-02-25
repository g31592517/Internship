import os

# Copy this file to src/config.py and fill in your details

PROFILES = {
    "USER1": {
        "NAME": "Your Name",
        "EMAIL": "your.email@example.com",
        "PHONE": "+254 700 000 000",
        "LINKEDIN": "linkedin.com/in/yourprofile",
        "GITHUB": "github.com/yourusername",
        "RESUME": os.path.abspath("resume.pdf"),
        "COVER_LETTER": "resume/cover_letter_path.txt",
        "CSV_KEYWORD": "internships"
    }
}

GMAIL_USER = "your.email@gmail.com"
GMAIL_PASS = "your-app-password"

# Tracks and Companies Configuration

IT_QUERIES = [
    "Information Technology Internship",
    "Software Engineering Internship",
]

IT_TARGETED_COMPANIES = [
    "Safaricom", 
    "Google",
    "Microsoft"
]

ADMIN_QUERIES = [
    "Public Administration Internship",
    "Public Policy Internship",
]

ADMIN_TARGETED_COMPANIES = [
    "United Nations",
    "World Vision"
]
