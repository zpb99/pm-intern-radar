from jd_analyzer.dedupe import group_roles, shingles, similarity
from jd_analyzer.models import Posting

BASE = " ".join(f"word{i}" for i in range(100))  # 100 distinct words


def posting(job_id, description, company="acme"):
    return Posting("greenhouse", company, job_id, "PM Intern", "", "", description, "", "")


def test_identical_copies_merge():
    roles = group_roles([posting("1", BASE), posting("2", BASE), posting("3", BASE)])
    assert len(roles) == 1 and len(roles[0].postings) == 3


def test_unrelated_postings_stay_separate():
    other = " ".join(f"other{i}" for i in range(100))
    assert len(group_roles([posting("1", BASE), posting("2", other, "zeta")])) == 2


def test_linking_is_transitive():
    words = BASE.split()
    a = " ".join(words[:60])
    b = " ".join(words[20:80])  # overlaps a and c, each ~50%
    c = " ".join(words[40:100])  # barely overlaps a
    assert similarity(shingles(a), shingles(c)) < 0.4
    roles = group_roles([posting("1", a), posting("2", b), posting("3", c)])
    assert len(roles) == 1


def test_threshold_boundary():
    words = BASE.split()
    a, b = posting("1", BASE), posting("2", " ".join(words[:50] + [f"new{i}" for i in range(50)]))
    score = similarity(shingles(a.description), shingles(b.description))
    assert len(group_roles([a, b], threshold=score)) == 1  # >= threshold merges
    assert len(group_roles([a, b], threshold=score + 0.01)) == 2


def test_empty_or_tiny_descriptions_never_merge():
    roles = group_roles([posting("1", ""), posting("2", ""), posting("3", "too short")])
    assert len(roles) == 3


def test_role_id_and_companies():
    roles = group_roles([posting("7", BASE, "duolingo"), posting("9", BASE, "duolingounirecruitment")])
    assert roles[0].role_id == "greenhouse:duolingo:7"
    assert roles[0].companies == ["duolingo", "duolingounirecruitment"]


def test_no_postings():
    assert group_roles([]) == []
