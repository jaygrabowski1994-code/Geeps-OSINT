"""
Shared DNS resolver helper.

dnspython's module-level dns.resolver.resolve() lazily builds a
"default resolver" that reads system DNS configuration (/etc/resolv.conf
on Unix) the first time it's used. That file isn't readable inside
Termux's app sandbox on Android -- there's no root, and Android apps
don't get access to system network config files -- so every call
fails with dns.resolver.NoResolverConfiguration: cannot open
/etc/resolv.conf, even though the device's own DNS obviously works
fine (that's why WHOIS/HTTP/TLS lookups elsewhere in this toolkit,
which don't go through dnspython, work correctly on the same device).

This helper tries the normal system-configured resolver first (so
Ubuntu/most Linux/macOS are untouched), and only falls back to a
hardcoded list of public resolvers if that fails -- which is exactly
the Termux case.
"""

from __future__ import annotations

_resolver = None

# Used only as a fallback when system DNS config can't be read at all
# (e.g. Termux/Android). Not used to override a working system resolver.
FALLBACK_NAMESERVERS = ["1.1.1.1", "8.8.8.8", "1.0.0.1", "8.8.4.4"]


def get_resolver():
    """
    Return a working dns.resolver.Resolver, cached after first call.

    Tries system configuration first; falls back to well-known public
    resolvers if the system config can't be read (Termux/Android) or
    yields no nameservers.
    """
    global _resolver
    if _resolver is not None:
        return _resolver

    import dns.resolver

    try:
        resolver = dns.resolver.Resolver(configure=True)
        if not resolver.nameservers:
            raise dns.resolver.NoResolverConfiguration("no nameservers found")
    except Exception:
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = FALLBACK_NAMESERVERS

    _resolver = resolver
    return resolver
