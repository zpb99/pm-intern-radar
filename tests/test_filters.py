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


# --- roles.toml -----------------------------------------------------------------

from jd_analyzer.filters import DEFAULT_CONFIG, PM_INTERN, RoleConfigError, RoleFilter, load_role_filter  # noqa: E402


def test_committed_roles_toml_is_the_pm_default():
    # roles.toml and the built-in default must not drift apart.
    loaded = load_role_filter(DEFAULT_CONFIG)
    assert loaded.title.pattern == PM_INTERN.title.pattern
    assert loaded.level.pattern == PM_INTERN.level.pattern
    assert loaded.exclude is None and loaded.name == "PM internships"


def test_missing_config_means_pm_default(tmp_path):
    assert load_role_filter(tmp_path / "nope.toml") is PM_INTERN


def write(tmp_path, text):
    f = tmp_path / "roles.toml"
    f.write_text(text)
    return f


def test_custom_config_with_exclude_and_no_level(tmp_path):
    f = write(tmp_path, "[filter]\nname = 'PMM'\ntitle = '\\bproduct\\s+marketing\\b'\nexclude = '\\bsenior\\b'\n")
    rule = load_role_filter(f)
    assert rule.matches("Product Marketing Manager")
    assert rule.matches("Product Marketing Intern")  # no level pattern: any level
    assert not rule.matches("Senior Product Marketing Manager")
    assert not rule.matches("Product Manager Intern")


@pytest.mark.parametrize(
    "text, message",
    [
        ("[filter\ntitle = 'x'", "not valid TOML"),
        ("title = 'x'", "needs a \\[filter\\] table"),
        ("[filter]\nlevel = 'intern'", "title pattern is required"),
        ("[filter]\ntitle = ''", "title pattern is required"),
        ("[filter]\ntitle = 'x'\nlevle = 'intern'", "unknown key"),  # typo caught, not ignored
        ("[filter]\ntitle = '(unclosed'", "title is not a valid regex"),
        ("[filter]\ntitle = 'x'\nexclude = '[bad'", "exclude is not a valid regex"),
        ("[filter]\ntitle = 5", "must be a string"),
    ],
)
def test_bad_configs_fail_loudly(tmp_path, text, message):
    with pytest.raises(RoleConfigError, match=message):
        load_role_filter(write(tmp_path, text))


def test_role_filter_requires_title():
    with pytest.raises(RoleConfigError):
        RoleFilter.from_patterns(name="x", title="")
