import pytest

from jd_analyzer.boards import Board, parse_board_line, read_boards, write_boards


def test_parse_prefixed_and_bare():
    assert parse_board_line("lever:spotify") == Board("lever", "spotify")
    assert parse_board_line("duolingo") == Board("greenhouse", "duolingo")
    assert parse_board_line("  Ashby : Ramp ") == Board("ashby", "ramp")  # case and spaces


@pytest.mark.parametrize("line", ["workday:uline", "lever:../x", "lever:", "greenhouse:a:b"])
def test_parse_rejects_bad_lines(line):
    with pytest.raises(ValueError):
        parse_board_line(line)


def test_read_boards_skips_comments_and_dedupes(tmp_path):
    f = tmp_path / "b.txt"
    f.write_text("# header\n\ngreenhouse:stripe  # note\nstripe\nlever:spotify\n")
    assert read_boards(f) == [Board("greenhouse", "stripe"), Board("lever", "spotify")]


def test_read_boards_names_the_bad_line(tmp_path):
    f = tmp_path / "b.txt"
    f.write_text("stripe\nlever:../../x\n")
    with pytest.raises(ValueError, match="line 2"):
        read_boards(f)


def test_write_then_read_round_trips(tmp_path):
    boards = [Board("ashby", "ramp"), Board("greenhouse", "figma")]
    write_boards(boards, tmp_path / "out" / "b.txt", header="two lines\nof header")
    assert read_boards(tmp_path / "out" / "b.txt") == boards
