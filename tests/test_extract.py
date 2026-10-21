from jd_analyzer.dedupe import Role
from jd_analyzer.extract import analyze_role, count_skills
from jd_analyzer.models import Posting
from jd_analyzer.skills import Skill

SKILLS = [Skill("SQL", "technical", r"\bsql\b"), Skill("MBA", "background", r"\bmba\b")]


def role(role_id, *descriptions):
    postings = [Posting("greenhouse", "acme", str(i), "PM Intern", "", "", d, "", "") for i, d in enumerate(descriptions)]
    return Role(role_id, postings)


def by_skill(rows):
    return {r["skill"]: r for r in rows}


def test_copies_within_a_role_count_once():
    # Same role posted twice, both mention SQL in requirements: counts as 1 role, not 2.
    text = "Requirements\n- SQL"
    rows = by_skill(count_skills([analyze_role(role("r1", text, text), SKILLS)], SKILLS))
    assert rows["SQL"]["roles_mentioning"] == 1 and rows["SQL"]["roles_requiring"] == 1


def test_required_preferred_and_mentioned_are_separate():
    analyzed = [
        analyze_role(role("r1", "Basic Qualifications\n- SQL\nPreferred Qualifications\n- MBA"), SKILLS),
        analyze_role(role("r2", "You will write SQL every day."), SKILLS),  # no sections at all
    ]
    rows = by_skill(count_skills(analyzed, SKILLS))
    assert rows["SQL"] == {
        "skill": "SQL", "category": "technical", "roles_mentioning": 2, "pct_of_roles": 100,
        "roles_requiring": 1, "roles_preferring": 0, "pct_of_roles_with_sections_requiring": 100,
    }
    assert (rows["MBA"]["roles_requiring"], rows["MBA"]["roles_preferring"]) == (0, 1)


def test_required_wins_over_preferred_in_the_same_role():
    analyzed = [analyze_role(role("r1", "Requirements\n- SQL\nBonus Points\n- Advanced SQL"), SKILLS)]
    rows = by_skill(count_skills(analyzed, SKILLS))
    assert (rows["SQL"]["roles_requiring"], rows["SQL"]["roles_preferring"]) == (1, 0)


def test_evidence_keeps_the_source_line():
    result = analyze_role(role("r1", "Requirements\n- Strong SQL"), SKILLS)
    assert result.evidence == [
        {"role_id": "r1", "skill": "SQL", "label": "required", "matched": "SQL", "line": "- Strong SQL"}
    ]


def test_no_roles_gives_zero_counts_not_a_crash():
    rows = count_skills([], SKILLS)
    assert all(r["roles_mentioning"] == 0 and r["pct_of_roles"] == 0 for r in rows)
