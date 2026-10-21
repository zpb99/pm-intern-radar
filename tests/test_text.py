from jd_analyzer.text import html_to_text


def test_unescapes_greenhouse_double_encoded_html():
    raw = "&lt;p&gt;Hello &amp;amp; welcome&lt;/p&gt;"
    assert html_to_text(raw) == "Hello & welcome"


def test_list_items_become_dash_lines():
    raw = "<p>You have:</p><ul><li>SQL</li><li>3+ years&nbsp;experience</li></ul>"
    assert html_to_text(raw) == "You have:\n- SQL\n- 3+ years experience"


def test_empty_and_none_like_input():
    assert html_to_text("") == ""
    assert html_to_text("<div>  </div>") == ""


def test_inline_tags_do_not_split_lines():
    assert html_to_text("<p>Strong <strong>SQL</strong> skills</p>") == "Strong SQL skills"


def test_hidden_separators_become_spaces_not_line_breaks():
    assert html_to_text("<p>one two three\x0bfour</p>") == "one two three four"


def test_windows_line_endings():
    assert html_to_text("<p>a</p>\r\n<p>b</p>") == "a\nb"
