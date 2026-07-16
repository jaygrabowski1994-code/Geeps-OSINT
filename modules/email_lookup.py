"""
Email Investigation module.

Performs entirely public/passive checks:
  - Syntax validation
  - MX record lookup (does the domain accept mail?)
  - Disposable/temp-mail domain check (local list)
  - Gravatar public profile presence (public API, no auth)
  - Optional Have I Been Pwned breach check IF the user supplies their
    own API key in config.json (HIBP requires a paid key as of their
    current API; the module never assumes one is present).

No inbox access, no send-a-verification-email tricks, no credential
stuffing. Purely OSINT-appropriate, publicly available signals.
"""

from __future__ import annotations

import hashlib
import re

from core.config import get as config_get
from core.logger import get_logger
from core.netutils import get
from core.plugins import PluginMeta
from core.ui import banner, clear, err, info, ok, pause, prompt, run_parallel, section, warn

log = get_logger("email")

MODULE_META = PluginMeta(
    key="2",
    name="Email Investigation",
    description="Syntax, MX, disposable-domain, Gravatar, and optional HIBP breach check",
    order=20,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Small, well-known sample of disposable-email domains. Not exhaustive --
# presented as a signal, not a verdict.
DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com",
    "trashmail.com", "yopmail.com", "getnada.com", "throwawaymail.com",
    "temp-mail.org", "fakeinbox.com", "sharklasers.com", "dispostable.com",
}


def _check_mx(domain: str) -> tuple[bool, str]:
    try:
        import dns.resolver
        from core.dns_helper import get_resolver
    except ImportError:
        return False, "dnspython not installed"

    try:
        answers = get_resolver().resolve(domain, "MX", lifetime=6)
        records = sorted((r.preference, str(r.exchange).rstrip(".")) for r in answers)
        return True, ", ".join(f"{host} (priority {pref})" for pref, host in records[:5])
    except dns.resolver.NXDOMAIN:
        return False, "domain does not exist"
    except dns.resolver.NoAnswer:
        return False, "no MX records found"
    except Exception as exc:  # timeout, no nameservers, etc.
        log.warning("MX lookup failed for %s: %s", domain, exc)
        return False, f"lookup failed ({exc})"


def _check_gravatar(email: str) -> tuple[bool, str]:
    email_hash = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
    url = f"https://www.gravatar.com/{email_hash}.json"
    result = get(url, allow_404=True)
    if result.status_code == 200:
        return True, f"https://www.gravatar.com/{email_hash}"
    if result.status_code == 404:
        return False, "no public Gravatar profile"
    return False, result.error or "inconclusive"


def _check_hibp(email: str) -> str:
    api_key = config_get("api_keys.hibp_api_key", "")
    if not api_key:
        return "skipped (no HIBP API key configured in config/config.json)"

    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
    result = get(url, headers={"hibp-api-key": api_key}, expect_json=True, allow_404=True)
    if result.status_code == 404:
        return "no breaches found"
    if result.ok and result.json_data:
        names = ", ".join(item.get("Name", "?") for item in result.json_data)
        return f"found in breaches: {names}"
    return f"lookup inconclusive ({result.error or result.status_code})"


def run() -> None:
    clear()
    banner("EMAIL INVESTIGATION")
    print("Runs passive, public checks only: syntax, MX records,\n"
          "disposable-domain match, and public Gravatar presence.\n"
          "Breach lookup runs only if you've configured an HIBP API key.\n")

    email = prompt("Enter email address to investigate")
    if not email:
        warn("No email entered. Returning to menu.")
        pause()
        return

    log.info("Email investigation started (domain only logged: %s)",
              email.split("@")[-1] if "@" in email else "invalid")

    section("Syntax validation")
    if not EMAIL_RE.match(email):
        err("This does not look like a valid email address.")
        pause()
        return
    ok("Email format is syntactically valid.")

    domain = email.rsplit("@", 1)[-1].lower()

    section("Disposable email check")
    if domain in DISPOSABLE_DOMAINS:
        warn("This domain is a known disposable/temporary email provider.")
    else:
        ok("Domain not found in local disposable-email list.")

    def _safe_mx():
        try:
            has_mx, detail = _check_mx(domain)
            if has_mx:
                ok(f"Domain accepts mail: {detail}")
            else:
                warn(f"No usable MX records ({detail}).")
        except Exception:
            log.exception("Unexpected error during MX lookup")
            err("Unexpected error during MX lookup.")

    def _safe_gravatar():
        try:
            has_gravatar, detail = _check_gravatar(email)
            if has_gravatar:
                ok(f"Public Gravatar profile found: {detail}")
            else:
                info(f"No public Gravatar profile ({detail}).")
        except Exception:
            log.exception("Unexpected error during Gravatar check")
            err("Unexpected error during Gravatar check.")

    def _safe_hibp():
        try:
            info(_check_hibp(email))
        except Exception:
            log.exception("Unexpected error during HIBP check")
            err("Unexpected error during breach check.")

    run_parallel({
        "MX record lookup": _safe_mx,
        "Gravatar public profile": _safe_gravatar,
        "Breach exposure (Have I Been Pwned)": _safe_hibp,
    })

    log.info("Email investigation complete for domain %s", domain)
    pause()
