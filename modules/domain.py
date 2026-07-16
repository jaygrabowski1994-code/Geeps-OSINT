"""
Domain Investigation module.

Public DNS/WHOIS/HTTP reconnaissance only -- everything here is data
any browser or `dig`/`whois` command could retrieve. No port scanning,
no vulnerability probing, no bypassing of auth.
"""

from __future__ import annotations

import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import urlparse

from core.logger import get_logger
from core.netutils import get
from core.plugins import PluginMeta
from core.ui import banner, clear, err, info, ok, pause, prompt, section, warn

log = get_logger("domain")

MODULE_META = PluginMeta(
    key="4",
    name="Domain Investigation",
    description="DNS records, WHOIS, HTTP reachability, and TLS certificate details",
    order=40,
)

DNS_RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]


def _normalize_domain(raw: str) -> str:
    raw = raw.strip()
    if "://" in raw:
        raw = urlparse(raw).netloc or raw
    return raw.split("/")[0].lower()


def _dns_lookup(domain: str) -> None:
    try:
        import dns.resolver
    except ImportError:
        err("The 'dnspython' package is not installed. Run Health Check to install dependencies.")
        return

    for record_type in DNS_RECORD_TYPES:
        try:
            answers = dns.resolver.resolve(domain, record_type, lifetime=6)
            values = [str(r).strip() for r in answers]
            ok(f"{record_type:6} {'; '.join(values)}")
        except dns.resolver.NoAnswer:
            pass  # normal: not every domain has every record type
        except dns.resolver.NXDOMAIN:
            err(f"{domain} does not exist (NXDOMAIN).")
            return
        except Exception as exc:
            log.debug("DNS %s lookup failed for %s: %s", record_type, domain, exc)
            warn(f"{record_type:6} lookup failed ({exc})")


def _whois_lookup(domain: str) -> None:
    try:
        import whois as whois_lib
    except ImportError:
        err("The 'python-whois' package is not installed. Run Health Check to install dependencies.")
        return

    try:
        data = whois_lib.whois(domain)
    except Exception as exc:
        log.warning("WHOIS lookup failed for %s: %s", domain, exc)
        warn(f"WHOIS lookup failed ({exc}). Some registrars/TLDs block automated WHOIS.")
        return

    if not data or not getattr(data, "domain_name", None):
        warn("No WHOIS data returned (registrar may use privacy protection).")
        return

    registrar = getattr(data, "registrar", None) or "unknown"
    creation = _first(getattr(data, "creation_date", None))
    expiration = _first(getattr(data, "expiration_date", None))
    name_servers = getattr(data, "name_servers", None) or []

    info(f"Registrar: {registrar}")
    info(f"Created: {creation or 'unknown'}")
    info(f"Expires: {expiration or 'unknown'}")
    if name_servers:
        ns_list = sorted({str(ns).lower() for ns in name_servers})
        info(f"Name servers: {', '.join(ns_list)}")


def _first(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _http_headers(domain: str) -> None:
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        result = get(url, allow_404=True)
        if result.ok or result.status_code:
            ok(f"{url} responded with HTTP {result.status_code}")
            server = None
            # requests text doesn't expose headers via our simplified FetchResult,
            # so we note that a live response was received; header/TLS detail below.
            return
    warn("Site did not respond over HTTPS or HTTP.")


def _tls_cert_info(domain: str) -> None:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=6) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
    except Exception as exc:
        log.debug("TLS cert fetch failed for %s: %s", domain, exc)
        warn(f"Could not retrieve TLS certificate ({exc}).")
        return

    if not cert:
        warn("No certificate data returned.")
        return

    issuer = dict(x[0] for x in cert.get("issuer", []))
    subject = dict(x[0] for x in cert.get("subject", []))
    not_after = cert.get("notAfter")

    info(f"Subject: {subject.get('commonName', 'unknown')}")
    info(f"Issuer: {issuer.get('organizationName', issuer.get('commonName', 'unknown'))}")
    info(f"Expires: {not_after or 'unknown'}")

    if not_after:
        try:
            expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days_left = (expiry - datetime.now(timezone.utc)).days
            if days_left < 0:
                err("Certificate has EXPIRED.")
            elif days_left < 14:
                warn(f"Certificate expires soon: {days_left} days left.")
            else:
                ok(f"Certificate valid for {days_left} more days.")
        except ValueError:
            pass


# Public aliases so other modules (e.g. employment.py) can reuse these
# checks without reaching into "private" underscored names.
normalize_domain = _normalize_domain
dns_lookup = _dns_lookup
whois_lookup = _whois_lookup
tls_cert_info = _tls_cert_info


def run() -> None:
    clear()
    banner("DOMAIN INVESTIGATION")
    print("Public DNS, WHOIS, and TLS certificate reconnaissance.\n")

    raw = prompt("Enter a domain (e.g. example.com)")
    if not raw:
        warn("No domain entered. Returning to menu.")
        pause()
        return

    domain = _normalize_domain(raw)
    if not domain or "." not in domain:
        err("That doesn't look like a valid domain.")
        pause()
        return

    log.info("Domain investigation started for %s", domain)

    section("DNS records")
    try:
        _dns_lookup(domain)
    except Exception:
        log.exception("Unexpected error during DNS lookup")
        err("Unexpected error during DNS lookup -- continuing.")

    section("WHOIS")
    try:
        _whois_lookup(domain)
    except Exception:
        log.exception("Unexpected error during WHOIS lookup")
        err("Unexpected error during WHOIS lookup -- continuing.")

    section("HTTP reachability")
    try:
        _http_headers(domain)
    except Exception:
        log.exception("Unexpected error during HTTP check")
        err("Unexpected error during HTTP check -- continuing.")

    section("TLS certificate")
    try:
        _tls_cert_info(domain)
    except Exception:
        log.exception("Unexpected error during TLS check")
        err("Unexpected error during TLS check -- continuing.")

    log.info("Domain investigation complete for %s", domain)
    pause()
