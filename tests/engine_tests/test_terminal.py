import shutil
from typing import NoReturn

import pytest

from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.terminal import Canvas, Terminal, TerminalConfig
from terminaltexteffects.utils.exceptions import (
    InvalidCharacterGroupError,
    InvalidCharacterSortError,
    InvalidColorSortError,
)
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color

pytestmark = [pytest.mark.engine, pytest.mark.terminal, pytest.mark.smoke]


def test_canvas_init_even() -> None:
    canvas = Canvas(10, 10)
    assert canvas.width == 10
    assert canvas.height == 10
    assert canvas.center_row == 5
    assert canvas.center_column == 5
    assert canvas.center == Coord(5, 5)


def test_canvas_init_odd() -> None:
    canvas = Canvas(11, 11)
    assert canvas.width == 11
    assert canvas.height == 11
    assert canvas.center_row == 6
    assert canvas.center_column == 6
    assert canvas.center == Coord(6, 6)


def test_canvas_single_col_row() -> None:
    canvas = Canvas(1, 1)
    assert canvas.width == 1
    assert canvas.height == 1
    assert canvas.center_row == 1
    assert canvas.center_column == 1
    assert canvas.center == Coord(1, 1)


@pytest.mark.parametrize("anchor", ["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"])
def test_canvas_anchor_text(anchor) -> None:
    c0 = EffectCharacter(0, symbol="a", input_column=1, input_row=1)
    c1 = EffectCharacter(1, symbol="b", input_column=2, input_row=1)
    canvas = Canvas(10, 10)
    chars = canvas._anchor_text([c0, c1], anchor=anchor)
    if anchor == "sw":
        assert chars[0].motion.current_coord == Coord(1, 1)
    elif anchor == "s":
        assert chars[0].motion.current_coord == Coord(5, 1)
    elif anchor == "se":
        assert chars[1].motion.current_coord == Coord(10, 1)
    elif anchor == "e":
        assert chars[1].motion.current_coord == Coord(10, 6)
    elif anchor == "ne":
        assert chars[1].motion.current_coord == Coord(10, 10)
    elif anchor == "n":
        assert chars[0].motion.current_coord == Coord(5, 10)
    elif anchor == "nw":
        assert chars[0].motion.current_coord == Coord(1, 10)
    elif anchor == "w":
        assert chars[0].motion.current_coord == Coord(1, 6)
    elif anchor == "c":
        assert chars[0].motion.current_coord == Coord(5, 6)
        assert chars[1].motion.current_coord == Coord(6, 6)


def test_canvas_coord_is_in_canvas() -> None:
    canvas = Canvas(10, 10)
    assert canvas.coord_is_in_canvas(Coord(5, 5))
    assert canvas.coord_is_in_canvas(Coord(1, 1))
    assert canvas.coord_is_in_canvas(Coord(10, 10))
    assert canvas.coord_is_in_canvas(Coord(1, 10))
    assert canvas.coord_is_in_canvas(Coord(10, 1))
    assert not canvas.coord_is_in_canvas(Coord(0, 0))
    assert not canvas.coord_is_in_canvas(Coord(11, 11))
    assert not canvas.coord_is_in_canvas(Coord(0, 5))
    assert not canvas.coord_is_in_canvas(Coord(5, 0))
    assert not canvas.coord_is_in_canvas(Coord(11, 5))
    assert not canvas.coord_is_in_canvas(Coord(5, 11))
    assert not canvas.coord_is_in_canvas(Coord(0, 0))
    assert not canvas.coord_is_in_canvas(Coord(11, 11))
    assert not canvas.coord_is_in_canvas(Coord(0, 5))
    assert not canvas.coord_is_in_canvas(Coord(5, 0))
    assert not canvas.coord_is_in_canvas(Coord(11, 5))
    assert not canvas.coord_is_in_canvas(Coord(5, 11))


def test_canvas_random_column() -> None:
    canvas = Canvas(10, 10)
    random_column = canvas.random_column()
    assert 1 <= random_column <= 10


