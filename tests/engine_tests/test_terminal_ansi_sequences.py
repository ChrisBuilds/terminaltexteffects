"""Tests for terminal input ANSI/control sequence handling."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pytest

from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.utils.exceptions import UnsupportedAnsiSequenceError
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.graphics import Color

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_character import EffectCharacter

pytestmark = [pytest.mark.engine, pytest.mark.terminal, pytest.mark.smoke]

UNSUPPORTED_CONTROL_CODEPOINTS = tuple(
    codepoint
    for codepoint in (*range(0x20), 0x7F, *range(0x80, 0xA0))
    if codepoint not in (ord("\t"), ord("\n"), ord("\r"))
)


def _make_terminal(
    input_data: str,
    *,
    existing_color_handling: Literal["always", "dynamic", "ignore"] = "ignore",
) -> Terminal:
    """Build a terminal that keeps the parsed input dimensions."""
    config = TerminalConfig._build_config()
    config.ignore_terminal_dimensions = True
    config.existing_color_handling = existing_color_handling
    return Terminal(input_data=input_data, config=config)


def _line_symbols(terminal: Terminal) -> list[str]:
    """Return sparse preprocessed lines expanded to their logical widths."""
    symbols_by_line: list[str] = []
    for line, width in zip(terminal._preprocessed_character_lines, terminal._preprocessed_line_widths):
        symbols = [" "] * width
        for character in line:
            symbols[terminal._preprocessed_character_columns[character]] = character.input_symbol
        symbols_by_line.append("".join(symbols))
    return symbols_by_line


def _characters_in_preprocessed_columns(
    terminal: Terminal,
    row: int,
    columns: range,
) -> list[EffectCharacter]:
    """Return retained characters at zero-based logical columns in a preprocessed row."""
    characters_by_column = {
        terminal._preprocessed_character_columns[character]: character
        for character in terminal._preprocessed_character_lines[row]
    }
    return [characters_by_column[column] for column in columns]


@pytest.mark.parametrize(
    "input_data",
    [
        "abc\x1b[2Jdef",
        "abc\x1b[?1049hdef",
        "abc\x1b]0;title\x07def",
        "abc\x1b7def",
    ],
)
def test_terminal_rejects_unsupported_ansi_sequences(input_data: str) -> None:
    """Unsupported terminal control sequences should fail before character setup."""
    config = TerminalConfig._build_config()

    with pytest.raises(UnsupportedAnsiSequenceError):
        Terminal(input_data=input_data, config=config)


@pytest.mark.parametrize(
    "codepoint",
    [pytest.param(codepoint, id=f"U+{codepoint:04X}") for codepoint in UNSUPPORTED_CONTROL_CODEPOINTS],
)
def test_terminal_rejects_raw_control_characters(codepoint: int) -> None:
    """Raw C0, DEL, and C1 controls should fail before they can become input characters."""
    control = chr(codepoint)

    with pytest.raises(UnsupportedAnsiSequenceError) as exc_info:
        _make_terminal(f"A{control}")

    assert exc_info.value.sequence == control


@pytest.mark.parametrize(
    "input_data",
    [
        pytest.param("\x00\x1b[31mA", id="control-before-sgr"),
        pytest.param("\x1b[31mA\x07", id="control-after-sgr"),
        pytest.param("\x1b[31mA\x1b[0m\x7f", id="control-after-reset"),
        pytest.param("\x1b[31m\x9bA", id="c1-csi-after-sgr"),
    ],
)
def test_terminal_rejects_raw_controls_around_valid_sgr_sequences(input_data: str) -> None:
    """Valid SGR state should not allow adjacent raw control characters into input."""
    with pytest.raises(UnsupportedAnsiSequenceError):
        _make_terminal(input_data)


def test_terminal_preserves_supported_structural_controls() -> None:
    """Tab, newline, and carriage return should retain their deliberate layout behavior."""
    terminal = _make_terminal("A\tB\nC\rD")

    assert _line_symbols(terminal) == ["A   B", "D"]


@pytest.mark.parametrize("sequence", ["\x1b[?25l", "\x1b[?25h", "\x1b[?7l", "\x1b[?7h"])
def test_terminal_ignores_neofetch_private_mode_sequences(sequence: str) -> None:
    """Known neofetch DEC private mode toggles should be accepted as no-op input state."""
    terminal = _make_terminal(f"a{sequence}b")

    assert _line_symbols(terminal) == ["ab"]


def test_terminal_unsupported_private_mode_error_reports_complete_sequence() -> None:
    """Unsupported private mode errors should include the complete CSI sequence."""
    with pytest.raises(UnsupportedAnsiSequenceError) as exc_info:
        _make_terminal("a\x1b[?1049hb")

    assert "\\x1b[?1049h" in str(exc_info.value)


def test_terminal_cursor_horizontal_absolute_overwrites_existing_cells() -> None:
    """CSI G should move to an absolute column and allow later text to overwrite."""
    terminal = _make_terminal("abc\x1b[1GX")

    assert _line_symbols(terminal) == ["Xbc"]


def test_terminal_cursor_sequences_move_cursor_on_virtual_screen() -> None:
    """Common fetch-style cursor sequences should move through the virtual screen."""
    input_data = "A\x1b[3CB\x1b[2DX\x1b[2BY\x1b[1AZ\x1b[3EJ\x1b[2FK\x1b[5Gl\x1b[2;3Hm\x1b[4;2fn"
    terminal = _make_terminal(input_data)

    assert _line_symbols(terminal) == [
        "A  XB",
        "  m  Z",
        "K   l",
        " n",
        "J",
    ]


def test_terminal_cursor_movement_clamps_before_origin() -> None:
    """Cursor movement before row or column zero should clamp to the virtual origin."""
    terminal = _make_terminal("ab\x1b[10D\x1b[10AX")

    assert _line_symbols(terminal) == ["Xb"]


def test_terminal_fetch_style_layout_places_text_next_to_logo() -> None:
    """fastfetch-style cursor movement should produce a side-by-side text grid."""
    input_data = "aa\nbb\ncc\x1b[1G\x1b[2A\x1b[5Ctitle\n\x1b[5Cinfo"
    terminal = _make_terminal(input_data)

    assert _line_symbols(terminal) == [
        "aa   title",
        "bb   info",
        "cc",
    ]


def test_terminal_allows_supported_color_sequences() -> None:
    """Supported 8-bit, 24-bit, and reset SGR color sequences should still parse."""
    input_data = "\x1b[38;2;255;0;0ma\x1b[48;5;106mb\x1b[0mc"

    terminal = _make_terminal(input_data)

    assert [character.input_symbol for character in terminal.get_characters()] == ["a", "b", "c"]


@pytest.mark.parametrize(
    "sequence",
    [
        "\x1b[3m",
        "\x1b[4m",
        "\x1b[31;3m",
        "\x1b[38:2::255:0:0m",
        "\x1b[38;5;256m",
        "\x1b[48;5;256m",
        "\x1b[38;2;300;0;0m",
        "\x1b[48;2;0;256;0m",
        "\x1b[38m",
        "\x1b[38;5m",
        "\x1b[38;2;1;2m",
    ],
)
def test_terminal_rejects_unsupported_or_malformed_sgr_sequences(sequence: str) -> None:
    """Unsupported styles, forms, ranges, and truncated colors should use the terminal parser error."""
    with pytest.raises(UnsupportedAnsiSequenceError) as exc_info:
        _make_terminal(f"{sequence}A")

    assert exc_info.value.sequence == sequence


@pytest.mark.parametrize(
    "sequence",
    [
        "\x1b[2;99A",
        "\x1b[2;99B",
        "\x1b[2;99C",
        "\x1b[2;99D",
        "\x1b[2;99E",
        "\x1b[2;99F",
        "\x1b[2;99G",
        "\x1b[1;2;3H",
        "\x1b[1;2;3f",
    ],
)
def test_terminal_rejects_excess_cursor_parameters(sequence: str) -> None:
    """Cursor commands should reject parameters beyond their defined arity."""
    with pytest.raises(UnsupportedAnsiSequenceError) as exc_info:
        _make_terminal(f"A{sequence}B")

    assert exc_info.value.sequence == sequence


def test_terminal_rejects_overlong_csi_parameter_with_parser_error() -> None:
    """Very long numeric fields should not leak Python integer conversion errors."""
    sequence = f"\x1b[{'9' * 5_000}C"

    with pytest.raises(UnsupportedAnsiSequenceError) as exc_info:
        _make_terminal(sequence)

    assert exc_info.value.sequence == sequence


@pytest.mark.parametrize(
    "sequence",
    [
        "\x1b[100000C",
        "\x1b[100000B",
        "\x1b[100001G",
        "\x1b[1001;1001H",
    ],
)
def test_terminal_rejects_cursor_sequences_that_create_excessive_virtual_screens(sequence: str) -> None:
    """Cursor movement should not be able to create impractically large virtual layouts."""
    with pytest.raises(UnsupportedAnsiSequenceError) as exc_info:
        _make_terminal(sequence)

    assert exc_info.value.sequence == sequence


def test_terminal_allows_large_cursor_movement_that_clamps_to_origin() -> None:
    """Large backward and upward movement should remain safe because it cannot grow the screen."""
    terminal = _make_terminal("AB\x1b[9999999D\x1b[9999999AX")

    assert _line_symbols(terminal) == ["XB"]


@pytest.mark.parametrize(
    ("sequence", "expected_fg", "expected_bg"),
    [
        ("\x1b[30ma", Color(0), None),
        ("\x1b[37ma", Color(7), None),
        ("\x1b[90ma", Color(8), None),
        ("\x1b[97ma", Color(15), None),
        ("\x1b[40ma", None, Color(0)),
        ("\x1b[47ma", None, Color(7)),
        ("\x1b[100ma", None, Color(8)),
        ("\x1b[107ma", None, Color(15)),
        ("\x1b[1;31;44ma", Color(9), Color(4)),
    ],
)
def test_terminal_sgr_3_and_4_bit_colors(
    sequence: str,
    expected_fg: Color | None,
    expected_bg: Color | None,
) -> None:
    """3/4-bit SGR color parameters should map to xterm color indexes."""
    terminal = _make_terminal(sequence)
    character = terminal._preprocessed_character_lines[0][0]

    assert character.animation.input_fg_color == expected_fg
    assert character.animation.input_bg_color == expected_bg


@pytest.mark.parametrize(
    ("input_data", "expected_fg", "expected_bold"),
    [
        ("\x1b[32ma", Color(2), False),
        ("\x1b[1m\x1b[32ma", Color(10), True),
        ("\x1b[32m\x1b[1ma", Color(10), True),
        ("\x1b[1m\x1b[32ma\x1b[22mb", Color(2), False),
        ("\x1b[1m\x1b[32ma\x1b[0mb", None, False),
    ],
)
def test_terminal_sgr_bold_brightens_standard_foreground_colors(
    input_data: str,
    expected_fg: Color | None,
    expected_bold: Literal[True, False],
) -> None:
    """Bold standard foreground SGR colors should resolve to bright xterm colors."""
    terminal = _make_terminal(input_data)
    character = terminal._preprocessed_character_lines[0][-1]

    assert character.animation.input_fg_color == expected_fg
    assert character.animation.input_bold is expected_bold


@pytest.mark.parametrize(
    ("input_data", "expected_fg", "expected_bg"),
    [
        ("\x1b[31;44ma\x1b[mb", None, None),
        ("\x1b[31;44ma\x1b[0mb", None, None),
        ("\x1b[31;44ma\x1b[39mb", None, Color(4)),
        ("\x1b[31;44ma\x1b[49mb", Color(1), None),
    ],
)
def test_terminal_sgr_reset_sequences(
    input_data: str,
    expected_fg: Color | None,
    expected_bg: Color | None,
) -> None:
    """SGR reset parameters should clear the expected input color channels."""
    terminal = _make_terminal(input_data)
    character = terminal._preprocessed_character_lines[0][1]

    assert character.animation.input_fg_color == expected_fg
    assert character.animation.input_bg_color == expected_bg


def test_terminal_fastfetch_style_output_with_swatch_background_colors() -> None:
    """A fastfetch-shaped sequence mix should parse layout and colored swatch spaces."""
    input_data = (
        " .'\n"
        "MMM\x1b[1G\x1b[1A\x1b[5Cuser@host\n"
        "\x1b[5COS: Test\n"
        "\x1b[5C\x1b[40m   \x1b[41m   \x1b[m\n"
        "\x1b[5C\x1b[100m   \x1b[101m   \x1b[m"
    )
    terminal = _make_terminal(input_data, existing_color_handling="always")

    assert _line_symbols(terminal) == [
        " .'  user@host",
        "MMM  OS: Test",
        "           ",
        "           ",
    ]
    swatch_row = _characters_in_preprocessed_columns(terminal, 2, range(5, 11))
    assert [character.animation.input_bg_color for character in swatch_row[:3]] == [Color(0), Color(0), Color(0)]
    assert [character.animation.input_bg_color for character in swatch_row[3:]] == [Color(1), Color(1), Color(1)]
    bright_swatch_row = _characters_in_preprocessed_columns(terminal, 3, range(5, 11))
    assert [character.animation.input_bg_color for character in bright_swatch_row[:3]] == [
        Color(8),
        Color(8),
        Color(8),
    ]
    assert [character.animation.input_bg_color for character in bright_swatch_row[3:]] == [
        Color(9),
        Color(9),
        Color(9),
    ]


def test_terminal_neofetch_style_output_with_private_modes_and_swatch_colors() -> None:
    """A neofetch-shaped sequence mix should ignore private modes and preserve layout/colors."""
    input_data = (
        "\x1b[?25l\x1b[?7l\x1b[0m\x1b[32m\x1b[1mL1\n"
        "\x1b[33mL2\n\x1b[0m"
        "\x1b[1A\x1b[9999999D\x1b[5C\x1b[1m\x1b[32mhost\x1b[0m\n"
        "\x1b[5C\x1b[30m\x1b[40m   \x1b[31m\x1b[41m   \x1b[m\n"
        "\x1b[5C\x1b[38;5;8m\x1b[48;5;8m   \x1b[38;5;9m\x1b[48;5;9m   \x1b[m"
        "\x1b[?25h\x1b[?7h"
    )
    terminal = _make_terminal(input_data, existing_color_handling="always")

    assert _line_symbols(terminal) == [
        "L1",
        "L2   host",
        "           ",
        "           ",
    ]
    assert terminal._preprocessed_character_lines[0][0].animation.input_fg_color == Color(10)
    assert terminal._preprocessed_character_lines[0][0].animation.input_bold is True
    assert terminal._preprocessed_character_lines[1][0].animation.input_fg_color == Color(11)
    assert terminal._preprocessed_character_lines[1][0].animation.input_bold is True
    assert terminal._preprocessed_character_lines[1][5].animation.input_fg_color == Color(10)
    assert terminal._preprocessed_character_lines[1][5].animation.input_bold is True
    standard_swatch_row = _characters_in_preprocessed_columns(terminal, 2, range(5, 11))
    assert [character.animation.input_bg_color for character in standard_swatch_row[:3]] == [
        Color(0),
        Color(0),
        Color(0),
    ]
    assert [character.animation.input_bg_color for character in standard_swatch_row[3:]] == [
        Color(1),
        Color(1),
        Color(1),
    ]
    bright_swatch_row = _characters_in_preprocessed_columns(terminal, 3, range(5, 11))
    assert [character.animation.input_bg_color for character in bright_swatch_row[:3]] == [
        Color(8),
        Color(8),
        Color(8),
    ]
    assert [character.animation.input_bg_color for character in bright_swatch_row[3:]] == [
        Color(9),
        Color(9),
        Color(9),
    ]


def test_terminal_keeps_colored_spaces_as_sparse_input_characters() -> None:
    """Foreground- and background-colored spaces must not become generic fill characters."""
    terminal = _make_terminal("\x1b[31m \x1b[39m \x1b[44m \x1b[0m", existing_color_handling="always")

    assert terminal._preprocessed_line_widths == [3]
    assert len(terminal._preprocessed_character_lines[0]) == 2
    assert [character.input_coord.column for character in terminal.get_characters()] == [1, 3]
    assert terminal.get_characters()[0].animation.input_fg_color == Color(1)
    assert terminal.get_characters()[1].animation.input_bg_color == Color(4)
    assert terminal.get_character_by_input_coord(Coord(2, 1)).is_fill_character is True  # type: ignore[union-attr]


def test_terminal_mixed_layout_style_fixture_preserves_sparse_layout_and_ids() -> None:
    """The mixed cursor/style fixture should retain its layout with only observable input characters."""
    input_path = Path(__file__).parents[1] / "testinput" / "mixed_layout_style_sequence_test.txt"
    terminal = _make_terminal(input_path.read_text(encoding="utf-8"))

    assert (terminal.canvas.width, terminal.canvas.height) == (62, 30)
    assert terminal._preprocessed_line_widths == [
        58,
        58,
        58,
        58,
        58,
        58,
        58,
        0,
        22,
        48,
        39,
        28,
        19,
        0,
        62,
        34,
        0,
        24,
        30,
        29,
        0,
        27,
        61,
        0,
        22,
        34,
        26,
        33,
        0,
        35,
    ]
    assert sum(map(len, terminal._preprocessed_character_lines)) == 687
    assert len(terminal.get_characters()) == 687
    assert terminal._next_character_id == 3100
