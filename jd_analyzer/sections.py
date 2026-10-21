"""Label each line of a description as required, preferred, or other.

Postings put requirements under headings like "Basic Qualifications", "About You"
or "Who You Are", and nice-to-haves under "Preferred Qualifications" or "Bonus
Points". Everything else (company intro, responsibilities, pay, EEO notice) is
"other". This is a heuristic: postings without recognizable headings get no
required/preferred lines, and the extract report says how many roles that is.
"""

import re

REQUIRED, PREFERRED, OTHER = "required", "preferred", "other"

_PREFERRED_HEADING = re.compile(r"prefer|bonus|nice[- ]to[- ]have|\ba plus\b|plus,|not required", re.I)
_REQUIRED_HEADING = re.compile(
    r"qualif|requirement|required|you have|you.ll need|you need|you bring|look(ing)? for|about you|"
    r"you are\b|let.s connect|skills and experience|you might be a fit|what it takes|essentials|"
    r"^\W*you\W*$",  # GoFundMe's bare "You…"
    re.I,
)
# A single bullet can downgrade itself: "- Bonus: consulting experience",
# "- Healthcare experience is a plus but not required".
_PREFERRED_ITEM = re.compile(r"^(bonus|nice to have|preferred)\b|\ba plus\b|not required|\bpreferred\b", re.I)


def _is_heading(line: str) -> bool:
    end = line.rstrip()
    ends_sentence = end.endswith(".") and not end.endswith("...")  # "✅ You have..." is a heading
    return not line.startswith("- ") and len(line) < 80 and not ends_sentence


def label_lines(description: str) -> list[tuple[str, str]]:
    """Return (label, line) for every non-empty line, in order."""
    out = []
    section, saw_bullet = OTHER, False
    # Split on \n only: str.splitlines() also breaks on invisible separators (U+2028...),
    # which a posting could use to push text out of its requirements section.
    for line in description.split("\n"):
        line = line.strip()
        if not line:
            continue
        if _is_heading(line):
            if _PREFERRED_HEADING.search(line):
                section = PREFERRED
            elif _REQUIRED_HEADING.search(line):
                section = REQUIRED
            else:
                section = OTHER
            saw_bullet = False
            out.append((OTHER, line))  # the heading itself isn't a requirement
            continue
        if section != OTHER and not line.startswith("- ") and saw_bullet:
            # A prose paragraph after the bullets is the pay/EEO boilerplate, not
            # another requirement. (Sections with no bullets at all keep their prose.)
            section = OTHER
        saw_bullet = saw_bullet or line.startswith("- ")
        label = section
        if label == REQUIRED and _PREFERRED_ITEM.search(line.removeprefix("- ")):
            label = PREFERRED
        out.append((label, line))
    return out
