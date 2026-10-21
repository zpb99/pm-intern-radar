"""Group cross-posted copies of the same job into one role.

Companies often post one internship once per location (Sezzle: 5 countries) or on
two boards (Duolingo). Counted as-is, those companies would dominate the skill
counts, so postings whose descriptions overlap heavily are merged into a role.

Similarity is the Jaccard overlap of 5-word "shingles" (every run of 5 words).
On the 2026-10-21 data, copies within a company scored 0.45-1.00 and no two
postings from different companies scored above 0.2, so 0.4 sits in that gap.
"""

import re
from dataclasses import dataclass

from jd_analyzer.models import Posting

SHINGLE_WORDS = 5
SAME_ROLE_THRESHOLD = 0.4


@dataclass
class Role:
    role_id: str
    postings: list[Posting]

    @property
    def title(self) -> str:
        return self.postings[0].title

    @property
    def companies(self) -> list[str]:
        return sorted({p.company for p in self.postings})


def shingles(text: str, k: int = SHINGLE_WORDS) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(words[i : i + k]) for i in range(len(words) - k + 1)}


def similarity(a: set, b: set) -> float:
    """Jaccard overlap. Two empty descriptions are NOT similar (0.0)."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def group_roles(postings: list[Posting], threshold: float = SAME_ROLE_THRESHOLD) -> list[Role]:
    """Merge postings into roles. Linking is transitive: if A~B and B~C, all are one role."""
    sets = [shingles(p.description) for p in postings]
    parent = list(range(len(postings)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(postings)):
        for j in range(i + 1, len(postings)):
            if similarity(sets[i], sets[j]) >= threshold:
                parent[root(j)] = root(i)

    groups: dict[int, list[Posting]] = {}
    for i, p in enumerate(postings):
        groups.setdefault(root(i), []).append(p)
    return [
        Role(role_id=f"{ps[0].source}:{ps[0].company}:{ps[0].job_id}", postings=ps)
        for ps in groups.values()
    ]
