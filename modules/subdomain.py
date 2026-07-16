"""
Subdomain Enumeration module.

Two entirely passive/public techniques:

  1. Certificate Transparency logs via crt.sh (https://crt.sh) -- a
     free public service that indexes CT logs every publicly-trusted
     CA is required to publish to. Any subdomain that ever had a
     public TLS certificate issued shows up here. No requests are
     made to the target at all for this phase.

  2. DNS brute force against a small built-in wordlist of common
     subdomain prefixes (www, api, mail, ...), resolved in parallel.
     This only sends ordinary DNS queries -- the same kind any
     browser/resolver sends -- no port scanning, no HTTP requests to
     unexpected hosts.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from core.logger import get_logger
from core.netutils import get
from core.plugins import PluginMeta
from core.ui import banner, clear, err, info, ok, pause, prompt, section, warn
from modules.domain import normalize_domain

log = get_logger("subdomain")

MODULE_META = PluginMeta(
    key="8",
    name="Subdomain Enumeration",
    description="Discover subdomains via certificate transparency logs (crt.sh) and parallel DNS brute force",
    order=45,
)

# Common subdomain prefixes -- deliberately small and maintainable
# rather than an exhaustive list; crt.sh usually surfaces far more
# real-world subdomains than brute force ever will, this is just a
# supplement for hosts that never got a public cert logged.
BRUTE_FORCE_WORDLIST = [
    "www", "mail", "webmail", "smtp", "pop", "imap", "ftp", "sftp",
    "admin", "administrator", "portal", "secure", "login", "sso",
    "api", "api1", "api2", "app", "apps", "dev", "develop", "staging",
    "stage", "test", "testing", "qa", "uat", "demo", "sandbox", "beta",
    "preview", "m", "mobile", "cdn", "static", "assets", "img", "images",
    "media", "video", "docs", "wiki", "forum", "support", "help", "status",
    "blog", "shop", "store", "vpn", "remote", "internal", "intranet",
    "git", "gitlab", "github", "jenkins", "ci", "build", "monitor",
    "grafana", "kibana", "db", "mysql", "sql", "ns1", "ns2", "mx",
    "autodiscover", "cpanel", "webdisk", "direct", "old", "new",
]


def _query_crtsh(domain: str) -> set[str]:
    """Query crt.sh for certs covering *.domain; return the set of subdomains found."""
    result = get(f"https://crt.sh/?q=%25.{domain}&output=json", expect_json=True)
    if not result.ok or not result.json_data:
        raise RuntimeError(result.error or f"crt.sh returned HTTP {result.status_code}")

    found: set[str] = set()
    for entry in result.json_data:
        name_value = entry.get("name_value", "")
        for name in name_value.split("\n"):
            name = name.strip().lower().lstrip("*.")
            if name and (name == domain or name.endswith("." + domain)):
                found.add(name)
    return found


def _resolve(hostname: str) -> bool:
    try:
        from core.dns_helper import get_resolver
    except ImportError:
        return False
    try:
        get_resolver().resolve(hostname, "A", lifetime=4)
        return True
    except Exception:
        return False


def _brute_force(domain: str) -> set[str]:
    candidates = [f"{word}.{domain}" for word in BRUTE_FORCE_WORDLIST]
    found: set[str] = set()
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(_resolve, host): host for host in candidates}
        for future in as_completed(futures):
            host = futures[future]
            try:
                if future.result():
                    found.add(host)
            except Exception:
                pass
    return found


def run() -> None:
    clear()
    banner("SUBDOMAIN ENUMERATION")
    print("Passive discovery via certificate transparency logs (crt.sh)\n"
          "plus a DNS brute-force pass against common subdomain names.\n")

    raw = prompt("Enter a domain (e.g. example.com)")
    if not raw:
        warn("No domain entered. Returning to menu.")
        pause()
        return

    domain = normalize_domain(raw)
    if not domain or "." not in domain:
        err("That doesn't look like a valid domain.")
        pause()
        return

    log.info("Subdomain enumeration started for %s", domain)
    all_found: set[str] = set()

    section("Certificate transparency (crt.sh)")
    try:
        ct_results = _query_crtsh(domain)
        if ct_results:
            ok(f"{len(ct_results)} unique hostname(s) found in CT logs.")
            for host in sorted(ct_results)[:200]:
                print(f"    {host}")
            if len(ct_results) > 200:
                info(f"...and {len(ct_results) - 200} more (truncated for display).")
            all_found |= ct_results
        else:
            info("No certificates found in CT logs for this domain.")
    except Exception as exc:
        log.warning("crt.sh query failed for %s: %s", domain, exc)
        warn(f"crt.sh lookup failed ({exc}). CT logs may be temporarily unavailable.")

    section(f"DNS brute force ({len(BRUTE_FORCE_WORDLIST)} common names)")
    try:
        import dns.resolver  # noqa: F401  -- just to check availability with a clear message
    except ImportError:
        err("The 'dnspython' package is not installed. Run Health Check to install dependencies.")
    else:
        try:
            brute_results = _brute_force(domain)
            new_hosts = brute_results - all_found
            if brute_results:
                ok(f"{len(brute_results)} host(s) resolved ({len(new_hosts)} new, not already in CT results).")
                for host in sorted(new_hosts):
                    print(f"    {host}")
            else:
                info("No additional hosts resolved from the brute-force list.")
            all_found |= brute_results
        except Exception:
            log.exception("Unexpected error during DNS brute force")
            err("Unexpected error during DNS brute force.")

    section("Summary")
    info(f"{len(all_found)} unique subdomain(s) discovered for {domain}.")
    log.info("Subdomain enumeration complete for %s: %d found", domain, len(all_found))

    pause()
