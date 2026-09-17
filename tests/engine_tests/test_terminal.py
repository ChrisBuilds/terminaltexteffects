# ruff: noqa: ANN001, D100, D103, E501, ERA001, TC006

from __future__ import annotations

import shutil
import sys
from dataclasses import FrozenInstanceError
from typing import Any, NoReturn, cast

import pytest

from terminaltexteffects.engine.base_character import EffectCharacter
from terminaltexteffects.engine.canvas import Canvas
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.argutils import CharacterGroup, CharacterSort, ColorSort
from terminaltexteffects.utils.exceptions import (
    InvalidCharacterCoordinateError,
    InvalidCharacterError,
    InvalidCharacterGroupError,
    InvalidCharacterSortError,
    InvalidCharacterVisibilityError,
    InvalidColorSortError,
    TerminalOutputActiveError,
    TerminalOutputNotPreparedError,
)
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color, ColorPair

pytestmark = [pytest.mark.engine, pytest.mark.terminal, pytest.mark.smoke]


@pytest.mark.parametrize(
    ("input_data", "expected_coords"),
    [
        pytest.param("X", [Coord(3, 3)], id="single-character"),
        pytest.param("XYZ", [Coord(2, 3), Coord(3, 3), Coord(4, 3)], id="odd-width"),
        pytest.param("X\nY\nZ", [Coord(3, 4), Coord(3, 3), Coord(3, 2)], id="odd-height"),
    ],
)
def test_terminal_center_anchor_odd_text_dimensions(input_data: str, expected_coords: list[Coord]) -> None:
    """Verify center anchoring aligns odd text dimensions to the canvas center."""
    config = TerminalConfig._build_config()
    config.canvas_width = 5
    config.canvas_height = 5
    config.anchor_text = "c"

    terminal = Terminal(input_data, config=config)

    assert [character.input_coord for character in terminal.get_characters()] == expected_coords


def test_terminal_direct_config_uses_defaults() -> None:
    """Verify library callers can pass a directly constructed config to Terminal."""
    terminal = Terminal("A", config=TerminalConfig())

    assert terminal.config == TerminalConfig._build_config()


def test_terminal_config_normalizes_direct_values() -> None:
    """Terminal configuration accepts CLI spellings and native library values."""
    config = TerminalConfig(
        tab_width=cast(Any, "4"),
        terminal_background_color=cast(Any, "#ffffff"),
    )

    assert config.tab_width == 4
    assert config.terminal_background_color == Color("ffffff")


def test_terminal_config_rejects_invalid_tab_width_during_construction() -> None:
    """Invalid tab widths fail at configuration time instead of terminal construction."""
    with pytest.raises(ValueError, match="tab_width"):
        TerminalConfig(tab_width=0)


def test_terminal_init_no_config() -> None:
    terminal = Terminal("test")
    assert terminal.config == TerminalConfig._build_config()


def test_terminal_init_with_config() -> None:
    config = TerminalConfig._build_config()
    config.frame_rate = 10
    terminal = Terminal("test", config=config)
    assert terminal.config.frame_rate == 10


@pytest.mark.parametrize(
    ("field_name", "initial_value", "later_value"),
    [
        ("tab_width", 2, 8),
        ("xterm_colors", True, False),
        ("no_color", True, False),
        ("terminal_background_color", Color("ffffff"), Color("000000")),
        ("existing_color_handling", "dynamic", "ignore"),
        ("wrap_text", True, False),
        ("frame_rate", 30, 0),
        ("canvas_width", 10, 20),
        ("canvas_height", 5, 10),
        ("anchor_canvas", "n", "s"),
        ("anchor_text", "e", "w"),
        ("ignore_terminal_dimensions", True, False),
        ("reuse_canvas", True, False),
        ("no_eol", True, False),
        ("no_restore_cursor", True, False),
    ],
)
def test_terminal_config_is_an_immutable_construction_snapshot(
    field_name: str,
    initial_value: object,
    later_value: object,
) -> None:
    """Every terminal option is copied at construction and immutable afterward."""
    config = TerminalConfig._build_config()
    setattr(config, field_name, initial_value)

    terminal = Terminal("A", config=config)
    setattr(config, field_name, later_value)

    assert terminal.config is not config
    assert getattr(terminal.config, field_name) == initial_value
    with pytest.raises(FrozenInstanceError, match=field_name):
        setattr(terminal.config, field_name, later_value)


@pytest.mark.parametrize("input_data", ["", "   ", "\x1b[0m", "\x1b[31m"])
def test_terminal_init_empty_text_region(input_data: str) -> None:
    """Verify Terminal supports text that produces no visible input characters."""
    terminal = Terminal(input_data)

    assert terminal.get_characters() == []
    assert (terminal.canvas.text_left, terminal.canvas.text_right) == (0, 0)
    assert (terminal.canvas.text_bottom, terminal.canvas.text_top) == (0, 0)
    assert not terminal.canvas.coord_is_in_text(Coord(1, 1))
    assert not terminal.canvas.coord_is_in_text(Coord(0, 0))


