# Geeps OSINT Hub -- Command Cheat Sheet

Quick reference for running, updating, and troubleshooting the toolkit
on Termux (Android) and Ubuntu/Debian.

---

## Launch

```bash
cd ~/Geeps-OSINT
python osint.py                 # interactive menu
python osint.py --list-modules  # list all modules without opening the menu
```

`--list-modules` is the fastest way to confirm which build you're
running: if it shows 10 modules with keys 1-10 in order, you're current.

---

## Menu options at a glance

| Key | Module | Input you'll be asked for | Needs internet? |
|-----|--------|---------------------------|-----------------|
| 1 | Username Investigation | a username | yes |
| 2 | Email Investigation | an email address | yes (MX/Gravatar) |
| 3 | Phone Investigation | a phone number with country code, e.g. `+14155552671` | no (core checks are offline) |
| 4 | Domain Investigation | a domain, e.g. `example.com` | yes |
| 5 | Subdomain Enumeration | a domain | yes |
| 6 | IP Investigation | an IP address (v4 or v6) | yes |
| 7 | Image Metadata (EXIF) | a path to a local image file | no |
| 8 | Employment Investigation | a full name (+ optional employer) | yes (domain check only) |
| 9 | Tool Manager | nothing -- just lists installed tools | no |
| 10 | Health Check | nothing -- runs diagnostics | yes (connectivity test) |

Press `0` to exit. Press Enter at any "Press Enter to return..." prompt
to go back to the menu. Ctrl+C bails out of a running module.

---

## Finding a photo for the EXIF module (Termux)

```bash
termux-setup-storage                      # one-time: grant the storage popup
ls ~/storage/shared/DCIM/Camera/ | head   # list your camera photos
ls -t ~/storage/shared/DCIM/Camera/*.jpg | head -1   # newest photo's full path
```

Paste the full path it prints into menu option 7. Use a photo taken by
your own camera app with location on -- social-media/downloaded images
usually have their metadata stripped.

---

## Updating to a new version

If you use Git (recommended):

```bash
cd ~/Geeps-OSINT
git pull
```

If you're unzipping a build instead:

```bash
cd ~
ls -t ~/storage/downloads/Geeps-OSINT*.zip | head -1   # find the NEWEST zip
# confirm it's the right one before extracting:
unzip -l "$(ls -t ~/storage/downloads/Geeps-OSINT*.zip | head -1)" | grep -E "ip_lookup|exif_lookup"
# then extract it over the repo:
unzip -o "$(ls -t ~/storage/downloads/Geeps-OSINT*.zip | head -1)"
cd Geeps-OSINT
python osint.py --list-modules            # verify 10 modules, keys 1-10
```

After extracting a new build, commit it so GitHub stays in sync:

```bash
git add -A
git commit -m "Update"
git push
```

Tidy up old downloads so you never re-extract a stale one:

```bash
rm ~/storage/downloads/Geeps-OSINT*.zip
```

---

## Installing dependencies

```bash
cd ~/Geeps-OSINT
pip install -r requirements.txt
```

If a package won't build on Termux, install a build toolchain and retry:

```bash
pkg install clang libffi openssl rust
pip install -r requirements.txt
```

Or just launch the app and run **Health Check (10)** -- it detects
missing packages and offers to install them.

---

## Optional external tools

These unlock extra coverage but aren't required. Menu option 9 (Tool
Manager) shows which are detected.

```bash
pip install sherlock-project     # Username: 400+ sites
pip install maigret              # Username: 3000+ sites
pkg install exiftool             # Image metadata (preferred over Pillow)
# PhoneInfoga: see https://github.com/sundowndev/phoneinfoga (prebuilt binaries)
```

---

## Optional API keys

Edit `config/config.json` (created automatically on first run):

```json
{
  "api_keys": {
    "hibp_api_key": "",       // Email: breach exposure (Have I Been Pwned, paid)
    "numverify_api_key": ""   // Phone: live carrier/line verification (free tier)
  }
}
```

This file is gitignored -- your keys never get committed.

---

## Reports

After any module finishes, you'll be asked whether to save a report.
Saying yes writes two files to `reports/`:

- `.html` -- open in a browser; use Print -> Save as PDF for a PDF copy
- `.json` -- structured data for scripting

```bash
ls -t ~/Geeps-OSINT/reports/ | head        # your most recent reports
```

The `reports/` folder is gitignored (reports can name who/what you
investigated).

---

## Troubleshooting

**"Invalid option" when picking a menu number that's shown**
Stale bytecode cache after an update. Clear it:

```bash
cd ~/Geeps-OSINT
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
python osint.py
```

**DNS lookups fail with "cannot open /etc/resolv.conf"**
You're on an old build -- this was fixed. Update (see above) and confirm
`core/dns_helper.py` exists:

```bash
ls ~/Geeps-OSINT/core/dns_helper.py
```

**"nothing to commit" when you expected changes**
The new files weren't extracted over the repo. Re-run the unzip step,
then `git status` should show the changes.

**Logs with full error detail** (when an on-screen message is short):

```bash
tail -f ~/Geeps-OSINT/logs/geeps-osint.log
```

**Check everything at once**: run Health Check (menu option 10).
