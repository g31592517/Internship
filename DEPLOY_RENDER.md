# Deploying Internship Finder on Render

This puts the whole platform (React website + Python API + scrapers + database) on the web as **one Render
Web Service** built from the `Dockerfile` in this repo. The repo already contains everything Render needs:

| File | What it does |
|---|---|
| `Dockerfile` | Builds the React app, installs the Python backend, starts `uvicorn` on Render's `$PORT` |
| `render.yaml` | Render *Blueprint*: service type, plan, region, health check, persistent disk, environment variables |
| `.dockerignore` | Keeps local junk (`.venv`, `node_modules`, `data/`, your resume…) out of the image |
| `requirements-api.txt` | Only the packages the server needs |

```
Browser ──https──▶ Render web service (one container)
                     ├─ /            the built React app
                     ├─ /api/...     FastAPI (search, profile, applications)
                     ├─ scrapers ──▶ MyJobMag, Corporate Staffing, Career Point Kenya, BrighterMonday, …
                     └─ /var/data    persistent disk: SQLite database + uploaded CVs
```

---

## 0. Plans: what the free plan means

`render.yaml` is set up for Render's **free** plan.

| | **Free** (current setup) | **Starter + disk** (to keep data) |
|---|---|---|
| Profiles, tracked applications, CVs | **Wiped** whenever the service sleeps, restarts or redeploys. Each visitor's browser re-creates their profile automatically; they re-upload their CV, and tracked applications start empty | **Kept** on a persistent disk |
| Sleeps when idle | Yes, after 15 min without traffic; the next visit waits ~1 min to wake | No |
| Email sending | Only through an HTTPS email API (**Brevo**). Render's free plan blocks SMTP ports 465/587, so Gmail SMTP **cannot** work | Brevo or Gmail SMTP |
| Monthly limit | 750 free instance-hours per workspace | none |
| Cost | free | paid instance + small disk, see [render.com/pricing](https://render.com/pricing) |

To upgrade later, see [Keeping data (upgrade)](#keeping-data-upgrade).

---

## 1. Code on GitHub

Render deploys from `https://github.com/g31592517/Internship` (branch `main`). After any change: `git push origin main`.

> The repo also tracks `resume/`, `resume.zip` and `src/test_send.py` (personal email addresses and a phone number).
> If the GitHub repo is **public**, make it private (GitHub → repo → Settings → Change visibility). Render works with
> private repos. Never commit API keys or passwords.

## 2. Create the service from the Blueprint

1. Sign up / log in at [dashboard.render.com](https://dashboard.render.com) (**Sign in with GitHub** is easiest).
2. Click **New → Blueprint**. If asked, connect GitHub and give Render access to the `Internship` repository.
3. Select **Internship**. Render reads `render.yaml` and shows one web service, `internship-finder` (plan: Free).
4. It asks for `BREVO_API_KEY` and `MAIL_FROM`. **Leave both empty for now**; email is set up in step 5.
5. Click **Deploy Blueprint**. The first build takes a few minutes. It's ready when the **Logs** show
   `Uvicorn running on http://0.0.0.0:10000`.

## 3. Check it works

Your site is at the address shown at the top of the service page, e.g. `https://internship-finder.onrender.com`.

1. Open `https://<your-app>.onrender.com/api/health`. You should see `{"ok":true,"email_sending":"off"}`.
2. Open the site, enter a course (e.g. *Software Engineering*), and click **Find Opportunities**.
   The **first search for a course takes 20–60 seconds**. Repeat searches are instant for 15 minutes.
3. Under the results, click **Details** next to "Searched N of 5 sources" to see which job sites answered Render.
4. Create a profile, open an opportunity, use **Open Application → Yes, I applied — track it**, and check **My applications**.

## 4. Share it

Send the `onrender.com` link. Each visitor creates their own profile (no password; the browser keeps a private key to it,
so they come back on the **same browser**).

## 5. Let every visitor apply by email (Brevo)

How "Apply Automatically" works: the visitor reviews the email and ticks a confirmation box, and then the platform sends it
**from your one verified sender address, under the visitor's name, with Reply-To set to the visitor's own email**.
The employer sees the student's name, the email body includes the student's email address, and pressing *Reply* goes
straight to the student. Visitors don't need any account or password; their profile email is used automatically.
Each visitor can also choose **"Open it in my email app"** to send it from their own mailbox instead.

1. Create a free account at [brevo.com](https://www.brevo.com).
2. **Add and verify a sender**: Brevo → **Senders, Domains & Dedicated IPs → Senders → Add a sender**. Use an address
   you own (e.g. a new Gmail made for the platform) and confirm it from the email Brevo sends you.
   (Emails sent "from" a gmail.com address through another service are more likely to land in spam. If you own a domain,
   authenticate it in Brevo → **Domains** and use an address on it.)
3. **Create an API key**: Brevo → **SMTP & API → API keys → Generate a new API key**. Copy it (shown only once).
4. Check Brevo → your name (top right) → **Security → Authorized IPs**: **"Block unknown IP addresses" must be OFF**,
   because Render's server IP isn't known in advance.
5. Render → your service → **Environment** → set
   - `BREVO_API_KEY` = the key from step 3
   - `MAIL_FROM` = the verified sender address from step 2
   → **Save Changes** (Render redeploys).
6. `/api/health` should now say `"email_sending":"configured (brevo)"`.
7. Test it: create a profile **with your own email** and apply to an opportunity that shows **Email application**.
   *Careful: this sends a real email to that employer.* To try it without sending, also add `APPLY_DRY_RUN` = `1`
   (remove it afterwards).

Limits: Brevo's free plan has a daily sending limit (check brevo.com/pricing). Each visitor is capped at
20 automatic applications per day, and every send needs the visitor's explicit confirmation.
If sending isn't configured, visitors still get the "Open it in my email app" option.

## 6. Updating the site

Every `git push` to `main` makes Render rebuild and redeploy automatically (on the free plan this also clears the data).

## 7. Custom domain (optional)

Render → service → **Settings → Custom Domains → Add**, then create the DNS record Render shows at your domain registrar.
HTTPS is set up automatically.

---

## Keeping data (upgrade)

Change the service to **Starter** and add a persistent disk: Render → service → **Settings → Instance Type → Starter**,
then **Disks → Add disk** with mount path `/var/data` and size 1 GB (or set `plan: starter` and the `disk:` block shown in
`render.yaml`, then push). `INTERNSHIP_DATA_DIR` is already `/var/data`. On a paid plan Gmail SMTP also works
(`SMTP_USER` / `SMTP_PASSWORD` with a Gmail App Password) if you prefer it to Brevo.

## Without the Blueprint (manual setup)

**New → Web Service** → pick the repo → **Language: Docker** → Region *Frankfurt* → Instance type *Free* →
Advanced: Health Check Path `/health`; Environment variables `INTERNSHIP_DATA_DIR=/var/data` (plus `BREVO_API_KEY`
and `MAIL_FROM` for email). Leave the start command empty; the Dockerfile's `CMD` already binds to `0.0.0.0:$PORT`.

---

## Environment variables reference

| Variable | Default | Purpose |
|---|---|---|
| `INTERNSHIP_DATA_DIR` | `/var/data` (in Docker) | Where the SQLite DB and CVs are stored; must be the disk mount path |
| `MAX_CONCURRENT_SCRAPES` | `2` | How many fresh course searches may scrape at once (protects the small instance and the job sites) |
| `BREVO_API_KEY` / `MAIL_FROM` | unset | Email via Brevo's HTTPS API (works on the free plan); `MAIL_FROM` = verified sender |
| `SMTP_USER` / `SMTP_PASSWORD` | unset | Email via SMTP instead (paid plans only: free plan blocks SMTP ports) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_SECURITY` | `smtp.gmail.com` / `465` / `ssl` | Non-Gmail providers |
| `APPLY_DRY_RUN` | unset | `1` = run the apply flow without sending email |
| `ALLOWED_ORIGINS` | localhost dev URLs | Only needed if you host the frontend on a *different* domain than the API |
| `PORT` | set by Render (`10000`) | Don't set it yourself |

## Backups

Render snapshots disks every 24 hours and keeps them for 7 days (service → **Disks**).
For your own copy: service → **Shell**, then
```bash
python -c "import sqlite3; sqlite3.connect('/var/data/app.db').backup(sqlite3.connect('/var/data/backup.db'))"
```
(or download `/var/data/app.db` while traffic is quiet).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Build fails at `npm ci` | `frontend/package-lock.json` must be committed. Run `npm install` in `frontend/` and commit the lock file |
| Health check fails / "No open ports detected" | The app must listen on `0.0.0.0:$PORT`; the Dockerfile does this. Don't override the start command |
| Site works but every search finds 0 results | Job sites may block requests from cloud servers. Open **Details** under the results: `blocked` = bot protection (we don't bypass it), `unavailable` = site down or changed. Check the service **Logs** too |
| A source works locally but is blocked on Render | Same cause, from datacenter IPs. Try another region, or accept that source is unavailable from the server |
| Search spins ~1 minute | Normal for the first search of a course (or after the free plan wakes up). Cached for 15 min afterwards |
| Profiles/applications disappeared | Expected on the free plan (no disk): profiles are restored by each browser, tracking resets. Upgrade to keep data |
| "A profile with this email already exists" | That email was registered from another browser. Use that browser, or a different email |
| "Automatic sending isn't configured" | Set `BREVO_API_KEY` and `MAIL_FROM` (step 5) |
| "The email service refused the message (HTTP 401…)" | Wrong `BREVO_API_KEY`, or Brevo is blocking unknown IPs (step 5.4) |
| "…refused the message (HTTP 400…)" mentioning the sender | `MAIL_FROM` isn't a verified sender in Brevo |
| SMTP times out on Render | Free plan blocks SMTP ports; use Brevo |

## Security notes

- There are no user accounts. Each profile is protected by a random secret held only by the browser that created
  it. The server stores just a hash of it. Someone who only knows a profile number can't see or use that profile.
- Email API keys / SMTP credentials live only in Render's environment settings. They are never stored in the database or sent to browsers.
- The app never stores passwords for third-party job sites, and never bypasses CAPTCHAs or bot protection.
- Before a wider launch, consider real logins (e.g. email magic-link) so students can recover profiles on a new device.
