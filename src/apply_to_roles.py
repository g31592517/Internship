import pandas as pd
import os
import glob
import time
import urllib.parse
import webbrowser
import smtplib
import ssl
import getpass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException

try:
    from src.config import PROFILES, GMAIL_USER, GMAIL_PASS
except ImportError:
    print("Error: src/config.py not found using 'src.config'. Trying local import...")
    try: 
        from config import PROFILES, GMAIL_USER, GMAIL_PASS
    except ImportError:
        print("CRITICAL ERROR: config.py not found. create one from src/config.sample.py")
        exit(1)

def load_cover_letter(path):
    with open(path, "r") as f:
        return f.read()

def load_applied_jobs():
    """Load the list of jobs previously applied to from a text file."""
    applied_file = "applied_jobs.txt"
    if not os.path.exists(applied_file):
        return set()
    with open(applied_file, "r") as f:
        return set(line.strip() for line in f if line.strip())

def log_applied_job(job_link):
    """Log a successfully applied job link to the text file."""
    with open("applied_jobs.txt", "a") as f:
        f.write(f"{job_link}\n")

def is_job_applied(job_link):
    """Check if a job link has already been applied to."""
    if not os.path.exists("applied_jobs.txt"):
        return False
    with open("applied_jobs.txt", "r") as f:
        applied = set(line.strip() for line in f if line.strip())
    return job_link in applied

def send_email_automatically(sender_email, sender_password, recipient_email, subject, body, attachment_path):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Attach body
        msg.attach(MIMEText(body, 'plain'))

        # Attach PDF
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        msg.attach(part)

        # Connect to Gmail SMTP
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print(f"  -> SUCCESS: Email sent to {recipient_email} with {os.path.basename(attachment_path)}")
        return True
    except Exception as e:
        print(f"  -> FAILED to send email: {e}")
        return False

def get_latest_csv(keyword):
    list_of_files = glob.glob(f'output/*{keyword}*.csv') 
    if not list_of_files:
        return None
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file

def init_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Uncomment to run headless
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    return driver

def apply_to_job(driver, job, profile, sender_email, sender_password):
    print(f"Applying to: {job['title']} at {job['company']}")
    
    # Handle CSV link formatting issues (remove trailing commas/extra data if stuck in link column)
    url = str(job['link']).split(',')[0].strip()
    
    # Check if this specific URL is in our 'applied_jobs.txt' file
    if is_job_applied(url):
        print(f"  -> Skipping: Already marked as applied.")
        return

    driver.get(url)
    time.sleep(3) # Wait for page load

    # Try to find email application
    try:
        mailto_links = driver.find_elements(By.XPATH, '//a[starts-with(@href, "mailto:")]')
        if mailto_links:
            email_link = mailto_links[0].get_attribute('href')
            target_email = email_link.replace("mailto:", "").split("?")[0].strip()
            
            # Filter out job board support emails
            if "myjobmag.co.ke" in target_email or "corporatestaffing.co.ke" in target_email or "services@" in target_email:
                print(f"  -> Skipping job board email: {target_email}")
                return

            print(f"  -> Found email: {target_email}")
            
            subject = f"Application for {job['title']} - {profile['NAME']}"
            body = load_cover_letter(profile['COVER_LETTER'])
            
            # Use Auto-Sender
            if sender_email and sender_password:
                success = send_email_automatically(
                    sender_email, sender_password, 
                    target_email, subject, body, 
                    profile['RESUME']
                )
                if success:
                    log_applied_job(url) # Log successful application
                    return # Skip form filling if email successful

            # Fallback if no sender credentials or failed
            mailto_url = f"mailto:{target_email}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
            webbrowser.open(mailto_url)
            print("  -> (Fallback) Opened email client.")
            return
    except Exception as e:
        print(f"  -> Error checking email: {e}")

    # Try to find structured form inputs
    try:
        # Common input names/ids
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for input_field in inputs:
            try:
                name_attr = input_field.get_attribute("name").lower()
                type_attr = input_field.get_attribute("type").lower()
                
                if "name" in name_attr and "first" in name_attr:
                    input_field.send_keys(profile['NAME'].split()[0])
                elif "name" in name_attr and "last" in name_attr:
                    input_field.send_keys(profile['NAME'].split()[-1])
                elif "name" in name_attr:
                    input_field.send_keys(profile['NAME'])
                elif "email" in name_attr or type_attr == "email":
                    input_field.send_keys(profile['EMAIL'])
                elif "phone" in name_attr or "tel" in name_attr:
                    input_field.send_keys(profile['PHONE'])
                elif "linkedin" in name_attr and profile['LINKEDIN']:
                    input_field.send_keys(profile['LINKEDIN'])
                elif "github" in name_attr and profile['GITHUB']:
                    input_field.send_keys(profile['GITHUB'])
                # File upload is tricky, usually requires specific path handling
                # elif type_attr == "file":
                #     input_field.send_keys(profile['RESUME'])
            except:
                pass
        
        print("  -> Filled common form fields (if found). Please review and submit manually.")
    except Exception as e:
        print(f"  -> Error form filling: {e}")

    # For web forms (since we didn't return early from email), pause for manual review/submission
    print("  -> WEB FORM DETECTED: Please review fields and click Submit manually.")
    input("  Press Enter when submit is done (or if you decide to skip/cancel) to continue...")
    log_applied_job(url) # Log as processed/applied after manual review

def main(sender_email, sender_pass):
    driver = init_driver()
    
    try:
        for key, profile in PROFILES.items():
            if profile.get('SKIP', False):
                print(f"Skipping profile: {key}")
                continue
            
            print(f"\n=== Processing Applications for {profile['NAME']} ({key}) ===")
            csv_file = get_latest_csv(profile['CSV_KEYWORD'])
            
            if not csv_file:
                print(f"No CSV files found for keyword: {profile['CSV_KEYWORD']}")
                continue

            print(f"Reading jobs from: {csv_file}")
            df = pd.read_csv(csv_file)
            
            # Filter out non-relevant jobs if needed, but CSV should separate them
            # For Hyniece (Public Admin), we iterate through her list
            # For Wesley (IT), we iterate through his list
            
            for index, row in df.iterrows():
                try:
                    apply_to_job(driver, row, profile, sender_email, sender_pass) 
                except Exception as e:
                    print(f"Critial error applying to {row.get('company', 'Unknown')}: {e}")
                    print("Attempting to restart driver...")
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = init_driver()
                    
    except KeyboardInterrupt:
        print("\nStopping application process.")
    finally:
        driver.quit()

if __name__ == "__main__":
    print(f"Starting auto-application with email: {GMAIL_USER}")
    main(GMAIL_USER, GMAIL_PASS)
