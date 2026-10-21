"""Count which skills PM-intern roles ask for.

Reads data/postings.csv (from fetch), merges cross-posted copies into roles,
labels each line required / preferred / other, and matches the skill list.

Usage:
    python -m jd_analyzer.extract

Writes:
    data/roles.csv           one row per role (which postings were merged)
    data/skill_counts.csv    one row per skill
    data/skill_evidence.csv  every match with the line it came from, for auditing
"""

import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path

from jd_analyzer.dedupe import Role, group_roles
from jd_analyzer.fetch import write_csv
from jd_analyzer.models import Posting
from jd_analyzer.sections import OTHER, PREFERRED, REQUIRED, label_lines
from jd_analyzer.skills import SKILLS, Skill

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


@dataclass
class RoleSkills:
    """What one role says about every skill."""

    role: Role
    has_sections: bool = False  # any line labeled required or preferred
    mentioned: set[str] = field(default_factory=set)
    required: set[str] = field(default_factory=set)
    preferred: set[str] = field(default_factory=set)
    evidence: list[dict] = field(default_factory=list)


def analyze_role(role: Role, skills: list[Skill] = SKILLS) -> RoleSkills:
    result = RoleSkills(role)
    for posting in role.postings:
        for label, line in label_lines(posting.description):
            if label != OTHER:
                result.has_sections = True
            for skill in skills:
                m = skill.search(line)
                if not m:
                    continue
                result.mentioned.add(skill.name)
                if label == REQUIRED:
                    result.required.add(skill.name)
                elif label == PREFERRED:
                    result.preferred.add(skill.name)
                result.evidence.append(
                    {"role_id": role.role_id, "skill": skill.name, "label": label,
                     "matched": m.group(0), "line": line[:300]}
                )
    return result


def count_skills(analyzed: list[RoleSkills], skills: list[Skill] = SKILLS) -> list[dict]:
    """One row per skill. Each role counts at most once per column."""
    with_sections = sum(r.has_sections for r in analyzed)
    rows = []
    for skill in skills:
        mentioned = sum(skill.name in r.mentioned for r in analyzed)
        required = sum(skill.name in r.required for r in analyzed)
        # A skill a role both requires and prefers (e.g. two bullets) counts as required.
        preferred = sum(skill.name in r.preferred and skill.name not in r.required for r in analyzed)
        rows.append({
            "skill": skill.name,
            "category": skill.category,
            "roles_mentioning": mentioned,
            "pct_of_roles": _pct(mentioned, len(analyzed)),
            "roles_requiring": required,
            "roles_preferring": preferred,
            "pct_of_roles_with_sections_requiring": _pct(required, with_sections),
        })
    return sorted(rows, key=lambda r: (-r["roles_mentioning"], -r["roles_requiring"], r["skill"]))


def _pct(n: int, total: int) -> int:
    return round(100 * n / total) if total else 0


def read_postings(path: Path) -> list[Posting]:
    with path.open(newline="", encoding="utf-8") as f:
        return [Posting(**row) for row in csv.DictReader(f)]


def main() -> int:
    postings = read_postings(DATA_DIR / "postings.csv")
    roles = group_roles(postings)
    analyzed = [analyze_role(r) for r in roles]
    counts = count_skills(analyzed)
    with_sections = sum(r.has_sections for r in analyzed)

    write_csv(
        [{"role_id": r.role.role_id, "title": r.role.title, "companies": " ".join(r.role.companies),
          "postings": len(r.role.postings), "locations": " | ".join(p.location for p in r.role.postings),
          "has_sections": r.has_sections} for r in analyzed],
        ["role_id", "title", "companies", "postings", "locations", "has_sections"],
        DATA_DIR / "roles.csv",
    )
    write_csv(counts, list(counts[0]), DATA_DIR / "skill_counts.csv")
    write_csv([e for r in analyzed for e in r.evidence], ["role_id", "skill", "label", "matched", "line"],
              DATA_DIR / "skill_evidence.csv")

    print(f"{len(postings)} postings -> {len(roles)} roles after merging cross-posts")
    print(f"{with_sections} of {len(roles)} roles have recognizable required/preferred sections\n")
    print(f"{'skill':42} {'category':11} {'mention':>9} {'required':>9} {'preferred':>9}")
    for r in counts:
        print(f"{r['skill']:42} {r['category']:11} {r['roles_mentioning']:4} {r['pct_of_roles']:3}% "
              f"{r['roles_requiring']:9} {r['roles_preferring']:9}")
    print(f"\nmention = roles mentioning it anywhere (of {len(roles)}); required/preferred = roles listing it "
          f"in that section (of {with_sections} with sections)")
    print("Wrote data/roles.csv, data/skill_counts.csv, data/skill_evidence.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