def test_canvas_random_row() -> None:
    canvas = Canvas(10, 10)
    random_row = canvas.random_row()
    assert 1 <= random_row <= 10


def test_canvas_random_coord_inside_canvas() -> None:
    canvas = Canvas(10, 10)
    random_coord = canvas.random_coord()
    assert 1 <= random_coord.column <= 10
    assert 1 <= random_coord.row <= 10


def test_canvas_random_coord_outside_canvas() -> None:
    canvas = Canvas(10, 10)
    random_coord = canvas.random_coord(outside_scope=True)
    if 1 <= random_coord.column <= 10:
        assert random_coord.row in {0, 11}
    elif 1 <= random_coord.row <= 10:
        assert random_coord.column in {0, 11}


def test_terminal_init_no_config() -> None:
    terminal = Terminal("test")
    assert terminal.config == TerminalConfig._build_config()


def test_terminal_init_with_config() -> None:
    config = TerminalConfig._build_config()
    config.frame_rate = 10
    terminal = Terminal("test", config=config)
    assert terminal.config.frame_rate == 10


def test_terminal_init_no_input() -> None:
    terminal = Terminal(input_data="")
    assert len(terminal.get_characters()) == 8


def test_terminal_init_ignore_terminal_dimensions() -> None:
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    terminal = Terminal("test", config=config)
    terminal._terminal_height = 1
    terminal._terminal_width = 4


def test_terminal_preprocess_input_data_existing_color() -> None:
    # test ANSI color string
    # char pos - symbol - fg - bg
    # (1,1) - a - 255,0,0 - 0,0,0
    # (2,1) - b - 0,255,0 - 0,0,0
    # (3,1) - c - 0,255,0 - 0,0,255
    # (4,1) - d - 196 - 0,0,0
    # (5,1) - e - 196 - 106
    # (6,1) - f - 196 - 68
    # (7,1) - g - 0,255,0 - 68

    # \x1b[38;2;255;0;0ma
    # \x1b[38;2;0;255;0mb
    # \x1b[48;2;0;0;255mc
    # \x1b[0m
    # \033[38;5;196md
    # \033[48;5;106me
    # \033[48;5;68mf
    # \x1b[38;2;;255;mg
    # \x1b[0m
    config = TerminalConfig._build_config()
    config.existing_color_handling = "always"
    terminal = Terminal(input_data="", config=config)
    input_data = "\x1b[38;2;255;0;0ma\x1b[38;2;0;255;0mb\x1b[48;2;0;0;255mc\x1b[0m\033[38;5;196md\033[48;5;106me\033[48;5;68mf\x1b[38;2;;255;mg\x1b[0m"
    chars = terminal._preprocess_input_data(input_data)[0]
    assert len(chars) == 7
    assert chars[0].animation.input_bg_color is None
    assert chars[0].animation.input_fg_color == Color("#FF0000")
    assert chars[1].animation.input_bg_color is None
    assert chars[1].animation.input_fg_color == Color("#00FF00")
    assert chars[2].animation.input_bg_color == Color("#0000FF")
    assert chars[2].animation.input_fg_color == Color("#00FF00")
    assert chars[3].animation.input_bg_color is None
    assert chars[3].animation.input_fg_color == Color(196)
    assert chars[4].animation.input_bg_color == Color(106)
    assert chars[4].animation.input_fg_color == Color(196)
    assert chars[5].animation.input_bg_color == Color(68)
    assert chars[5].animation.input_fg_color == Color(196)
    assert chars[6].animation.input_bg_color == Color(68)
    assert chars[6].animation.input_fg_color == Color("#00FF00")
    chars = terminal._preprocess_input_data(input_data)[0]
    test_char_colors = chars[0].animation.current_character_visual.colors
    assert test_char_colors is not None
    assert test_char_colors.bg_color is None
    assert test_char_colors.fg_color == Color("#FF0000")