def test_terminal_init_fully_clipped_text_region() -> None:
    """Verify Terminal supports input that lies entirely outside a constrained canvas."""
    config = TerminalConfig._build_config()
    config.canvas_width = 1
    terminal = Terminal("   X", config=config)

    assert terminal.get_characters() == []
    assert (terminal.canvas.text_width, terminal.canvas.text_height) == (0, 0)
    assert not terminal.canvas.coord_is_in_text(Coord(0, 0))


@pytest.mark.parametrize("method_name", ["random_column", "random_row", "random_coord"])
@pytest.mark.parametrize(
    ("input_data", "canvas_width"),
    [("   ", -1), ("\x1b[0m", -1), ("   X", 1)],
)
def test_empty_text_boundary_rejects_random_selection(
    method_name: str,
    input_data: str,
    canvas_width: int,
) -> None:
    config = TerminalConfig._build_config()
    config.canvas_width = canvas_width
    terminal = Terminal(input_data, config=config)

    with pytest.raises(ValueError, match="empty text boundary"):
        getattr(terminal.canvas, method_name)(within_text_boundary=True)


def test_terminal_empty_input_uses_minimal_canvas_without_placeholder_text() -> None:
    terminal = Terminal(input_data="")

    assert terminal.get_characters() == []
    assert (terminal.canvas.width, terminal.canvas.height) == (1, 1)
    assert (terminal.canvas.text_width, terminal.canvas.text_height) == (0, 0)


def test_terminal_trims_trailing_unstyled_whitespace_from_geometry() -> None:
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True

    terminal = Terminal("A   \n\n", config=config)

    assert (terminal.canvas.width, terminal.canvas.height) == (1, 1)
    assert [(character.input_symbol, character.input_coord) for character in terminal.get_characters()] == [
        ("A", Coord(1, 1)),
    ]


def test_terminal_preserves_leading_and_internal_unstyled_whitespace() -> None:
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True

    terminal = Terminal(" A B   \n\n", config=config)

    assert (terminal.canvas.width, terminal.canvas.height) == (4, 1)
    assert [(character.input_symbol, character.input_coord) for character in terminal.get_characters()] == [
        ("A", Coord(2, 1)),
        ("B", Coord(4, 1)),
    ]


def test_terminal_preserves_styled_trailing_space() -> None:
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True

    terminal = Terminal("A\x1b[41m ", config=config)

    assert (terminal.canvas.width, terminal.canvas.height) == (2, 1)
    assert [(character.input_symbol, character.input_coord) for character in terminal.get_characters()] == [
        ("A", Coord(1, 1)),
        (" ", Coord(2, 1)),
    ]


def test_terminal_preserves_styled_space_on_trailing_row() -> None:
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True

    terminal = Terminal("A\n\x1b[41m ", config=config)

    assert (terminal.canvas.width, terminal.canvas.height) == (1, 2)
    assert [(character.input_symbol, character.input_coord) for character in terminal.get_characters()] == [
        ("A", Coord(1, 2)),
        (" ", Coord(1, 1)),
    ]


def test_terminal_trims_trailing_cursor_movement_but_preserves_internal_gap() -> None:
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True

    trailing_movement = Terminal("A\x1b[3C", config=config)
    internal_movement = Terminal("A\x1b[3CB", config=config)

    assert (trailing_movement.canvas.width, trailing_movement.canvas.height) == (1, 1)
    assert (internal_movement.canvas.width, internal_movement.canvas.height) == (5, 1)
    assert [(character.input_symbol, character.input_coord) for character in internal_movement.get_characters()] == [
        ("A", Coord(1, 1)),
        ("B", Coord(5, 1)),
    ]


def test_terminal_wrap_and_anchor_use_trimmed_input_geometry() -> None:
    config = TerminalConfig._build_config()
    config.canvas_width = 3
    config.canvas_height = 3
    config.wrap_text = True
    config.anchor_text = "ne"
    config.ignore_terminal_dimensions = True

    terminal = Terminal("AB   \n\n", config=config)

    assert [(character.input_symbol, character.input_coord) for character in terminal.get_characters()] == [
        ("A", Coord(2, 3)),
        ("B", Coord(3, 3)),
    ]


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
    assert test_char_colors.bg is None
    assert test_char_colors.fg == Color("#FF0000")


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
        assert row_offset == 4
    elif anchor in ["nw", "n", "ne"]:
        assert row_offset == 9
    else:
        assert row_offset == 0


