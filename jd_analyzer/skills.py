"""The skill taxonomy: what to look for in a posting, and how to spot it.

Each skill is a regex (case-insensitive) plus an optional `exclude` regex for
known false positives. Patterns use \\b word boundaries so "ml" doesn't match
"HTML" and "sql" doesn't match "NoSQL". Edit this list freely; tests in
tests/test_skills.py pin the tricky cases.

The list was written from the requirement lines of the 2026-10-21 postings, so
it reflects what these postings say, not a theory of what PMs need.
"""

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    pattern: str
    exclude: str = ""  # phrases whose matches don't count ("code of conduct")
    veto: str = ""  # if the line contains this, nothing in it counts
    _re: re.Pattern = field(init=False, repr=False, compare=False)
    _ex: re.Pattern | None = field(init=False, repr=False, compare=False)
    _veto: re.Pattern | None = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "_re", re.compile(self.pattern, re.I))
        object.__setattr__(self, "_ex", re.compile(self.exclude, re.I) if self.exclude else None)
        object.__setattr__(self, "_veto", re.compile(self.veto, re.I) if self.veto else None)

    def search(self, line: str) -> re.Match | None:
        """First match in the line, ignoring matches inside an excluded phrase."""
        if self._veto and self._veto.search(line):
            return None
        blocked = [m.span() for m in self._ex.finditer(line)] if self._ex else []
        for m in self._re.finditer(line):
            if not any(s <= m.start() < e for s, e in blocked):
                return m
        return None


TECHNICAL, TOOLS, PM_CRAFT, SOFT, BACKGROUND = "technical", "tools", "pm craft", "soft skill", "background"

SKILLS = [
    # Technical
    Skill("SQL", TECHNICAL, r"\bsql\b"),
    Skill("Python", TECHNICAL, r"\bpython\b"),
    Skill("Reads or writes code", TECHNICAL, r"\b(coding|codebase|code|programming)\b", exclude=r"code of (conduct|ethics)|zip code"),
    # A degree list that also accepts business, design, etc. is "any major", not a technical ask.
    Skill("Technical background (CS/engineering only)", TECHNICAL,
          r"computer science|computer engineering|software engineering|electrical engineering|"
          r"technical (background|foundation|fluency|field|degree|concepts)|engineering degree|degree in engineering",
          veto=r"business|psycholog|econom|\bdesign\b|interactive design|finance|information systems|non-technical"),
    Skill("Data analysis", TECHNICAL, r"data analy|analy[sz]\w* data|data[- ]driven|\banalytics\b|dashboards?|quantitative"),
    Skill("A/B testing & experiments", TECHNICAL, r"\ba/b\b|experiment(s|ation|ing)?\b"),
    Skill("Metrics & KPIs", TECHNICAL, r"\bmetrics\b|\bkpis?\b|success measures"),
    Skill("APIs", TECHNICAL, r"\bapis?\b"),
    Skill("Cloud (AWS/Azure/GCP)", TECHNICAL, r"\baws\b|\bazure\b|\bgcp\b|cloud (services|technolog|platform|infrastructure)"),
    Skill("AI / ML (any mention)", TECHNICAL,
          r"\bai\b|\bllms?\b|machine learning|\bml\b|generative ai|\bgenai\b|artificial intelligence",
          exclude=r"\bai operations\b"),  # Gemini's team name
    Skill("Uses AI tools hands-on", TECHNICAL,
          r"\bchatgpt\b|\bclaude\b|\bcursor\b|ai tool(s|ing)|generative ai tools|experiment\w* with (llms|ai)|"
          r"using ai\b|use ai\b|used ai\b|with ai\b|ai to (prototype|analy|build|automate)|fluency in ai|"
          r"(utiliz|leverag)\w* (generative )?ai\b"),
    # Tools
    Skill("Excel / spreadsheets", TOOLS, r"\bexcel\b|google sheets|spreadsheets?"),
    Skill("Jira / Confluence", TOOLS, r"\bjira\b|\bconfluence\b"),
    Skill("Figma", TOOLS, r"\bfigma\b"),
    Skill("Analytics tools (Tableau, Amplitude...)", TOOLS, r"\btableau\b|\bamplitude\b|\bmixpanel\b|google analytics|\blooker\b"),
    Skill("Slides / presentations", TOOLS, r"powerpoint|\bslides\b|presentations?|presenting"),
    # PM craft
    Skill("User research & customer empathy", PM_CRAFT,
          r"user research|ux research|customer (interviews?|research|discovery|feedback)|\bempath|understand\w* (users|customers)|"
          r"user needs|customer needs|talk\w* (to|with) (users|customers)|field research"),
    Skill("Specs, PRDs & user stories", PM_CRAFT,
          r"\bspecs?\b|\bprds?\b|product requirements|requirements doc|user stories|design docs?|gathering requirements"),
    Skill("Roadmaps", PM_CRAFT, r"roadmap"),
    Skill("Prioritization", PM_CRAFT, r"prioriti[sz]"),
    Skill("Go-to-market & launches", PM_CRAFT, r"go[- ]to[- ]market|\bgtm\b|\blaunch(es|ing)?\b"),
    Skill("Competitive & market research", PM_CRAFT, r"competitive (analysis|research|landscape)|market research|competitor"),
    Skill("Product sense", PM_CRAFT, r"product (sense|intuition|instinct|thinking)"),
    Skill("Agile / scrum", PM_CRAFT, r"\bagile\b|\bscrum\b|\bsprints?\b|backlog"),
    Skill("Prototyping", PM_CRAFT, r"prototyp"),
    Skill("Strategy", PM_CRAFT, r"product strategy|\bstrateg(y|ic)\b"),
    # Soft skills
    Skill("Communication", SOFT, r"communicat"),
    Skill("Cross-functional collaboration", SOFT, r"cross[- ]functional|collaborat|work\w* (closely |well )?(with|across) (engineer|design|functions|teams)"),
    Skill("Comfort with ambiguity", SOFT, r"ambigu|uncertainty"),
    Skill("Ownership & bias to action", SOFT,
          r"ownership|bias (for|toward|towards) (action|moving)|self[- ]starter|\binitiative\b|independently|drive (work|results)|deliver results"),
    Skill("Structured / analytical thinking", SOFT, r"problem[- ]solv|structured|analytical|critical thinking|logical reasoning"),
    Skill("Curiosity & growth mindset", SOFT, r"curio|growth mindset|eager to learn|passion for learning|keen learner"),
    Skill("Leadership & influence", SOFT, r"leadership|influence|without (direct )?authority"),
    Skill("Fast-paced environment", SOFT, r"fast[- ](paced|moving)|high[- ]growth|high intensity|speed matters|moving fast"),
    # Background
    Skill("MBA", BACKGROUND, r"\bmba\b"),
    Skill("Bachelor's degree", BACKGROUND, r"bachelor|undergraduate"),
    Skill("Master's / graduate degree", BACKGROUND, r"master.?s\b|graduate degree|advanced degree"),
    Skill("Prior internship or PM experience", BACKGROUND,
          r"\b(prior|previous|hands-on)\b[^.\n]{0,80}\b(experience|internship)\b|product management experience"),
    Skill("Full-time work experience", BACKGROUND,
          r"\d\+? years|years of (professional |work |full-time )?experience|prior professional experience|professional experience"),
    Skill("Consulting background", BACKGROUND, r"consulting|\bmbb\b"),
    Skill("Startup experience", BACKGROUND, r"start-?ups?\b"),
]
