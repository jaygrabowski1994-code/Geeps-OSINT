# Geeps OSINT Hub

A modular, terminal-based OSINT (Open Source Intelligence) toolkit. Every
module works only with **publicly available information** -- no
credential stuffing, no authenticated scraping, no bypassing platform
protections. It's meant for legitimate research, digital-footprint
self-audits, and public-record verification.

## Features

| Menu | Module | What it does |
|---|---|---|
| 1 | Username Investigation | Checks a username across 55 major public platforms in parallel, with optional handoff to [Sherlock](https://github.com/sherlock-project/sherlock) (400+ sites) and [Maigret](https://github.com/soxoj/maigret) (3000+ sites), with results parsed into clean, consistent output |
| 2 | Email Investigation | Syntax validation, MX record lookup, disposable-domain check, public Gravatar lookup, optional HIBP breach check -- network checks run in parallel |
| 3 | Phone Investigation | Offline validation, region, timezone, and carrier metadata via libphonenumber; optional numverify live verification; optional [PhoneInfoga](https://github.com/sundowndev/phoneinfoga) handoff if installed |
| 4 | Domain Investigation | DNS records, WHOIS, HTTP reachability, and TLS certificate details -- all four run in parallel |
| 5 | Subdomain Enumeration | Passive discovery via certificate transparency logs (crt.sh) plus a parallel DNS brute force against common subdomain names |
| 6 | IP Investigation | Geolocation, network ownership (ISP/org/ASN), and reverse DNS for an IP address via public no-key sources; flags hosting/proxy/mobile networks |
| 7 | Image Metadata (EXIF) | Extracts embedded metadata (camera, timestamps, and GPS coordinates) from a local image via exiftool, with a Pillow fallback; surfaces GPS as a map link |
| 8 | Employment Investigation | Generates public search links (name/employer) and verifies a claimed employer's public web presence -- never scrapes LinkedIn or any authenticated platform |
| 9 | Tool Manager | Read-only inventory of which external OSINT tools (Sherlock, PhoneInfoga, Maigret, Amass, etc.) are installed on this system |
| 10 | Health Check | Verifies Python version, dependencies, config, logging, network connectivity, and which plugins loaded; can auto-install missing packages |

Every module:
- Has isolated error handling -- one failed lookup never crashes the app
- Logs to `logs/geeps-osint.log` (rotating, gitignored)
- Reads settings/API keys from `config/config.json` (gitignored; created
  automatically from `config/config.example.json` on first run)
- Works with **zero API keys and zero external tools installed** --
  optional keys/tools only unlock extra enrichment
- Can save its output as a report (see below) -- no per-module code
  needed for this, it's automatic

## Report generation

After any module finishes, you'll be asked whether to save a report.
Say yes and you get two files in `reports/` (gitignored -- reports can
contain the person/domain/number you investigated):

- **`.html`** -- a styled, self-contained report you can open in any
  browser. Use the browser's own **Print → Save as PDF** to get a PDF
  copy; this avoids pulling in a native PDF-rendering dependency (e.g.
  WeasyPrint needs system Cairo/Pango libraries that are painful to
  install on Termux) just to reproduce what a browser already does.
- **`.json`** -- the same data, structured, for scripting or archival.

## Optional external tools

Two menus offer to hand off to a well-known external tool if it's
installed, instead of reimplementing it:

- **Sherlock / Maigret** (Username Investigation) -- Sherlock checks
  400+ sites, Maigret 3000+, versus this toolkit's own 55-site
  built-in list. Both are offered if installed, and their results are
  parsed into the same clean output format as the built-in checks.
  Install: `pipx install sherlock-project` and/or `pip install maigret`
- **PhoneInfoga** (Phone Investigation) -- runs additional scanners
  (VoIP/OVH detection, footprint search-link generation). Note: this
  upstream project describes itself as stable but unmaintained.
  Install: see [releases](https://github.com/sundowndev/phoneinfoga) for
  prebuilt binaries, or use their Docker image.
- **exiftool** (Image Metadata) -- the preferred EXIF backend; if it's
  not installed, the module falls back to Pillow for standard EXIF.
  Install: Termux `pkg install exiftool`, Ubuntu
  `sudo apt install libimage-exiftool-perl`.

Both are entirely optional -- every module works fully without them,
and the app only ever offers to run them, never auto-runs them.
**Tool Manager** (menu 7) shows which external tools it can currently
see on your `PATH`.

## Requirements

- Python 3.8+
- Internet access for most modules (Phone Investigation's core checks
  work fully offline)

## Installation

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

git clone https://github.com/<your-username>/Geeps-OSINT.git
cd Geeps-OSINT

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python3 osint.py
```

If you'd rather not use a virtual environment, the app will still work --
its built-in Health Check / dependency checker will offer to install
missing packages for you (falling back to `--break-system-packages` on
newer Debian/Ubuntu releases that block system-wide pip installs by
default).

Optional external tools:

```bash
# Sherlock (username enumeration across 400+ sites)
python3 -m pip install --user pipx && pipx install sherlock-project

# PhoneInfoga (additional phone number scanners)
# Prebuilt binaries / Docker image: https://github.com/sundowndev/phoneinfoga
```

### Termux (Android)

```bash
pkg update && pkg upgrade -y
pkg install -y python git

# Some packages (e.g. python-whois, dnspython) need a working build
# toolchain on some Termux setups:
pkg install -y clang libffi openssl rust

git clone https://github.com/<your-username>/Geeps-OSINT.git
cd Geeps-OSINT

pip install --upgrade pip
pip install -r requirements.txt

python osint.py
```

If any package fails to build on Termux, run the app anyway (`python
osint.py`) and use menu option **6 (Health Check)** -- it will detect
what's missing and attempt to install it automatically.

Optional external tools on Termux:

```bash
# Sherlock
pip install pipx && pipx install sherlock-project

# PhoneInfoga: no official Termux/Android build; the Go binary can
# sometimes be built from source with `pkg install golang`, but this
# is unsupported by the upstream project. Skip it on Termux if this
# doesn't work cleanly -- Phone Investigation's other checks all work
# fine without it.
```

## Configuration

On first run, `config/config.json` is created automatically from
`config/config.example.json`. Optional API keys go here:

```json
{
  "api_keys": {
    "hibp_api_key": "",
    "hunter_io_api_key": "",
    "numverify_api_key": ""
  }
}
```

- **hibp_api_key** -- [Have I Been Pwned](https://haveibeenpwned.com/API/Key)
  (paid key). Unlocks breach-exposure checks in Email Investigation.
- **numverify_api_key** -- [numverify.com](https://numverify.com/) free
  tier available. Unlocks live carrier/line-type verification in Phone
  Investigation.

`config/config.json` is gitignored -- your keys never get committed.

## Project layout

```
Geeps-OSINT/
├── osint.py                    # Entry point
├── core/
│   ├── config.py                # Config loading (config/config.json)
│   ├── logger.py                # Rotating file + console logging
│   ├── dependencies.py          # Startup dependency check / auto-install
│   ├── netutils.py              # Shared HTTP helper (timeouts, retries)
│   ├── dns_helper.py            # Resolver with public-DNS fallback (Termux/Android fix)
│   ├── plugins.py               # Plugin discovery/registry -- see "Plugin system" below
│   ├── report.py                # Report engine (HTML/JSON) -- see "Report generation" above
│   ├── tools.py                 # External-tool detection (used by Tool Manager)
│   ├── sherlock_runner.py       # Optional Sherlock launcher + result parser
│   ├── maigret_runner.py        # Optional Maigret launcher (shares Sherlock's parser)
│   ├── phoneinfoga_runner.py    # Optional PhoneInfoga subprocess launcher
│   └── ui.py                    # Shared terminal UI, width-aware wrapping, parallel-run helper, report hooks
├── modules/                     # Each file here = one auto-discovered menu entry
│   ├── menu.py                  # (not a plugin -- builds the menu from the registry)
│   ├── username.py
│   ├── email_lookup.py
│   ├── phone.py
│   ├── domain.py
│   ├── subdomain.py
│   ├── ip_lookup.py
│   ├── exif_lookup.py
│   ├── employment.py
│   ├── tool_manager.py
│   └── health.py
├── config/
│   └── config.example.json
├── requirements.txt
├── logs/                        # created at runtime, gitignored
└── reports/                     # created on demand, gitignored
```

## Plugin system

Menu entries aren't hardcoded -- `osint.py` and `modules/menu.py` build
the menu at startup by scanning `modules/` for any file that exposes a
`MODULE_META` object and a `run()` function. Adding a new investigation
module is a **one-file operation**:

```python
# modules/my_new_module.py
from core.plugins import PluginMeta
from core.ui import banner, clear, ok, pause

MODULE_META = PluginMeta(
    key="9",                 # menu key; "0" is reserved for Exit
    name="My New Module",
    description="One-line summary shown in the menu and --list-modules",
    order=100,                # lower numbers appear higher in the menu
)

def run() -> None:
    clear()
    banner("MY NEW MODULE")
    ok("Do your investigation here.")
    pause()
```

Drop that file in `modules/` and it appears in the menu on the next
run -- no edits to `menu.py` or `osint.py` needed. Its output is
automatically eligible for report saving too, for free.

**Two rules that keep discovery and reports safe:**

1. Only do lightweight work (defining functions/constants) at module
   scope. Import third-party packages (`requests`, `dnspython`,
   `phonenumbers`, ...) *inside* `run()` or a helper function, not at
   the top of the file. That way, if your module's dependency isn't
   installed, it fails to load cleanly and shows up flagged in Health
   Check -- instead of crashing every other module too.
2. Use `core.ui`'s `ok()`/`warn()`/`err()`/`info()`/`section()`/
   `prompt()` for all output instead of raw `print()` where you want
   it to show up in a saved report. Plain `print()` still works, it
   just won't appear in the HTML/JSON report.

If your module runs several independent network checks, use
`core.ui.run_parallel()` to run them concurrently with clean, ordered
output (see `modules/domain.py` for an example) instead of a raw
`ThreadPoolExecutor`, which would interleave output from different
checks into a mess.

Run `python3 osint.py --list-modules` any time to see every discovered
module, including ones that failed to load and why.

## Ethical use

This toolkit is built to only touch publicly reachable, unauthenticated
data sources. Use it only on people/organizations you have a legitimate
reason to research (yourself, your own attack surface, consenting
research subjects, public-record due diligence, etc.) and in compliance
with the terms of service of every site involved and applicable law in
your jurisdiction.

## Troubleshooting

Run **Health Check** (menu option 6) first for any issue -- it checks
Python version, every dependency, config validity, log directory
writability, basic network/DNS connectivity, and which plugins loaded
successfully, and can auto-install missing packages.

You can also run `python3 osint.py --list-modules` to see every
discovered module without starting the interactive menu -- useful for
confirming a new drop-in module registered correctly.

Logs with full stack traces are always written to
`logs/geeps-osint.log`, even when the on-screen message is short.
