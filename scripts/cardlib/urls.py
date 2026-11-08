"""Strict https URL parsing and the issuer -> official domain table."""

import re
import unicodedata
from types import MappingProxyType
from urllib.parse import urlsplit

# The only issuers the app covers, each with its one official domain.
ISSUER_DOMAINS = MappingProxyType({
    "Chase": "chase.com",
    "American Express": "americanexpress.com",
    "Citi": "citi.com",
    "Capital One": "capitalone.com",
    "Discover": "discover.com",
    "Wells Fargo": "wellsfargo.com",
    "Bank of America": "bankofamerica.com",
})

_LABEL = r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
_HOST = re.compile(rf"{_LABEL}(?:\.{_LABEL})*")


def _has_hidden_chars(url):
    """Whitespace, control/format chars (e.g. zero-width space) or a backslash anywhere."""
    return "\\" in url or any(
        ch.isspace() or unicodedata.category(ch)[0] in "CZ" for ch in url)


def https_host(url):
    """Return the lowercased host of a clean ``https://`` URL, or None.

    Clean means: no user/password, no backslash, whitespace or control chars,
    a plain ``[a-z0-9.-]`` host (no wildcard, IP literal or percent-escape) and
    no port other than an explicit 443.
    """
    if not isinstance(url, str) or _has_hidden_chars(url):
        return None
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return None
    if parts.scheme != "https" or not host or not _HOST.fullmatch(host):
        return None
    if parts.netloc.lower() not in (host, f"{host}:443"):
        return None  # userinfo, empty port or a port other than 443
    return host


def _under(host, domain):
    return host == domain or host.endswith("." + domain)


def is_issuer_url(url, issuer=None):
    """True when ``url`` is a clean https URL on an issuer's official domain (or subdomain).

    With ``issuer``, the domain must be that issuer's own domain.
    """
    host = https_host(url)
    if host is None:
        return False
    if issuer is not None:
        domain = ISSUER_DOMAINS.get(issuer)
        return domain is not None and _under(host, domain)
    return any(_under(host, domain) for domain in ISSUER_DOMAINS.values())
