"""
Employment Investigation module.

Scope, by design: this module ONLY works with information a person or
company has already made publicly visible, and it never logs into or
scrapes platforms that require authentication or prohibit automated
access (e.g. LinkedIn's ToS forbids scraping). Instead it:

  1. Builds direct, pre-filled search-engine queries a human can open
     to review public professional profiles and news mentions.
  2. If given a claimed employer name/domain, runs a public WHOIS/DNS/
     TLS check on that company's domain (via the domain module) so you
     can sanity-check "does this company's web presence look real and
     currently active" -- useful for spotting fake employer claims.

It does not attempt to defeat CAPTCHAs, log in anywhere, or bulk-scrape
any social network.
"""

from __future__ import annotations

from urllib.parse import quote_plus

from core.logger import get_logger
from core.ui import banner, clear, info, ok, pause, prompt, section, warn
from modules import domain as domain_module

log = get_logger("employment")


def _build_search_links(full_name: str, employer: str | None) -> list[tuple[str, str]]:
    name_q = quote_plus(full_name)
    links = [
        ("LinkedIn (public search results)", f"https://www.google.com/search?q=site:linkedin.com/in+{name_q}"),
        ("General web search", f"https://www.google.com/search?q=%22{name_q}%22"),
        ("News mentions", f"https://news.google.com/search?q=%22{name_q}%22"),
    ]
    if employer:
        employer_q = quote_plus(employer)
        links.append(
            ("Name + employer search",
             f"https://www.google.com/search?q=%22{name_q}%22+%22{employer_q}%22")
        )
        links.append(
            ("Company press/about pages",
             f"https://www.google.com/search?q=%22{employer_q}%22+(press+OR+about+OR+team)")
        )
    return links


def run() -> None:
    clear()
    banner("EMPLOYMENT INVESTIGATION")
    print("Uses only publicly available information: this generates direct\n"
          "search links to public profiles/news, and can verify a claimed\n"
          "employer's public web presence. It does not log into or scrape\n"
          "any authenticated platform (e.g. LinkedIn).\n")

    full_name = prompt("Enter the person's full name")
    if not full_name:
        warn("No name entered. Returning to menu.")
        pause()
        return

    employer = prompt("Claimed employer name (optional, Enter to skip)", required=False)
    employer_domain = prompt("Claimed employer website/domain (optional, Enter to skip)", required=False)

    log.info("Employment investigation started")

    section("Public search links")
    for label, url in _build_search_links(full_name, employer or None):
        info(f"{label}:")
        print(f"    {url}")

    if employer_domain:
        section(f"Employer domain sanity check: {employer_domain}")
        try:
            domain = domain_module.normalize_domain(employer_domain)
            domain_module.dns_lookup(domain)
            domain_module.whois_lookup(domain)
            domain_module.tls_cert_info(domain)
        except Exception:
            log.exception("Unexpected error during employer domain check")
            warn("Unexpected error checking employer domain -- see log for details.")
    else:
        section("Employer domain sanity check")
        info("Skipped (no employer domain provided).")

    ok("Open the links above in a browser to review public results manually.")
    log.info("Employment investigation complete")
    pause()
