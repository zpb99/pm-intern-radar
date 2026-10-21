import pytest

from jd_analyzer.skills import SKILLS

BY_NAME = {s.name: s for s in SKILLS}


def hits(name, line):
    return BY_NAME[name].search(line) is not None


def test_names_are_unique():
    assert len(BY_NAME) == len(SKILLS)


@pytest.mark.parametrize(
    "name, line",
    [
        ("SQL", "- Experience reviewing/coding with Python and SQL"),
        ("Python", "- Experience reviewing/coding with Python and SQL"),
        ("Reads or writes code", "- you can read a codebase"),
        ("Reads or writes code", "Code of conduct applies. Also comfort reading code."),  # 2nd 'code' counts
        ("Technical background (CS/engineering only)", "Pursuing a degree in Computer Science"),
        ("Uses AI tools hands-on", "- You've used AI tooling for personal productivity"),
        ("Uses AI tools hands-on", "- Utilizes generative AI responsibly"),
        ("Uses AI tools hands-on", "candidates must be comfortable leveraging AI to enhance productivity"),
        ("Data analysis", "- A base-level understanding of data analysis"),
        ("A/B testing & experiments", "requiring data analysis, A/B testing, or metrics"),
        ("Uses AI tools hands-on", "- Fluency with AI tools like Claude Code, Cursor"),
        ("Uses AI tools hands-on", "comfortable using AI tools to prototype"),
        ("AI / ML (any mention)", "Proven fluency in AI and LLMs"),
        ("Excel / spreadsheets", "familiarity with Excel and Powerpoint"),
        ("Slides / presentations", "familiarity with Excel and Powerpoint"),
        ("Specs, PRDs & user stories", "writing user stories, creating product plans"),
        ("Prioritization", "prioritisation frameworks"),  # British spelling
        ("Communication", "Strong written and verbal communication skills"),
        ("Cross-functional collaboration", "You work well across functions"),
        ("Comfort with ambiguity", "ambiguity energizes you"),
        ("MBA", "Currently pursuing an MBA, master's"),
        ("Master's / graduate degree", "Currently pursuing an MBA, master's"),
        ("Prior internship or PM experience", "Prior internship or project experience in product"),
        ("Consulting background", "Bonus: ex-consulting experience (MBB or similar)"),
        ("Full-time work experience", "3+ years of professional experience as a PM"),
        ("Full-time work experience", "pursuing an MBA, with prior professional experience"),
        ("Startup experience", "Hands-on experience from a prior internship, a startup"),
    ],
)
def test_matches(name, line):
    assert hits(name, line)


@pytest.mark.parametrize(
    "name, line",
    [
        ("SQL", "Experience with NoSQL databases"),
        ("Reads or writes code", "Please review our code of conduct."),
        ("Reads or writes code", "Enter your zip code"),
        ("AI / ML (any mention)", "We said it plainly"),  # 'ai' inside a word
        ("AI / ML (any mention)", "Build HTML emails"),  # 'ml' inside a word
        ("APIs", "Rapid growth"),
        ("Uses AI tools hands-on", "We are an AI company"),  # mention, not hands-on use
        ("MBA", "Members of the team"),
        ("Product sense", "This makes sense for the product"),
        ("Leadership & influence", "Our product led growth"),  # "led" is too ambiguous to count
        ("Excel / spreadsheets", "You will excellently communicate"),
        ("Startup experience", "Click start up to begin"),
        ("Bachelor's degree", "Graduate degree holders"),
        ("Full-time work experience", "A 12-week internship experience"),
        # Degree lists that also accept non-technical majors are "any major", not technical asks.
        ("Technical background (CS/engineering only)", "- Bachelor's degree in Engineering, Business, Psychology, Design, Computer Science"),
        ("Technical background (CS/engineering only)", "a variety of technical and non-technical backgrounds"),
        ("AI / ML (any mention)", "you work across engineering, operations, data, and AI operations"),
    ],
)
def test_rejects(name, line):
    assert not hits(name, line)
