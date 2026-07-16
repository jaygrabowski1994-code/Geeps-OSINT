# Geeps OSINT Hub

A modular, terminal-based OSINT (Open Source Intelligence) toolkit. Every
module works only with **publicly available information** -- no
credential stuffing, no authenticated scraping, no bypassing platform
protections. It's meant for legitimate research, digital-footprint
self-audits, and public-record verification.

## Features

| Menu option | Module | What it does |
|---|---|---|
| 1 | Username Investigation | Checks a username's presence across major public platforms (GitHub, Reddit, Steam, etc.) via unauthenticated profile URLs |
| 2 | Email Investigation | Syntax validation, MX record lookup, disposable-domain check, public Gravatar lookup, optional HIBP breach check |
| 3 | Phone Investigation | Offline validation, region, timezone, and carrier metadata via libphonenumber; optional live verification |
| 4 | Domain Investigation | DNS records, WHOIS, HTTP reachability, TLS certificate details |
| 5 | Employment Investigation | Generates public search links (name/employer) and verifies a claimed employer's public web presence -- never scrapes LinkedIn or any authenticated platform |
| 6 | Health Check | Verifies Python version, dependencies, config, logging, and network connectivity; can auto-install missing packages |

Every module:
- Has isolated error handling -- one failed lookup never crashes the app
- Logs to `logs/geeps-osint.log` (rotating, gitignored)
- Reads settings/API keys from `config/config.json` (gitignored; created
  automatically from `config/config.example.json` on first run)
- Works with **zero API keys configured** -- optional keys only unlock
  extra enrichment (HIBP breach data, numverify live carrier lookup)

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
├── osint.py              # Entry point
├── core/
│   ├── config.py          # Config loading (config/config.json)
│   ├── logger.py          # Rotating file + console logging
│   ├── dependencies.py    # Startup dependency check / auto-install
│   ├── netutils.py        # Shared HTTP helper (timeouts, retries)
│   ├── plugins.py         # Plugin discovery/registry -- see "Plugin system" below
│   └── ui.py               # Shared terminal UI helpers
├── modules/                # Each file here = one auto-discovered menu entry
│   ├── menu.py             # (not a plugin -- builds the menu from the registry)
│   ├── username.py
│   ├── email_lookup.py
│   ├── phone.py
│   ├── domain.py
│   ├── employment.py
│   └── health.py
├── config/
│   └── config.example.json
├── requirements.txt
└── logs/                  # created at runtime, gitignored
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
    key="8",                 # menu key; "0" is reserved for Exit
    name="My New Module",
    description="One-line summary shown in the menu and --list-modules",
    order=80,                # lower numbers appear higher in the menu
)

def run() -> None:
    clear()
    banner("MY NEW MODULE")
    ok("Do your investigation here.")
    pause()
```

Drop that file in `modules/` and it appears in the menu on the next
run -- no edits to `menu.py` or `osint.py` needed.

**One rule to keep discovery safe:** only do lightweight work (defining
functions/constants) at module scope. Import third-party packages
(`requests`, `dnspython`, `phonenumbers`, ...) *inside* `run()` or a
helper function, not at the top of the file. That way, if your module's
dependency isn't installed, it fails to load cleanly and shows up
flagged in Health Check -- instead of crashing every other module too.

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