def test_terminal_center_canvas_offset_aligns_lower_center_cells(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Terminal, "_get_terminal_dimensions", lambda _: (10, 10))
    config = TerminalConfig._build_config()
    config.canvas_width = 5
    config.canvas_height = 5
    config.anchor_canvas = "c"

    terminal = Terminal(input_data="test", config=config)

    assert terminal.canvas_column_offset == 2
    assert terminal.canvas_row_offset == 2
    assert Coord(
        terminal.canvas.center_column + terminal.canvas_column_offset,
        terminal.canvas.center_row + terminal.canvas_row_offset,
    ) == Coord(5, 5)


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


def test_terminal_wrap_text_ignoring_terminal_dimensions_preserves_all_input() -> None:
    """Ensure automatic height includes all wrapped rows when terminal limits are ignored."""
    config = TerminalConfig._build_config()
    config.canvas_width = 3
    config.wrap_text = True
    config.ignore_terminal_dimensions = True
    terminal = Terminal(input_data="ABCDEF", config=config)

    assert (terminal.canvas.width, terminal.canvas.height) == (3, 2)
    assert "".join(character.input_symbol for character in terminal.get_characters()) == "ABCDEF"
    assert (terminal.canvas.text_width, terminal.canvas.text_height) == (3, 2)


def test_terminal_wrap_text_reuses_wrapped_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify canvas sizing and input setup share one wrapped-row allocation."""
    original_wrap_lines = Terminal._wrap_lines
    wrap_call_count = 0

    def wrapped_lines_spy(
        terminal: Terminal,
        lines: list[list[EffectCharacter]],
        width: int,
    ) -> list[list[EffectCharacter]]:
        nonlocal wrap_call_count
        wrap_call_count += 1
        return original_wrap_lines(terminal, lines, width)

    monkeypatch.setattr(Terminal, "_wrap_lines", wrapped_lines_spy)
    config = TerminalConfig._build_config()
    config.canvas_width = 3
    config.wrap_text = True
    config.ignore_terminal_dimensions = True

    terminal = Terminal(input_data="ABCDEF", config=config)

    assert wrap_call_count == 1
    assert terminal._wrapped_character_lines is not None
    assert len(terminal._wrapped_character_lines) == 2


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
    assert terminal._inner_fill_characters == []

    inner_fill_characters = terminal.get_characters(input_chars=False, inner_fill_chars=True)

    assert len(inner_fill_characters) == 2


def test_terminal_make_outer_fill_characters() -> None:
    config = TerminalConfig._build_config()
    config.canvas_width = 16
    terminal = Terminal(input_data="test test test", config=config)
    assert terminal._outer_fill_characters == []

    outer_fill_characters = terminal.get_characters(input_chars=False, outer_fill_chars=True)

    assert len(outer_fill_characters) == 2


def test_terminal_add_character() -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="test", config=config)
    terminal.add_character("a", Coord(0, 0))
    assert len(terminal.get_characters(added_chars=True)) == 5
    assert len(terminal._added_characters) == 1
    assert terminal._added_characters[0].input_symbol == "a"


@pytest.mark.parametrize("coord", [(1, 1), None, Coord(column=True, row=1), Coord(1, cast(Any, 1.5))])
def test_terminal_add_character_rejects_invalid_coordinates(coord: object) -> None:
    """Added characters require a `Coord` containing actual integer values."""
    terminal = Terminal(input_data="test", config=TerminalConfig._build_config())

    with pytest.raises(InvalidCharacterCoordinateError):
        terminal.add_character("a", coord)  # type: ignore[arg-type]

    assert terminal.get_characters(input_chars=False, added_chars=True) == []


def test_terminal_same_layer_collision_prefers_higher_character_id() -> None:
    """The newer input character should win a same-layer moving-character collision."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    terminal = Terminal(input_data="AB", config=config)
    first_character, second_character = terminal.get_characters()
    first_character.motion.set_coordinate(Coord(1, 1))
    second_character.motion.set_coordinate(Coord(1, 1))
    terminal.set_character_visibility(second_character, is_visible=True)
    terminal.set_character_visibility(first_character, is_visible=True)

    assert second_character.character_id > first_character.character_id
    assert terminal.get_formatted_output_string() == "B "