@pytest.mark.parametrize("anchor", ["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"])
def test_terminal_calc_canvas_offsets(anchor, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Terminal, "_get_terminal_dimensions", lambda _: (10, 10))
    config = TerminalConfig._build_config()
    config.anchor_canvas = anchor
    terminal = Terminal(input_data="test", config=config)
    assert terminal._terminal_height == 10
    assert terminal._terminal_width == 10
    column_offset, row_offset = terminal._calc_canvas_offsets()
    if anchor in ["s", "n", "c"]:
        assert column_offset == 3
    elif anchor in ["se", "e", "ne"]:
        assert column_offset == 6
    else:
        assert column_offset == 0
    if anchor in ["e", "w", "c"]:
        assert row_offset == 5
    elif anchor in ["nw", "n", "ne"]:
        assert row_offset == 9
    else:
        assert row_offset == 0


def test_terminal_get_canvas_dimensions_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Terminal, "_get_terminal_dimensions", lambda _: (10, 10))
    config = TerminalConfig._build_config()
    config.canvas_width = 5
    config.canvas_height = 5
    terminal = Terminal(input_data="test", config=config)
    assert terminal.canvas.width == 5
    assert terminal.canvas.height == 5


def test_terminal_get_canvas_dimensions_match_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Terminal, "_get_terminal_dimensions", lambda _: (10, 10))
    config = TerminalConfig._build_config()
    config.canvas_width = 0
    config.canvas_height = 0
    terminal = Terminal(input_data="test", config=config)
    assert terminal.canvas.width == 10
    assert terminal.canvas.height == 10


def test_terminal_get_canvas_dimensions_match_input_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Terminal, "_get_terminal_dimensions", lambda _: (10, 10))
    config = TerminalConfig._build_config()
    config.canvas_width = -1
    config.canvas_height = -1
    terminal = Terminal(input_data="test", config=config)
    assert terminal.canvas.width == 4
    assert terminal.canvas.height == 1


def test_terminal_get_canvas_dimensions_match_input_text_wrap_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Terminal, "_get_terminal_dimensions", lambda _: (10, 10))
    config = TerminalConfig._build_config()
    config.canvas_width = -1
    config.canvas_height = -1
    config.wrap_text = True
    terminal = Terminal(input_data="testtesttest", config=config)
    assert terminal.canvas.width == 10
    assert terminal.canvas.height == 2


def test_get_terminal_dimensions_raise_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_oserror() -> NoReturn:
        raise OSError

    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="test", config=config)
    old_f = shutil.get_terminal_size
    monkeypatch.setattr(shutil, "get_terminal_size", raise_oserror)
    w, h = terminal._get_terminal_dimensions()
    monkeypatch.setattr(shutil, "get_terminal_size", old_f)  # unpatch to avoid side effects in pytest output
    assert w == 80
    assert h == 24


def test_terminal_get_piped_input_is_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    assert Terminal.get_piped_input() == ""


def test_terminal_get_piped_input_is_not_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("sys.stdin.read", lambda: "test")
    assert Terminal.get_piped_input() == "test"


def test_terminal_wrap_lines() -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="testtesttest", config=config)
    lines = terminal._wrap_lines(terminal._preprocessed_character_lines, 4)
    assert len(lines) == 3


def test_terminal_make_inner_fill_characters() -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="test test test", config=config)
    assert len(terminal._inner_fill_characters) == 2


def test_terminal_make_outer_fill_characters() -> None:
    config = TerminalConfig._build_config()
    config.canvas_width = 16
    terminal = Terminal(input_data="test test test", config=config)
    assert len(terminal._outer_fill_characters) == 2


def test_terminal_add_character() -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="test", config=config)
    terminal.add_character("a", Coord(0, 0))
    assert len(terminal.get_characters(added_chars=True)) == 5
    assert len(terminal._added_characters) == 1
    assert terminal._added_characters[0].input_symbol == "a"


