"""Decide whether a job title is a PM internship."""

import re

# "Product Manager", "Product Management", "Associate Product Manager".
# Does NOT match "Product Marketing Manager" or "Program Manager".
_PM = re.compile(r"\bproduct\s+manage(r|ment)\b", re.IGNORECASE)

# \b = word boundary. Without it, "intern" matches "International".
_INTERN = re.compile(r"\b(intern|interns|internship|mba)\b", re.IGNORECASE)


def is_pm_intern(title: str) -> bool:
    """True if the title is a product-management internship or MBA PM role."""
    return bool(_PM.search(title) and _INTERN.search(title))