def test_terminal_same_layer_collision_order_survives_membership_churn() -> None:
    """Removing and restoring visibility should not alter the character-ID painter order."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    terminal = Terminal(input_data="A", config=config)
    input_character = terminal.get_characters()[0]
    helper = terminal.add_character("B", input_character.input_coord)
    terminal.set_character_visibility(helper, is_visible=True)
    terminal.set_character_visibility(input_character, is_visible=True)
    terminal.set_character_visibility(helper, is_visible=False)
    terminal.set_character_visibility(helper, is_visible=True)

    assert helper.character_id > input_character.character_id
    assert terminal.get_formatted_output_string() == "B"


def test_terminal_same_layer_added_character_paints_over_fill_character() -> None:
    """A higher-ID helper should paint over a same-layer fill character."""
    config = TerminalConfig._build_config()
    config.canvas_width = 2
    config.ignore_terminal_dimensions = True
    terminal = Terminal(input_data="A", config=config)
    fill_character = terminal.get_character_by_input_coord(Coord(2, 1))
    assert fill_character is not None
    helper = terminal.add_character("B", Coord(2, 1))
    terminal.set_character_visibility(helper, is_visible=True)
    terminal.set_character_visibility(fill_character, is_visible=True)

    assert helper.character_id > fill_character.character_id
    assert terminal.get_formatted_output_string() == " B"


def test_terminal_layer_precedence_overrides_character_id_order() -> None:
    """A higher layer should win even when its character has the lower ID."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    terminal = Terminal(input_data="A", config=config)
    input_character = terminal.get_characters()[0]
    helper = terminal.add_character("B", input_character.input_coord)
    input_character.layer = 1
    terminal.set_character_visibility(input_character, is_visible=True)
    terminal.set_character_visibility(helper, is_visible=True)

    assert helper.character_id > input_character.character_id
    assert terminal.get_formatted_output_string() == "A"


def test_terminal_direct_layer_change_invalidates_cached_painter_order() -> None:
    """Changing a visible character's layer should reorder the next and subsequent frames."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    terminal = Terminal(input_data="A", config=config)
    input_character = terminal.get_characters()[0]
    helper = terminal.add_character("B", input_character.input_coord)
    input_character.layer = 1
    terminal.set_character_visibility(input_character, is_visible=True)
    terminal.set_character_visibility(helper, is_visible=True)

    assert terminal.get_formatted_output_string() == "A"
    assert terminal._visible_character_order_dirty is False

    helper.layer = 2

    assert terminal._visible_character_order_dirty is True
    assert terminal.get_formatted_output_string() == "B"
    assert terminal.get_formatted_output_string() == "B"


def test_terminal_moved_character_clears_its_previous_rendered_cell() -> None:
    """Sparse row construction should not retain a character's previous frame position."""
    config = TerminalConfig._build_config()
    config.canvas_width = 3
    config.canvas_height = 2
    config.ignore_terminal_dimensions = True
    terminal = Terminal(input_data="A", config=config)
    character = terminal.get_characters()[0]
    terminal.set_character_visibility(character, is_visible=True)

    assert terminal.get_formatted_output_string() == "   \nA  "

    character.motion.set_coordinate(Coord(3, 2))

    assert terminal.get_formatted_output_string() == "  A\n   "


