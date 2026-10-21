from jd_analyzer.sections import OTHER, PREFERRED, REQUIRED, label_lines


def labels(text):
    return [(label, line) for label, line in label_lines(text)]


def test_required_then_preferred_then_boilerplate():
    text = "\n".join(
        [
            "About Acme",
            "We build things.",
            "Basic Qualifications",
            "- SQL",
            "- Strong communication",
            "Preferred Qualifications",
            "- MBA",
            "The pay for this role is $50/hour. We are an equal opportunity employer.",
        ]
    )
    assert labels(text) == [
        (OTHER, "About Acme"),
        (OTHER, "We build things."),
        (OTHER, "Basic Qualifications"),
        (REQUIRED, "- SQL"),
        (REQUIRED, "- Strong communication"),
        (OTHER, "Preferred Qualifications"),
        (PREFERRED, "- MBA"),
        (OTHER, "The pay for this role is $50/hour. We are an equal opportunity employer."),
    ]


def test_inline_bonus_and_a_plus_downgrade_to_preferred():
    text = "Who You Are\n- Curious\n- Bonus: consulting experience\n- Healthcare is a plus but not required"
    assert [lab for lab, _ in label_lines(text)] == [OTHER, REQUIRED, PREFERRED, PREFERRED]


def test_section_without_bullets_keeps_its_lines():
    # Some boards list requirements as plain sentences, no "- " bullets.
    text = "Qualifications\nPursuing a degree in Computer Science.\nStrong written communication."
    assert [lab for lab, _ in label_lines(text)] == [OTHER, REQUIRED, REQUIRED]


def test_unrecognized_heading_ends_the_section():
    text = "Requirements\n- SQL\nWhat You'll Do\n- Write specs"
    assert [lab for lab, _ in label_lines(text)] == [OTHER, REQUIRED, OTHER, OTHER]


def test_no_headings_means_nothing_is_required():
    text = "We want someone great.\n- Knows SQL\n- Ships fast"
    assert {lab for lab, _ in label_lines(text)} == {OTHER}


def test_bullets_before_any_heading_are_other():
    assert label_lines("- SQL") == [(OTHER, "- SQL")]


import pytest  # noqa: E402


@pytest.mark.parametrize(
    "heading",
    [
        "What we look for:",  # Databricks, Sezzle
        "You Are:",  # Roblox
        "WHAT YOU NEED:",
        "Essentials to Succeed",  # ShopBack
        "You…",  # GoFundMe
        "✅ You have...",  # Duolingo: ends in an ellipsis, not a sentence period
        "Who You Are:",
        "Required Skills and Experience:",
    ],
)
def test_real_requirement_headings(heading):
    assert label_lines(f"{heading}\n- SQL")[1] == (REQUIRED, "- SQL")


@pytest.mark.parametrize("heading", ["You Will:", "What You'll Do:", "🧠 You will...", "About Datadog:"])
def test_real_non_requirement_headings(heading):
    assert label_lines(f"{heading}\n- SQL")[1][0] == OTHER


def test_empty():
    assert label_lines("") == []
