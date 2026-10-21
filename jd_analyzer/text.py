"""Turn job-board HTML into readable plain text."""

import html
import re
from html.parser import HTMLParser

_OTHER_BREAKS = re.compile(r"[\x0b\x0c\x1c-\x1e\x85\u2028\u2029]")

# Tags that end a line of text when they close.
_BLOCK_TAGS = {"p", "div", "li", "ul", "ol", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.parts.append("\n- ")
        elif tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(raw: str) -> str:
    """Convert HTML (possibly entity-escaped, as Greenhouse sends it) to plain text.

    Bullet points become "- " lines, so requirement lists stay one-per-line,
    which the keyword extraction step will rely on.
    """
    if not raw:
        return ""
    # Greenhouse double-encodes: the HTML itself arrives as "&lt;p&gt;...".
    # Unescaping once turns it back into real tags.
    unescaped = html.unescape(raw)
    parser = _TextExtractor()
    parser.feed(unescaped)
    text = "".join(parser.parts).replace("\xa0", " ")
    # Only \n separates lines. Other characters str.splitlines() would break on (U+2028,
    # vertical tab, form feed...) are invisible in a posting, so they become spaces.
    text = _OTHER_BREAKS.sub(" ", text.replace("\r\n", "\n").replace("\r", "\n"))
    lines = (re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n"))
    text = "\n".join(line for line in lines if line and line != "-")
    return text
