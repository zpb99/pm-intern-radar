"""Decide which job titles to track.

The rule lives in roles.toml (see that file). A title is kept when it matches
`title` AND `level`, and does not match `exclude`. Without roles.toml, the
built-in default tracks PM internships.
"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "roles.toml"
_KEYS = {"name", "title", "level", "exclude"}


class RoleConfigError(ValueError):
    """roles.toml is missing a field, has an unknown one, or has a bad regex."""


@dataclass(frozen=True)
class RoleFilter:
    name: str
    title: re.Pattern
    level: re.Pattern | None = None
    exclude: re.Pattern | None = None

    @classmethod
    def from_patterns(cls, name: str, title: str, level: str = "", exclude: str = "") -> "RoleFilter":
        def compile_(key: str, pattern: str) -> re.Pattern | None:
            if not pattern:
                return None
            try:
                return re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                raise RoleConfigError(f"{key} is not a valid regex ({e}): {pattern!r}") from None

        if not title:
            raise RoleConfigError("title pattern is required")
        return cls(name or "matching roles", compile_("title", title), compile_("level", level), compile_("exclude", exclude))

    def matches(self, title: str) -> bool:
        return bool(
            self.title.search(title)
            and (self.level is None or self.level.search(title))
            and not (self.exclude and self.exclude.search(title))
        )


# "Product Manager", "Product Management", "Associate Product Manager" (not "Product
# Marketing Manager" or "Program Manager"), plus the whole word intern/internship/MBA.
# \b = word boundary. Without it, "intern" matches "International".
PM_INTERN = RoleFilter.from_patterns(
    name="PM internships",
    title=r"\bproduct\s+manage(r|ment)\b",
    level=r"\b(intern|interns|internship|mba)\b",
)


def load_role_filter(path: Path = DEFAULT_CONFIG) -> RoleFilter:
    """Read the [filter] table from a roles.toml. A missing file means the PM default."""
    if not path.exists():
        return PM_INTERN
    try:
        config = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise RoleConfigError(f"{path.name} is not valid TOML: {e}") from None
    table = config.get("filter")
    if not isinstance(table, dict):
        raise RoleConfigError(f"{path.name} needs a [filter] table")
    unknown = set(table) - _KEYS
    if unknown:
        raise RoleConfigError(f"{path.name}: unknown key(s) {sorted(unknown)}; allowed: {sorted(_KEYS)}")
    if not all(isinstance(v, str) for v in table.values()):
        raise RoleConfigError(f"{path.name}: every value in [filter] must be a string")
    return RoleFilter.from_patterns(**{k: table.get(k, "") for k in _KEYS})


def is_pm_intern(title: str) -> bool:
    """The built-in PM-internship rule, regardless of roles.toml."""
    return PM_INTERN.matches(title)
