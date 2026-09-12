"""Tests for the terminal symbol and display-cell width contract."""

import pytest

from terminaltexteffects.engine.animation import CharacterVisual, Scene
from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.exceptions import InvalidSymbolError
from terminaltexteffects.utils.geometry import Coord

pytestmark = [pytest.mark.engine, pytest.mark.terminal, pytest.mark.smoke]


def _make_terminal(input_data: str, *, canvas_width: int = -1, wrap_text: bool = True) -> Terminal:
    """Build a terminal without applying the host terminal's dimensions."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    config.canvas_width = canvas_width
    config.wrap_text = wrap_text
    return Terminal(input_data=input_data, config=config)


def _show_input_characters(terminal: Terminal) -> None:
    """Make every retained input character visible."""
    for character in terminal.get_characters():
        terminal.set_character_visibility(character, is_visible=True)


@pytest.mark.parametrize(("symbol", "expected_width"), [("A", 1), ("é", 1), ("界", 2), ("😀", 2)])
def test_character_visual_reports_symbol_cell_width(symbol: str, expected_width: int) -> None:
    """Printable scalar symbols should report their terminal-cell width."""
    assert CharacterVisual(symbol).cell_width == expected_width


@pytest.mark.parametrize("symbol", ["", "AB", "\u0301", "e\u0301", "👩‍💻", "\n"])
def test_character_visual_rejects_unsupported_symbols(symbol: str) -> None:
    """Empty, multi-code-point, and independently unprintable symbols should be rejected."""
    with pytest.raises(InvalidSymbolError) as exc_info:
        CharacterVisual(symbol)

    assert exc_info.value.symbol == symbol


@pytest.mark.parametrize("input_data", ["e\u0301", "👩‍💻"])
def test_terminal_rejects_multi_codepoint_input_graphemes(input_data: str) -> None:
    """Input grapheme clusters should fail when they cannot map to one engine character."""
    with pytest.raises(InvalidSymbolError):
        _make_terminal(input_data)


def test_terminal_lays_out_and_renders_wide_input_symbols() -> None:
    """Wide input symbols should advance two cells without adding a second character."""
    terminal = _make_terminal("A界B")
    _show_input_characters(terminal)

    assert terminal.canvas.width == 4
    assert [(character.input_symbol, character.input_coord.column) for character in terminal.get_characters()] == [
        ("A", 1),
        ("界", 2),
        ("B", 4),
    ]
    assert terminal.canvas.text_right == 4
    wide_character = terminal.get_characters()[1]
    assert terminal.get_character_by_input_coord(Coord(3, 1)) is wide_character
    assert wide_character.neighbors["east"] is terminal.get_characters()[2]
    assert terminal.get_characters()[2].neighbors["west"] is wide_character
    assert terminal._inner_fill_characters == []
    assert terminal.get_formatted_output_string() == "A界B"


def test_terminal_wraps_wide_symbols_without_splitting_them() -> None:
    """A wide symbol that cannot fit at line end should move wholly to the next row."""
    terminal = _make_terminal("A界B", canvas_width=2)
    _show_input_characters(terminal)

    assert [(character.input_symbol, character.input_coord) for character in terminal.get_characters()] == [
        ("A", Coord(1, 3)),
        ("界", Coord(1, 2)),
        ("B", Coord(1, 1)),
    ]
    assert terminal.get_formatted_output_string() == "A \n界\nB "


def test_cursor_overwrite_of_wide_symbol_clears_its_full_footprint() -> None:
    """Writing into either cell of a wide input symbol should remove the whole symbol."""
    terminal = _make_terminal("界\x1b[2GX")
    _show_input_characters(terminal)

    assert terminal.get_formatted_output_string() == " X"


def test_wide_helper_overwrites_both_lower_layer_cells() -> None:
    """A wide higher-layer helper should replace both cells beneath its visual."""
    terminal = _make_terminal("AB", canvas_width=2)
    _show_input_characters(terminal)
    helper = terminal.add_character("界", Coord(1, 1))
    helper.layer = 1
    terminal.set_character_visibility(helper, is_visible=True)

    assert terminal.get_formatted_output_string() == "界"


def test_single_cell_helper_overwrites_entire_lower_layer_wide_symbol() -> None:
    """Overwriting a wide symbol's continuation cell should clear its leading cell."""
    terminal = _make_terminal("界", canvas_width=2)
    _show_input_characters(terminal)
    helper = terminal.add_character("X", Coord(2, 1))
    helper.layer = 1
    terminal.set_character_visibility(helper, is_visible=True)

    assert terminal.get_formatted_output_string() == " X"


@pytest.mark.parametrize("symbol", ["", "AB", "e\u0301", "👩‍💻"])
def test_terminal_add_character_rejects_unsupported_symbols(symbol: str) -> None:
    """Helper characters should enforce the shared symbol contract."""
    terminal = _make_terminal("A")

    with pytest.raises(InvalidSymbolError):
        terminal.add_character(symbol, Coord(1, 1))


@pytest.mark.parametrize("symbol", ["", "AB", "e\u0301", "👩‍💻"])
def test_scene_add_frame_rejects_unsupported_symbols(symbol: str) -> None:
    """Scene frames should enforce the shared symbol contract."""
    scene = Scene("test")

    with pytest.raises(InvalidSymbolError):
        scene.add_frame(symbol, 1)


@pytest.mark.parametrize("symbol", ["", "AB", "e\u0301", "👩‍💻"])
def test_set_appearance_rejects_unsupported_symbols(symbol: str) -> None:
    """Direct visual changes should enforce the shared symbol contract."""
    terminal = _make_terminal("A")
    character = terminal.get_characters()[0]

    with pytest.raises(InvalidSymbolError):
        character.animation.set_appearance(symbol)