@pytest.mark.parametrize("anchor", ["n", "ne", "e", "se", "s", "sw", "w", "nw", "c"])
def test_terminal_sparse_rendering_preserves_canvas_anchor_offsets(
    anchor: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sparse output should retain exact blank padding for every canvas anchor."""
    monkeypatch.setattr(Terminal, "_get_terminal_dimensions", lambda _: (10, 10))
    config = TerminalConfig._build_config()
    config.canvas_width = 3
    config.canvas_height = 2
    config.anchor_canvas = cast(Any, anchor)
    terminal = Terminal(input_data="A", config=config)
    character = terminal.get_characters()[0]
    terminal.set_character_visibility(character, is_visible=True)
    row = character.motion.current_coord.row + terminal.canvas_row_offset
    column = character.motion.current_coord.column + terminal.canvas_column_offset
    expected_rows = [" " * terminal.visible_right for _ in range(terminal.visible_top)]
    expected_rows[row - 1] = f"{' ' * (column - 1)}A{' ' * (terminal.visible_right - column)}"

    assert terminal.get_formatted_output_string() == "\n".join(expected_rows[::-1])


def test_terminal_sparse_rendering_preserves_ansi_reset_sequences() -> None:
    """Sparse row reuse should retain each visual's complete formatted symbol."""
    terminal = Terminal(input_data="A", config=TerminalConfig._build_config())
    character = terminal.get_characters()[0]
    character.animation.set_appearance(colors=ColorPair(fg=Color("ff0000")))
    terminal.set_character_visibility(character, is_visible=True)

    assert terminal.get_formatted_output_string() == "\x1b[38;2;255;0;0mA\x1b[0m"


def test_terminal_input_character_uses_input_preexisting_colors() -> None:
    config = TerminalConfig._build_config()
    config.existing_color_handling = "always"
    terminal = Terminal(input_data="test", config=config)
    assert terminal.get_characters()[0].uses_input_preexisting_colors is True


def test_terminal_fill_character_does_not_use_input_preexisting_colors() -> None:
    config = TerminalConfig._build_config()
    config.canvas_width = 6
    config.canvas_height = 2
    config.existing_color_handling = "always"
    terminal = Terminal(input_data="abcd\nef gh", config=config)
    fill_characters = terminal.get_characters(input_chars=False, inner_fill_chars=True)

    assert fill_characters[0].uses_input_preexisting_colors is False


def test_terminal_added_character_does_not_use_input_preexisting_colors() -> None:
    config = TerminalConfig._build_config()
    config.existing_color_handling = "always"
    terminal = Terminal(input_data="test", config=config)
    helper = terminal.add_character("a", Coord(0, 0))
    assert helper.uses_input_preexisting_colors is False


@pytest.mark.parametrize(
    "sort",
    [ColorSort.LEAST_TO_MOST, ColorSort.MOST_TO_LEAST, ColorSort.RANDOM],
)
def test_terminal_get_input_colors(sort) -> None:
    config = TerminalConfig._build_config()
    input_data = "\x1b[38;2;255;0;0maaaaaaa\x1b[38;2;0;255;0mb\x1b[48;2;0;0;255mcccc"
    terminal = Terminal(input_data=input_data, config=config)
    colors = terminal.get_input_colors(sort=sort)
    if sort == ColorSort.MOST_TO_LEAST:
        assert colors[0] == Color("#FF0000")
    elif sort == ColorSort.LEAST_TO_MOST:
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
        CharacterSort.BOTTOM_TO_TOP_LEFT_TO_RIGHT,
        CharacterSort.OUTSIDE_ROW_TO_MIDDLE,
        CharacterSort.BOTTOM_TO_TOP_RIGHT_TO_LEFT,
        CharacterSort.MIDDLE_ROW_TO_OUTSIDE,
        CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT,
        CharacterSort.TOP_TO_BOTTOM_RIGHT_TO_LEFT,
        CharacterSort.RANDOM,
    ],
)
def test_terminal_get_characters_with_character_sort(sort) -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcde\nfghij\nklmno", config=config)
    chars = terminal.get_characters(sort=sort)
    if sort == CharacterSort.BOTTOM_TO_TOP_LEFT_TO_RIGHT:
        assert chars[0].input_symbol == "k"
        assert chars[-1].input_symbol == "e"
    elif sort == CharacterSort.OUTSIDE_ROW_TO_MIDDLE:
        assert chars[0].input_symbol == "a"
        assert chars[-1].input_symbol == "j"
    elif sort == CharacterSort.BOTTOM_TO_TOP_RIGHT_TO_LEFT:
        assert chars[0].input_symbol == "o"
        assert chars[-1].input_symbol == "a"
    elif sort == CharacterSort.MIDDLE_ROW_TO_OUTSIDE:
        assert chars[0].input_symbol == "f"
        assert chars[-1].input_symbol == "o"
    elif sort == CharacterSort.TOP_TO_BOTTOM_LEFT_TO_RIGHT:
        assert chars[0].input_symbol == "a"
        assert chars[-1].input_symbol == "o"
    elif sort == CharacterSort.TOP_TO_BOTTOM_RIGHT_TO_LEFT:
        assert chars[0].input_symbol == "e"
        assert chars[-1].input_symbol == "k"
    else:
        assert len(chars) == 15


@pytest.mark.parametrize(
    ("input_data", "sort", "expected_symbols"),
    [
        ("abcde", CharacterSort.OUTSIDE_ROW_TO_MIDDLE, "abcde"),
        ("abcde", CharacterSort.MIDDLE_ROW_TO_OUTSIDE, "abcde"),
        ("abc\ndef\nghi", CharacterSort.OUTSIDE_ROW_TO_MIDDLE, "abcghidef"),
        ("abc\ndef\nghi", CharacterSort.MIDDLE_ROW_TO_OUTSIDE, "defabcghi"),
        ("abc\ndef\nghi\njkl", CharacterSort.OUTSIDE_ROW_TO_MIDDLE, "abcjkldefghi"),
        ("abc\ndef\nghi\njkl", CharacterSort.MIDDLE_ROW_TO_OUTSIDE, "defghiabcjkl"),
    ],
)
def test_terminal_outside_middle_sorts_order_complete_rows(
    input_data: str,
    sort: CharacterSort,
    expected_symbols: str,
) -> None:
    """Outside/middle sorts preserve row contents for odd and even row counts."""
    terminal = Terminal(input_data=input_data, config=TerminalConfig._build_config())

    assert "".join(character.input_symbol for character in terminal.get_characters(sort=sort)) == expected_symbols


def test_terminal_spatial_sort_uses_input_coordinates_after_motion() -> None:
    """Moving a character does not change its position in an input-coordinate sort."""
    terminal = Terminal(input_data="abc\ndef\nghi", config=TerminalConfig._build_config())
    first_character = terminal.get_characters()[0]
    first_character.motion.set_coordinate(Coord(100, 100))

    sorted_characters = terminal.get_characters(sort=CharacterSort.MIDDLE_ROW_TO_OUTSIDE)

    assert "".join(character.input_symbol for character in sorted_characters) == "defabcghi"


