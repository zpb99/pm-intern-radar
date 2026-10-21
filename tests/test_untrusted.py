import pytest

from jd_analyzer.untrusted import clean_text, safe_url


@pytest.mark.parametrize(
    "raw, clean",
    [
        ("plain text", "plain text"),
        ("tab\there", "tab here"),
        ("zero​width", "zero width"),
        ("right‮to-left override", "right to-left override"),
        ("isolate⁦x⁩", "isolate x"),
        ("line separator", "line separator"),
        ("para separator", "para separator"),
        ("bom﻿here", "bom here"),
        ("c1\x85control", "c1 control"),
        ("  padded  ", "padded"),
        ("café — résumé", "café — résumé"),  # visible Unicode kept
        ("", ""),
    ],
)
def test_clean_text(raw, clean):
    assert clean_text(raw) == clean


@pytest.mark.parametrize(
    "url, ok",
    [
        ("https://jobs.ashbyhq.com/acme/1", True),
        ("http://x.com/a?b=c&d=e#f", True),
        ("javascript:alert(1)", False),
        ("JAVASCRIPT:alert(1)", False),
        ("data:text/html,hi", False),
        ("ftp://x.com/a", False),
        ("https://", False),
        ("https://x.com/a b", False),
        ("https://x.com/\x01", False),
        ("https://x.com/‮", False),
        ("https://x.com/(a)", False),
        ("", False),
    ],
)
def test_safe_url(url, ok):
    assert (safe_url(url) == url) if ok else (safe_url(url) is None)