@pytest.mark.parametrize(
    "sort",
    [Terminal.ColorSort.LEAST_TO_MOST, Terminal.ColorSort.MOST_TO_LEAST, Terminal.ColorSort.RANDOM],
)
def test_terminal_get_input_colors(sort) -> None:
    config = TerminalConfig._build_config()
    input_data = "\x1b[38;2;255;0;0maaaaaaa\x1b[38;2;0;255;0mb\x1b[48;2;0;0;255mcccc"
    terminal = Terminal(input_data=input_data, config=config)
    colors = terminal.get_input_colors(sort=sort)
    if sort == Terminal.ColorSort.MOST_TO_LEAST:
        assert colors[0] == Color("#FF0000")
    elif sort == Terminal.ColorSort.LEAST_TO_MOST:
        assert colors[0] == Color("#0000FF")
    else:
        assert len(colors) == 3


def test_terminal_get_input_colors_no_colors() -> None:
    config = TerminalConfig._build_config()
    input_data = "test"
    terminal = Terminal(input_data=input_data, config=config)
    colors = terminal.get_input_colors()
    assert len(colors) == 0


def test_terminal_get_input_colors_invalid_sort() -> None:
    config = TerminalConfig._build_config()
    input_data = "\x1b[38;2;255;0;0maaaaaaa\x1b[38;2;0;255;0mb\x1b[48;2;0;0;255mcccc"
    terminal = Terminal(input_data=input_data, config=config)
    with pytest.raises(InvalidColorSortError):
        terminal.get_input_colors(sort="invalid")  # type: ignore[arg-type] # testing invalid sort


@pytest.mark.parametrize("input_chars", [True, False])
@pytest.mark.parametrize("inner_fill_chars", [True, False])
@pytest.mark.parametrize("outer_fill_chars", [True, False])
@pytest.mark.parametrize("added_chars", [True, False])
def test_terminal_get_characters(input_chars, inner_fill_chars, outer_fill_chars, added_chars) -> None:
    config = TerminalConfig._build_config()
    config.canvas_width = 6
    config.canvas_height = 2
    terminal = Terminal(input_data="abcd\nef gh", config=config)
    terminal.add_character("a", Coord(0, 0))
    chars = terminal.get_characters(
        input_chars=input_chars,
        inner_fill_chars=inner_fill_chars,
        outer_fill_chars=outer_fill_chars,
        added_chars=added_chars,
    )
    expected_chars = 0
    if input_chars:
        expected_chars += 8
    if inner_fill_chars:
        expected_chars += 2
    if outer_fill_chars:
        expected_chars += 2
    if added_chars:
        expected_chars += 1
    assert len(chars) == expected_chars


@pytest.mark.parametrize(
    "sort",
    [
        Terminal.CharacterSort.BOTTOM_TO_TOP_LEFT_TO_RIGHT,
        Terminal.CharacterSort.OUTSIDE_ROW_TO_MIDDLE,
        Terminal.CharacterSort.BOTTOM_TO_TOP_RIGHT_TO_LEFT,
        Terminal.CharacterSort.MIDDLE_ROW_TO_OUTSIDE,
        Terminal.CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT,
        Terminal.CharacterSort.TOP_TO_BOTTOM_RIGHT_TO_LEFT,
        Terminal.CharacterSort.RANDOM,
    ],
)
def test_terminal_get_characters_with_character_sort(sort) -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcde\nfghij\nklmno", config=config)
    chars = terminal.get_characters(sort=sort)
    if sort == Terminal.CharacterSort.BOTTOM_TO_TOP_LEFT_TO_RIGHT:
        assert chars[0].input_symbol == "k"
        assert chars[-1].input_symbol == "e"
    elif sort == Terminal.CharacterSort.OUTSIDE_ROW_TO_MIDDLE:
        assert chars[0].input_symbol == "a"
        assert chars[-1].input_symbol == "h"
    elif sort == Terminal.CharacterSort.BOTTOM_TO_TOP_RIGHT_TO_LEFT:
        assert chars[0].input_symbol == "o"
        assert chars[-1].input_symbol == "a"
    elif sort == Terminal.CharacterSort.MIDDLE_ROW_TO_OUTSIDE:
        assert chars[0].input_symbol == "h"
        assert chars[-1].input_symbol == "a"
    elif sort == Terminal.CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT:
        assert chars[0].input_symbol == "a"
        assert chars[-1].input_symbol == "o"
    elif sort == Terminal.CharacterSort.TOP_TO_BOTTOM_RIGHT_TO_LEFT:
        assert chars[0].input_symbol == "e"
        assert chars[-1].input_symbol == "k"
    else:
        assert len(chars) == 15


