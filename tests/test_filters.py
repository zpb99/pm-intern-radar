import pytest

from jd_analyzer.filters import is_pm_intern


@pytest.mark.parametrize(
    "title",
    [
        "Product Manager, MBA Intern",
        "Product Management Intern (2027) - Amsterdam",
        "[Summer 2027] Product Management Intern",
        "Associate Product Manager Intern",
        "MBA Product Manager Internship",
        "product  manager intern",  # odd spacing and case
    ],
)
def test_matches_pm_internships(title):
    assert is_pm_intern(title)


@pytest.mark.parametrize(
    "title",
    [
        "Product Manager | International",  # "intern" inside "International"
        "Senior Product Manager, Internal Tools",  # "intern" inside "Internal"
        "Product Manager",  # full-time, no intern marker
        "Associate Product Manager, New Grad (2027 Start)",  # early career, not intern
        "Product Marketing Manager Intern",  # marketing, not PM
        "Technical Program Manager Intern",  # program, not product
        "Software Engineering Intern",
        "Product Design Intern",
        "",
    ],
)
def test_rejects_non_pm_or_non_intern(title):
    assert not is_pm_intern(title)
