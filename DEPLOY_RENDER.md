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

## 0. Pick a plan (read this first)

| | **Starter + disk** (recommended) | **Free** (try-out only) |
|---|---|---|
| Profiles, applications, CVs | **Kept** on a persistent disk | **Wiped** on every deploy, restart, or sleep |
| Sleeps when idle | No | Yes, after 15 min without traffic; the next visit waits ~1 min to wake |
| Monthly limit | none | 750 free instance-hours per workspace |
| Cost | paid instance + small disk, see [render.com/pricing](https://render.com/pricing) | free |

Render does not allow persistent disks on free web services, so students' profiles and tracked applications
only survive on a paid instance. `render.yaml` is set up for **Starter + a 1 GB disk**. To try it for free first,
see [Free-plan variant](#free-plan-variant) below.

---

## 1. Put the code on GitHub

Render deploys from a Git repository. This project's remote is `https://github.com/g31592517/Internship`.

From the project folder:
```bash
git add -A
git commit -m "Web platform + Render deployment"
git push origin main
```

> **Check before pushing:** the repo already tracks `resume/`, `resume.zip` and `src/test_send.py` (which contains
> personal email addresses and a phone number). If the GitHub repo is **public**, make it private
> (GitHub → repo → Settings → Danger Zone → Change visibility) or remove those files. Render works with private repos.
> Never commit `src/config.py` or any SMTP password; `.gitignore` already excludes `config.py` and `data/`.

## 2. Create the service from the Blueprint

1. Sign up / log in at [dashboard.render.com](https://dashboard.render.com) (signing in with GitHub is easiest).
2. If asked, let Render access your GitHub account. If the repo is private, grant access to the `Internship` repo.
3. Click **New → Blueprint**.
4. Select the **Internship** repository. Render reads `render.yaml` and shows one web service, `internship-finder`,
   with a disk `internship-data`.
5. Render asks for the two secret values, `SMTP_USER` and `SMTP_PASSWORD`.
   You can **leave both empty** for now (see step 5 to switch email on later).
6. Add a payment method if Render asks (needed for the Starter plan and the disk). Then click **Apply** / **Deploy Blueprint**.

The first build takes a few minutes (it builds the React app, then installs Python packages). Watch **Logs**.
It is ready when you see:
```
Uvicorn running on http://0.0.0.0:10000
```

## 3. Check it works

Your site is at `https://internship-finder.onrender.com` (or whatever name Render gave it; it's at the top of the service page).

1. Open `https://<your-app>.onrender.com/api/health`. You should see `{"ok":true,"email_sending":"not configured"}`.
2. Open the site, enter a course (e.g. *Software Engineering*), and click **Find Opportunities**.
   The **first search for a course takes 20–60 seconds** (it visits every job site). Repeat searches are instant for 15 minutes.
3. Under the results, click **Details** next to "Searched N of 5 sources". This shows which job sites answered from
   Render's servers (see Troubleshooting if a site that worked locally is blocked here).
4. Create a profile, apply to something with **Open Application → Yes, I applied — track it**, and check **My applications**.

## 4. Share it

Send students the `onrender.com` link. Each student creates their own profile. There are no passwords:
the browser keeps a private key to the profile, so a student must use **the same browser/device** to come back to it.
Clearing browser data loses access to that profile (they can create a new one with a different email).

## 5. (Optional) Turn on "Apply Automatically" by email

Email applications are sent from **one mailbox you control**, with the student set as *Reply-To*. With Gmail:

1. Turn on 2-Step Verification for the Gmail account.
2. Create an **App Password**: Google Account → Security → 2-Step Verification → App passwords.
3. Render → your service → **Environment** → set
   - `SMTP_USER` = the Gmail address
   - `SMTP_PASSWORD` = the 16-character app password (not the normal password)
4. **Save Changes**. Render redeploys automatically.
5. `/api/health` should now say `"email_sending":"configured"`.

Other providers: also set `SMTP_HOST`, `SMTP_PORT`, and `SMTP_SECURITY` (`ssl`, `starttls` or `none`).
Gmail caps how much one account can send per day, so for heavy use switch to a transactional email provider.
To test the whole flow without sending anything, add `APPLY_DRY_RUN` = `1`.

Students always see the exact email and must tick a confirmation box before it is sent. Each student is limited to 20 automatic applications a day.

## 6. Updating the site

Every `git push` to `main` makes Render rebuild and redeploy automatically. With a disk attached, a deploy
causes a few seconds of downtime (Render stops the old instance before starting the new one). Data on the disk is kept.

## 7. Custom domain (optional)

Render → service → **Settings → Custom Domains → Add**, then create the DNS record Render shows you at your domain
registrar. HTTPS is set up automatically.

---

## Free-plan variant

To try it without paying, edit `render.yaml` before creating the Blueprint:
```yaml
    plan: free
    # delete these four lines:
    # disk:
    #   name: internship-data
    #   mountPath: /var/data
    #   sizeGB: 1
```
Everything works, but the database and CVs are lost whenever the service restarts, redeploys, or sleeps.
After 15 idle minutes the first visitor waits about a minute.
To upgrade later, change `plan` back to `starter` and restore the `disk:` block (or do it in the dashboard), then push.

## Without the Blueprint (manual setup)

**New → Web Service** → pick the repo → **Language: Docker** → Region *Frankfurt* → Instance type *Starter* →
Advanced:
- Health Check Path: `/health`
- Add Disk: name `internship-data`, mount path `/var/data`, size 1 GB
- Environment variables: `INTERNSHIP_DATA_DIR=/var/data` (plus the optional SMTP ones)

Leave the start command empty; the Dockerfile's `CMD` already binds to `0.0.0.0:$PORT`.

---

## Environment variables reference

| Variable | Default | Purpose |
|---|---|---|
| `INTERNSHIP_DATA_DIR` | `/var/data` (in Docker) | Where the SQLite DB and CVs are stored; must be the disk mount path |
| `MAX_CONCURRENT_SCRAPES` | `2` | How many fresh course searches may scrape at once (protects the small instance and the job sites) |
| `SMTP_USER` / `SMTP_PASSWORD` | unset | Mailbox for "Apply Automatically"; unset = email sending off |
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
| Profiles/applications disappeared | You're on the free plan (no disk) or `INTERNSHIP_DATA_DIR` doesn't match the disk mount path |
| "A profile with this email already exists" | That email was registered from another browser. Use that browser, or a different email |
| "Automatic sending isn't configured" | Set `SMTP_USER` / `SMTP_PASSWORD` (step 5) |
| Email send fails with an authentication error | Use a Gmail **App Password**, not the account password; 2-Step Verification must be on |

## Security notes

- There are no user accounts. Each profile is protected by a random secret held only by the browser that created
  it. The server stores just a hash of it. Someone who only knows a profile number can't see or use that profile.
- SMTP credentials live only in Render's environment settings. They are never stored in the database or sent to browsers.
- The app never stores passwords for third-party job sites, and never bypasses CAPTCHAs or bot protection.
- Before a wider launch, consider real logins (e.g. email magic-link) so students can recover profiles on a new device.