def test_terminal_get_characters_invalid_character_sort() -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcde\nfghij\nklmno", config=config)
    with pytest.raises(InvalidCharacterSortError):
        terminal.get_characters(sort="invalid")  # type: ignore[arg-type] # testing invalid sort


@pytest.mark.parametrize("input_chars", [True, False])
@pytest.mark.parametrize("inner_fill_chars", [True, False])
@pytest.mark.parametrize("outer_fill_chars", [True, False])
@pytest.mark.parametrize("added_chars", [True, False])
def test_terminal_get_characters_grouped(input_chars, inner_fill_chars, outer_fill_chars, added_chars) -> None:
    config = TerminalConfig._build_config()
    config.canvas_width = 7
    terminal = Terminal(input_data="abcde\nfg hij\nklmno", config=config)
    terminal.add_character("a", Coord(0, 0))
    chars = terminal.get_characters_grouped(
        input_chars=input_chars,
        inner_fill_chars=inner_fill_chars,
        outer_fill_chars=outer_fill_chars,
        added_chars=added_chars,
    )
    expected_string = ""
    for group in chars:
        expected_string += "".join([char.input_symbol for char in group])
    expected_string_length = 0
    if input_chars:
        expected_string_length += 15
    if inner_fill_chars:
        expected_string_length += 3
    if outer_fill_chars:
        expected_string_length += 3
    if added_chars:
        expected_string_length += 1
    assert len(expected_string) == expected_string_length


@pytest.mark.parametrize(
    "grouping",
    [
        Terminal.CharacterGroup.CENTER_TO_OUTSIDE_DIAMONDS,
        Terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT,
        Terminal.CharacterGroup.COLUMN_RIGHT_TO_LEFT,
        Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM,
        Terminal.CharacterGroup.ROW_BOTTOM_TO_TOP,
        Terminal.CharacterGroup.OUTSIDE_TO_CENTER_DIAMONDS,
        Terminal.CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT,
        Terminal.CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT,
        Terminal.CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT,
        Terminal.CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT,
    ],
)
def test_terminal_get_characters_grouped_with_grouping(grouping) -> None:
    # test data:
    # abcde
    # fghij
    # klmno
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcde\nfghij\nklmno", config=config)
    terminal.add_character("a", Coord(0, 0))
    chars = terminal.get_characters_grouped(grouping=grouping)
    if grouping == Terminal.CharacterGroup.CENTER_TO_OUTSIDE_DIAMONDS:
        assert chars[0][0].input_symbol == "h"
        assert chars[-1][-1].input_symbol == "e"
    elif grouping == Terminal.CharacterGroup.COLUMN_LEFT_TO_RIGHT:
        assert chars[0][0].input_symbol == "k"
        assert chars[-1][-1].input_symbol == "e"
    elif grouping == Terminal.CharacterGroup.COLUMN_RIGHT_TO_LEFT:
        assert chars[0][0].input_symbol == "o"
        assert chars[-1][-1].input_symbol == "a"
    elif grouping == Terminal.CharacterGroup.ROW_TOP_TO_BOTTOM:
        assert chars[0][0].input_symbol == "a"
        assert chars[-1][-1].input_symbol == "o"
    elif grouping == Terminal.CharacterGroup.ROW_BOTTOM_TO_TOP:
        assert chars[0][0].input_symbol == "k"
        assert chars[-1][-1].input_symbol == "e"
    elif grouping == Terminal.CharacterGroup.OUTSIDE_TO_CENTER_DIAMONDS:
        assert chars[0][0].input_symbol == "k"
        assert chars[-1][-1].input_symbol == "h"
    elif grouping == Terminal.CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT:
        assert chars[0][0].input_symbol == "e"
        assert chars[-1][-1].input_symbol == "k"
    elif grouping == Terminal.CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT:
        assert chars[0][0].input_symbol == "a"
        assert chars[-1][-1].input_symbol == "o"
    elif grouping == Terminal.CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT:
        assert chars[0][0].input_symbol == "o"
        assert chars[-1][-1].input_symbol == "a"
    elif grouping == Terminal.CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT:
        assert chars[0][0].input_symbol == "k"
        assert chars[-1][-1].input_symbol == "e"


