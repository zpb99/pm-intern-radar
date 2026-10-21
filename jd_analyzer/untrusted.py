"""Cleaning for text and links that come from third-party job postings.

Used by both outputs: the radar's Markdown report and the MCP server's JSON.
"""

import re
import unicodedata
from urllib.parse import urlparse

# Unicode categories that are invisible or move text around: control characters (Cc),
# format characters such as zero-width spaces and right-to-left overrides (Cf), and
# line/paragraph separators (Zl, Zp). They can hide or reorder text, so they become spaces.
_HIDDEN = {"Cc", "Cf", "Zl", "Zp"}

# A URL is accepted only if it is made entirely of these (RFC 3986) characters, so the
# string we check is exactly the string we pass on. Parens and brackets are excluded
# because they can end a Markdown link.
_SAFE_URL = re.compile(r"[A-Za-z0-9\-._~:/?#@!$&'*+,;=%]+")


def clean_text(value: str) -> str:
    """Replace invisible and reordering characters with spaces, then collapse runs of spaces."""
    flat = "".join(" " if unicodedata.category(ch) in _HIDDEN else ch for ch in value)
    return re.sub(r" {2,}", " ", flat).strip()


def safe_url(url: str) -> str | None:
    """The URL unchanged if it is a plain http(s) URL with a host, else None."""
    if not url or not _SAFE_URL.fullmatch(url):
        return None
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.hostname:
        return url
    return None