def test_terminal_spatial_grouping_uses_input_coordinates_after_motion() -> None:
    """Moving a character does not change its input-coordinate spatial group."""
    terminal = Terminal(input_data="abc\ndef", config=TerminalConfig._build_config())
    first_character = terminal.get_characters()[0]
    first_character.motion.set_coordinate(Coord(100, 100))

    grouped_characters = terminal.get_characters_grouped(CharacterGroup.ROW_TOP_TO_BOTTOM)

    assert [
        "".join(character.input_symbol for character in group) for group in grouped_characters
    ] == ["abc", "def"]


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
    terminal.add_character("a", Coord(1, 1))
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
        CharacterGroup.CENTER_TO_OUTSIDE,
        CharacterGroup.COLUMN_LEFT_TO_RIGHT,
        CharacterGroup.COLUMN_RIGHT_TO_LEFT,
        CharacterGroup.ROW_TOP_TO_BOTTOM,
        CharacterGroup.ROW_BOTTOM_TO_TOP,
        CharacterGroup.OUTSIDE_TO_CENTER,
        CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT,
        CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT,
        CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT,
        CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT,
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
    if grouping == CharacterGroup.CENTER_TO_OUTSIDE:
        assert chars[0][0].input_symbol == "h"
        assert chars[-1][-1].input_symbol == "e"
    elif grouping == CharacterGroup.COLUMN_LEFT_TO_RIGHT:
        assert chars[0][0].input_symbol == "k"
        assert chars[-1][-1].input_symbol == "e"
    elif grouping == CharacterGroup.COLUMN_RIGHT_TO_LEFT:
        assert chars[0][0].input_symbol == "o"
        assert chars[-1][-1].input_symbol == "a"
    elif grouping == CharacterGroup.ROW_TOP_TO_BOTTOM:
        assert chars[0][0].input_symbol == "a"
        assert chars[-1][-1].input_symbol == "o"
    elif grouping == CharacterGroup.ROW_BOTTOM_TO_TOP:
        assert chars[0][0].input_symbol == "k"
        assert chars[-1][-1].input_symbol == "e"
    elif grouping == CharacterGroup.OUTSIDE_TO_CENTER:
        assert chars[0][0].input_symbol == "k"
        assert chars[-1][-1].input_symbol == "h"
    elif grouping == CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT:
        assert chars[0][0].input_symbol == "e"
        assert chars[-1][-1].input_symbol == "k"
    elif grouping == CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT:
        assert chars[0][0].input_symbol == "a"
        assert chars[-1][-1].input_symbol == "o"
    elif grouping == CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT:
        assert chars[0][0].input_symbol == "o"
        assert chars[-1][-1].input_symbol == "a"
    elif grouping == CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT:
        assert chars[0][0].input_symbol == "k"
        assert chars[-1][-1].input_symbol == "e"


@pytest.mark.parametrize(
    ("grouping", "expected_groups"),
    [
        pytest.param(
            CharacterGroup.COLUMN_LEFT_TO_RIGHT,
            [["d", "a"], ["e", "b"], ["f", "c"]],
            id="left-to-right",
        ),
        pytest.param(
            CharacterGroup.COLUMN_RIGHT_TO_LEFT,
            [["f", "c"], ["e", "b"], ["d", "a"]],
            id="right-to-left",
        ),
    ],
)
def test_terminal_get_characters_grouped_columns_preserve_order_and_canvas_bounds(
    grouping: CharacterGroup,
    expected_groups: list[list[str]],
) -> None:
    """Verify column groups retain row order and exclude characters beyond the canvas."""
    config = TerminalConfig._build_config()
    config.canvas_width = 3
    config.canvas_height = 2
    terminal = Terminal(input_data="abc\ndef", config=config)
    terminal.add_character("z", Coord(4, 1))

    groups = terminal.get_characters_grouped(grouping, added_chars=True)

    assert [[character.input_symbol for character in group] for group in groups] == expected_groups


