"""
IP Investigation module.

Public, no-API-key reconnaissance for an IPv4/IPv6 address:
  - Geolocation + network ownership (country, region, city, ISP, org,
    ASN) via ip-api.com's free endpoint (no key required; rate-limited
    to ~45 requests/min for casual use).
  - Reverse DNS (PTR) via the system/fallback resolver.
  - Basic classification: whether the address is private/reserved
    (RFC1918 etc.), which is worth flagging before anyone tries to
    "investigate" a LAN address that has no public footprint.

All entirely passive -- it never connects *to* the target IP, only
queries public databases about it. No port scanning, no probing.
"""

from __future__ import annotations

import ipaddress

from core.logger import get_logger
from core.netutils import get
from core.plugins import PluginMeta
from core.ui import banner, clear, err, info, ok, pause, prompt, section, warn

log = get_logger("ip")

MODULE_META = PluginMeta(
    key="6",
    name="IP Investigation",
    description="Geolocation, ASN/network ownership, and reverse DNS for an IP address (public sources)",
    order=60,
)


def _classify(ip_obj) -> list[str]:
    """Return human-readable notes about special-use ranges the IP falls in."""
    notes = []
    if ip_obj.is_private:
        notes.append("private / RFC1918 (no public footprint expected)")
    if ip_obj.is_loopback:
        notes.append("loopback")
    if ip_obj.is_link_local:
        notes.append("link-local")
    if ip_obj.is_reserved:
        notes.append("reserved")
    if ip_obj.is_multicast:
        notes.append("multicast")
    if getattr(ip_obj, "is_global", False):
        notes.append("globally routable")
    return notes


def _geo_lookup(ip: str) -> None:
    # ip-api.com: free, no key. Explicitly request the fields we use.
    fields = "status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,asname,reverse,mobile,proxy,hosting,query"
    result = get(f"http://ip-api.com/json/{ip}", params={"fields": fields}, expect_json=True)

    if not result.ok or not result.json_data:
        warn(f"Geolocation lookup failed ({result.error or f'HTTP {result.status_code}'}).")
        return

    data = result.json_data
    if data.get("status") != "success":
        warn(f"Geolocation service could not resolve this IP ({data.get('message', 'unknown reason')}).")
        return

    location_bits = [data.get("city"), data.get("regionName"), data.get("country")]
    location = ", ".join(b for b in location_bits if b)
    if location:
        ok(f"Location: {location}")
    if data.get("zip"):
        info(f"Postal area: {data['zip']}")
    if data.get("lat") is not None and data.get("lon") is not None:
        info(f"Coordinates (approx): {data['lat']}, {data['lon']}")
    if data.get("timezone"):
        info(f"Timezone: {data['timezone']}")

    if data.get("isp"):
        ok(f"ISP: {data['isp']}")
    if data.get("org") and data.get("org") != data.get("isp"):
        info(f"Organization: {data['org']}")
    if data.get("as"):
        info(f"ASN: {data['as']}")
    if data.get("asname"):
        info(f"AS name: {data['asname']}")

    # These flags are the closest ip-api gives to a "reputation" signal.
    flags = []
    if data.get("hosting"):
        flags.append("hosting/datacenter")
    if data.get("proxy"):
        flags.append("proxy/VPN/Tor exit")
    if data.get("mobile"):
        flags.append("mobile network")
    if flags:
        warn(f"Network type flags: {', '.join(flags)}")


def _reverse_dns(ip: str) -> None:
    try:
        import dns.resolver
        import dns.reversename
        from core.dns_helper import get_resolver
    except ImportError:
        warn("dnspython not installed -- skipping reverse DNS. Run Health Check to install.")
        return

    try:
        rev_name = dns.reversename.from_address(ip)
        answers = get_resolver().resolve(rev_name, "PTR", lifetime=6)
        names = [str(r).rstrip(".") for r in answers]
        ok(f"Reverse DNS (PTR): {', '.join(names)}")
    except dns.resolver.NXDOMAIN:
        info("No reverse DNS (PTR) record.")
    except dns.resolver.NoAnswer:
        info("No reverse DNS (PTR) record.")
    except Exception as exc:
        log.debug("Reverse DNS failed for %s: %s", ip, exc)
        warn(f"Reverse DNS lookup failed ({exc}).")


def run() -> None:
    clear()
    banner("IP INVESTIGATION")
    print("Public geolocation, network ownership (ASN), and reverse DNS.\n"
          "Passive only -- queries public databases, never contacts the IP.\n")

    raw = prompt("Enter an IP address (IPv4 or IPv6)")
    if not raw:
        warn("No IP entered. Returning to menu.")
        pause()
        return

    try:
        ip_obj = ipaddress.ip_address(raw)
    except ValueError:
        err("That doesn't look like a valid IP address.")
        pause()
        return

    ip = str(ip_obj)
    log.info("IP investigation started for %s", ip)

    section("Classification")
    notes = _classify(ip_obj)
    if notes:
        for note in notes:
            info(note)
    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
        warn("This is not a public address -- geolocation/ASN lookups will not return useful data.")
        pause()
        return
    ok("Address is publicly routable.")

    section("Geolocation & network ownership")
    try:
        _geo_lookup(ip)
    except Exception:
        log.exception("Unexpected error during geo lookup")
        err("Unexpected error during geolocation lookup.")

    section("Reverse DNS")
    try:
        _reverse_dns(ip)
    except Exception:
        log.exception("Unexpected error during reverse DNS")
        err("Unexpected error during reverse DNS lookup.")

    log.info("IP investigation complete for %s", ip)
    pause()