def test_terminal_get_characters_grouped_invalid_grouping() -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcde\nfghij\nklmno", config=config)
    with pytest.raises(InvalidCharacterGroupError):
        terminal.get_characters_grouped(grouping="invalid")  # type: ignore[arg-type] # testing invalid group


def test_terminal_get_character_by_input_coord_valid() -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd", config=config)
    char = terminal.get_character_by_input_coord(Coord(1, 1))
    assert char is not None
    assert char.input_symbol == "a"


def test_terminal_get_character_by_input_coord_invalid() -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd", config=config)
    char = terminal.get_character_by_input_coord(Coord(1, 2))
    assert char is None


@pytest.mark.parametrize("visiblity", [True, False])
def test_terminal_set_character_visibility(visiblity) -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd", config=config)
    assert len(terminal._visible_characters) == 0
    c = terminal.get_character_by_input_coord(Coord(1, 1))
    terminal.set_character_visibility(c, visiblity)  # type: ignore[arg-type]
    if visiblity:
        assert len(terminal._visible_characters) == 1
    else:
        assert len(terminal._visible_characters) == 0


def test_terminal_get_formatted_output_string() -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd", config=config)
    output_string = terminal.get_formatted_output_string()
    assert output_string == "    "
    terminal.set_character_visibility(terminal.get_character_by_input_coord(Coord(1, 1)), is_visible=True)  # type: ignore[arg-type]
    output_string = terminal.get_formatted_output_string()
    assert output_string == "a   "


def test_terminal_update_terminal_state() -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd", config=config)
    terminal._update_terminal_state()
    assert terminal.terminal_state == ["    "]
    terminal.set_character_visibility(terminal.get_character_by_input_coord(Coord(1, 1)), is_visible=True)  # type: ignore[arg-type]
    terminal._update_terminal_state()
    assert terminal.terminal_state == ["a   "]


def test_terminal_prep_canvas(capsys) -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd\nefgh\nijkl", config=config)
    terminal.prep_canvas()
    captured = capsys.readouterr()
    assert captured.out == "\x1b[?25l    \n    \n    \n\x1b7"


def test_terminal_restore_cursor(capsys) -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd\nefgh\nijkl", config=config)
    terminal.restore_cursor()
    captured = capsys.readouterr()
    assert captured.out == "\x1b[?25h\n"


def test_terminal_restore_cursor_end_symbol(capsys) -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd\nefgh\nijkl", config=config)
    terminal.restore_cursor(end_symbol="test")
    captured = capsys.readouterr()
    assert captured.out == "\x1b[?25htest"


def test_terminal_restore_cursor_end_symbol_no_eol(capsys) -> None:
    config = TerminalConfig._build_config()
    config.no_eol = True
    terminal = Terminal(input_data="abcd\nefgh\nijkl", config=config)
    terminal.restore_cursor()
    captured = capsys.readouterr()
    assert captured.out == "\x1b[?25h"


def test_terminal_print(capsys) -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd\nefgh\nijkl", config=config)
    terminal.print("abcd\nefgh\nijkl")
    captured = capsys.readouterr()
    assert captured.out == "\x1b8\x1b7\x1b[3Aabcd\nefgh\nijkl"


def test_terminal_move_cursor_to_top(capsys) -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd\nefgh\nijkl", config=config)
    terminal.move_cursor_to_top()
    captured = capsys.readouterr()
    assert captured.out == "\x1b8\x1b7\x1b[3A"