@pytest.mark.parametrize(
    ("grouping", "expected_groups"),
    [
        (CharacterGroup.COLUMN_LEFT_TO_RIGHT, [["d", "a"], ["e", "b"], ["f", "c"]]),
        (CharacterGroup.COLUMN_RIGHT_TO_LEFT, [["f", "c"], ["e", "b"], ["d", "a"]]),
        (CharacterGroup.ROW_TOP_TO_BOTTOM, [["a", "b", "c"], ["d", "e", "f"]]),
        (CharacterGroup.ROW_BOTTOM_TO_TOP, [["d", "e", "f"], ["a", "b", "c"]]),
        (CharacterGroup.DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT, [["d"], ["e", "a"], ["f", "b"], ["c"]]),
        (CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT, [["c"], ["f", "b"], ["e", "a"], ["d"]]),
        (CharacterGroup.DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT, [["a"], ["d", "b"], ["e", "c"], ["f"]]),
        (CharacterGroup.DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT, [["f"], ["e", "c"], ["d", "b"], ["a"]]),
        (CharacterGroup.CENTER_TO_OUTSIDE, [["e"], ["d", "f", "b"], ["a", "c"]]),
        (CharacterGroup.OUTSIDE_TO_CENTER, [["a", "c"], ["d", "f", "b"], ["e"]]),
    ],
)
def test_terminal_get_characters_grouped_preserves_order_with_offset_canvas_bounds(
    grouping: CharacterGroup,
    expected_groups: list[list[str]],
) -> None:
    """Every grouping honors populated keys and ordering when canvas bounds do not start at one."""
    terminal = Terminal(input_data="abc\ndef", config=TerminalConfig._build_config())
    terminal.canvas = Canvas(top=14, right=16, bottom=11, left=12)
    terminal._input_characters = terminal.canvas._anchor_text(terminal._input_characters, "sw")

    groups = terminal.get_characters_grouped(grouping)

    assert [[character.input_symbol for character in group] for group in groups] == expected_groups


@pytest.mark.parametrize("grouping", list(CharacterGroup))
def test_terminal_get_characters_grouped_excludes_off_canvas_added_characters(grouping: CharacterGroup) -> None:
    """Every grouping excludes selected added characters outside the visible canvas."""
    config = TerminalConfig._build_config()
    config.canvas_width = 3
    config.canvas_height = 2
    terminal = Terminal(input_data="abc\ndef", config=config)
    off_canvas_character = terminal.add_character("z", Coord(4, 1))

    groups = terminal.get_characters_grouped(grouping, added_chars=True)

    assert all(character is not off_canvas_character for group in groups for character in group)


def test_terminal_ungrouped_inventory_includes_off_canvas_added_characters() -> None:
    """Ungrouped retrieval retains helpers that spatial grouping intentionally omits."""
    terminal = Terminal(input_data="abc", config=TerminalConfig._build_config())
    off_canvas_character = terminal.add_character("z", Coord(terminal.canvas.right + 1, terminal.canvas.bottom))

    assert off_canvas_character in terminal.get_characters(input_chars=False, added_chars=True)


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


def test_terminal_set_character_visibility_is_idempotent() -> None:
    """Repeated visibility changes keep both visibility indexes consistent."""
    terminal = Terminal(input_data="a", config=TerminalConfig._build_config())
    character = terminal.get_characters()[0]

    terminal.set_character_visibility(character, is_visible=True)
    terminal.set_character_visibility(character, is_visible=True)

    assert terminal._visible_characters == {character}
    assert terminal._visible_characters_by_id == [character]
    assert character.is_visible

    terminal.set_character_visibility(character, is_visible=False)
    terminal.set_character_visibility(character, is_visible=False)

    assert terminal._visible_characters == set()
    assert terminal._visible_characters_by_id == []
    assert not character.is_visible


def test_terminal_set_character_visibility_rejects_foreign_character() -> None:
    """A terminal must not adopt another terminal's character into its render state."""
    terminal = Terminal(input_data="a", config=TerminalConfig._build_config())
    foreign_terminal = Terminal(input_data="b", config=TerminalConfig._build_config())
    foreign_character = foreign_terminal.get_characters()[0]

    with pytest.raises(InvalidCharacterError):
        terminal.set_character_visibility(foreign_character, is_visible=True)

    assert not foreign_character.is_visible
    assert not terminal._visible_characters
    assert not terminal._visible_characters_by_id


def test_terminal_set_character_visibility_rejects_unregistered_character() -> None:
    """Directly constructed characters are not implicitly registered with a terminal."""
    terminal = Terminal(input_data="a", config=TerminalConfig._build_config())
    unregistered_character = EffectCharacter(0, "a", 1, 1)

    with pytest.raises(InvalidCharacterError):
        terminal.set_character_visibility(unregistered_character, is_visible=True)

    assert not unregistered_character.is_visible


@pytest.mark.parametrize("visibility", [1, 0, "yes", None, object()])
def test_terminal_set_character_visibility_rejects_non_boolean_values(visibility: object) -> None:
    """Visibility accepts only booleans, not merely truthy or falsey values."""
    terminal = Terminal(input_data="a", config=TerminalConfig._build_config())
    character = terminal.get_characters()[0]

    with pytest.raises(InvalidCharacterVisibilityError):
        terminal.set_character_visibility(character, visibility)  # type: ignore[arg-type]

    assert not character.is_visible
    assert not terminal._visible_characters
    assert not terminal._visible_characters_by_id


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
    terminal.prep_canvas()
    capsys.readouterr()
    terminal.restore_cursor()
    captured = capsys.readouterr()
    assert captured.out == "\x1b[?25h\n"


def test_terminal_restore_cursor_end_symbol(capsys) -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd\nefgh\nijkl", config=config)
    terminal.prep_canvas()
    capsys.readouterr()
    terminal.restore_cursor(end_symbol="test")
    captured = capsys.readouterr()
    assert captured.out == "\x1b[?25htest"


def test_terminal_restore_cursor_end_symbol_no_eol(capsys) -> None:
    config = TerminalConfig._build_config()
    config.no_eol = True
    terminal = Terminal(input_data="abcd\nefgh\nijkl", config=config)
    terminal.prep_canvas()
    capsys.readouterr()
    terminal.restore_cursor()
    captured = capsys.readouterr()
    assert captured.out == "\x1b[?25h"


def test_terminal_print(capsys) -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd\nefgh\nijkl", config=config)
    terminal.prep_canvas()
    capsys.readouterr()
    terminal.print("abcd\nefgh\nijkl")
    captured = capsys.readouterr()
    assert captured.out == "\x1b8\x1b7\x1b[3Aabcd\nefgh\nijkl"


def test_terminal_move_cursor_to_top(capsys) -> None:
    config = TerminalConfig._build_config()
    terminal = Terminal(input_data="abcd\nefgh\nijkl", config=config)
    terminal.prep_canvas()
    capsys.readouterr()
    terminal.move_cursor_to_top()
    captured = capsys.readouterr()
    assert captured.out == "\x1b8\x1b7\x1b[3A"


@pytest.mark.parametrize("method_name", ["print", "move_cursor_to_top"])
def test_terminal_cursor_output_requires_preparation(method_name: str) -> None:
    """Cursor-relative output cannot consume an unknown terminal-global saved position."""
    terminal = Terminal("A")

    if method_name == "print":
        with pytest.raises(TerminalOutputNotPreparedError, match=method_name):
            terminal.print("A")
    else:
        with pytest.raises(TerminalOutputNotPreparedError, match=method_name):
            terminal.move_cursor_to_top()


def test_terminal_prepare_and_restore_are_idempotent(capsys: pytest.CaptureFixture[str]) -> None:
    """Repeated lifecycle calls emit each setup and cleanup sequence only once."""
    terminal = Terminal("A")

    terminal.prep_canvas()
    terminal.prep_canvas()
    terminal.restore_cursor()
    terminal.restore_cursor()

    assert capsys.readouterr().out == "\x1b[?25l \n\x1b7\x1b[?25h\n"


def test_terminal_can_prepare_again_after_restoration(capsys: pytest.CaptureFixture[str]) -> None:
    """A terminal may start a new lifecycle after completing the previous one."""
    terminal = Terminal("A")

    terminal.prep_canvas()
    terminal.restore_cursor()
    terminal.prep_canvas()
    terminal.restore_cursor()

    lifecycle_output = "\x1b[?25l \n\x1b7\x1b[?25h\n"
    assert capsys.readouterr().out == lifecycle_output * 2


def test_terminal_restore_flushes_without_eol_or_cursor_sequence(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cleanup flushes stdout even when both configurable writes are suppressed."""
    config = TerminalConfig._build_config()
    config.no_eol = True
    config.no_restore_cursor = True
    terminal = Terminal("A", config=config)
    flush_calls = 0

    def track_flush() -> None:
        nonlocal flush_calls
        flush_calls += 1

    terminal.prep_canvas()
    monkeypatch.setattr(sys.stdout, "flush", track_flush)
    terminal.restore_cursor()

    assert flush_calls == 1


def test_terminal_rejects_overlapping_stdout_lifecycles() -> None:
    """Two terminals cannot overwrite the one terminal-global DEC saved cursor position."""
    first_terminal = Terminal("A")
    second_terminal = Terminal("B")

    first_terminal.prep_canvas()
    try:
        with pytest.raises(TerminalOutputActiveError):
            second_terminal.prep_canvas()
    finally:
        first_terminal.restore_cursor()


def test_terminal_preparation_failure_releases_stdout_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """A partial preparation failure does not block later terminal output."""
    terminal = Terminal("A")

    class FailingStdout:
        def write(self, _value: str) -> NoReturn:
            message = "stdout write failed"
            raise OSError(message)

        def flush(self) -> None:
            pass

    with monkeypatch.context() as patch_context:
        patch_context.setattr(sys, "stdout", FailingStdout())
        with pytest.raises(OSError, match="stdout write failed"):
            terminal.prep_canvas()

    assert not terminal._output_prepared
    replacement_terminal = Terminal("B")
    replacement_terminal.prep_canvas()
    replacement_terminal.restore_cursor()
